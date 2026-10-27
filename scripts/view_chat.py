"""Serve the project chat viewer and open a selected export in a browser."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
import webbrowser


PROJECT = Path(__file__).resolve().parents[1]


def select_chat(value, project=PROJECT):
    folder = (project / "chat_ot_logs").resolve()
    if value is None:
        files = sorted(folder.glob("*.otlp.json"))
        return files[0] if len(files) == 1 else None
    candidate = Path(value)
    if not candidate.is_absolute():
        if candidate.suffix == ".json":
            candidate = project / candidate if candidate.parts[0] == "chat_ot_logs" else folder / candidate
        else:
            candidate = folder / f"{value}.otlp.json"
    candidate = candidate.resolve()
    if not candidate.is_relative_to(folder) or not candidate.is_file() or not candidate.name.endswith(".otlp.json"):
        raise ValueError("Choose an existing .otlp.json file inside chat_ot_logs/, or its chat ID.")
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chat", nargs="?", help="Chat ID or exported JSON path; auto-loads when there is one export")
    parser.add_argument("--port", type=int, default=8000, help="Preferred localhost port (default: 8000; falls back to a free port)")
    parser.add_argument("--no-open", action="store_true", help="Print the viewer URL without launching a browser")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535.")
    try:
        selected = select_chat(args.chat)
    except ValueError as exc:
        parser.error(str(exc))
    handler = partial(SimpleHTTPRequestHandler, directory=str(PROJECT))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_port}/chat_viewer.html"
    if selected:
        url += "?" + urlencode({"chat": selected.relative_to(PROJECT).as_posix()})
    print(f"Chat viewer: {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    with server:
        if not args.no_open:
            try:
                if not webbrowser.open(url):
                    print("Open the URL above in your browser.", flush=True)
            except webbrowser.Error:
                print("Open the URL above in your browser.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
