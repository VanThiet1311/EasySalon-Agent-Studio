#!/usr/bin/env python3
"""Theo dõi thay đổi mã nguồn (Frontend HTML/CSS/JS & Backend Python) hỗ trợ Auto-Watch / Hot Reload."""

import glob
import hashlib
import os
import re
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
MODULES_DIR = os.path.join(FRONTEND_DIR, "modules")
STYLE_DIR = os.path.join(FRONTEND_DIR, "style")
STUDIO_DIR = os.path.join(BASE_DIR, "studio")

MODULE_ORDER = [
    "core.js",
    "settings.js",
    "task.js",
    "diagram.js",
    "git.js",
    "logs.js",
    "init.js",
]

STYLE_ORDER = [
    "style.css",
    "task.css",
    "git.css",
    "diagram.css",
    "settings.css",
    "logs.css",
]

_dev_watch_lock = threading.Lock()
_dev_watch_cache = {
    "mtime_key": "",
    "html_template": None,
    "css_hash": "",
    "dom_js_hash": "",
    "py_hash": "",
    "version": "",
    "updated_at": 0.0,
}


def get_watched_python_files():
    py_files = [
        os.path.join(BASE_DIR, "easysalon_studio.py"),
        os.path.join(BASE_DIR, "bridge.py"),
        os.path.join(BASE_DIR, "config.py"),
    ]
    py_files.extend(sorted(glob.glob(os.path.join(STUDIO_DIR, "*.py"))))
    return [fp for fp in py_files if os.path.exists(fp)]


def get_dev_watch_state():
    """Đọc trực tiếp frontend/index.html, frontend/styles.css, frontend/modules/*.js & app.js và tính hash phục vụ Hot Reload."""
    html_fp = os.path.join(FRONTEND_DIR, "index.html")
    css_fp = os.path.join(FRONTEND_DIR, "styles.css")
    js_fp = os.path.join(FRONTEND_DIR, "app.js")
    py_files = get_watched_python_files()

    module_fps = [os.path.join(MODULES_DIR, mf) for mf in MODULE_ORDER]
    existing_module_fps = [fp for fp in module_fps if os.path.exists(fp)]

    style_fps = [os.path.join(STYLE_DIR, sf) for sf in STYLE_ORDER]
    existing_style_fps = [fp for fp in style_fps if os.path.exists(fp)]

    watched_files = [html_fp, css_fp, js_fp, os.path.join(BASE_DIR, ".env")] + existing_module_fps + existing_style_fps + py_files
    mtimes = []
    latest_mtime = 0.0
    for fp in watched_files:
        try:
            if os.path.exists(fp):
                st = os.stat(fp)
                mtimes.append(f"{os.path.basename(fp)}:{st.st_mtime_ns}:{st.st_size}")
                if st.st_mtime > latest_mtime:
                    latest_mtime = st.st_mtime
        except Exception:
            pass
    mtime_key = "|".join(mtimes)

    with _dev_watch_lock:
        if _dev_watch_cache["mtime_key"] == mtime_key and _dev_watch_cache["html_template"] is not None:
            return _dev_watch_cache.copy()

        index_raw = ""
        css_raw = ""
        js_raw = ""
        try:
            if os.path.exists(html_fp):
                with open(html_fp, "r", encoding="utf-8") as f:
                    index_raw = f.read()

            if existing_style_fps:
                css_parts = []
                for fp in existing_style_fps:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                        cleaned = re.sub(r'@import\s+["\'][^"\']+["\'];\s*', '', content)
                        css_parts.append(cleaned)
                css_raw = "\n\n".join(css_parts)
                try:
                    should_write_css = True
                    if os.path.exists(css_fp):
                        with open(css_fp, "r", encoding="utf-8") as f:
                            if f.read() == css_raw:
                                should_write_css = False
                    if should_write_css:
                        with open(css_fp, "w", encoding="utf-8") as f:
                            f.write(css_raw)
                except Exception:
                    pass
            elif os.path.exists(css_fp):
                with open(css_fp, "r", encoding="utf-8") as f:
                    css_raw = f.read()

            if existing_module_fps:
                mod_parts = []
                for fp in existing_module_fps:
                    with open(fp, "r", encoding="utf-8") as f:
                        mod_parts.append(f.read())
                js_raw = "\n\n".join(mod_parts)
                try:
                    should_write_js = True
                    if os.path.exists(js_fp):
                        with open(js_fp, "r", encoding="utf-8") as f:
                            if f.read() == js_raw:
                                should_write_js = False
                    if should_write_js:
                        with open(js_fp, "w", encoding="utf-8") as f:
                            f.write(js_raw)
                except Exception:
                    pass
            elif os.path.exists(js_fp):
                with open(js_fp, "r", encoding="utf-8") as f:
                    js_raw = f.read()
        except Exception:
            pass

        html_tpl = (
            index_raw
            .replace("/* {{STUDIO_CSS}} */", css_raw)
            .replace("{{STUDIO_CSS}}", css_raw)
            .replace("/* {{STUDIO_JS}} */", js_raw)
            .replace("{{STUDIO_JS}}", js_raw)
        )

        py_code_parts = []
        for fp in py_files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    py_code_parts.append(f.read())
            except Exception:
                pass

        dom_js_str = index_raw + "\n" + js_raw
        py_str = "\n".join(py_code_parts)

        css_hash = hashlib.sha1(css_raw.encode("utf-8", errors="ignore")).hexdigest()[:12]
        dom_js_hash = hashlib.sha1(dom_js_str.encode("utf-8", errors="ignore")).hexdigest()[:12]
        py_hash = hashlib.sha1(py_str.encode("utf-8", errors="ignore")).hexdigest()[:12]
        version = f"{css_hash}_{dom_js_hash}_{py_hash}"

        _dev_watch_cache.update({
            "mtime_key": mtime_key,
            "html_template": html_tpl,
            "css_hash": css_hash,
            "dom_js_hash": dom_js_hash,
            "py_hash": py_hash,
            "version": version,
            "updated_at": round(latest_mtime, 3),
        })
        return _dev_watch_cache.copy()
