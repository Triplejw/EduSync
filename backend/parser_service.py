import easyocr
import numpy as np
from PIL import Image
import io
import os
import subprocess
import tempfile
from pdf2image import convert_from_bytes
from pydantic import BaseModel
import pypdf

print("Loading EasyOCR on CPU...")
# English only, lighter model
reader = easyocr.Reader(['en'], gpu=False) 
print("✅ EasyOCR Loaded on CPU")

def extract_text_from_pdf_native(file_bytes):
    """Try to read text directly (0.1s) instead of using OCR"""
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader_pdf = pypdf.PdfReader(pdf_file)
        text = ""
        # Read up to 10 pages max (fast enough)
        max_pages = min(len(reader_pdf.pages), 10)
        
        for i in range(max_pages):
            page_text = reader_pdf.pages[i].extract_text()
            if page_text:
                text += page_text + "\n"
        
        # If we got a decent amount of text, return it
        if len(text) > 500: 
            return text
    except Exception as e:
        print(f"Native extraction failed: {e}")
    return None

def extract_text_from_image(file_bytes):
    text_content = []
    
    try:
        # 1. FAST PATH: Try Native PDF Extraction first
        if file_bytes.startswith(b'%PDF'):
            print("📄 Detected PDF. Attempting Fast Extraction...")
            native_text = extract_text_from_pdf_native(file_bytes)
            if native_text:
                print("⚡ Fast Extraction Success! Skipped OCR.")
                return native_text
            
            print("⚠️ Fast Extraction failed (Scanned PDF?). Switching to OCR.")
            # 2. SLOW PATH: OCR
            # Only convert FIRST 5 PAGES to save time
            # The LLM will truncate anyway, so page 35 is useless.
            print("📸 Converting first 5 pages to images...")
            images = convert_from_bytes(file_bytes, first_page=1, last_page=5)
        else:
            # Single Image
            images = [Image.open(io.BytesIO(file_bytes)).convert("RGB")]

        # Loop through images (Max 5)
        for i, img in enumerate(images):
            print(f"   👁️ OCR Processing page {i+1}/{len(images)}...")
            image_np = np.array(img)
            # detail=0 returns simple list of strings
            result = reader.readtext(image_np, detail=0, paragraph=True)
            text_content.append(" ".join(result))
            
        return "\n\n".join(text_content)
        
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return ""


def extract_text_from_ppt(file_bytes, file_ext):
    """Convert PPT/PPTX to PDF and run existing OCR pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input{file_ext}")
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        cmd = [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            tmpdir,
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"PPT conversion failed. Ensure LibreOffice is installed. {stderr}")

        expected_pdf = os.path.splitext(input_path)[0] + ".pdf"
        pdf_path = expected_pdf if os.path.exists(expected_pdf) else None
        if not pdf_path:
            for name in os.listdir(tmpdir):
                if name.lower().endswith(".pdf"):
                    pdf_path = os.path.join(tmpdir, name)
                    break
        if not pdf_path:
            raise RuntimeError("PPT conversion failed: PDF not found.")

        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
        return extract_text_from_image(pdf_bytes)


def extract_text_from_document(file_bytes, file_ext=None):
    ext = (file_ext or "").lower()
    if ext in [".ppt", ".pptx"]:
        return extract_text_from_ppt(file_bytes, ext)
    return extract_text_from_image(file_bytes)