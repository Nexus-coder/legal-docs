#!/usr/bin/env python3
"""
run_ingestion.py – CLI entry-point for the RAG ingestion pipeline.

Usage
-----
    # Dry run against all cleaned texts to verify chunking
    python run_ingestion.py --dry-run
    
    # Ingest all cleaned text files into Pinecone
    python run_ingestion.py

    # Ingest a single file
    python run_ingestion.py --file cleaned/my_document.txt
"""

import argparse
import sys
import logging
from pathlib import Path

from legal_rag.pipeline import ingest_file, ingest_batch
from legal_cleaner.config import setup_logging, OUTPUT_DIR

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="Ingest cleaned legal text into the Pinecone Vector DB."
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="Path to a single cleaned .txt file to ingest.",
    )
    parser.add_argument(
        "--cleaned-dir", "-c",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory containing cleaned .txt files to ingest (default: {OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run chunking but skip embedding and uploading to Pinecone.",
    )
    args = parser.parse_args()

    if args.file:
        if not args.file.exists():
            print(f"Error: file not found – {args.file}", file=sys.stderr)
            sys.exit(1)
        ingest_file(args.file, dry_run=args.dry_run)
        return

    ingest_batch(args.cleaned_dir, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
