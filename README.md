# AAU Moodle Dark

A dark theme and two small userscripts for Al Ain University's Moodle
(`https://online-learning.aau.ac.ae/moodle/`). Everything is client-side: it only changes how the
site looks in your own browser.

## Install (once per device)

Install [Stylus](https://addons.mozilla.org/firefox/addon/styl-us/) and
[Violentmonkey](https://addons.mozilla.org/firefox/addon/violentmonkey/), then open each link below.
The extension shows an install page; tap **Install**. Works on Firefox for desktop and Android.

| What | Extension | Install link |
|---|---|---|
| Dark theme | Stylus | [aau-moodle-dark.user.css](https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/aau-moodle-dark.user.css) |
| Course list (dashboard boxes + Navigation order/colours) | Violentmonkey | [aau-moodle-courses.user.js](https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/userscripts/aau-moodle-courses.user.js) |
| moodle-watch bell (needs Tailscale to the S20) | Violentmonkey | [aau-moodle-bell.user.js](https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/userscripts/aau-moodle-bell.user.js) |

Updates arrive automatically: both extensions re-check these links on a schedule and install any
file whose `@version` went up. To pull one immediately, use the extension's "check for updates".

## Layout

```
aau-moodle-dark.user.css     installable theme (generated — do not edit by hand)
userscripts/                 Violentmonkey scripts (edit directly)
build/gen_dark.py            generator: theme stylesheet -> dark overrides + tweaks.css
build/tweaks.css             all hand-written fixes (edit this, then regenerate)
tools/import-ntfy.py         one-off: import old ntfy notifications into moodle-watch's events.json
tools/paste-chunks.py        fallback: push a big file to a phone's clipboard in pieces
```

## Changing the theme

1. Edit `build/tweaks.css` (or the palette at the top of `HEADER` in `build/gen_dark.py`).
2. Bump the version in the `HEADER` comment of `build/gen_dark.py` (`AAU Moodle Dark vX.Y`).
3. Regenerate: `python3 build/gen_dark.py all.css build/aau-moodle-dark.css`
   (`all.css` = the theme's `all` stylesheet, saved from DevTools → Style Editor; it stays out of git).
4. Commit and push. Devices update on their next check.

## Changing the course list

Edit the `COURSES` list at the top of `userscripts/aau-moodle-courses.user.js`
(order = display order; `id` = number after `course/view.php?id=`), bump `@version`, push.

## Licence

MIT — see `LICENSE`. The university theme's own stylesheet is not included.
