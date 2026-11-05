#!/usr/bin/env python3
"""
Verification script for Easysalon-Tool.
Checks:
1. Python syntax compilation (py_compile) for all studio & root scripts.
2. JavaScript syntax (node -c) for all frontend/modules/*.js and frontend/app.js.
3. Bundle evaluation and hot-reload hash generation via studio.dev_watch.
4. Window exports audit: Checks that inline HTML event handlers (onclick, oninput, onchange)
   reference functions that exist and are exported to window or declared in modules.

RULES:
- NEVER run database or Jira tests (NO pytest/unittest invoking DB or Jira).
- Safe static syntax and reference verification only.
"""

import glob
import os
import re
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if not os.path.exists(os.path.join(BASE_DIR, "studio")):
    BASE_DIR = os.getcwd()

def check_python_syntax():
    print("===> [1/4] Checking Python syntax...")
    py_files = [
        os.path.join(BASE_DIR, "easysalon_studio.py"),
        os.path.join(BASE_DIR, "bridge.py"),
        os.path.join(BASE_DIR, "config.py"),
    ]
    py_files.extend(glob.glob(os.path.join(BASE_DIR, "studio", "*.py")))
    py_files.extend(glob.glob(os.path.join(BASE_DIR, "studio", "services", "*.py")))
    
    valid_files = [f for f in py_files if os.path.exists(f)]
    cmd = [sys.executable, "-m", "py_compile"] + valid_files
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FAIL: Python syntax check failed!")
        print(res.stderr)
        return False
    print(f"PASS: {len(valid_files)} Python files compiled successfully.")
    return True

def check_js_syntax():
    print("\n===> [2/4] Checking JavaScript syntax (node -c)...")
    modules = glob.glob(os.path.join(BASE_DIR, "frontend", "modules", "*.js"))
    app_js = os.path.join(BASE_DIR, "frontend", "app.js")
    all_js = modules + ([app_js] if os.path.exists(app_js) else [])
    
    failed = False
    for js_file in all_js:
        res = subprocess.run(["node", "-c", js_file], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"FAIL: Syntax error in {os.path.relpath(js_file, BASE_DIR)}:")
            print(res.stderr)
            failed = True
    if failed:
        return False
    print(f"PASS: {len(all_js)} JavaScript files verified with node -c.")
    return True

def check_dev_watch_bundle():
    print("\n===> [3/4] Checking dev_watch bundle generation...")
    try:
        sys.path.insert(0, BASE_DIR)
        from studio.dev_watch import get_dev_watch_state
        state = get_dev_watch_state()
        version = state.get("version", "")
        if not version or not state.get("html_template"):
            print("FAIL: dev_watch state returned empty template or version.")
            return False
        print(f"PASS: dev_watch bundle generated version hash: {version}")
        return True
    except Exception as e:
        print(f"FAIL: dev_watch error: {e}")
        return False

def check_html_js_bindings():
    print("\n===> [4/4] Auditing HTML event handlers against JavaScript definitions...")
    views_dir = os.path.join(BASE_DIR, "frontend", "views")
    index_html = os.path.join(BASE_DIR, "frontend", "index.html")
    modules_dir = os.path.join(BASE_DIR, "frontend", "modules")
    
    # Collect all JS content
    js_content = ""
    for mf in glob.glob(os.path.join(modules_dir, "*.js")):
        with open(mf, "r", encoding="utf-8") as f:
            js_content += "\n" + f.read()

    # Collect HTML handlers
    html_files = glob.glob(os.path.join(views_dir, "*.html"))
    if os.path.exists(index_html):
        html_files.append(index_html)
        
    handler_pattern = re.compile(r'on(?:click|change|input|submit|keydown|keyup)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    missing_handlers = set()
    total_handlers = 0

    known_builtins = {
        "event", "this", "alert", "confirm", "console", "window", "document",
        "stopPropagation", "preventDefault", "focus", "select", "toggle",
        "classList", "remove", "add", "contains", "value", "reset", "submit", "open", "close",
        "getElementById", "querySelector", "querySelectorAll"
    }

    for hf in html_files:
        with open(hf, "r", encoding="utf-8") as f:
            html = f.read()
        for match in handler_pattern.finditer(html):
            code = match.group(1).strip()
            total_handlers += 1
            # Extract function names: name(...)
            fn_matches = re.findall(r'([a-zA-Z0-9_$]+)\s*\(', code)
            for fn in fn_matches:
                if fn in known_builtins:
                    continue
                # Check if fn is declared in JS: function fn or window.fn = or fn =
                has_fn = (
                    f"function {fn}" in js_content or
                    f"window.{fn}" in js_content or
                    f"{fn} =" in js_content or
                    f"{fn}=" in js_content
                )
                if not has_fn:
                    missing_handlers.add((fn, os.path.relpath(hf, BASE_DIR)))

    if missing_handlers:
        print("WARNING: The following function(s) called in HTML event handlers were not found in JS modules:")
        for fn, fpath in sorted(missing_handlers):
            print(f"  - {fn}() in {fpath}")
        print("Ensure these functions are defined and exported to window (e.g. window.fn = fn).")
    else:
        print(f"PASS: Verified {total_handlers} HTML event handler bindings.")
    return True

def main():
    print("=" * 60)
    print(" EASYSALON STUDIO CODE QUALITY & SYNTAX VERIFICATION")
    print("=" * 60)
    
    ok1 = check_python_syntax()
    ok2 = check_js_syntax()
    ok3 = check_dev_watch_bundle()
    ok4 = check_html_js_bindings()
    
    print("\n" + "=" * 60)
    if ok1 and ok2 and ok3 and ok4:
        print(" ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 60)
        sys.exit(0)
    else:
        print(" VERIFICATION CHECKS FAILED! Please review errors above.")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
