"""
chunker.py – Semantic legal-text splitting.

Uses LangChain's RecursiveCharacterTextSplitter with custom separators
tailored to Kenyan legal formatting (Orders, Rules, Sections, etc.).
"""

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.services.legal_rag.config import CHUNK_SIZE, CHUNK_OVERLAP

def chunk_legal_text(text: str, source_metadata: dict = None) -> list[Document]:
    """
    Splits legal text semantically based on Kenyan formatting.
    """
    separators = [
        "\nOrder ", 
        "\nORDER ", 
        "\nRule ", 
        "\nRULE ",
        "\nPART ",
        "\nSection ",
        "\n\n", 
        "\n", 
        " "
    ]
    
    text_splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False
    )
    
    chunks = text_splitter.create_documents([text], metadatas=[source_metadata or {}])
    return chunks

def chunk_file(file_path: Path | str) -> list[Document]:
    """
    Reads a cleaned .txt file and chunks it.
    """
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8")
    
    # Inject simple metadata
    is_rules = "rules" in file_path.name.lower()
    source_type = "civil_procedure" if is_rules else "legislation"
    
    metadata = {
        "source": file_path.name,
        "source_type": source_type
    }
    
    return chunk_legal_text(text, metadata)
