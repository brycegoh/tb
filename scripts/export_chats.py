#!/usr/bin/env python3
"""List project chats or export explicitly selected chat IDs as OTLP JSON.

Examples:
  python3 scripts/export_chats.py --list
  python3 scripts/export_chats.py --chat-id CHAT_ID [--chat-id ANOTHER_ID]
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile


PROJECT = Path(__file__).resolve().parents[1]


def attributes(values):
    return [{"key": k, "value": {"stringValue": str(v)}} for k, v in values.items()]


def timestamp_ns(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = dt - epoch
    return str((delta.days * 86400 + delta.seconds) * 10**9 + delta.microseconds * 1000)


def read_session(path, project, home=None, limit=None, seen=()):
    """Read only complete JSONL records; ignore an active writer's partial tail."""
    if path in seen:
        raise ValueError("Circular chat history reference")
    with path.open("rb") as stream:
        first = json.loads(next(stream))
        meta = first.get("payload", {})
        if first.get("type") != "session_meta" or Path(meta.get("cwd", "")).resolve() != project:
            return None
        messages = []
        base = meta.get("history_base")
        if base:
            base_id = base["thread_id"]
            if home is None or not re.fullmatch(r"[a-f0-9-]+", base_id):
                raise ValueError("Cannot resolve chat history base")
            candidates = [p for folder in ("sessions", "archived_sessions")
                          for p in (home / folder).rglob(f"*{base_id}.jsonl")]
            if len(candidates) != 1:
                raise ValueError(f"Expected one history segment for {base_id}; found {len(candidates)}")
            earlier = read_session(candidates[0], project, home,
                                   base["end_byte_offset"], (*seen, path))
            if earlier is None:
                raise ValueError("History segment does not belong to this project")
            messages.extend(earlier[1])
        for number, line in enumerate(stream, 2):
            if limit is not None and stream.tell() > limit:
                break
            if not line.endswith(b"\n"):
                break
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON") from exc
            payload = record.get("payload", {})
            if record.get("type") != "response_item" or payload.get("type") != "message":
                continue
            role = payload.get("role")
            if role not in ("user", "assistant"):
                continue
            parts = []
            for part in payload.get("content", []):
                if part.get("type") in ("input_text", "output_text", "text"):
                    text = part.get("text", "")
                    if role == "user" and text.lstrip().startswith(("<environment_context>", "# AGENTS.md instructions")):
                        continue
                    parts.append(text)
                elif part.get("type") in ("input_image", "image"):
                    parts.append("[Image attachment]")
            text = "\n".join(parts)
            if text.strip():
                messages.append((record["timestamp"], role, payload.get("phase") or "", text))
    return meta, messages


def session_paths(home, project):
    # The index also locates archived or migrated rollouts. Fall back to files
    # when the index is absent. Always verify the session's own cwd before export.
    databases = sorted(home.glob("state_*.sqlite"), key=lambda p: int(p.stem.split("_")[-1]))
    if databases:
        with sqlite3.connect(databases[-1].resolve().as_uri() + "?mode=ro", uri=True) as db:
            return [Path(row[0]) for row in db.execute(
                "SELECT rollout_path FROM threads WHERE cwd = ?", (str(project),)
            )]
    return [p for folder in ("sessions", "archived_sessions") for p in (home / folder).rglob("*.jsonl")]


def write_atomic(path, text):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(text)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def portable_links(text, project, output):
    """Resolve project links relative to the JSON file, like Markdown links."""
    def replace(match):
        target = match.group(2)
        location = target[1:-1] if target.startswith("<") and target.endswith(">") else target
        if not location.startswith("/"):
            return match.group(0)
        path = Path(location).resolve()
        try:
            path.relative_to(project)
        except ValueError:
            return match.group(0)
        relative = Path(os.path.relpath(path, output.resolve())).as_posix()
        if target.startswith("<") or " " in relative:
            relative = f"<{relative}>"
        return match.group(1) + relative + match.group(3)

    return re.sub(r"(!?\[[^\]\n]*\]\()(<[^>\n]+>|[^)\n]+)(\))", replace, text)


def project_sessions(home, project):
    sessions = {}
    for path in sorted(set(session_paths(home, project))):
        with path.open(encoding="utf-8") as stream:
            first = json.loads(next(stream))
        meta = first.get("payload", {})
        if first.get("type") == "session_meta" and Path(meta.get("cwd", "")).resolve() == project:
            session_id = str(meta.get("id") or meta["session_id"])
            sessions[session_id] = (path, meta)
    return sessions


def export(home, project, output, selected_ids):
    project = project.resolve()
    if not selected_ids:
        raise ValueError("Select at least one chat ID; use --list to find chats.")
    sessions = project_sessions(home, project)
    missing = set(selected_ids) - sessions.keys()
    if missing:
        raise ValueError("Chat IDs not found in this project: " + ", ".join(sorted(missing)))
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    failures = 0
    for selected_id in dict.fromkeys(selected_ids):
        path = sessions[selected_id][0]
        try:
            session = read_session(path, project, home)
            if session is None:
                continue
            meta, messages = session
            session_id = str(meta.get("id") or meta["session_id"])
            if Path(session_id).name != session_id or session_id in (".", ".."):
                raise ValueError("unsafe session id")
            logs = []
            for index, (stamp, role, phase, text) in enumerate(messages):
                logs.append({
                    "timeUnixNano": timestamp_ns(stamp),
                    "severityNumber": 9,
                    "severityText": "INFO",
                    "body": {"stringValue": portable_links(text, project, output)},
                    "attributes": attributes({
                        "event.name": "chat.message", "gen_ai.conversation.id": session_id,
                        "chat.role": role, "chat.phase": phase, "chat.message.index": index,
                    }),
                })
            document = {"resourceLogs": [{
                "resource": {"attributes": attributes({
                    "service.name": "codex-chat",
                    "project.path": Path(os.path.relpath(project, output.resolve())).as_posix(),
                })},
                "scopeLogs": [{"scope": {"name": "tb.chat_export", "version": "1.0.0"}, "logRecords": logs}],
            }]}
            write_atomic(output / f"{session_id}.otlp.json", json.dumps(document, ensure_ascii=False, indent=2) + "\n")
            print(f"Exported {session_id}: {len(messages)} messages")
            count += 1
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            print(f"Could not export {path}: {exc}", file=sys.stderr)
            failures += 1
    print(f"{count} chat(s) exported to {output}")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true", help="List available project chats without exporting")
    action.add_argument("--chat-id", action="append", help="Export only this chat ID; repeat to select multiple chats")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--output", type=Path, help="Default: <project>/chat_ot_logs")
    args = parser.parse_args()
    project = args.project.resolve()
    try:
        home = args.codex_home.expanduser()
        if args.list:
            for session_id, (_, meta) in project_sessions(home, project).items():
                print(f"{session_id}\t{meta.get('timestamp', '')}")
            return 0
        return export(home, project, args.output or project / "chat_ot_logs", args.chat_id)
    except (OSError, sqlite3.Error, ValueError, KeyError, StopIteration) as exc:
        parser.exit(1, f"Export failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
