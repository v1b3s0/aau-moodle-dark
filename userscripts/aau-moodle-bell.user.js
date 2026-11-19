// ==UserScript==
// @name         AAU Moodle Bell (moodle-watch)
// @namespace    v1b3s
// @version      1.4
// @description  Replaces Moodle's notification bell with moodle-watch course-change events served from the S20.
// @match        https://online-learning.aau.ac.ae/moodle/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_addStyle
// @connect      100.83.36.81
// @run-at       document-idle
// @homepageURL  https://github.com/v1b3s0/aau-moodle-dark
// @updateURL    https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/userscripts/aau-moodle-bell.user.js
// @downloadURL  https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/userscripts/aau-moodle-bell.user.js
// @license      MIT
// ==/UserScript==

(function () {
  "use strict";

  const SRC = "http://100.83.36.81:8787/events.json"; // S20 over Tailscale
  const REFRESH_MS = 5 * 60 * 1000;
  const COURSE_URL = "https://online-learning.aau.ac.ae/moodle/course/view.php?id=";

  const original = document.querySelector(".popover-region-notifications");
  if (!original) return; // login page etc.

  /* ---------- styles: reuse the dark theme's variables, with fallbacks ---------- */
  GM_addStyle(`
    .popover-region-notifications { display: none !important; }
    .mw-bell { position: relative; display: flex; align-items: center; }
    .mw-toggle { cursor: pointer; position: relative; display: inline-flex; align-items: center; justify-content: center;
      width: 40px; height: 36px; padding: 0 !important; border: 0; border-radius: 8px;
      color: var(--accent, #f9165e); font-size: 1.15rem; background: none; }
    .mw-toggle:hover, .mw-toggle:focus-visible { color: var(--hover, #ff5c8d); background: var(--surface-3, #232020); }
    /* Moodle's .icon has margin-right: .5rem, which pushed the bell off-centre */
    .mw-toggle .icon { margin: 0 !important; width: auto; height: auto; }
    .mw-count { position: absolute; top: -6px; right: -2px; min-width: 18px; height: 18px; padding: 0 5px;
      border-radius: 9px; background: var(--accent-deep, #c0104a); color: #fff; font-size: 11px; font-weight: 700;
      line-height: 18px; text-align: center; }
    .mw-panel { position: absolute; top: calc(100% + 10px); right: 0; width: min(400px, calc(100vw - 24px)); max-height: 70vh; overflow: auto;
      z-index: 1050; background: var(--surface, #121111); border: 1px solid var(--border, #2f2b2b); border-radius: 10px;
      box-shadow: 0 10px 30px rgba(0,0,0,.5); color: var(--text, #f5f3f3); text-align: left; }
    .mw-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px;
      border-bottom: 1px solid var(--border, #2f2b2b); font-weight: 700; position: sticky; top: 0;
      background: var(--surface, #121111); }
    .mw-head button { background: none; border: 0; color: var(--accent, #f9165e); font-weight: 600; cursor: pointer; font-size: .85rem; }
    .mw-head button:hover { color: var(--hover, #ff5c8d); }
    .mw-item { display: block; padding: 12px 16px; border-bottom: 1px solid var(--border, #2f2b2b);
      color: inherit !important; text-decoration: none !important; }
    .mw-item:hover { background: var(--surface-2, #1a1818); }
    .mw-item.mw-unread { box-shadow: inset 3px 0 0 var(--accent, #f9165e); }
    .mw-top { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 4px; }
    .mw-course { font-weight: 700; }
    .mw-time { color: var(--text-soft, #e4e0e0); opacity: .7; font-size: .8rem; white-space: nowrap; }
    .mw-line { font-size: .85rem; line-height: 1.4; color: var(--text-soft, #e4e0e0); }
    .mw-line.add { color: var(--ok-text, #86efac); }
    .mw-line.del { color: var(--bad-text, #fca5a5); }
    .mw-empty { padding: 20px 16px; color: var(--text-soft, #e4e0e0); opacity: .8; }
  `);

  /* ---------- DOM ---------- */
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text; // textContent only: event text comes from teachers
    return n;
  };

  const wrap = el("div", "mw-bell");
  const toggle = el("button", "mw-toggle");
  toggle.type = "button";
  toggle.title = "Course changes (moodle-watch)";
  toggle.setAttribute("aria-label", "Course changes");
  toggle.appendChild(el("i", "icon fa fa-bell fa-fw"));
  const count = el("span", "mw-count");
  count.hidden = true;
  toggle.appendChild(count);

  const panel = el("div", "mw-panel");
  panel.hidden = true;
  const head = el("div", "mw-head");
  head.appendChild(el("span", null, "Course changes"));
  const markBtn = el("button", null, "Mark all read");
  head.appendChild(markBtn);
  const list = el("div");
  panel.append(head, list);

  wrap.append(toggle, panel);
  original.parentNode.insertBefore(wrap, original);

  /* ---------- state ---------- */
  let events = [];
  let status = "Loading…";
  let seenAtOpen = 0; // items newer than this stay highlighted while the panel is open

  const lastSeen = () => GM_getValue("mwLastSeen", 0);
  const maxId = () => events.reduce((m, e) => Math.max(m, e.id || 0), 0);

  function ago(ts) {
    const s = Math.max(0, Date.now() / 1000 - ts);
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    if (s < 7 * 86400) return `${Math.floor(s / 86400)}d ago`;
    return new Date(ts * 1000).toLocaleDateString();
  }

  function updateCount() {
    const n = events.filter((e) => e.id > lastSeen()).length;
    count.textContent = n > 99 ? "99+" : String(n);
    count.hidden = n === 0;
  }

  function render() {
    list.textContent = "";
    if (!events.length) {
      list.appendChild(el("div", "mw-empty", status));
      return;
    }
    for (const e of [...events].reverse()) {
      const a = el("a", "mw-item" + (e.id > seenAtOpen ? " mw-unread" : ""));
      // cid 0 = course not in courses.json (e.g. imported from an old ntfy backup): go to My courses
      a.href = e.cid > 0 ? COURSE_URL + encodeURIComponent(e.cid)
                         : "https://online-learning.aau.ac.ae/moodle/my/courses.php";
      const top = el("div", "mw-top");
      top.append(el("span", "mw-course", e.course || `Course ${e.cid}`), el("span", "mw-time", ago(e.ts)));
      a.appendChild(top);
      for (const line of e.lines || []) {
        const kind = line.startsWith("+") ? " add" : line.startsWith("-") ? " del" : "";
        a.appendChild(el("div", "mw-line" + kind, line.replace(/^[+~-]\s*/, "")));
      }
      list.appendChild(a);
    }
    if (status) list.appendChild(el("div", "mw-empty", status));
  }

  function load() {
    GM_xmlhttpRequest({
      method: "GET",
      url: SRC + "?t=" + Date.now(), // bypass caching
      timeout: 6000,
      onload: (r) => {
        if (r.status === 404) { events = []; status = "No course changes logged yet."; }
        else if (r.status === 200) {
          try {
            const data = JSON.parse(r.responseText);
            events = Array.isArray(data) ? data : [];
            status = "";
          } catch { status = "events.json is unreadable."; }
        } else status = `S20 server error (${r.status}).`;
        updateCount(); if (!panel.hidden) render();
      },
      onerror: () => { status = "Can't reach the S20 (is Tailscale up?)."; updateCount(); if (!panel.hidden) render(); },
      ontimeout: () => { status = "S20 didn't answer in time."; updateCount(); if (!panel.hidden) render(); },
    });
  }

  /* ---------- behaviour ---------- */
  function open() {
    seenAtOpen = lastSeen();
    panel.hidden = false;
    render();
    GM_setValue("mwLastSeen", Math.max(lastSeen(), maxId())); // opening = read
    updateCount();
  }
  const close = () => { panel.hidden = true; };

  toggle.addEventListener("click", (e) => { e.stopPropagation(); panel.hidden ? open() : close(); });
  markBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    GM_setValue("mwLastSeen", maxId());
    seenAtOpen = maxId();
    updateCount(); render();
  });
  document.addEventListener("click", (e) => { if (!wrap.contains(e.target)) close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });

  load();
  setInterval(load, REFRESH_MS);
})();
