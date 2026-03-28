"""
legal_rag – RAG ingestion pipeline for Kenyan legal documents.
"""

from app.services.legal_rag.pipeline import ingest_file, ingest_batch

__all__ = ["ingest_file", "ingest_batch"]
