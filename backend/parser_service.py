"""Document text extraction with lazy OCR initialization."""

import io
import os
import subprocess
import tempfile
import threading
from pathlib import Path


_reader = None
_reader_error: str | None = None
_reader_lock = threading.Lock()


def get_ocr_status() -> dict:
    """Return OCR readiness without downloading or loading OCR models."""
    return {"loaded": _reader is not None, "load_error": _reader_error, "backend": "EasyOCR"}


def get_ocr_reader():
    """Initialize the shared English EasyOCR reader only when OCR is required."""
    global _reader, _reader_error
    if _reader is not None:
        return _reader
    with _reader_lock:
        if _reader is not None:
            return _reader
        try:
            import easyocr

            model_dir = Path(
                os.environ.get(
                    "EDUSYNC_OCR_MODEL_DIR",
                    Path(__file__).resolve().parent / "models" / "easyocr",
                )
            ).expanduser()
            model_dir.mkdir(parents=True, exist_ok=True)
            user_network_dir = model_dir / "user_network"
            user_network_dir.mkdir(parents=True, exist_ok=True)
            _reader = easyocr.Reader(
                ["en"],
                gpu=False,
                model_storage_directory=str(model_dir),
                user_network_directory=str(user_network_dir),
            )
            _reader_error = None
            return _reader
        except Exception as exc:
            _reader_error = str(exc)
            raise RuntimeError(f"EasyOCR failed to initialize: {exc}") from exc


def extract_text_from_pdf_native(file_bytes):
    """Read embedded PDF text before falling back to OCR."""
    try:
        import pypdf

        reader_pdf = pypdf.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader_pdf.pages[:10]:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if len(text) > 500:
            return text
    except Exception as exc:
        print(f"Native extraction failed: {exc}")
    return None


def extract_text_from_image(file_bytes):
    """Extract text from an image or scanned PDF."""
    from PIL import Image
    import numpy as np

    if file_bytes.startswith(b"%PDF"):
        native_text = extract_text_from_pdf_native(file_bytes)
        if native_text:
            return native_text
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(file_bytes, first_page=1, last_page=5)
    else:
        images = [Image.open(io.BytesIO(file_bytes)).convert("RGB")]

    reader = get_ocr_reader()
    text_content = []
    for image in images:
        result = reader.readtext(np.array(image), detail=0, paragraph=True)
        text_content.append(" ".join(result))
    return "\n\n".join(text_content)


def extract_text_from_ppt(file_bytes, file_ext):
    """Convert PPT/PPTX to PDF with LibreOffice, then extract its text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input{file_ext}")
        with open(input_path, "wb") as file_handle:
            file_handle.write(file_bytes)
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmpdir, input_path],
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"PPT conversion failed. Install LibreOffice. {stderr}")

        pdf_path = os.path.splitext(input_path)[0] + ".pdf"
        if not os.path.exists(pdf_path):
            candidates = [name for name in os.listdir(tmpdir) if name.lower().endswith(".pdf")]
            if not candidates:
                raise RuntimeError("PPT conversion failed: PDF not found.")
            pdf_path = os.path.join(tmpdir, candidates[0])
        with open(pdf_path, "rb") as pdf_file:
            return extract_text_from_image(pdf_file.read())


def extract_text_from_document(file_bytes, file_ext=None):
    ext = (file_ext or "").lower()
    if ext in {".ppt", ".pptx"}:
        return extract_text_from_ppt(file_bytes, ext)
    return extract_text_from_image(file_bytes)
