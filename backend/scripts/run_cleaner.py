#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.services.ingestion.parser import parse_document

SOURCES_DIR = Path("sources")
OUTPUT_DIR = Path("cleaned")

def process_file(file_path: Path, output_dir: Path):
    try:
        print(f"Parsing {file_path.name} with MarkItDown...")
        markdown_text = parse_document(str(file_path))
        output_file = output_dir / f"{file_path.stem}.md"
        output_file.write_text(markdown_text, encoding="utf-8")
        print(f"Saved cleanly to {output_file}")
    except Exception as e:
        print(f"Failed to parse {file_path.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert docs to LLM-ready Markdown using MarkItDown.")
    parser.add_argument("--file", "-f", type=Path, help="Single file to process.")
    parser.add_argument("--sources-dir", "-s", type=Path, default=SOURCES_DIR)
    parser.add_argument("--output-dir", "-o", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        process_file(args.file, args.output_dir)
        return

    args.sources_dir.mkdir(parents=True, exist_ok=True)
    for file_path in args.sources_dir.glob("*"):
        if file_path.is_file():
            process_file(file_path, args.output_dir)

if __name__ == "__main__":
    main()
