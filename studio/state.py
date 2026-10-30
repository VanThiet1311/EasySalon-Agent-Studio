#!/usr/bin/env python3
"""Quản lý trạng thái ứng dụng (app_state), hàng đợi (queue_state.json) và lịch sử nhật ký (messages.json)."""

import datetime
import json
import os
import shutil
import subprocess
import threading
import urllib.request
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESSAGES_FILE = os.path.join(BASE_DIR, "messages.json")
QUEUE_STATE_FILE = os.path.join(BASE_DIR, "queue_state.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SETTINGS = {
    'engine': 'gemini_cli',  # 'gemini_cli' (Gemini CLI / Antigravity) | 'opencode' (9router OpenCode)
    'effort': 'high',  # 'low' | 'medium' | 'high' | 'xhigh' | 'max'
    'model': 'gemini-3.8-flash-high',
    'opencode_model': '9router/ag/gemini-3.8-flash-high',
    'api_provider': 'gemini',  # 'gemini' | 'claude' | 'openai' | 'custom'
    'gemini_api_key': '',
    'claude_api_key': '',
    'openai_api_key': '',
    'custom_api_key': '',
    'custom_endpoint': '',
    'fe_workspace': '/run/media/thietnv/Data/Project/easysalon-webapp',
    'be_workspace': '/run/media/thietnv/Data/Project/easysalon-api',
    'agy_bin': '',
    'opencode_bin': '',
}


def load_settings():
    """Tải cấu hình người dùng từ settings.json (hoặc trả về mặc định)."""
    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            if isinstance(data, dict):
                merged.update(data)
            return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)


def is_nine_router_online(url: str = "http://127.0.0.1:20128/v1/models") -> bool:
    """Kiểm tra proxy 9router của OpenCode có đang hoạt động trên localhost không."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EasySalonStudio"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_gemini_cli_status() -> dict:
    """
    Kiểm tra trạng thái cài đặt và đăng nhập của Gemini CLI (Antigravity agy).
    Xác định terminal ngầm đã sẵn sàng thực thi và đã xác thực tài khoản Google hay chưa.
    """
    try:
        from config import get_agy_bin
        agy_bin = get_agy_bin()
        installed = bool(shutil.which(agy_bin) or (os.path.exists(agy_bin) and os.access(agy_bin, os.X_OK)))
        cred_file = os.path.expanduser('~/.config/antigravity/credential-user-scope')
        scope_id = ''
        if os.path.exists(cred_file):
            try:
                with open(cred_file, 'r', encoding='utf-8') as f:
                    scope_id = f.read().strip()
            except Exception:
                pass
        logged_in = bool(scope_id)
        version = ''
        if installed:
            try:
                res = subprocess.run([agy_bin, '--version'], capture_output=True, text=True, timeout=1.5)
                if res.returncode == 0:
                    version = res.stdout.strip()
            except Exception:
                pass

        inst_file = os.path.expanduser('~/.gemini/antigravity-cli/installation_id')
        inst_id = ''
        if os.path.exists(inst_file):
            try:
                with open(inst_file, 'r', encoding='utf-8') as f:
                    inst_id = f.read().strip()
            except Exception:
                pass

        settings_file = os.path.expanduser('~/.gemini/antigravity-cli/settings.json')
        cli_settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    cli_settings = json.load(f)
            except Exception:
                pass

        system_user = os.environ.get('USER') or os.environ.get('USERNAME') or 'system'

        return {
            'installed': installed,
            'logged_in': logged_in,
            'ready': installed and logged_in,
            'version': version,
            'bin_path': agy_bin,
            'scope_id': scope_id,
            'credential_path': '~/.config/antigravity/credential-user-scope',
            'config_path': '~/.gemini/antigravity-cli/settings.json',
            'installation_id': inst_id,
            'system_user': system_user,
            'cli_model': cli_settings.get('model', 'Gemini 3.8 Flash (High)'),
            'agent_mode': cli_settings.get('agentMode', 'accept-edits'),
            'trusted_workspaces_count': len(cli_settings.get('trustedWorkspaces', [])),
            'trusted_workspaces': cli_settings.get('trustedWorkspaces', [])
        }
    except Exception as e:
        return {
            'installed': False,
            'logged_in': False,
            'ready': False,
            'version': '',
            'bin_path': '',
            'scope_id': '',
            'credential_path': '~/.config/antigravity/credential-user-scope',
            'config_path': '~/.gemini/antigravity-cli/settings.json',
            'installation_id': '',
            'system_user': os.environ.get('USER') or 'system',
            'cli_model': '',
            'agent_mode': '',
            'trusted_workspaces_count': 0,
            'trusted_workspaces': [],
            'error': str(e)
        }


def save_settings(settings_dict: dict):
    """Lưu cấu hình người dùng vào settings.json và đồng bộ môi trường os.environ."""
    try:
        curr = load_settings()
        if isinstance(settings_dict, dict):
            curr.update(settings_dict)

            # Đồng bộ sang os.environ để Antigravity harness và các subagent đọc được
            if curr.get('gemini_api_key'):
                os.environ['GEMINI_API_KEY'] = curr['gemini_api_key']
                os.environ['GOOGLE_API_KEY'] = curr['gemini_api_key']
            if curr.get('claude_api_key'):
                os.environ['ANTHROPIC_API_KEY'] = curr['claude_api_key']
            if curr.get('openai_api_key'):
                os.environ['OPENAI_API_KEY'] = curr['openai_api_key']
            if curr.get('custom_endpoint'):
                os.environ['OPENAI_BASE_URL'] = curr['custom_endpoint']
            if curr.get('custom_api_key'):
                os.environ['CUSTOM_API_KEY'] = curr['custom_api_key']

            try:
                import config
                if curr.get('fe_workspace'):
                    config.FE_WORKSPACE = os.path.expanduser(str(curr['fe_workspace']).strip())
                if curr.get('be_workspace'):
                    config.BE_WORKSPACE = os.path.expanduser(str(curr['be_workspace']).strip())
            except Exception:
                pass

        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(curr, f, ensure_ascii=False, indent=2)
        return curr
    except Exception as e:
        print(f"[WARN] Không thể lưu settings.json: {e}")
        return dict(DEFAULT_SETTINGS)


state_lock = threading.Lock()
app_state = {
    'is_running': False,
    'current_process': None,
    'mode': 'task',  # 'task' | 'fixbug'
    'active_round': 0,
    'total_rounds': 0,
    'active_speaker': '',
    'status_text': 'Sẵn sàng',
    'current_session': None,
    'active_tasks': {},
    'task_queue': [],
    'settings': load_settings(),
    'diagram_cache': None,
    'diagram_cache_key': None
}


def save_queue_state_unlocked():
    """Lưu trạng thái hàng đợi (task_queue) và các phiên thực thi (active_tasks) xuống đĩa."""
    try:
        serializable_tasks = {}
        for tid, ts in app_state.get('active_tasks', {}).items():
            serializable_tasks[tid] = {
                'task_id': ts.get('task_id', tid),
                'title': ts.get('title', ''),
                'mode': ts.get('mode', 'task'),
                'queue_status': ts.get('queue_status', 'running' if ts.get('is_running') else 'done'),
                'is_running': bool(ts.get('is_running', False)),
                'status': ts.get('status', 'running' if ts.get('is_running') else 'completed'),
                'active_round': ts.get('active_round', 0),
                'total_rounds': ts.get('total_rounds', 0),
                'active_speaker': ts.get('active_speaker', ''),
                'status_text': ts.get('status_text', ''),
                'session': ts.get('session')
            }
        payload = {
            'task_queue': app_state.get('task_queue', []),
            'active_tasks': serializable_tasks,
            'updated_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
        }
        with open(QUEUE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_queue_state():
    """Khôi phục trạng thái hàng đợi từ đĩa khi khởi động server và tự động chạy tiếp các tác vụ đang dở."""
    if not os.path.exists(QUEUE_STATE_FILE):
        return
    try:
        with open(QUEUE_STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        with state_lock:
            q = data.get('task_queue', [])
            if isinstance(q, list) and q:
                for item in q:
                    # Nếu tác vụ đang chạy dở khi server reload, đặt lại thành 'queued' để queue_worker tự động chạy tiếp
                    if item.get('status') == 'running':
                        item['status'] = 'queued'
                        item['isRunning'] = False
                app_state['task_queue'] = q
            saved_tasks = data.get('active_tasks', {})
            if isinstance(saved_tasks, dict):
                for tid, ts in saved_tasks.items():
                    was_running = bool(ts.get('is_running')) or ts.get('queue_status') in ('running', 'queued')
                    ts['is_running'] = False
                    ts['current_process'] = None
                    if was_running:
                        ts['queue_status'] = 'queued'
                        ts['status_text'] = 'Đang tiếp tục thực thi từ hàng đợi...'
                        if ts.get('session') and ts['session'].get('status') == 'RUNNING':
                            ts['session']['status'] = 'QUEUED'
                    if ts.get('session'):
                        for trn in ts['session'].get('turns', []):
                            trn['is_streaming'] = False
                    app_state['active_tasks'][tid] = ts
    except Exception:
        pass


def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def save_messages(messages):
    temp = MESSAGES_FILE + '.tmp'
    try:
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, MESSAGES_FILE)
    except Exception:
        pass


def add_work_log(log_type, title, details='', status='SUCCESS', duration=0, target='both', turns=None):
    """Ghi nhận lịch sử làm việc vào hệ thống nhật ký."""
    log_entry = {
        'id': f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}",
        'type': log_type,  # 'TASK', 'FIX_BUG', 'GIT_SWITCH', 'DISCUSS'
        'created_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y'),
        'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
        'title': title,
        'details': details,
        'status': status,
        'duration_sec': duration,
        'target': target,
        'turns': turns or []
    }
    messages = load_messages()
    messages.append(log_entry)
    save_messages(messages)
    return log_entry
