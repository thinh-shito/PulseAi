"""
File processor utility to extract text from DOCX and PDF files.
"""
import io
import docx2txt

try:
    import pdftotext
except ImportError:
    pdftotext = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def convert_file_to_text(file_content: bytes, file_extension: str) -> str:
    """
    Converts docx/pdf file content to plain text.
    Uses docx2txt and pdftotext (with a fallback to pypdf).
    """
    ext = file_extension.lower().lstrip(".")
    if ext == "docx":
        file_like = io.BytesIO(file_content)
        return docx2txt.process(file_like)
    elif ext == "pdf":
        file_like = io.BytesIO(file_content)
        if pdftotext is not None:
            try:
                pdf = pdftotext.PDF(file_like)
                return "\n".join(pdf)
            except Exception:
                pass

        # Fallback to PdfReader
        if PdfReader is not None:
            reader = PdfReader(file_like)
            text_parts = []
            for page in reader.pages:
                part = page.extract_text()
                if part:
                    text_parts.append(part)
            return "\n".join(text_parts)

        raise ImportError("Neither pdftotext nor pypdf is available for PDF parsing")
    else:
        # Fallback for plain text files
        try:
            return file_content.decode("utf-8")
        except Exception:
            raise ValueError(
                f"Unsupported file extension for text conversion: {file_extension}"
            )