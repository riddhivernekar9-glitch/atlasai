from pathlib import Path
from pypdf import PdfReader


def read_pdf_text(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages).strip()
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF {path.name}: {e}")