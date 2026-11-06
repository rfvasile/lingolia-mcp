"""lingolia-mcp [--data-dir DIR] serve | update | status | search QUERY"""

import argparse
import json
import os
from pathlib import Path

from lingolia_mcp.index import Index

MAX_FAILED = 0.1  # share of pages that may fail before an update keeps the old index


def default_data_dir() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "lingolia-mcp"


def main() -> None:
    parser = argparse.ArgumentParser(prog="lingolia-mcp", description="Lingolia's French rules for Claude, over MCP")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir(), help="where the index lives (default: %(default)s)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="the MCP server, on stdio")
    commands.add_parser("update", help="read Lingolia's rule pages into the index, one a second")
    commands.add_parser("status", help="what the index holds")
    search = commands.add_parser("search", help="answer a query as find_rule would")
    search.add_argument("query")
    args = parser.parse_args()
    index = Index(args.data_dir / "rules.db")

    match args.command:
        case "serve":
            from lingolia_mcp.server import build_server

            build_server(index).run(show_banner=False)
        case "update":
            from lingolia_mcp.crawl import crawl

            pages, failed = crawl()
            if not pages or failed > MAX_FAILED * (len(pages) + failed):
                raise SystemExit(f"✗ {failed} pages failed, {len(pages)} read: the index is unchanged")
            index.replace(pages)
            print(f"✓ {len(pages)} pages, {sum(len(p.sections) for p in pages)} sections in {index.path}")
        case "status":
            status = index.status()
            print(f"{status['pages']} pages, {status['sections']} sections, built {status['built']}" if status else "No index yet: run `lingolia-mcp update`.")
        case "search":
            print(json.dumps(index.search(args.query), ensure_ascii=False, indent=1))
