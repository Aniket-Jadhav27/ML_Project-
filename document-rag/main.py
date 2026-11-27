import os
from pathlib import Path
import sys
from typing import Optional

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

from rule_based_extractor import RuleBasedExtractor, ExtractedPageStructure

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CHROMA_PATH = BASE_DIR / "chroma_db"
DATA_DIR = BASE_DIR / "data"

EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-3.5-flash-lite")
FALLBACK_LLM_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite,gemini-3.8-flash").split(",")
    if m.strip()
]

_genai_client: Optional[genai.Client] = None


def get_genai_client() -> genai.Client:
    """Lazily initialize the Gemini API client using GEMINI_API_KEY."""
    global _genai_client
    if _genai_client is None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in environment or document-rag/.env")
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client


def generate_rag_answer(context: str, question: str) -> str:
    """Generate an answer using Gemini with automatic fallback on transient 503/429 errors."""
    system_instruction = (
        "Answer using only the supplied document excerpts. "
        "When answering questions about tables, identify the exact row, column, and cell value coordinates if applicable. "
        "Do not invent facts. If the evidence is insufficient, say so. "
        "Cite supporting chunk IDs, table IDs, and page numbers."
    )
    prompt = f"DOCUMENT EXCERPTS:\n{context}\n\nQUESTION: {question}"
    models_to_try = [LLM_MODEL] + [m for m in FALLBACK_LLM_MODELS if m != LLM_MODEL]
    last_error: Optional[Exception] = None

    for model_name in models_to_try:
        try:
            interaction = get_genai_client().interactions.create(
                model=model_name,
                input=prompt,
                system_instruction=system_instruction,
                generation_config={"temperature": 0},
                store=False,
            )
            return interaction.output_text or ""
        except Exception as exc:
            last_error = exc
            err_str = str(exc).lower()
            if any(code in err_str for code in ("503", "429", "service_unavailable", "high demand", "resource_exhausted")):
                continue
            raise

    raise RuntimeError(f"All Gemini models failed: {last_error}")


client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(
    name="document_qa",
    metadata={"hnsw:space": "cosine"},
)

extractor = RuleBasedExtractor()


def extract_text_from_file(file_path: Path):
    """Extract structured document elements using RuleBasedExtractor."""
    content_bytes = file_path.read_bytes()
    return extractor.extract_document(content_bytes, file_path.name)


def chunk_document(pages_struct):
    """Chunk extracted document while preserving tables, cell coordinates, and headers."""
    return extractor.chunk_structured_document(pages_struct)


def embed(texts):
    if not texts:
        return []
    result = get_genai_client().models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    return [emb.values for emb in result.embeddings]


def resolve_document_path(target_path=None) -> Path | None:
    """Find the document to index from a provided path or the data/ directory."""
    if target_path:
        p = Path(target_path)
        if not p.is_absolute():
            candidate = BASE_DIR / p
            if candidate.exists():
                return candidate
        return p if p.exists() else None

    if not DATA_DIR.exists():
        return None

    # Priority: document.pdf -> document.txt -> any *.pdf -> any *.txt
    candidates = [
        DATA_DIR / "document.pdf",
        DATA_DIR / "document.txt",
        *sorted(DATA_DIR.glob("*.pdf")),
        *sorted(DATA_DIR.glob("*.txt")),
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def index_document(file_path=None):
    doc_path = resolve_document_path(file_path)

    if not doc_path:
        print("Document not found!")
        print("Please place your PDF or TXT file inside the 'data/' folder")
        print("or specify the path: python main.py index <path_to_file>")
        return

    print(f"Loading document: {doc_path.resolve()} ({doc_path.suffix.upper()})")

    # 1. Rule-Based Extraction
    pages_struct = extract_text_from_file(doc_path)
    if not pages_struct:
        print("The document contains no readable text.")
        return

    # 2. Convert Extracted Data into Structured JSON
    doc_json = extractor.convert_to_json(pages_struct, doc_path.name)
    json_path = DATA_DIR / f"{doc_path.stem}_extracted.json"
    extractor.save_json_file(doc_json, json_path)

    total_tables = sum(len(p.tables) for p in pages_struct)
    total_headers = sum(1 for p in pages_struct if p.header)
    total_footers = sum(1 for p in pages_struct if p.footer)

    print(f"--- Rule-Based Extraction & JSON Conversion ---")
    print(f"  • Pages: {len(pages_struct)}")
    print(f"  • Headers Detected: {total_headers}")
    print(f"  • Footers Detected: {total_footers}")
    print(f"  • Tables Detected: {total_tables}")
    print(f"  • JSON File Persisted: {json_path.name}")

    for p in pages_struct:
        for tbl in p.tables:
            print(f"    - Table {tbl.table_id} on Page {tbl.page}: {tbl.num_rows} rows x {tbl.num_cols} cols (bbox: {tbl.bbox})")

    # 3. Create Vector DB Chunks from JSON Schema
    chunks = extractor.chunk_from_json(doc_json)
    if not chunks:
        print("The document contains no readable content after chunking.")
        return

    table_chunks = sum(1 for c in chunks if c.get("chunk_type") == "table")
    body_chunks = sum(1 for c in chunks if c.get("chunk_type") == "body")
    print(f"  • Total Chunks Created from JSON: {len(chunks)} ({table_chunks} table chunks, {body_chunks} text chunks)")

    old_ids = collection.get()["ids"]
    if old_ids:
        collection.delete(ids=old_ids)

    batch_size = 16

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed([c["text"] for c in batch])

        collection.add(
            ids=[f"chunk_{c['chunk_id']}" for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=vectors,
            metadatas=[
                {
                    "chunk_id": c["chunk_id"],
                    "page": c["page"],
                    "chunk_type": c.get("chunk_type", "body"),
                    "table_id": c.get("table_id", 0),
                    "start_char": c["start"],
                    "end_char": c["end"],
                    "source": doc_path.name,
                }
                for c in batch
            ],
        )

        print(f"Indexed {min(start + batch_size, len(chunks))}/{len(chunks)}")

    print(f"Indexing completed successfully for '{doc_path.name}'!")


def ask_question(question):
    if collection.count() == 0:
        print("No indexed document. Run python main.py index first.")
        return

    question_vector = embed([question])[0]

    # Semantic Vector Search in ChromaDB
    results = collection.query(
        query_embeddings=[question_vector],
        n_results=min(5, collection.count()),
    )

    context_parts = []
    for document, metadata in zip(results["documents"][0], results["metadatas"][0]):
        chunk_type = metadata.get("chunk_type", "body")
        table_id = metadata.get("table_id", 0)
        label = f"Table {table_id}" if chunk_type == "table" else "Text"
        context_parts.append(
            f"[Chunk {metadata['chunk_id']} | Page {metadata.get('page', 1)} | Type: {label}]\n{document}"
        )

    context = "\n\n".join(context_parts)

    print("\nAnswer:")
    print(generate_rag_answer(context, question))

    print("\nRetrieved chunks:")
    for metadata, distance in zip(
        results["metadatas"][0],
        results["distances"][0],
    ):
        page_info = f" (Page {metadata.get('page')})" if "page" in metadata else ""
        type_info = f" [{metadata.get('chunk_type', 'body').upper()}]"
        print(
            f"Chunk {metadata['chunk_id']}{type_info}{page_info} "
            f"(distance: {distance:.3f})"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py index               # Automatically index PDF or TXT from data/")
        print("  python main.py index <file_path>   # Index a specific PDF or TXT file")
        print("  python main.py chat                # Start interactive Q&A session")
        print("  python main.py ask \"<question>\"    # Ask a single question directly")
    elif sys.argv[1].lower() == "index":
        custom_path = sys.argv[2] if len(sys.argv) > 2 else None
        index_document(custom_path)
    elif sys.argv[1].lower() == "chat":
        if collection.count() == 0:
            print("No index found. Run python main.py index first.")
        else:
            print("Ask questions about your document. Type 'exit' to quit.")
            while True:
                question = input("\nYou: ").strip()
                if question.lower() in {"exit", "quit"}:
                    break
                if question:
                    ask_question(question)
    elif sys.argv[1].lower() == "ask":
        if len(sys.argv) < 3:
            print("Please provide a question: python main.py ask \"<question>\"")
        else:
            ask_question(" ".join(sys.argv[2:]))
    else:
        print("Unknown command. Use index, chat, or ask.")
