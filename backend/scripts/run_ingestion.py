#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.services.ingestion.indexer import index_markdown

OUTPUT_DIR = Path("cleaned")

def ingest_file(file_path: Path):
    print(f"Indexing {file_path.name} into Pinecone...")
    text = file_path.read_text(encoding="utf-8")
    try:
        nodes_indexed = index_markdown(text, {"source": file_path.name})
        print(f"Indexed {nodes_indexed} nodes from {file_path.name}.")
    except Exception as e:
        print(f"LlamaIndex upload failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ingest Markdown into Pinecone via LlamaIndex.")
    parser.add_argument("--file", "-f", type=Path, help="Single .md file to ingest.")
    parser.add_argument("--cleaned-dir", "-c", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    if args.file:
        ingest_file(args.file)
        return

    if not args.cleaned_dir.exists():
        print(f"Directory {args.cleaned_dir} does not exist.")
        sys.exit(1)
        
    for file_path in args.cleaned_dir.glob("*.md"):
        ingest_file(file_path)

if __name__ == "__main__":
    main()
