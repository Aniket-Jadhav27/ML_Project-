import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from google import genai
from google.genai import types

from rule_based_extractor import RuleBasedExtractor, ExtractedPageStructure

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CHROMA_PATH = BASE_DIR / "chroma_db"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

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
        "When answering from tables, specify the exact row, column, and cell coordinates if asked. "
        "Do not invent facts. If the evidence is insufficient, say so clearly. "
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

# Rule-Based Document Extractor instance
extractor = RuleBasedExtractor()

# In-memory storage for user-specific structured document metadata
user_document_structures: Dict[str, List[Dict[str, Any]]] = {}


def get_user_collection(user_id: Optional[str] = "default"):
    """
    Returns an isolated ChromaDB collection for each user account.
    This guarantees that User A's uploaded documents are never visible or searchable by User B.
    """
    raw_id = str(user_id or "default").strip().lower()
    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_id)
    if not clean_id or clean_id == "anonymous":
        clean_id = "default"
    col_name = f"user_{clean_id}"
    return client.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},
    )


app = FastAPI(title="Document RAG Engine API with Multi-User Isolation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    user_id: Optional[str] = "default"


class ChunkInfo(BaseModel):
    chunk_id: int
    page: int
    start_char: int
    end_char: int
    source: str
    text: str
    chunk_type: Optional[str] = "body"
    table_id: Optional[int] = 0
    distance: Optional[float] = 0.0


class AskResponse(BaseModel):
    question: str
    answer: str
    chunks: List[ChunkInfo]


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    res = get_genai_client().models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    return [emb.values for emb in res.embeddings]


@app.get("/api/rag/health")
def health():
    return {
        "status": "UP",
        "embed_model": EMBED_MODEL,
        "llm_model": LLM_MODEL,
    }


@app.get("/api/rag/structure")
def get_document_structure(user_id: Optional[str] = Query("default")):
    """Returns the full rule-based extraction structure for the specific user."""
    raw_id = str(user_id or "default").strip().lower()
    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_id) or "default"

    if clean_id in user_document_structures:
        return user_document_structures[clean_id]

    # Try loading from saved JSON file on disk
    json_pattern = f"{clean_id}_*_extracted.json"
    matching_files = list(DATA_DIR.glob(json_pattern))
    if matching_files:
        try:
            doc_data = json.loads(matching_files[-1].read_text(encoding="utf-8"))
            pages = doc_data.get("pages", [])
            user_document_structures[clean_id] = pages
            return pages
        except Exception:
            pass

    return []


@app.get("/api/rag/json")
def get_extracted_json(user_id: Optional[str] = Query("default")):
    """Returns the full extracted document in structured JSON format for the user."""
    return get_document_structure(user_id)


@app.get("/api/rag/tables")
def get_document_tables(user_id: Optional[str] = Query("default")):
    """Returns all extracted tables for the specific user."""
    pages = get_document_structure(user_id)
    tables = []
    for page in pages:
        for tbl in page.get("tables", []):
            tables.append(tbl)
    return tables


@app.get("/api/rag/chunks")
def get_all_chunks(user_id: Optional[str] = Query("default")):
    """Returns all chunks belonging ONLY to the requested user."""
    user_col = get_user_collection(user_id)
    all_data = user_col.get()
    results = []
    if not all_data or not all_data["ids"]:
        return results

    for i in range(len(all_data["ids"])):
        meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
        doc_text = all_data["documents"][i] if all_data["documents"] else ""
        results.append({
            "chunk_id": meta.get("chunk_id", i),
            "page": meta.get("page", 1),
            "chunk_type": meta.get("chunk_type", "body"),
            "table_id": meta.get("table_id", 0),
            "start_char": meta.get("start_char", 0),
            "end_char": meta.get("end_char", 0),
            "source": meta.get("source", "document"),
            "text": doc_text,
            "distance": 0.0,
        })
    return sorted(results, key=lambda x: x["chunk_id"])


@app.post("/api/rag/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form("default"),
):
    """
    Extracts, converts to JSON, and indexes document into the user's isolated collection.
    Only the uploading user will have access to this document.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    filename = file.filename or "uploaded_file"
    raw_id = str(user_id or "default").strip().lower()
    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_id) or "default"

    # 1. Rule-Based Document Extraction
    try:
        pages_struct: List[ExtractedPageStructure] = extractor.extract_document(contents, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract document structures: {e}")

    # 2. Convert Extracted Data into Structured JSON format
    doc_json = extractor.convert_to_json(pages_struct, filename)

    # 3. Save User-Isolated JSON file to data/ directory
    json_filename = f"{clean_id}_{Path(filename).stem}_extracted.json"
    json_path = DATA_DIR / json_filename
    extractor.save_json_file(doc_json, json_path)

    # Cache structured page data for this user
    user_document_structures[clean_id] = doc_json.get("pages", [])

    # 4. Generate Semantic Chunks from the JSON format
    chunks = extractor.chunk_from_json(doc_json)
    if not chunks:
        raise HTTPException(status_code=400, detail="No readable text found after extraction")

    # 5. User-Scoped Vector DB Storage:
    # Clear previous document chunks ONLY for this user
    user_col = get_user_collection(clean_id)
    old_ids = user_col.get()["ids"]
    if old_ids:
        user_col.delete(ids=old_ids)

    # Batch embed and store into user's isolated collection
    batch_size = 16
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed_texts([c["text"] for c in batch])
        user_col.add(
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
                    "source": filename,
                    "user_id": clean_id,
                }
                for c in batch
            ],
        )

    # 6. Save user-namespaced raw file to data/ directory
    target_path = DATA_DIR / f"{clean_id}_{filename}"
    target_path.write_bytes(contents)

    total_tables = sum(len(p.tables) for p in pages_struct)
    total_headers = sum(1 for p in pages_struct if p.header)
    total_footers = sum(1 for p in pages_struct if p.footer)

    return {
        "status": "success",
        "user_id": clean_id,
        "filename": filename,
        "json_filename": json_filename,
        "page_count": len(pages_struct),
        "chunk_count": len(chunks),
        "tables_detected": total_tables,
        "headers_detected": total_headers,
        "footers_detected": total_footers,
    }


@app.post("/api/rag/ask")
async def ask(request: Request):
    question = ""
    user_id = "default"
    try:
        data = await request.json()
        if isinstance(data, dict):
            question = data.get("question", "")
            user_id = data.get("user_id", "default")
    except Exception:
        pass

    if not question:
        question = request.query_params.get("question", "")
    if not user_id or user_id == "default":
        user_id = request.query_params.get("user_id", "default")

    question = str(question).strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    user_col = get_user_collection(user_id)
    count = user_col.count()

    if count == 0:
        return AskResponse(
            question=question,
            answer="No documents are currently indexed for your account. Please upload a PDF or text file first.",
            chunks=[],
        )

    q_vector = embed_texts([question])[0]
    results = user_col.query(
        query_embeddings=[q_vector],
        n_results=min(5, count),
    )

    chunks: List[ChunkInfo] = []
    context_parts = []

    if results and results["documents"] and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = (
            results["distances"][0]
            if "distances" in results and results["distances"]
            else [0.0] * len(docs)
        )

        for d, m, dist in zip(docs, metas, dists):
            chunk_type = m.get("chunk_type", "body")
            table_id = m.get("table_id", 0)

            chunk_info = ChunkInfo(
                chunk_id=m.get("chunk_id", 0),
                page=m.get("page", 1),
                chunk_type=chunk_type,
                table_id=table_id,
                start_char=m.get("start_char", 0),
                end_char=m.get("end_char", 0),
                source=m.get("source", "document"),
                text=d,
                distance=round(dist, 4) if dist is not None else 0.0,
            )
            chunks.append(chunk_info)

            type_label = f"Table {table_id}" if chunk_type == "table" else "Text"
            context_parts.append(
                f"[Chunk {chunk_info.chunk_id} | Page {chunk_info.page} | Type: {type_label}]\n{d}"
            )

    context = "\n\n".join(context_parts)

    try:
        answer_text = generate_rag_answer(context, question)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM generation failed: {exc}")

    return AskResponse(
        question=question,
        answer=answer_text,
        chunks=chunks,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
