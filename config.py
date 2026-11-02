#!/usr/bin/env python3
"""
EasySalon Agent Bridge - Configuration & Environment Loader
Tự động tải cấu hình từ file .env thuần Python (không cần phụ thuộc thư viện ngoài).
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, '.env')
ENV_EXAMPLE_FILE = os.path.join(BASE_DIR, '.env.example')


def load_env_file(filepath=ENV_FILE):
    """
    Đọc file .env nếu tồn tại, gán các biến vào os.environ.
    Hỗ trợ comment (#), khoảng trắng, bỏ dấu nháy kép / đơn.
    """
    target_file = filepath
    if not os.path.isfile(target_file):
        # Nếu chưa có .env, thử fallback đọc .env.example
        if os.path.isfile(ENV_EXAMPLE_FILE):
            target_file = ENV_EXAMPLE_FILE
        else:
            return

    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    # Chỉ gán nếu chưa được truyền từ biến môi trường hệ thống
                    if key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        print(f"[Warning] Không thể đọc file cấu hình {target_file}: {e}")


# Tự động nạp cấu hình khi import config
load_env_file()


SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')


def _read_json_settings():
    """Đọc file settings.json nếu tồn tại để lấy cấu hình dự phòng."""
    try:
        if os.path.isfile(SETTINGS_FILE):
            import json
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _resolve_path(key, default_val, json_key=None):
    """
    Quy tắc ưu tiên:
    1. Biến môi trường os.environ (từ file .env hoặc hệ thống)
    2. Cấu hình được người dùng lưu qua UI vào settings.json
    3. Giá trị mặc định (Fallback)
    """
    val = os.environ.get(key)
    if val and str(val).strip():
        return os.path.expanduser(os.path.expandvars(str(val).strip()))

    j_key = json_key or key.lower()
    st = _read_json_settings()
    j_val = st.get(j_key)
    if j_val and str(j_val).strip():
        return os.path.expanduser(os.path.expandvars(str(j_val).strip()))

    return os.path.expanduser(os.path.expandvars(default_val.strip())) if default_val else ''


# 1. Đường dẫn Workspace của Frontend & Backend
FE_WORKSPACE = _resolve_path('FE_WORKSPACE', '/run/media/thietnv/Data/Project/easysalon-webapp', 'fe_workspace')
BE_WORKSPACE = _resolve_path('BE_WORKSPACE', '/run/media/thietnv/Data/Project/easysalon-api', 'be_workspace')

# 2. Cấu hình Web Server
WEB_PORT = int(os.environ.get('WEB_PORT', '8765'))
WEB_HOST = os.environ.get('WEB_HOST', '0.0.0.0')

# 3. Đường dẫn dữ liệu Antigravity / Gemini CLI
BRAIN_DIR = _resolve_path('BRAIN_DIR', os.path.expanduser('~/.gemini/antigravity-cli/brain'))
HISTORY_FILE = _resolve_path('HISTORY_FILE', os.path.expanduser('~/.gemini/antigravity-cli/history.jsonl'))

# 4. Cấu hình Telegram Bot (@easysalon_bot)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
TELEGRAM_BOT_NAME = os.environ.get('TELEGRAM_BOT_NAME', '@easysalon_bot').strip()
TELEGRAM_ALLOWED_USERS = [
    x.strip() for x in os.environ.get('TELEGRAM_ALLOWED_USERS', '').split(',') if x.strip()
]
TELEGRAM_ENABLED = os.environ.get('TELEGRAM_ENABLED', 'false').lower() in ('true', '1', 'yes')


def get_agy_bin():
    """
    Tìm đường dẫn file thực thi agy (Antigravity CLI / Gemini CLI).
    Quy tắc ưu tiên:
    1. os.environ['AGY_BIN']
    2. settings.json ('agy_bin')
    3. Tìm kiếm trong PATH hoặc các đường dẫn chuẩn theo user hiện tại
    4. Fallback 'agy'
    """
    custom = os.environ.get('AGY_BIN')
    if custom and (os.path.exists(custom) or shutil.which(custom)):
        return custom

    st = _read_json_settings()
    j_bin = st.get('agy_bin')
    if j_bin and (os.path.exists(j_bin) or shutil.which(j_bin)):
        return j_bin

    return (
        shutil.which('agy')
        or os.path.expanduser('~/.local/bin/agy')
        or os.path.expanduser('~/.gemini/antigravity-cli/bin/agy')
        or 'agy'
    )


def get_opencode_bin():
    """
    Tìm đường dẫn file thực thi opencode (OpenCode CLI / 9router).
    Quy tắc ưu tiên:
    1. os.environ['OPENCODE_BIN']
    2. settings.json ('opencode_bin')
    3. Tìm kiếm trong PATH hoặc các đường dẫn npm global / local bin
    4. Fallback 'opencode'
    """
    custom = os.environ.get('OPENCODE_BIN')
    if custom and (os.path.exists(custom) or shutil.which(custom)):
        return custom

    st = _read_json_settings()
    j_bin = st.get('opencode_bin')
    if j_bin and (os.path.exists(j_bin) or shutil.which(j_bin)):
        return j_bin

    return (
        shutil.which('opencode')
        or os.path.expanduser('~/.npm-global/bin/opencode')
        or os.path.expanduser('~/.local/bin/opencode')
        or '/usr/local/bin/opencode'
        or 'opencode'
    )


def get_nine_router_bin():
    """
    Tìm đường dẫn file thực thi 9router (Proxy 9router cho OpenCode).
    """
    custom = os.environ.get('NINE_ROUTER_BIN')
    if custom and (os.path.exists(custom) or shutil.which(custom)):
        return custom

    st = _read_json_settings()
    j_bin = st.get('nine_router_bin')
    if j_bin and (os.path.exists(j_bin) or shutil.which(j_bin)):
        return j_bin

    return (
        shutil.which('9router')
        or os.path.expanduser('~/.npm-global/bin/9router')
        or os.path.expanduser('~/.local/bin/9router')
        or '/usr/local/bin/9router'
        or '9router'
    )


