"""Generate dark-mode overrides (usage: python3 build/gen_dark.py all.css build/aau-moodle-dark.css) from a Moodle theme stylesheet.

For every rule that sets a light background, a dark text colour or a light
border, emit a rule with the SAME selector (so specificity ties, and Stylus
wins by loading later) that swaps the colour for a palette variable.
Saturated colours (brand buttons, alerts) are left alone.
"""
import sys, colorsys, re
import tinycss2
from tinycss2 import color3

src, out = sys.argv[1], sys.argv[2]
sheet = tinycss2.parse_stylesheet(open(src, encoding="utf-8").read(),
                                  skip_comments=True, skip_whitespace=True)

def lum(c):  # relative luminance, 0 = black, 1 = white
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c.red) + 0.7152 * f(c.green) + 0.0722 * f(c.blue)

def sat(c):
    return colorsys.rgb_to_hls(c.red, c.green, c.blue)[2]

def first_color(tokens):
    """Return the colour token in a value, or None if the value has images/gradients."""
    found = None
    for t in tokens:
        if t.type == "url" or (t.type == "function" and "gradient" in t.lower_name):
            return "IMAGE"
        if t.type in ("whitespace", "comment"):
            continue
        c = color3.parse_color(t)
        if c is not None and not isinstance(c, str):
            found = c
    return found

def is_slate(c):
    """The theme's dark blue-grey family (#2b353b, #435764, #333e45 ...)."""
    h, l, sa = colorsys.rgb_to_hls(c.red, c.green, c.blue)
    return 0.45 < h < 0.70 and 0.04 < sa <= 0.40 and 0.08 < l < 0.40

def map_bg(c):
    if c.alpha < 0.5:
        return None
    if is_slate(c):
        return "var(--surface-3)"
    if sat(c) > 0.25:
        return None
    L = lum(c)
    if L > 0.80: return "var(--surface)"
    if L > 0.55: return "var(--surface-2)"
    return None

def map_text(c, hover=False):
    if c.alpha < 0.3 or sat(c) > 0.25:
        return None
    if hover:
        return "var(--hover)"
    L = lum(c)
    if L < 0.08: return "var(--text)"
    if L < 0.80: return "var(--text-soft)"
    return "var(--text)"

def map_border(c):
    if c.alpha < 0.3 or sat(c) > 0.25:
        return None
    return "var(--border)" if lum(c) > 0.45 else None

BORDER_PROPS = {"border-color", "border-top-color", "border-bottom-color",
                "border-left-color", "border-right-color"}
BORDER_SHORT = {"border", "border-top", "border-bottom", "border-left", "border-right"}

HOVER_RE = re.compile(r":(hover|focus|active)")

def is_hover(sel):
    parts = [p for p in sel.split(",") if p.strip()]
    return bool(parts) and all(HOVER_RE.search(p) for p in parts) and not re.search(r"btn|button|tr:hover|carousel|badge", sel)

def has_saturated_bg(decls):
    for d in decls:
        if d.type == "declaration" and d.lower_name in ("background", "background-color"):
            c = first_color(d.value)
            if c not in (None, "IMAGE") and c.alpha >= 0.5 and sat(c) > 0.25:
                return True
    return False

# Colours that MEAN something (pass/fail, warnings, status) keep their colour.
SEMANTIC_RE = re.compile(r"success|danger|warning|error|alert|correct|incorrect|valid|"
                         r"notify|overdue|late|submission|early|completion|progress|grade|online|offline|"
                         r"\.que\b|feedback|status|required|deprecated|calendar_event|"
                         r"-info\b", re.I)

def accent_for(prop, c, hover):
    """Saturated (branded) colour -> sakura palette."""
    if c.alpha < 0.3 or sat(c) <= 0.25:
        return None
    if prop == "bg":
        return "var(--accent-deep)"
    if prop == "text":
        return "var(--hover)" if hover else "var(--accent)"
    return "var(--accent)"   # borders / accent lines

def convert_decls(content, sel=""):
    decls = tinycss2.parse_declaration_list(content, skip_comments=True, skip_whitespace=True)
    outl = []
    on_colour = has_saturated_bg(decls)   # text on a coloured button/badge: leave it
    hover = is_hover(sel)
    semantic = bool(SEMANTIC_RE.search(sel))
    for d in decls:
        if d.type != "declaration":
            continue
        name = d.lower_name
        imp = " !important" if d.important else ""
        if name in ("background", "background-image"):
            grads = [t for t in d.value if t.type == "function" and "gradient" in t.lower_name]
            if grads and not any(t.type == "url" for t in d.value):
                cols = [color3.parse_color(t) for t in tinycss2.parse_component_value_list(
                        tinycss2.serialize(grads[0].arguments))]
                cols = [c for c in cols if c is not None and not isinstance(c, str)]
                # light, grey gradient -> drop it and use a flat surface colour
                if cols and all(map_bg(c) for c in cols):
                    outl.append(f"background-image: none{imp};")
                    outl.append(f"background-color: {map_bg(cols[-1])}{imp};")
                # branded (saturated) gradient -> flat accent, unless it carries meaning
                elif cols and not semantic and any(accent_for("bg", c, hover) for c in cols):
                    outl.append(f"background-image: none{imp};")
                    outl.append(f"background-color: var(--accent-deep){imp};")
                continue
        c = first_color(d.value)
        if c is None or c == "IMAGE":
            continue
        if name in ("background", "background-color"):
            v = map_bg(c) or (None if semantic else accent_for("bg", c, hover))
            if v: outl.append(f"background-color: {v}{imp};")
        elif name == "color":
            if on_colour:
                continue
            v = map_text(c, hover) or (None if semantic else accent_for("text", c, hover))
            if v: outl.append(f"color: {v}{imp};")
        elif name in BORDER_PROPS:
            v = map_border(c) or (None if semantic else accent_for("border", c, hover))
            if v: outl.append(f"{name}: {v}{imp};")
        elif name in BORDER_SHORT:
            v = map_border(c) or (None if semantic else accent_for("border", c, hover))
            if v: outl.append(f"{name}-color: {v}{imp};")
    return outl

stats = {"rules": 0, "decls": 0}

def walk(rules, indent=""):
    chunks = []
    for r in rules:
        if r.type == "qualified-rule":
            sel = tinycss2.serialize(r.prelude).strip()
            if "vjs" in sel or "video-js" in sel:   # video player is already dark
                continue
            decls = list(dict.fromkeys(convert_decls(r.content, sel)))  # drop duplicates
            if decls:
                if '"' not in sel and "'" not in sel:   # commas inside strings must stay put
                    sel = re.sub(r"\s*,\s*", ",\n" + indent, sel)
                body = "".join(f"{indent}  {d}\n" for d in decls)
                chunks.append(f"{indent}{sel} {{\n{body}{indent}}}\n")
                stats["rules"] += 1
                stats["decls"] += len(decls)
        elif r.type == "at-rule" and r.lower_at_keyword in ("media", "supports") and r.content:
            prelude = tinycss2.serialize(r.prelude).strip()
            if r.lower_at_keyword == "media" and re.match(r"^print\b", prelude):
                continue
            inner = walk(tinycss2.parse_rule_list(r.content, skip_comments=True,
                                                  skip_whitespace=True), indent + "  ")
            if inner:
                chunks.append(f"{indent}@{r.lower_at_keyword} {prelude} {{\n"
                              + "".join(inner) + f"{indent}}}\n")
    return chunks

HEADER = """/* ==== AAU Moodle Dark v2.2 (generated from theme mb2cg 'all' stylesheet) ====
   Edit ONLY the palette below to re-theme everything. */
:root {
  /* near-neutral, very dark blacks (a whisper of red) */
  --bg: #0a0909;          /* page background */
  --surface: #121111;     /* blocks, header (was white) */
  --surface-2: #1a1818;   /* title bars, cards, menus (was light grey) */
  --surface-3: #232020;   /* buttons, hover fills */
  --border: #2f2b2b;      /* borders */
  --input-bg: #060505;    /* text boxes: darker than what they sit on */
  /* text: bright neutral white */
  --text: #f5f3f3;
  --text-soft: #e4e0e0;
  --text-muted: var(--text-soft);
  /* accent: #f9165e (replaces the theme's red / blue / orange / green branding) */
  --accent: #f9165e;      /* links, icons, accent lines */
  --hover: #ff5c8d;       /* anything hovered/focused */
  --accent-deep: #c0104a; /* filled accents: buttons, active items (white text sits on it) */
  --accent-2: var(--accent-deep);
  --highlight: rgba(249, 22, 94, 0.30);  /* highlighted text, selections */
  /* meaning colours, toned for dark: tinted fill + light text */
  --ok-bg: rgba(34, 197, 94, 0.14);    --ok-text: #86efac;
  --bad-bg: rgba(239, 68, 68, 0.16);   --bad-text: #fca5a5;
  --warn-bg: rgba(234, 179, 8, 0.14);  --warn-text: #fde68a;
  --info-bg: rgba(56, 189, 248, 0.12); --info-text: #bae6fd;
}

html, body, #page #page-a, #page #page-b {
  background-color: var(--bg) !important;
  color: var(--text);
}

/* ==== Generated overrides ==== */
"""

import os
body = walk(sheet)
HERE = os.path.dirname(os.path.abspath(__file__))
tweaks_path = os.path.join(HERE, "tweaks.css")
tweaks = open(tweaks_path, encoding="utf-8").read() if os.path.exists(tweaks_path) else ""
css = (HEADER + "\n".join(body)
       + "\n/* ==== Hand tweaks (from tweaks.css) ==== */\n" + tweaks)
open(out, "w", encoding="utf-8").write(css)

# Same theme as an installable UserCSS file: open its URL in a browser with Stylus to
# install it (no copy/paste), and Stylus re-checks @updateURL for newer versions.
VERSION = re.search(r"AAU Moodle Dark v([0-9.]+)", HEADER).group(1)
UPDATE_URL = "https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/aau-moodle-dark.user.css"
usercss = f"""/* ==UserStyle==
@name         AAU Moodle Dark
@namespace    v1b3s
@version      {VERSION}.0
@description  Dark theme for Al Ain University's Moodle
@author       v1b3s
@updateURL    {UPDATE_URL}
@homepageURL  https://github.com/v1b3s0/aau-moodle-dark
@license      MIT
@preprocessor default
==/UserStyle== */

@-moz-document url-prefix("https://online-learning.aau.ac.ae/moodle/") {{
{css}
}}
"""
uc_path = os.path.join(os.path.dirname(HERE), "aau-moodle-dark.user.css")   # repo root
open(uc_path, "w", encoding="utf-8").write(usercss)
print(stats)
