"""
resume_parser.py
Extracts raw text from uploaded resume files.
Supports: PDF, DOCX, TXT
"""
import io
import pdfplumber
from docx import Document


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from a resume file.
    Returns cleaned text string.
    """
    ext = filename.lower().split(".")[-1]

    if ext == "pdf":
        return _extract_pdf(file_bytes)
    elif ext in ("doc", "docx"):
        return _extract_docx(file_bytes)
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: .{ext}")


def _extract_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])