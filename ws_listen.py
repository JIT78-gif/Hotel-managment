"""Tiny helper to watch the staff WebSocket from the command line.

Usage:
    python ws_listen.py <staff_jwt>

Pass the staff_token returned by POST /auth/activate (the long eyJ... string).
Prints every event the backend pushes. Ctrl+C to stop.
"""
import json
import sys

from websockets.sync.client import connect

DEFAULT_URL = "ws://localhost:8000/ws/staff"


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__)
        sys.exit(1)

    token = sys.argv[1].strip().strip("<>").strip('"').strip("'")
    if not token.startswith("eyJ"):
        print(f"WARNING: token doesn't look like a JWT (should start with 'eyJ'). Got: {token[:20]}...")

    url = f"{DEFAULT_URL}?token={token}"
    print(f"Connecting to {DEFAULT_URL} ... (Ctrl+C to stop)")
    with connect(url) as ws:
        print("Connected. Waiting for events.\n")
        try:
            while True:
                msg = ws.recv()
                try:
                    print(json.dumps(json.loads(msg), indent=2))
                except (ValueError, TypeError):
                    print(msg)
                print("-" * 50)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
