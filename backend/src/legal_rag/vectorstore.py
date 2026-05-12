"""
vectorstore.py – Embeddings and Vector DB integration.
"""

import logging
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from src.legal_rag.config import rag_settings

logger = logging.getLogger(__name__)


def upload_chunks(chunks):
    """
    Embeds chunks using text-embedding-3-small and uploads to the Vector DB.
    """
    if not rag_settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    if not (rag_settings.PINECONE_API_KEY and rag_settings.PINECONE_INDEX_NAME):
        raise ValueError("PINECONE_API_KEY or PINECONE_INDEX_NAME is not set.")

    logger.info("Initializing OpenAI embeddings (model: text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=rag_settings.OPENAI_API_KEY
    )

    logger.info(
        f"Uploading {len(chunks)} chunks to Pinecone index '{rag_settings.PINECONE_INDEX_NAME}'..."
    )

    # PineconeVectorStore automatically batches the embedding API calls and uploads
    vector_store = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=rag_settings.PINECONE_INDEX_NAME,
        pinecone_api_key=rag_settings.PINECONE_API_KEY,
    )

    logger.info("Upload complete. The Knowledge Layer is updated.")
    return vector_store
