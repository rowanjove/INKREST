"""CLI entry point for exporters.

Usage:
    python -m novel_agent.exporters.cli --format txt --root-dir . --output out.txt
    python -m novel_agent.exporters.cli --format epub --root-dir . --output out.epub --title "我的小说"
    python -m novel_agent.exporters.cli --format pdf --root-dir . --output out.pdf --chapter-ids "001,002"
"""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Novel Agent Exporter")
    parser.add_argument("--format", required=True, choices=["txt", "epub", "pdf"], help="Export format")
    parser.add_argument("--root-dir", required=True, help="Project root directory")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--title", default="未命名小说", help="Book title")
    parser.add_argument("--chapter-ids", default=None, help="Comma-separated chapter IDs")
    args = parser.parse_args()

    root_dir = Path(args.root_dir)
    output_path = Path(args.output)
    chapter_ids = [c.strip() for c in args.chapter_ids.split(",")] if args.chapter_ids else None

    from novel_agent.exporters import export_txt, export_epub, export_pdf

    try:
        if args.format == "txt":
            export_txt(root_dir, output_path, chapter_ids=chapter_ids)
        elif args.format == "epub":
            export_epub(root_dir, output_path, chapter_ids=chapter_ids, title=args.title)
        elif args.format == "pdf":
            export_pdf(root_dir, output_path, chapter_ids=chapter_ids, title=args.title)
        print(f"Export complete: {output_path}")
    except Exception as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
