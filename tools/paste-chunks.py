#!/usr/bin/env python3
"""Feed a big file to the RedMagic's clipboard in pieces small enough to paste.

Usage:  python3 paste-chunks.py aau-moodle-dark.min.css [chunk_size]

For each piece it runs `ssh redmagic termux-clipboard-set`, then waits for Enter.
On the phone, paste each piece at the very end of the Stylus editor (long-press -> Paste),
then press Enter here for the next one. The pieces join back into the exact original text.
Termux must be running on the phone (Termux:API does the clipboard work).
"""
import subprocess, sys

path = sys.argv[1] if len(sys.argv) > 1 else "aau-moodle-dark.min.css"
size = int(sys.argv[2]) if len(sys.argv) > 2 else 15000   # last paste broke at ~19.5k chars

text = open(path, encoding="utf-8").read()
chunks = [text[i:i + size] for i in range(0, len(text), size)]
print(f"{len(text)} characters -> {len(chunks)} pieces of up to {size}\n")

for n, chunk in enumerate(chunks, 1):
    r = subprocess.run(["ssh", "redmagic", "termux-clipboard-set"],
                       input=chunk.encode("utf-8"))
    if r.returncode != 0:
        sys.exit(f"ssh/termux-clipboard-set failed on piece {n} (exit {r.returncode})")
    tail = chunk[-25:].replace("\n", " ")
    input(f"[{n}/{len(chunks)}] on clipboard. Paste at the END, check it ends with: ...{tail!r}  then press Enter ")

print("\nAll pieces sent. Save the style in Stylus.")
