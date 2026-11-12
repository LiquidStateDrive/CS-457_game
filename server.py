#!/usr/bin/env python3
"""Nine Men's Morris Game Server CLI.

Conforms to docs/other_specifications.md:
-h Displays usage message
-p Listening port (required; binds to 0.0.0.0).
"""

import argparse
import sys
from src.server_fsm import GameServer


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Nine Men's Morris Game Server",
        add_help=True,
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        required=True,
        help="Listening port (required; binds to 0.0.0.0)",
    )
    return parser.parse_args(args)


def main():
    args = parse_args()
    server = GameServer(host="0.0.0.0", port=args.port)
    try:
        server.serve_forever()
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
