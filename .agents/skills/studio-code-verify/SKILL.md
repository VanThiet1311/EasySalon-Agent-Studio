---
name: studio-code-verify
description: Comprehensive quality, syntax, UI styling, and safety verification rules for Easysalon-Tool. Use before committing changes or after modifying frontend modules, HTML views, or backend Python services to prevent runtime regressions and syntax errors.
---

# Easysalon Studio Code Verification & Quality Standards

This skill provides essential guidelines and automated checks for AI agents developing in the **Easysalon-Tool** repository. Follow these rules to prevent recurring runtime errors, styling violations, and broken script evaluations.

---

## 1. Safety & Testing Rules (CRITICAL)

- **NEVER RUN DATABASE OR JIRA TESTS**:
  - **TUYỆT ĐỐI NÉ / KHÔNG CHẠY** any test suites, scripts, or fixtures related to Database or Jira (e.g., `test_mysql*`, `test_database*`, `test_jira*`, tests that mutate MySQL DB data or make mutation requests to Jira).
  - Do NOT run generic `pytest` or `unittest` commands that discover and run these tests automatically.
- **Allowed verification**:
  - Run syntax compilation: `node -c frontend/modules/*.js`, `node -c frontend/app.js`, `python3 -m py_compile`.
  - Run the repository verification script:
    ```bash
    python3 .agents/skills/studio-code-verify/verify.py
    ```
  - Functional end-to-end testing is conducted by the user.

---

## 2. Frontend Architecture & Bundling Rules

The frontend uses modular files in `frontend/modules/` that are dynamically concatenated into `frontend/app.js` and inlined into `frontend/index.html` via `studio/dev_watch.py`.

### Module Load Order:
1. `common.js`
2. `core.js`
3. `settings.js`
4. `task.js`
5. `diagram.js`
6. `git.js`
7. `logs.js`
8. `jira.js`
9. `notes.js`
10. `init.js`

### Mandatory Rules for JS Modules:
1. **Window Exports**:
   - Any function invoked from HTML (`onclick`, `oninput`, `onchange`, `onsubmit`) or across different modules **MUST** be explicitly exported to `window` (e.g. `window.sendActiveJiraToTask = sendActiveJiraToTask;`).
   - Forgetting `window.funcName = funcName;` causes `ReferenceError: funcName is not defined` when the user clicks the UI element.
2. **Prevent Top-Level Script Failure**:
   - Because all modules are concatenated into a single evaluation context in `frontend/app.js`, a single uncaught syntax error or top-level runtime exception immediately aborts the evaluation of all subsequent modules.
   - Never declare duplicate top-level `const` or `let` variables with identical names across modules.
3. **HTML Escaping**:
   - Always sanitize dynamic strings before inserting into `.innerHTML` using `escapeHtml(str)` to prevent XSS and broken HTML layout.
4. **Preserve Exact Regex Anchors & Code Integrity**:
   - Critical functions like `switchDiagramViewTab(tab)` in `frontend/app.js` rely on exact regex matching ending with `\n    }` (4 spaces).
   - Do not alter spacing or delete core function signatures unless explicitly requested.

---

## 3. UI Settings, Colors & Design Standards

Follow the strict visual standards defined in `AGENTS.md`:

1. **Active Background Color**:
   - When tabs or cards in Settings (Sidebar tab, Model family tab, Effort card, Engine card) or Filters are active (`.is-active`), the background **LUÔN LUÔN là màu xanh dương (#1677ff)** (`linear-gradient(135deg, #1677ff 0%, #0958d9 100%)`).
   - Active text is always white (`#ffffff`).
   - **Tuyệt đối không dùng** dark cyan (`bg-cyan-950`) or dark/murky colors for active state.
2. **Clean Typography**:
   - Standard font: `'Be Vietnam Pro', Inter, system-ui, -apple-system, sans-serif` (`font-sans`) for regular text, badges, titles, and Vietnamese content.
   - **Never apply `font-mono`** to regular descriptions, badges, or Vietnamese text. `font-mono` is strictly reserved for code, file paths, commit hashes, logs, and terminal commands.
3. **Minimalist Aesthetic (No Emoji Clutter)**:
   - Remove frivolous emojis (`🧠`, `🚀`, `⚡`, `⚖️`, `🟣`, `🟢`, `💡`, `⚙️`) from titles, selectors, tabs, and action cards. Keep the design elegant, clean, and adhering to modern Ant Design / SaaS standards.

---

## 4. Jira Formatting & Media Handling

1. **Clean Formatting Artifacts**:
   - Jira text often contains raw wiki/markdown bold markers (`**text**`), stray/italic slashes (`//text//` or `//`), or verbose markdown attachment links (`[image-xxx.png](/api/jira/attachment?id=...)`).
   - Use `formatJiraText(text)` (in `frontend/modules/jira.js` and `studio/services/jira_service.py`) to clean `**` and `//` while preserving URLs (`http://`, `https://`, `/api/...`).
   - Reformat inline image links into clean textual references like `[Ảnh minh chứng: filename.png]`.
2. **Attachment ID Resolution**:
   - Jira ADF nodes store media as UUIDs (`attrs.id = "6be5d0c9-..."`), but Jira Cloud attachment download endpoints require numeric attachment IDs (`fields.attachment[].id = 32318`).
   - Always map ADF media UUIDs and filenames to numeric IDs via `_ATTACHMENT_ID_MAP` in `studio/services/jira_service.py` to prevent HTTP 404 errors.
3. **Interactive Image Preview (Lightbox Modal)**:
   - All attachment thumbnails and inline description images must support click-to-preview via `openImagePreviewModal(url, title)` with ESC or backdrop click to close.

---

## 5. Git Conflict & Rollback Standards

- All Git conflict modals (Pull, Cherry-pick, Merge) must include the standard rollback button:
  `Trở lại trạng thái chưa merge hay cherry-pick` (triggering `doAbortConflictAction(role)` -> `git merge --abort` / `git cherry-pick --abort`).
- Provide interactive CodeLens buttons (`Accept Current Change`, `Accept Incoming Change`, `Accept Both Changes`).

---

## 6. Pre-Commit Verification Checklist

Before completing any task, execute:
```bash
python3 .agents/skills/studio-code-verify/verify.py
```
Ensure all 4 phases pass:
- [x] Python syntax check (`py_compile`)
- [x] JavaScript syntax check (`node -c`)
- [x] dev_watch bundle generation & hash calculation
- [x] HTML event handlers binding audit (all `onclick`/`oninput`/`onchange` functions exist and are exported)
