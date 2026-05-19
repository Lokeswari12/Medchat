"""
Handles text extraction from PDF, TXT, and image files.
"""
import os

def extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return _extract_pdf(filepath)
    elif ext == ".txt":
        return _extract_txt(filepath)
    elif ext in (".png", ".jpg", ".jpeg"):
        return _extract_image(filepath)
    return ""


def _extract_pdf(path: str) -> str:
    try:
        import PyPDF2
        text = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return "\n".join(text)
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def _extract_txt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"[TXT read error: {e}]"


def _extract_image(path: str) -> str:
    """Attempt OCR via pytesseract if available, otherwise return placeholder."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(path)
        return pytesseract.image_to_string(img)
    except ImportError:
        return (
            "Image uploaded for cancer screening analysis. "
            "The image contains medical scan data requiring expert interpretation. "
            "Please analyze this medical image for any signs of malignancy, "
            "abnormal cell growth, or tumor markers."
        )
    except Exception as e:
        return f"[Image processing error: {e}]"
