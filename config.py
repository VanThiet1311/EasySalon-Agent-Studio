#!/usr/bin/env python3
"""
EasySalon Agent Bridge - Configuration & Environment Loader
Tự động tải cấu hình từ file .env thuần Python (không cần phụ thuộc thư viện ngoài).
"""

import os
import shutil
import platform
import glob

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


STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
os.makedirs(STORAGE_DIR, exist_ok=True)


def _resolve_storage_file(filename: str) -> str:
    """Trả về đường dẫn file trong thư mục storage/. Nếu file tồn tại ở root mà chưa có trong storage/, tự động di chuyển vào storage/."""
    storage_path = os.path.join(STORAGE_DIR, filename)
    root_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(storage_path) and os.path.exists(root_path):
        try:
            import shutil
            shutil.move(root_path, storage_path)
        except Exception:
            return root_path
    return storage_path


SETTINGS_FILE = _resolve_storage_file('settings.json')


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


def _resolve_workspace(key, json_key, default_val):
    """
    Quy tắc ưu tiên cho Workspace:
    1. settings.json (Nguồn cấu hình chính thức từ UI)
    2. Biến môi trường os.environ (.env / hệ thống)
    3. Giá trị mặc định (Fallback)
    """
    st = _read_json_settings()
    j_val = st.get(json_key)
    if j_val and str(j_val).strip():
        return os.path.expanduser(os.path.expandvars(str(j_val).strip()))

    val = os.environ.get(key)
    if val and str(val).strip():
        return os.path.expanduser(os.path.expandvars(str(val).strip()))

    return os.path.expanduser(os.path.expandvars(default_val.strip())) if default_val else ''


def get_fe_workspace() -> str:
    """Lấy đường dẫn Frontend Workspace (easysalon-webapp) trực tiếp từ settings.json."""
    return _resolve_workspace('FE_WORKSPACE', 'fe_workspace', '/run/media/thietnv/Data/Project/easysalon-webapp')


def get_be_workspace() -> str:
    """Lấy đường dẫn Backend Workspace (easysalon-api) trực tiếp từ settings.json."""
    return _resolve_workspace('BE_WORKSPACE', 'be_workspace', '/run/media/thietnv/Data/Project/easysalon-api')


def get_workspace(role: str = 'fe') -> str:
    """Lấy đường dẫn Workspace theo vai trò ('fe' | 'be') trực tiếp từ settings.json."""
    r = str(role or 'fe').strip().lower()
    if r in ('be', 'backend', 'api'):
        return get_be_workspace()
    return get_fe_workspace()


# 1. Đường dẫn Workspace của Frontend & Backend (khởi tạo từ settings.json)
FE_WORKSPACE = get_fe_workspace()
BE_WORKSPACE = get_be_workspace()


def refresh_workspaces():
    """Làm mới lại các biến FE_WORKSPACE & BE_WORKSPACE theo settings.json mới nhất."""
    global FE_WORKSPACE, BE_WORKSPACE
    FE_WORKSPACE = get_fe_workspace()
    BE_WORKSPACE = get_be_workspace()
    return FE_WORKSPACE, BE_WORKSPACE


def _resolve_path(key, default_val, json_key=None):
    """
    Quy tắc ưu tiên cho các biến đường dẫn chung:
    1. Cấu hình được người dùng lưu qua UI vào settings.json
    2. Biến môi trường os.environ (từ file .env hoặc hệ thống)
    3. Giá trị mặc định (Fallback)
    """
    j_key = json_key or key.lower()
    st = _read_json_settings()
    j_val = st.get(j_key)
    if j_val and str(j_val).strip():
        return os.path.expanduser(os.path.expandvars(str(j_val).strip()))

    val = os.environ.get(key)
    if val and str(val).strip():
        return os.path.expanduser(os.path.expandvars(str(val).strip()))

    return os.path.expanduser(os.path.expandvars(default_val.strip())) if default_val else ''

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


def detect_installed_cli_path(target: str) -> dict:
    """
    Tự động dò tìm đường dẫn nhị phân đã cài đặt của Antigravity CLI ('agy') hoặc OpenCode CLI ('opencode').
    Hỗ trợ cả môi trường Linux/Unix (POSIX) và Windows.
    """
    target_clean = str(target or 'agy').strip().lower()
    is_windows = (platform.system() == 'Windows' or os.name == 'nt')
    found_path = None
    exists = False

    if target_clean in ('agy', 'antigravity', 'gemini_cli'):
        if is_windows:
            candidates = [
                shutil.which('agy.exe'),
                shutil.which('agy.cmd'),
                shutil.which('agy'),
                shutil.which('antigravity.exe'),
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\antigravity-cli\agy.exe'),
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\Antigravity\agy.exe'),
                os.path.expandvars(r'%LOCALAPPDATA%\antigravity-cli\bin\agy.exe'),
                os.path.expandvars(r'%APPDATA%\antigravity-cli\bin\agy.exe'),
                os.path.expandvars(r'%APPDATA%\npm\agy.cmd'),
                os.path.expanduser(r'~\.gemini\antigravity-cli\bin\agy.exe'),
                os.path.expanduser(r'~\.gemini\antigravity-cli\bin\agy.cmd'),
                os.path.expanduser(r'~\.local\bin\agy.exe'),
                os.path.expandvars(r'%ProgramFiles%\Antigravity\agy.exe'),
                os.path.expandvars(r'%ProgramFiles(x86)%\Antigravity\agy.exe'),
            ]
            fallback = shutil.which('agy') or os.path.expandvars(r'%LOCALAPPDATA%\Programs\antigravity-cli\agy.exe') or 'agy.exe'
        else:
            candidates = [
                shutil.which('agy'),
                os.path.expanduser('~/.local/bin/agy'),
                os.path.expanduser('~/.gemini/antigravity-cli/bin/agy'),
                os.path.expanduser('~/.antigravity/bin/agy'),
                '/usr/local/bin/agy',
                '/usr/bin/agy',
                '/opt/homebrew/bin/agy',
            ]
            fallback = shutil.which('agy') or os.path.expanduser('~/.local/bin/agy') or 'agy'

        for c in candidates:
            if c:
                if os.path.isabs(c) and os.path.exists(c):
                    found_path = os.path.abspath(c)
                    exists = True
                    break
                w = shutil.which(c)
                if w:
                    found_path = os.path.abspath(w) if os.path.exists(w) else w
                    exists = True
                    break

        return {
            'target': 'agy',
            'path': found_path or fallback,
            'exists': exists or bool(found_path and os.path.exists(found_path)),
            'platform': 'windows' if is_windows else 'linux',
            'fallback': fallback
        }

    else:
        if is_windows:
            candidates = [
                shutil.which('opencode.cmd'),
                shutil.which('opencode.exe'),
                shutil.which('opencode.ps1'),
                shutil.which('opencode'),
                os.path.expandvars(r'%APPDATA%\npm\opencode.cmd'),
                os.path.expandvars(r'%APPDATA%\npm\opencode.ps1'),
                os.path.expanduser(r'~\AppData\Roaming\npm\opencode.cmd'),
                os.path.expandvars(r'%LOCALAPPDATA%\npm-global\opencode.cmd'),
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\opencode\opencode.exe'),
                os.path.expandvars(r'%ProgramFiles%\nodejs\opencode.cmd'),
                r'C:\Program Files\nodejs\opencode.cmd',
                os.path.expandvars(r'%LOCALAPPDATA%\Yarn\bin\opencode.cmd'),
                os.path.expanduser(r'~\.config\yarn\global\node_modules\.bin\opencode.cmd'),
            ]
            fallback = shutil.which('opencode') or os.path.expandvars(r'%APPDATA%\npm\opencode.cmd') or 'opencode.cmd'
        else:
            candidates = [
                shutil.which('opencode'),
                os.path.expanduser('~/.npm-global/bin/opencode'),
                os.path.expanduser('~/.local/bin/opencode'),
                '/usr/local/bin/opencode',
                '/usr/bin/opencode',
                '/opt/homebrew/bin/opencode',
            ]
            try:
                candidates.extend(sorted(glob.glob(os.path.expanduser('~/.nvm/versions/node/*/bin/opencode')), reverse=True))
                candidates.extend(glob.glob(os.path.expanduser('~/.local/share/fnm/current/bin/opencode')))
                candidates.extend(glob.glob(os.path.expanduser('~/.volta/bin/opencode')))
            except Exception:
                pass
            candidates.extend([
                os.path.expanduser('~/.yarn/bin/opencode'),
                os.path.expanduser('~/.config/yarn/global/node_modules/.bin/opencode'),
            ])
            fallback = shutil.which('opencode') or os.path.expanduser('~/.npm-global/bin/opencode') or 'opencode'

        for c in candidates:
            if c:
                if os.path.isabs(c) and os.path.exists(c):
                    found_path = os.path.abspath(c)
                    exists = True
                    break
                w = shutil.which(c)
                if w:
                    found_path = os.path.abspath(w) if os.path.exists(w) else w
                    exists = True
                    break

        return {
            'target': 'opencode',
            'path': found_path or fallback,
            'exists': exists or bool(found_path and os.path.exists(found_path)),
            'platform': 'windows' if is_windows else 'linux',
            'fallback': fallback
        }


def get_agy_bin():
    """
    Tìm đường dẫn file thực thi agy (Antigravity CLI / Gemini CLI).
    Quy tắc ưu tiên:
    1. os.environ['AGY_BIN']
    2. settings.json ('agy_bin')
    3. Tìm kiếm tự động theo hệ điều hành (Linux/Windows)
    4. Fallback 'agy'
    """
    custom = os.environ.get('AGY_BIN')
    if custom and (os.path.exists(custom) or shutil.which(custom)):
        return custom

    st = _read_json_settings()
    j_bin = st.get('agy_bin')
    if j_bin and (os.path.exists(j_bin) or shutil.which(j_bin)):
        return j_bin

    detected = detect_installed_cli_path('agy')
    return detected.get('path') or 'agy'


def get_opencode_bin():
    """
    Tìm đường dẫn file thực thi opencode (OpenCode CLI / 9router).
    Quy tắc ưu tiên:
    1. os.environ['OPENCODE_BIN']
    2. settings.json ('opencode_bin')
    3. Tìm kiếm tự động theo hệ điều hành (Linux/Windows)
    4. Fallback 'opencode'
    """
    custom = os.environ.get('OPENCODE_BIN')
    if custom and (os.path.exists(custom) or shutil.which(custom)):
        return custom

    st = _read_json_settings()
    j_bin = st.get('opencode_bin')
    if j_bin and (os.path.exists(j_bin) or shutil.which(j_bin)):
        return j_bin

    detected = detect_installed_cli_path('opencode')
    return detected.get('path') or 'opencode'


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


def __getattr__(name: str):
    """
    Truy cập thuộc tính module động: FE_WORKSPACE & BE_WORKSPACE luôn trả về
    đường dẫn mới nhất từ settings.json theo thời gian thực.
    """
    if name == 'FE_WORKSPACE':
        return get_fe_workspace()
    if name == 'BE_WORKSPACE':
        return get_be_workspace()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")



