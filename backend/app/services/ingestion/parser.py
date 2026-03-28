import os
from markitdown import MarkItDown

def parse_document(file_path: str) -> str:
    """
    Parses a document (PDF, Word, Excel, etc.) into well-structured Markdown
    using Microsoft's MarkItDown library.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")
        
    md = MarkItDown()
    result = md.convert(file_path)
    return result.text_content
