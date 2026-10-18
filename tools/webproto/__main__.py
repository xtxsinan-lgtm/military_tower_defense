"""CLI entry point for tools.webproto (`python3 -m tools.webproto --port 8765`)."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .server import run_server


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.webproto",
        description="Nightwatch Interactive Web Paper Prototype Server (D4-2)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose HTTP request logging")
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
