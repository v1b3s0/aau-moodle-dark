# Notes for Claude sessions working in this repo

- Every change that should reach devices MUST bump the version, or Stylus/Violentmonkey will ignore it:
  - theme: `AAU Moodle Dark vX.Y` in the `HEADER` of `build/gen_dark.py` (becomes `@version X.Y.0`),
  - userscripts: `@version` in the script header.
- Never edit `aau-moodle-dark.user.css` by hand; change `build/tweaks.css` / `build/gen_dark.py` and
  regenerate with `python3 build/gen_dark.py <all.css> build/aau-moodle-dark.css`
  (needs `pip install tinycss2`). Validate the output parses before committing.
- Never commit the university theme's `all.css`, any Moodle token, ntfy topic, or sesskey.
- Keep everything cosmetic on quiz/assignment pages: no JS that touches answers or submissions.
- Hand fixes in `tweaks.css` use `!important` deliberately; scope phone-sensitive header layout to
  `@media (min-width: 769px)` (the theme collapses header tools below 768px).
