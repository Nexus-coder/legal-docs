"""
pipeline.py – Orchestration for the RAG ingestion process.
"""

import logging
from pathlib import Path

from legal_rag.chunker import chunk_file
from legal_rag.vectorstore import upload_chunks

logger = logging.getLogger(__name__)

def ingest_file(file_path: Path | str, dry_run: bool = False):
    """ 
    Reads a cleaned text file, chunks it, and optionally uploads to Pinecone. 
    """
    file_path = Path(file_path)
    logger.info("📄 Ingesting: %s", file_path.name)
    
    chunks = chunk_file(file_path)
    logger.info("   Success: Generated %d semantic chunks.", len(chunks))
    
    if dry_run:
        logger.info("   [DRY RUN] Skipping vector upload.")
        if chunks:
            logger.debug("   Sample chunk preview:\n---\n%s\n---", chunks[0].page_content[:300])
        return chunks
        
    upload_chunks(chunks)
    logger.info("✅ Ingestion complete for %s", file_path.name)
    return chunks

def ingest_batch(directory: Path | str, dry_run: bool = False):
    """
    Processes all .txt files in a directory.
    """
    directory = Path(directory)
    txt_files = sorted(directory.glob("*.txt"))
    
    if not txt_files:
        logger.warning("No .txt files found in %s", directory)
        return []
    
    logger.info("Found %d file(s) in %s", len(txt_files), directory)
    
    all_chunks = []
    for file_path in txt_files:
        try:
            chunks = chunk_file(file_path)
            all_chunks.extend(chunks)
        except Exception:
            logger.exception("❌ Failed to chunk %s", file_path.name)
            continue
            
    logger.info("Generated a total of %d chunks from %d files.", len(all_chunks), len(txt_files))
    
    if dry_run:
        logger.info("[DRY RUN] Skipping batch vector upload.")
        return all_chunks
        
    upload_chunks(all_chunks)
    logger.info("✅ Batch ingestion complete.")
    return all_chunks
