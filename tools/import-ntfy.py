#!/usr/bin/env python3
"""Import moodle-watch notifications from an ntfy Android backup into events.json.

Usage:  python import-ntfy.py <ntfy-backup.json>            # dry run, writes nothing
        python import-ntfy.py <ntfy-backup.json> --apply    # merge into events.json

Only notifications from moodle-watch's own course topic (NTFY_TOPIC in the env file)
whose title is a course in courses.json are imported, so infra/health alerts never reach the bell. The topic is read on the
S20 and never printed.
"""
import json, os, sys
from pathlib import Path

CONF  = Path(os.environ.get("MW_CONF",  Path.home() / ".config" / "moodle-watch"))
STATE = Path(os.environ.get("MW_STATE", Path.home() / ".local" / "share" / "moodle-watch"))
EVENTS = STATE / "events.json"
KEEP = 200

def die(msg):
    print(f"error: {msg}", file=sys.stderr); sys.exit(1)

def load_env():
    env = {}
    for line in (CONF / "env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def first(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if not args:
        die(__doc__.strip().splitlines()[2])

    topic = os.environ.get("NTFY_TOPIC", load_env().get("NTFY_TOPIC", "")).strip()
    if not topic:
        die("NTFY_TOPIC not found in env file")
    courses = json.loads((CONF / "courses.json").read_text())
    label2cid = {v: int(k) for k, v in courses.items()}

    try:
        backup = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except Exception as e:
        die(f"can't read backup: {e}")
    if not isinstance(backup, dict):
        die("backup is not a JSON object")
    print("backup sections:", ", ".join(f"{k}({len(v) if isinstance(v, list) else type(v).__name__})"
                                        for k, v in backup.items()))

    subs = backup.get("subscriptions") or []
    notifs = backup.get("notifications") or []
    if not notifs:
        die("backup has no notifications — re-export choosing the option that includes notifications")

    sub_ids = {first(s, "id") for s in subs if first(s, "topic") == topic}
    if not sub_ids:
        die(f"moodle-watch topic not among the {len(subs)} subscriptions in the backup")

    imported, unmatched = [], {}
    for n in notifs:
        if first(n, "subscriptionId", "subscription_id") not in sub_ids:
            continue
        if n.get("deleted"):
            continue
        ts = first(n, "timestamp", "time", default=0)
        try:
            ts = int(ts)
        except (TypeError, ValueError):
            continue
        if ts > 10**12:          # milliseconds -> seconds
            ts //= 1000
        title = str(first(n, "title", default="")).strip()
        lines = [l for l in str(first(n, "message", default="")).splitlines() if l.strip()]
        if not lines:
            continue
        cid = label2cid.get(title, 0)
        if not cid:
            # course changes are always titled with a course from courses.json;
            # anything else (heartbeat / recovered alerts sent to this topic in the past) is skipped
            unmatched[title or "(no title)"] = unmatched.get(title or "(no title)", 0) + 1
            continue
        imported.append({"ts": ts, "cid": cid, "course": title, "lines": lines})

    # existing log, minus test events
    try:
        existing = json.loads(EVENTS.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    except (FileNotFoundError, ValueError):
        existing = []
    tests = [e for e in existing if str(e.get("course", "")).startswith("TEST")]
    existing = [e for e in existing if e not in tests]

    seen = {(e.get("ts"), e.get("course"), tuple(e.get("lines") or [])) for e in existing}
    new = []
    for i, e in enumerate(sorted(imported, key=lambda e: e["ts"])):
        key = (e["ts"], e["course"], tuple(e["lines"]))
        if key in seen:
            continue
        seen.add(key)
        e["id"] = e["ts"] * 1000 + (i % 1000)   # same scale as log_event's millisecond ids
        new.append(e)

    merged = sorted(existing + new, key=lambda e: e.get("id", 0))[-KEEP:]

    print(f"moodle-watch notifications in backup: {len(imported)}")
    print(f"new (not already in events.json):     {len(new)}")
    print(f"test events removed:                   {len(tests)}")
    if new:
        from datetime import datetime
        fmt = lambda t: datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")
        print(f"date range: {fmt(new[0]['ts'])}  ->  {fmt(new[-1]['ts'])}")
    if unmatched:
        print("skipped (title isn't a course in courses.json):")
        for t, c in sorted(unmatched.items()):
            print(f"  {c:>3} x {t}")
    print(f"events.json after merge: {len(merged)} entries (cap {KEEP})")

    if not apply:
        print("\ndry run — nothing written. Re-run with --apply to merge.")
        return
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = EVENTS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, EVENTS)
    print(f"\nwritten: {EVENTS}")

if __name__ == "__main__":
    main()
