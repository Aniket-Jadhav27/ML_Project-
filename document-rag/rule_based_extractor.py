"""
Rule-Based Document Extractor & JSON Serializer
-----------------------------------------------
Extracts structured document elements:
- Running Headers (based on top margin threshold, regex, and repetition)
- Running Footers (based on bottom margin threshold, page number regex, and repetition)
- Tables with full positional values (Row index, Column index, Cell bounding boxes, Header tags)
- Body text blocks (paragraphs located outside headers, footers, and table regions)

Conversion to JSON & Vector DB:
- Converts all extracted structures into clean, standardized JSON schemas.
- Saves the JSON document to disk (<filename>_extracted.json).
- Converts JSON structures into semantic chunks ready for vector database (ChromaDB) storage.
"""

import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
import pypdf


@dataclass
class CellPositionalData:
    row_idx: int
    col_idx: int
    text: str
    bbox: Optional[Tuple[float, float, float, float]] = None  # (x0, top, x1, bottom)
    is_header: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row_idx,
            "col": self.col_idx,
            "text": self.text,
            "bbox": [round(v, 2) for v in self.bbox] if self.bbox else None,
            "is_header": self.is_header,
        }


@dataclass
class ExtractedTable:
    table_id: int
    page: int
    bbox: Tuple[float, float, float, float]
    num_rows: int
    num_cols: int
    headers: List[str] = field(default_factory=list)
    cells: List[CellPositionalData] = field(default_factory=list)
    raw_rows: List[List[str]] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Formats the table into standard GitHub-flavored Markdown."""
        if not self.raw_rows:
            return ""
        lines = []
        headers = [c if c else f"Col_{i}" for i, c in enumerate(self.raw_rows[0])]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for row in self.raw_rows[1:]:
            padded_row = [(c if c else "") for c in row]
            while len(padded_row) < len(headers):
                padded_row.append("")
            lines.append("| " + " | ".join(padded_row[:len(headers)]) + " |")

        return "\n".join(lines)

    def to_positional_text(self) -> str:
        """Generates explicit row, column, and cell coordinate annotations for LLM grounding."""
        box_str = (
            f"x0={self.bbox[0]:.1f}, top={self.bbox[1]:.1f}, "
            f"x1={self.bbox[2]:.1f}, bottom={self.bbox[3]:.1f}"
        )
        lines = [
            f"[TABLE {self.table_id} | Page {self.page} | Dimensions: {self.num_rows} Rows x {self.num_cols} Cols | BBox: ({box_str})]"
        ]

        md = self.to_markdown()
        if md:
            lines.append(md)
            lines.append("")

        lines.append("--- Cell Position Mapping ---")
        for cell in self.cells:
            cell_tag = "Header" if cell.is_header else "Data"
            coord_str = ""
            if cell.bbox:
                coord_str = f" @ [x0={cell.bbox[0]:.1f}, top={cell.bbox[1]:.1f}, x1={cell.bbox[2]:.1f}, bottom={cell.bbox[3]:.1f}]"
            lines.append(
                f"• Row {cell.row_idx}, Col {cell.col_idx} ({cell_tag}){coord_str}: {cell.text}"
            )

        return "\n".join(lines)

    def to_json_dict(self) -> Dict[str, Any]:
        """Serializes the table into a clean JSON object with row records and cell matrices."""
        row_objects = []
        headers = self.headers
        for r_idx in range(1, len(self.raw_rows)):
            row = self.raw_rows[r_idx]
            row_dict = {}
            for c_idx, cell_value in enumerate(row):
                col_name = headers[c_idx] if c_idx < len(headers) and headers[c_idx] else f"Column_{c_idx}"
                row_dict[col_name] = cell_value
            row_objects.append({
                "row_index": r_idx,
                "data": row_dict
            })

        return {
            "table_id": self.table_id,
            "page": self.page,
            "bounding_box": {
                "x0": round(self.bbox[0], 2),
                "top": round(self.bbox[1], 2),
                "x1": round(self.bbox[2], 2),
                "bottom": round(self.bbox[3], 2),
            },
            "dimensions": {
                "rows": self.num_rows,
                "columns": self.num_cols,
            },
            "headers": self.headers,
            "rows": row_objects,
            "cells": [c.to_dict() for c in self.cells],
            "markdown": self.to_markdown(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_json_dict()


@dataclass
class HeaderFooterBlock:
    category: str  # "header" or "footer"
    text: str
    page: int
    bbox: Tuple[float, float, float, float]
    rule: str

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "page": self.page,
            "text": self.text,
            "bounding_box": {
                "x0": round(self.bbox[0], 2),
                "top": round(self.bbox[1], 2),
                "x1": round(self.bbox[2], 2),
                "bottom": round(self.bbox[3], 2),
            },
            "rule": self.rule,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_json_dict()


@dataclass
class ExtractedPageStructure:
    page: int
    width: float
    height: float
    header: Optional[HeaderFooterBlock] = None
    footer: Optional[HeaderFooterBlock] = None
    tables: List[ExtractedTable] = field(default_factory=list)
    body_text: str = ""
    full_text: str = ""

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page,
            "page_dimensions": {
                "width": round(self.width, 2),
                "height": round(self.height, 2),
            },
            "header": self.header.to_json_dict() if self.header else None,
            "footer": self.footer.to_json_dict() if self.footer else None,
            "tables": [t.to_json_dict() for t in self.tables],
            "body_text": self.body_text,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_json_dict()


class RuleBasedExtractor:
    """
    Applies spatial and regex rules to extract document structures:
    1. Header Zone: Top margin (e.g. top < 12% of page height or < 100pt).
    2. Footer Zone: Bottom margin (e.g. bottom > 90% of page height or > page_height - 90pt).
    3. Table Detection: Extracts structured rows, columns, and cell bounding boxes.
    4. Body Text: Words outside header, footer, and table bounding boxes.
    5. JSON Conversion: Converts extracted pages into JSON format.
    6. Vector DB Chunking: Chunks the JSON representation for ChromaDB storage.
    """

    PAGE_NUMBER_PATTERN = re.compile(
        r"^(page\s+\d+(\s+of\s+\d+)?|\d+(\s*/\s*\d+)?|-\s*\d+\s*-|\d+)$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        header_ratio: float = 0.12,
        footer_ratio: float = 0.10,
        max_header_margin_pt: float = 100.0,
        max_footer_margin_pt: float = 85.0,
    ):
        self.header_ratio = header_ratio
        self.footer_ratio = footer_ratio
        self.header_margin_pt = max_header_margin_pt
        self.footer_margin_pt = max_footer_margin_pt

    def extract_document(self, content_bytes: bytes, filename: str) -> List[ExtractedPageStructure]:
        suffix = Path(filename).suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(content_bytes)
        elif suffix in {".txt", ".md"}:
            return self._extract_plain_text(content_bytes)
        else:
            raise ValueError(f"Unsupported file format '{suffix}'. Supported: .pdf, .txt, .md")

    def _extract_pdf(self, content_bytes: bytes) -> List[ExtractedPageStructure]:
        extracted_pages: List[ExtractedPageStructure] = []

        try:
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    p_width = float(page.width)
                    p_height = float(page.height)

                    header_bottom_threshold = max(p_height * self.header_ratio, self.header_margin_pt)
                    footer_top_threshold = min(p_height * (1.0 - self.footer_ratio), p_height - self.footer_margin_pt)

                    # 1. Extract Tables with positional cell coordinates
                    found_tables = page.find_tables()
                    table_bboxes = []
                    extracted_tables: List[ExtractedTable] = []

                    for t_idx, t in enumerate(found_tables, start=1):
                        table_bbox = tuple(t.bbox)  # (x0, top, x1, bottom)
                        table_bboxes.append(table_bbox)

                        raw_data = t.extract()
                        cleaned_rows = [
                            [str(cell).strip() if cell is not None else "" for cell in row]
                            for row in raw_data
                        ]

                        headers = cleaned_rows[0] if cleaned_rows else []

                        cells_data: List[CellPositionalData] = []
                        if hasattr(t, "rows") and t.rows:
                            for r_idx, row_obj in enumerate(t.rows):
                                if hasattr(row_obj, "cells"):
                                    for c_idx, cell_box in enumerate(row_obj.cells):
                                        cell_text = ""
                                        if r_idx < len(cleaned_rows) and c_idx < len(cleaned_rows[r_idx]):
                                            cell_text = cleaned_rows[r_idx][c_idx]

                                        c_bbox = tuple(cell_box) if cell_box else None
                                        cells_data.append(
                                            CellPositionalData(
                                                row_idx=r_idx,
                                                col_idx=c_idx,
                                                text=cell_text,
                                                bbox=c_bbox,
                                                is_header=(r_idx == 0),
                                            )
                                        )

                        num_r = len(cleaned_rows)
                        num_c = max(len(r) for r in cleaned_rows) if cleaned_rows else 0

                        extracted_tables.append(
                            ExtractedTable(
                                table_id=t_idx,
                                page=page_idx,
                                bbox=table_bbox,
                                num_rows=num_r,
                                num_cols=num_c,
                                headers=headers,
                                cells=cells_data,
                                raw_rows=cleaned_rows,
                            )
                        )

                    # 2. Extract words and classify into Header, Footer, and Body
                    words = page.extract_words(keep_blank_chars=False)

                    header_words = []
                    footer_words = []
                    body_words = []

                    for w in words:
                        w_top = float(w["top"])
                        w_bottom = float(w["bottom"])
                        w_x0 = float(w["x0"])
                        w_x1 = float(w["x1"])

                        inside_table = False
                        for (tx0, ttop, tx1, tbottom) in table_bboxes:
                            cx = (w_x0 + w_x1) / 2.0
                            cy = (w_top + w_bottom) / 2.0
                            if tx0 <= cx <= tx1 and ttop <= cy <= tbottom:
                                inside_table = True
                                break

                        if inside_table:
                            continue

                        if w_bottom <= header_bottom_threshold:
                            header_words.append(w)
                        elif w_top >= footer_top_threshold:
                            footer_words.append(w)
                        else:
                            body_words.append(w)

                    header_block = None
                    if header_words:
                        h_text = " ".join(w["text"] for w in header_words).strip()
                        if h_text:
                            hx0 = min(float(w["x0"]) for w in header_words)
                            htop = min(float(w["top"]) for w in header_words)
                            hx1 = max(float(w["x1"]) for w in header_words)
                            hbottom = max(float(w["bottom"]) for w in header_words)
                            header_block = HeaderFooterBlock(
                                category="header",
                                text=h_text,
                                page=page_idx,
                                bbox=(hx0, htop, hx1, hbottom),
                                rule="Rule_H1_TopMargin",
                            )

                    footer_block = None
                    if footer_words:
                        f_text = " ".join(w["text"] for w in footer_words).strip()
                        if f_text:
                            fx0 = min(float(w["x0"]) for w in footer_words)
                            ftop = min(float(w["top"]) for w in footer_words)
                            fx1 = max(float(w["x1"]) for w in footer_words)
                            fbottom = max(float(w["bottom"]) for w in footer_words)

                            rule_name = "Rule_F1_BottomMargin"
                            if self.PAGE_NUMBER_PATTERN.match(f_text):
                                rule_name = "Rule_F2_PageNumber"

                            footer_block = HeaderFooterBlock(
                                category="footer",
                                text=f_text,
                                page=page_idx,
                                bbox=(fx0, ftop, fx1, fbottom),
                                rule=rule_name,
                            )

                    body_text = self._assemble_words_into_text(body_words)

                    full_text_parts = []
                    if header_block:
                        full_text_parts.append(f"[PAGE {page_idx} HEADER]: {header_block.text}")

                    if body_text.strip():
                        full_text_parts.append(body_text.strip())

                    for tbl in extracted_tables:
                        full_text_parts.append(tbl.to_positional_text())

                    if footer_block:
                        full_text_parts.append(f"[PAGE {page_idx} FOOTER]: {footer_block.text}")

                    combined_page_text = "\n\n".join(full_text_parts)

                    extracted_pages.append(
                        ExtractedPageStructure(
                            page=page_idx,
                            width=p_width,
                            height=p_height,
                            header=header_block,
                            footer=footer_block,
                            tables=extracted_tables,
                            body_text=body_text,
                            full_text=combined_page_text,
                        )
                    )

        except Exception:
            return self._fallback_pypdf(content_bytes)

        return extracted_pages

    def _assemble_words_into_text(self, words: List[Dict[str, Any]], line_tolerance: float = 3.0) -> str:
        if not words:
            return ""

        sorted_words = sorted(words, key=lambda w: (round(float(w["top"]) / line_tolerance), float(w["x0"])))

        lines: List[List[Dict[str, Any]]] = []
        current_line: List[Dict[str, Any]] = []
        last_top = None

        for w in sorted_words:
            w_top = float(w["top"])
            if last_top is None or abs(w_top - last_top) <= line_tolerance:
                current_line.append(w)
                last_top = w_top if last_top is None else (last_top + w_top) / 2.0
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [w]
                last_top = w_top

        if current_line:
            lines.append(current_line)

        text_lines = []
        for line in lines:
            line_str = " ".join(w["text"] for w in sorted(line, key=lambda x: float(x["x0"])))
            if line_str.strip():
                text_lines.append(line_str.strip())

        return "\n".join(text_lines)

    def _extract_plain_text(self, content_bytes: bytes) -> List[ExtractedPageStructure]:
        text = content_bytes.decode("utf-8-sig", errors="replace")
        return [
            ExtractedPageStructure(
                page=1,
                width=612.0,
                height=792.0,
                body_text=text,
                full_text=text,
            )
        ]

    def _fallback_pypdf(self, content_bytes: bytes) -> List[ExtractedPageStructure]:
        reader = pypdf.PdfReader(io.BytesIO(content_bytes))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            txt = page.extract_text() or ""
            pages.append(
                ExtractedPageStructure(
                    page=i,
                    width=612.0,
                    height=792.0,
                    body_text=txt,
                    full_text=txt,
                )
            )
        return pages

    def convert_to_json(
        self,
        extracted_pages: List[ExtractedPageStructure],
        filename: str = "document",
    ) -> Dict[str, Any]:
        """
        Step 1: Converts the extracted data into a standardized hierarchical JSON document.
        """
        total_tables = sum(len(p.tables) for p in extracted_pages)
        total_headers = sum(1 for p in extracted_pages if p.header)
        total_footers = sum(1 for p in extracted_pages if p.footer)

        return {
            "document_name": filename,
            "metadata": {
                "total_pages": len(extracted_pages),
                "total_tables": total_tables,
                "total_headers": total_headers,
                "total_footers": total_footers,
                "extraction_method": "rule_based_spatial_and_regex",
            },
            "pages": [p.to_json_dict() for p in extracted_pages],
        }

    def save_json_file(self, document_json: Dict[str, Any], output_path: Path) -> Path:
        """Persists the extracted JSON document to disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(document_json, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def chunk_from_json(
        self,
        document_json: Dict[str, Any],
        max_chunk_size: int = 1500,
        overlap: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Step 2: Converts the JSON-formatted data into vector database chunks for ChromaDB.
        - Tables are emitted as structured JSON objects with cell mappings and markdown.
        - Body paragraphs are emitted with structured JSON metadata.
        """
        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0
        doc_name = document_json.get("document_name", "document")

        for page in document_json.get("pages", []):
            p_num = page.get("page_number", 1)
            header_text = page.get("header", {}).get("text", "") if page.get("header") else ""
            footer_text = page.get("footer", {}).get("text", "") if page.get("footer") else ""

            # 1. Chunk Each Table from the JSON Schema
            for tbl in page.get("tables", []):
                table_id = tbl.get("table_id", 1)
                dims = tbl.get("dimensions", {})
                num_rows = dims.get("rows", 0)
                num_cols = dims.get("columns", 0)

                # Build rich JSON text representation for the Vector DB
                json_payload = {
                    "format": "JSON_TABLE_SCHEMA",
                    "table_id": table_id,
                    "page": p_num,
                    "dimensions": dims,
                    "headers": tbl.get("headers", []),
                    "rows": tbl.get("rows", []),
                }

                # Hybrid text: JSON schema + Positional mapping for LLM grounding
                table_content_parts = [
                    f"[JSON TABLE SCHEMA - Table {table_id} | Page {p_num} | {num_rows} Rows x {num_cols} Cols]",
                    json.dumps(json_payload, indent=2, ensure_ascii=False),
                    "",
                    "--- Markdown View ---",
                    tbl.get("markdown", ""),
                    "",
                    "--- Positional Cells ---",
                ]

                for cell in tbl.get("cells", []):
                    c_tag = "Header" if cell.get("is_header") else "Data"
                    bbox = cell.get("bbox")
                    b_str = f" @ {bbox}" if bbox else ""
                    table_content_parts.append(
                        f"• Row {cell.get('row')}, Col {cell.get('col')} ({c_tag}){b_str}: {cell.get('text')}"
                    )

                chunk_text = "\n".join(table_content_parts)

                chunks.append(
                    {
                        "chunk_id": chunk_idx,
                        "page": p_num,
                        "chunk_type": "table",
                        "table_id": table_id,
                        "num_rows": num_rows,
                        "num_cols": num_cols,
                        "text": chunk_text,
                        "json_data": json.dumps(json_payload),
                        "start": 0,
                        "end": len(chunk_text),
                    }
                )
                chunk_idx += 1

            # 2. Chunk Body Text from the JSON Schema
            body = page.get("body_text", "")
            if body.strip():
                start = 0
                while start < len(body):
                    end = min(start + max_chunk_size, len(body))
                    chunk_str = body[start:end].strip()

                    if chunk_str:
                        body_json = {
                            "format": "JSON_BODY_TEXT",
                            "page": p_num,
                            "header_context": header_text if header_text else None,
                            "content": chunk_str,
                        }

                        header_prefix = f"[{header_text}]\n" if header_text else ""
                        full_chunk = f"{header_prefix}{chunk_str}\n\n[Structured JSON]: {json.dumps(body_json, ensure_ascii=False)}"

                        chunks.append(
                            {
                                "chunk_id": chunk_idx,
                                "page": p_num,
                                "chunk_type": "body",
                                "table_id": 0,
                                "num_rows": 0,
                                "num_cols": 0,
                                "text": full_chunk,
                                "json_data": json.dumps(body_json),
                                "start": start,
                                "end": end,
                            }
                        )
                        chunk_idx += 1

                    if end == len(body):
                        break
                    start = end - overlap

        return chunks

    def chunk_structured_document(
        self,
        extracted_pages: List[ExtractedPageStructure],
        max_chunk_size: int = 1500,
        overlap: int = 200,
    ) -> List[Dict[str, Any]]:
        """Convenience method converting extracted pages directly through the JSON pipeline."""
        doc_json = self.convert_to_json(extracted_pages)
        return self.chunk_from_json(doc_json, max_chunk_size=max_chunk_size, overlap=overlap)
