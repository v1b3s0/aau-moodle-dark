// ==UserScript==
// @name         AAU Moodle Courses
// @namespace    v1b3s
// @version      1.1
// @description  Hand-ordered, colour-coded course list: replaces the dashboard's Course overview and tidies the Navigation block.
// @match        https://online-learning.aau.ac.ae/moodle/*
// @grant        GM_addStyle
// @run-at       document-idle
// @homepageURL  https://github.com/v1b3s0/aau-moodle-dark
// @updateURL    https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/userscripts/aau-moodle-courses.user.js
// @downloadURL  https://raw.githubusercontent.com/v1b3s0/aau-moodle-dark/main/userscripts/aau-moodle-courses.user.js
// @license      MIT
// ==/UserScript==

(function () {
  "use strict";

  /* ======================= EDIT THIS WHEN COURSES CHANGE =======================
     Order here = order on the dashboard and in the Navigation block.
     id:   the number after course/view.php?id= in the course's URL
     name: what to show (Moodle's own name is replaced)
     rgb:  colour as "r, g, b" (shown as a translucent fill, like the text highlight) */
  const COURSES = [
    { id: 8155, name: "DSA-62D",               rgb: "88, 101, 242"  }, // blurple
    { id: 8560, name: "DSA-2D",                rgb: "165, 180, 252" }, // light blurple (lab)
    { id: 8684, name: "Physics I-63D",         rgb: "147, 51, 234"  }, // purple
    { id: 8244, name: "Physics I Lab-62D",     rgb: "192, 132, 252" }, // light purple
    { id: 7904, name: "Physics I Tutorial",    rgb: "192, 132, 252" }, // light purple (tutorial, 2D)
    { id: 8632, name: "Linear Algebra-63D",    rgb: "249, 115, 22"  }, // orange
    { id: 8250, name: "English 2-61D",         rgb: "22, 163, 74"   }, // dark green
  ];
  /* Courses to remove completely from the Navigation block. */
  const HIDE = [1365]; // مساق تعليمي للطلاب (orientation course)
  /* ============================================================================ */

  const BASE = "https://online-learning.aau.ac.ae/moodle/course/view.php?id=";
  const byId = new Map(COURSES.map((c, i) => [c.id, { ...c, order: i }]));
  const idOf = (a) => {
    const m = /course\/view\.php\?id=(\d+)$/.exec(a.getAttribute("href") || "");
    return m ? Number(m[1]) : null;
  };

  GM_addStyle(`
    /* dashboard: hide Moodle's filters, search and banner cards */
    .block_myoverview [data-region="myoverview"] { display: none !important; }
    .mw-courses { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; margin-top: 4px; }
    .mw-course {
      display: flex; align-items: center; min-height: 64px; padding: 14px 18px;
      background-color: rgba(var(--course), .30); border: 1px solid rgba(var(--course), .55);
      border-radius: 10px; color: var(--text, #f5f3f3) !important; font-weight: 700 !important;
      font-size: 1.05rem; text-decoration: none !important;
      transition: background-color .12s ease, transform .12s ease;
    }
    .mw-course:hover, .mw-course:focus-visible {
      background-color: rgba(var(--course), .50); color: #fff !important; transform: translateY(-2px);
    }
  `);

  /* ---------- Dashboard: Course overview -> compact coloured boxes ---------- */
  const overview = document.querySelector(".block_myoverview .card-text");
  if (overview && !overview.querySelector(".mw-courses")) {
    const grid = document.createElement("div");
    grid.className = "mw-courses";
    for (const c of COURSES) {
      const a = document.createElement("a");
      a.className = "mw-course";
      a.href = BASE + c.id;
      a.style.setProperty("--course", c.rgb);
      a.textContent = c.name;
      grid.appendChild(a);
    }
    overview.prepend(grid);
  }

  /* ---------- Navigation block: order, rename, colour, hide ---------- */
  function fixNav() {
    const block = document.querySelector(".block_navigation");
    if (!block) return;
    const items = new Map(); // parent <ul> -> [{li, order}]
    for (const a of block.querySelectorAll('.tree_item a[href*="course/view.php?id="]')) {
      const id = idOf(a);
      if (id == null) continue;
      const li = a.closest("li");
      if (HIDE.includes(id)) { if (li) li.remove(); continue; }
      const c = byId.get(id);
      if (!c) continue;
      a.style.setProperty("--course", c.rgb);
      const label = a.querySelector(".item-content-wrap");
      if (label) label.textContent = c.name; else a.lastChild && (a.lastChild.textContent = c.name);
      a.title = c.name;
      if (li && li.parentElement) {
        if (!items.has(li.parentElement)) items.set(li.parentElement, []);
        items.get(li.parentElement).push({ li, order: c.order });
      }
    }
    // re-append in configured order; anything not in COURSES stays where it was, before them
    for (const [ul, list] of items) {
      list.sort((x, y) => x.order - y.order).forEach(({ li }) => ul.appendChild(li));
    }
  }
  fixNav();
})();
