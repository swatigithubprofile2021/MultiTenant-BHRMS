from pathlib import Path
import fitz  # PyMuPDF
import pymupdf4llm
from llama_index.core import Document
from datetime import datetime, timedelta, date
import datetime
import hashlib
from fastapi import UploadFile, HTTPException



def get_time_filter(filter_type: str):
    now = datetime.utcnow()
    if filter_type == "day":
        return now - timedelta(days=1)
    elif filter_type == "week":
        return now - timedelta(weeks=1)
    elif filter_type == "month":
        return now - timedelta(days=30)
    elif filter_type == "year":
        return now - timedelta(days=365)
    elif filter_type == "max":
        return None
    else:
        raise ValueError("Invalid filter type")


def get_summary_date_range(time_filter: str):
    today = date.today()
    if time_filter == "day":
        return today, today
    elif time_filter == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    elif time_filter == "month":
        start = today.replace(day=1)
        return start, today
    elif time_filter == "year":
        start = today.replace(month=1, day=1)
        return start, today
    elif time_filter == "max":
        return None, None
    else:
        raise ValueError("Invalid time filter")


def load_mixed_layout_pdf_local(data_dir: str):
    data_dir = Path(data_dir)
    documents = []

    for pdf_path in data_dir.glob("*.pdf"):
        # print(pdf_path)
        doc = fitz.open(pdf_path)

        for idx, page in enumerate(doc, start=1):
            # 1. Try to get text with layout preserved (blocks)
            text = page.get_text("text")

            # Table Extraction (Crucial for HR Policies)
            tabs = page.find_tables()
            table_md = ""
            if tabs.tables:
                table_md = tabs[0].to_markdown()

            # Combine page content with table data
            page_content = f"{text}\n\n{table_md}"

            # 2. Fallback: If page is empty, it's likely a scanned image
            if not page_content.strip():
                # Trigger OCR on this specific page
                pix = page.get_pixmap()
                # This requires 'easyocr' or 'pytesseract'
                import pytesseract
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(pix.tobytes()))
                page_content = pytesseract.image_to_string(img)

            documents.append(
                Document(
                    text=page_content,
                    id_=f"{pdf_path}_{idx}",
                    metadata={"file_path": str(pdf_path), "page": idx},
                )
            )

        doc.close()
    # Combine and wrap for LlamaIndex
    # print(len(documents))
    return documents


# 1. Scalable Reader: Handles multi-column & tables by converting to Markdown
def load_mixed_layout_pdf(file_path):
    # PyMuPDF4LLM is layout-aware and extracts tables as MD tables
    md_text = pymupdf4llm.to_markdown(file_path)
    return [Document(text=md_text, metadata={"source": file_path})]


def delete_file(file_path: Path):
    """
    Safely delete a file if it exists
    """
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception  as e:
        # Log the error or handle it as needed
        print(f"Error deleting file {file_path}: {e}")
        


async def read_file_in_chunks(file, chunk_size: int = 1024 * 1024):
    """
    Async generator to read file in chunks

    Usage:
        async for chunk in read_file_in_chunks(file):
            ...
    """
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        yield chunk