#!/usr/bin/env python3
"""Quản lý trạng thái ứng dụng (app_state), hàng đợi (queue_state.json) và lịch sử nhật ký (messages.json)."""

import datetime
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
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


MESSAGES_FILE = _resolve_storage_file("messages.json")
QUEUE_STATE_FILE = _resolve_storage_file("queue_state.json")
SETTINGS_FILE = _resolve_storage_file("settings.json")

DEFAULT_SETTINGS = {
    'engine': 'gemini_cli',  # 'gemini_cli' (Gemini CLI / Antigravity) | 'opencode' (9router OpenCode)
    'effort': 'high',  # 'low' | 'medium' | 'high' | 'xhigh' | 'max'
    'model': 'gemini-3.8-flash-high',
    'opencode_model': '9router/ag/gemini-3.8-flash',
    'api_provider': 'gemini',  # 'gemini' | 'claude' | 'openai' | 'deepseek' | 'custom'
    'gemini_api_key': '',
    'claude_api_key': '',
    'openai_api_key': '',
    'deepseek_api_key': '',
    'custom_api_key': '',
    'custom_endpoint': '',
    'jira_host': '',
    'jira_email': '',
    'jira_api_token': '',
    'fe_workspace': '/run/media/thietnv/Data/Project/easysalon-webapp',
    'be_workspace': '/run/media/thietnv/Data/Project/easysalon-api',
    'agy_bin': '',
    'opencode_bin': '',
}


def normalize_9router_model_id(mid: str) -> str:
    """Đảm bảo model 9router luôn có đúng namespace provider prefix (ví dụ '9router/ag/gemini-...' thay vì '9router/gemini-...')."""
    if not mid:
        return mid
    s = str(mid).strip()
    if s.startswith('opencode/'):
        return s
    prefix = '9router/' if s.startswith('9router/') else ''
    raw = s[len(prefix):] if prefix else s
    if raw.startswith('opencode/'):
        return raw
    # Các họ mô hình trên 9router Antigravity luôn cần namespace 'ag/'
    if any(raw.startswith(p) for p in ('gemini-', 'claude-', 'gpt-oss-')):
        raw = f"ag/{raw}"
    return f"{prefix or '9router/'}{raw}"


def get_opencode_configured_model() -> str:
    """Đọc model hiện tại đang được cấu hình trong ~/.config/opencode/opencode.json."""
    try:
        config_path = os.path.expanduser('~/.config/opencode/opencode.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            m = cfg.get('model')
            res = ''
            if isinstance(m, str) and m.strip():
                res = m.strip()
            elif isinstance(m, dict):
                pid = str(m.get('providerID') or '').strip()
                mid = str(m.get('model') or m.get('id') or '').strip()
                if pid and mid:
                    res = f"{pid}/{mid}" if not mid.startswith(pid) else mid
                else:
                    res = mid or pid
            if res:
                return normalize_9router_model_id(res)
    except Exception:
        pass
    return ''


def sync_all_api_keys_and_providers(settings: dict = None) -> dict:
    """
    Đồng bộ và ưu tiên các API Key của mô hình vào môi trường hệ thống và cấu hình OpenCode:
    1. Ưu tiên các API Key người dùng cấu hình so với mặc định/fallback.
    2. Đồng bộ sang os.environ (GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_GENERATIVE_AI_API_KEY,
       ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENAI_BASE_URL, CUSTOM_API_KEY, NINE_ROUTER_API_KEY).
    3. Đồng bộ API Key và Base URL vào provider '9router' trong ~/.config/opencode/opencode.json.
    """
    if settings is None:
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
        except Exception:
            settings = dict(DEFAULT_SETTINGS)

    if not isinstance(settings, dict):
        settings = dict(DEFAULT_SETTINGS)

    gemini_key = str(settings.get('gemini_api_key') or '').strip()
    claude_key = str(settings.get('claude_api_key') or '').strip()
    openai_key = str(settings.get('openai_api_key') or '').strip()
    deepseek_key = str(settings.get('deepseek_api_key') or '').strip()
    custom_key = str(settings.get('custom_api_key') or '').strip()
    custom_endpoint = str(settings.get('custom_endpoint') or '').strip()

    # 1. Đồng bộ biến môi trường hệ thống (ưu tiên key đã cấu hình)
    if gemini_key:
        os.environ['GEMINI_API_KEY'] = gemini_key
        os.environ['GOOGLE_API_KEY'] = gemini_key
        os.environ['GOOGLE_GENERATIVE_AI_API_KEY'] = gemini_key

    if claude_key:
        os.environ['ANTHROPIC_API_KEY'] = claude_key

    if openai_key:
        os.environ['OPENAI_API_KEY'] = openai_key

    if deepseek_key:
        os.environ['DEEPSEEK_API_KEY'] = deepseek_key
        os.environ.setdefault('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

    if custom_endpoint:
        os.environ['OPENAI_BASE_URL'] = custom_endpoint

    if custom_key:
        os.environ['CUSTOM_API_KEY'] = custom_key
        os.environ['NINE_ROUTER_API_KEY'] = custom_key

    if settings.get('jira_host'):
        os.environ['JIRA_HOST'] = str(settings['jira_host']).strip()
    if settings.get('jira_email'):
        os.environ['JIRA_EMAIL'] = str(settings['jira_email']).strip()
    if settings.get('jira_api_token'):
        os.environ['JIRA_API_TOKEN'] = str(settings['jira_api_token']).strip()

    # 2. Đồng bộ cấu hình ~/.config/opencode/opencode.json
    try:
        config_path = os.path.expanduser('~/.config/opencode/opencode.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                provider = cfg.setdefault('provider', {})
                nine_router = provider.setdefault('9router', {})
                opts = nine_router.setdefault('options', {})

                changed = False
                # Ưu tiên custom API key nếu có
                if custom_key:
                    if opts.get('apiKey') != custom_key:
                        opts['apiKey'] = custom_key
                        changed = True
                elif not opts.get('apiKey'):
                    opts['apiKey'] = 'sk-6507521eca6e4614-6o4r60-5aa0309e'
                    changed = True

                if custom_endpoint:
                    if opts.get('baseURL') != custom_endpoint:
                        opts['baseURL'] = custom_endpoint
                        changed = True
                elif not opts.get('baseURL'):
                    opts['baseURL'] = 'http://127.0.0.1:20128/v1'
                    changed = True

                if changed:
                    tmp_path = config_path + '.tmp'
                    with open(tmp_path, 'w', encoding='utf-8') as f:
                        json.dump(cfg, f, indent=2)
                    os.replace(tmp_path, config_path)
    except Exception as e:
        pass

    return settings


def detect_api_key_or_quota_error(data) -> dict | None:
    """
    Phát hiện các lỗi liên quan đến API Key mô hình (hết token, quota, sai key, v.v.).
    Trả về dict chi tiết cảnh báo hoặc None nếu không phát hiện lỗi.
    """
    if data is None:
        return None

    raw_str = ""
    err_obj = {}

    if isinstance(data, dict):
        err_obj = data
        raw_str = json.dumps(data, ensure_ascii=False)
    elif isinstance(data, str):
        raw_str = data.strip()
        if (raw_str.startswith('{') and raw_str.endswith('}')) or (raw_str.startswith('[') and raw_str.endswith(']')):
            try:
                parsed = json.loads(raw_str)
                if isinstance(parsed, dict):
                    err_obj = parsed
            except Exception:
                pass
    elif isinstance(data, Exception):
        raw_str = str(data)
    else:
        raw_str = str(data)

    if not raw_str:
        return None

    raw_lower = raw_str.lower()

    # 1. QUOTA & TOKEN EXHAUSTION
    quota_keywords = [
        'resource_exhausted',
        'quota exceeded',
        'quota_exceeded',
        'exceeded your current quota',
        'insufficient_quota',
        'rate_limit_exceeded',
        'rate_limit_error',
        'out of credits',
        'out of tokens',
        'credit limit reached',
        'insufficient balance',
        'insufficient_balance',
        'not enough tokens',
        'billing_hard_limit_reached',
        'too many requests',
        '429 too many requests',
        'check quota',
        'hết token',
        'hết hạn mức',
        'vượt quá hạn mức'
    ]
    is_quota = any(kw in raw_lower for kw in quota_keywords)

    # 2. AUTHENTICATION & INVALID KEY
    auth_keywords = [
        'invalid_api_key',
        'api_key_invalid',
        'api key not valid',
        'authentication_error',
        'invalid x-api-key',
        'incorrect api key provided',
        '401 unauthorized',
        'permission_denied',
        'permissiondenied',
        'key không hợp lệ',
        'sai api key',
        'unauthorized'
    ]
    is_auth = any(kw in raw_lower for kw in auth_keywords)

    # 3. ROUTE / PROVIDER ERROR
    route_keywords = [
        'provider.no-route',
        'model unavailable'
    ]
    is_route = any(kw in raw_lower for kw in route_keywords)

    if not (is_quota or is_auth or is_route):
        return None

    now_ts = int(time.time() * 1000)
    now_str = datetime.datetime.now().strftime("%H:%M:%S")

    # Bóc tách thông điệp rõ ràng từ JSON nếu có
    clean_msg = ""
    if err_obj:
        if isinstance(err_obj.get('error'), dict):
            clean_msg = err_obj['error'].get('message') or err_obj['error'].get('reason') or ''
        elif isinstance(err_obj.get('error'), str):
            clean_msg = err_obj['error']
        elif err_obj.get('message'):
            clean_msg = str(err_obj['message'])

    if is_quota:
        return {
            "id": f"err_quota_{now_ts}",
            "error_type": "quota_exceeded",
            "title": "API Key Hết Token / Quota",
            "message": clean_msg or "Khóa API đã hết hạn mức token hoặc vượt quá giới hạn lượt gọi (Rate Limit / Quota Exceeded).",
            "action_hint": "Vui lòng vào tab Cài đặt để cập nhật API Key mới hoặc nạp thêm token.",
            "raw_error": raw_str[:500],
            "timestamp": now_str
        }

    if is_auth:
        return {
            "id": f"err_auth_{now_ts}",
            "error_type": "invalid_key",
            "title": "API Key Không Hợp Lệ",
            "message": clean_msg or "Không thể xác thực API Key với nhà cung cấp. Khóa có thể đã hết hạn, bị thu hồi hoặc nhập sai.",
            "action_hint": "Vui lòng kiểm tra và dán lại API Key chính xác trong tab Cài đặt.",
            "raw_error": raw_str[:500],
            "timestamp": now_str
        }

    if is_route:
        return {
            "id": f"err_route_{now_ts}",
            "error_type": "provider_error",
            "title": "Không Thể Kết Nối Mô Hình",
            "message": clean_msg or "Mô hình hiện tại không khả dụng hoặc chưa được hỗ trợ bởi nhà cung cấp đã chọn.",
            "action_hint": "Vui lòng kiểm tra lại cấu hình Engine và Model trong tab Cài đặt.",
            "raw_error": raw_str[:500],
            "timestamp": now_str
        }

    return None


def load_settings():
    """Tải cấu hình người dùng từ settings.json (hoặc trả về mặc định)."""
    if not os.path.exists(SETTINGS_FILE):
        merged = dict(DEFAULT_SETTINGS)
    else:
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                merged = dict(DEFAULT_SETTINGS)
                if isinstance(data, dict):
                    merged.update(data)
                if 'opencode_model' in merged and merged['opencode_model']:
                    merged['opencode_model'] = re.sub(r'-(low|medium|high|xhigh|max)$', '', str(merged['opencode_model']), flags=re.IGNORECASE)
                    merged['opencode_model'] = normalize_9router_model_id(merged['opencode_model'])
        except Exception:
            merged = dict(DEFAULT_SETTINGS)

    # Đọc model đang kích hoạt trong OpenCode CLI / config nếu có
    try:
        cfg_model = detect_opencode_active_model()
        if cfg_model:
            is_free_or_agent = ('free' in cfg_model.lower()) or cfg_model.endswith('-agent')
            clean_model = cfg_model if is_free_or_agent else re.sub(r'-(low|medium|high|xhigh|max)$', '', cfg_model, flags=re.IGNORECASE)
            if clean_model:
                clean_model = normalize_9router_model_id(clean_model)
                config_path = os.path.expanduser('~/.config/opencode/opencode.json')
                if os.path.exists(config_path):
                    if not os.path.exists(SETTINGS_FILE) or os.path.getmtime(config_path) >= os.path.getmtime(SETTINGS_FILE) or merged.get('opencode_model') in ('', '9router/ag/gemini-3.8-flash', 'ag/gemini-3.8-flash', '9router/gemini-3.8-flash'):
                        merged['opencode_model'] = clean_model
                else:
                    merged['opencode_model'] = clean_model
    except Exception:
        pass

    # Đọc mức suy luận thực tế người dùng đã chọn trong OpenCode TUI.
    # OpenCode lưu lựa chọn này ở ~/.local/state/opencode/model.json (khóa 'variant').
    try:
        if str(merged.get('engine') or '').strip().lower() == 'opencode':
            variant_effort = get_opencode_model_variant(merged.get('opencode_model') or detect_opencode_active_model())
            if variant_effort:
                merged['effort'] = variant_effort
    except Exception:
        pass

    # Đồng bộ API key và biến môi trường ngay khi nạp cấu hình
    sync_all_api_keys_and_providers(merged)

    return merged


def is_nine_router_online(url: str = "http://127.0.0.1:20128/v1/models") -> bool:
    """Kiểm tra proxy 9router của OpenCode có đang hoạt động trên localhost không."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EasySalonStudio"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_nine_router_background() -> dict:
    """Khởi động 9router ngầm trên cổng 20128 để OpenCode kết nối không cần mở terminal riêng."""
    if is_nine_router_online():
        return {
            'success': True,
            'online': True,
            'message': '9router proxy đã đang chạy ngầm trên cổng 20128'
        }
    from config import get_nine_router_bin
    bin_path = get_nine_router_bin()
    if not (shutil.which(bin_path) or (os.path.exists(bin_path) and os.access(bin_path, os.X_OK))):
        return {
            'success': False,
            'online': False,
            'message': f'Không tìm thấy binary 9router tại: {bin_path}'
        }
    try:
        subprocess.Popen(
            [bin_path, '-n', '--skip-update'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        for _ in range(15):
            time.sleep(0.3)
            if is_nine_router_online():
                return {
                    'success': True,
                    'online': True,
                    'message': 'Đã khởi động 9router ngầm thành công trên cổng 20128!'
                }
        return {
            'success': False,
            'online': False,
            'message': 'Đã phát lệnh chạy 9router nhưng chưa kết nối được cổng 20128'
        }
    except Exception as e:
        return {
            'success': False,
            'online': False,
            'message': f'Lỗi khởi động 9router: {str(e)}'
        }


def start_gemini_cli_background() -> dict:
    """Khởi động Gemini CLI background daemon (agy remote-control start) để chạy ngầm không gián đoạn."""
    from config import get_agy_bin
    agy_bin = get_agy_bin()
    if not (shutil.which(agy_bin) or (os.path.exists(agy_bin) and os.access(agy_bin, os.X_OK))):
        return {
            'success': False,
            'active': False,
            'message': f'Không tìm thấy binary agy tại: {agy_bin}'
        }
    try:
        res = subprocess.run([agy_bin, 'remote-control', 'start'], capture_output=True, text=True, timeout=8)
        out = (res.stdout or '') + (res.stderr or '')
        # Kiểm tra lại trạng thái
        status = get_gemini_cli_status()
        is_active = status.get('daemon_active') or status.get('ready')
        return {
            'success': True,
            'active': is_active,
            'message': 'Gemini CLI daemon đã được kích hoạt chạy ngầm thành công!' if is_active else out.strip()
        }
    except Exception as e:
        return {
            'success': False,
            'active': False,
            'message': f'Lỗi khi khởi chạy Gemini CLI ngầm: {str(e)}'
        }


_9ROUTER_RAW_MODELS = set()


def sync_opencode_provider_models(models_set):
    """Đăng ký danh sách các model của 9router vào ~/.config/opencode/opencode.json để OpenCode route chính xác."""
    try:
        config_path = os.path.expanduser('~/.config/opencode/opencode.json')
        if not os.path.exists(config_path):
            return
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            return
        provider = cfg.setdefault('provider', {})
        nine_router = provider.setdefault('9router', {})
        existing_models = nine_router.setdefault('models', {})
        changed = False

        # Dọn dẹp triệt để các model rác / ô nhiễm không hợp lệ (như opencode/* hoặc bare gemini-/claude- thiếu namespace ag/)
        to_delete = [
            k for k in list(existing_models.keys())
            if k.startswith('opencode/')
            or (any(k.startswith(p) for p in ('gemini-', 'claude-', 'gpt-oss-')) and not k.startswith('ag/'))
        ]
        for k in to_delete:
            del existing_models[k]
            changed = True

        for mid in (models_set or []):
            if not mid:
                continue
            mid_str = str(mid).strip()
            if mid_str.startswith('opencode/'):
                continue
            clean_mid = mid_str.replace('9router/', '').strip()
            if any(clean_mid.startswith(p) for p in ('gemini-', 'claude-', 'gpt-oss-')):
                clean_mid = f"ag/{clean_mid}"
            if clean_mid and clean_mid not in existing_models:
                existing_models[clean_mid] = {
                    'modalities': {'input': ['text', 'image'], 'output': ['text']},
                    'name': clean_mid
                }
                changed = True
        if changed:
            tmp_path = config_path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
            os.replace(tmp_path, config_path)
    except Exception:
        pass


def _opencode_model_key(model_id: str) -> str:
    """Bỏ tiền tố provider khỏi model id để tra cứu trong provider.models của opencode.json."""
    s = str(model_id or '').strip()
    for prefix in ('9router/', 'opencode/'):
        if s.startswith(prefix):
            return s[len(prefix):]
    return s


def sync_opencode_active_model(settings: dict):
    """
    Ghi model hiệu dụng (base model + effort) vào ~/.config/opencode/opencode.json để
    terminal `opencode` mở thủ công luôn khớp với mức suy luận đang chọn trên UI Studio.
    Trước đây Studio chỉ lưu settings.json nên terminal vẫn chạy model cũ (thường là High).

    - Model có biến thể effort (Gemini/Claude/GPT...) -> đổi hậu tố model id.
    - Model không có biến thể (ví dụ DeepSeek) -> giữ nguyên model id và ghi
      `options.reasoningEffort` để provider nhận đúng mức suy luận đã chọn.
    """
    try:
        if not isinstance(settings, dict):
            return

        base = normalize_9router_model_id(str(settings.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip())
        effort = str(settings.get('effort') or 'high').strip().lower()

        try:
            from studio.services.terminal_service import resolve_effective_opencode_model
            target = resolve_effective_opencode_model(base, effort)
        except Exception:
            if re.search(r'-(low|medium|high|xhigh|max)$', base, re.IGNORECASE):
                target = base
            elif ('free' in base.lower()) or base.endswith('-agent'):
                target = base
            else:
                target = f"{base}-{effort}"
        target = normalize_9router_model_id(target)

        # Đọc lại config SAU khi resolve (hàm trên có thể đã ghi thêm model variants).
        config_path = os.path.expanduser('~/.config/opencode/opencode.json')
        if not os.path.exists(config_path):
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            return

        changed = cfg.get('model') != target
        cfg['model'] = target

        # Ghi lựa chọn effort vào state của OpenCode TUI để giao diện `opencode`
        # hiển thị đúng mức đang chọn trong Studio (OpenCode lưu ở khóa 'variant').
        save_opencode_model_variant(base, effort)
        if target != base:
            save_opencode_model_variant(target, effort)

        base_key = _opencode_model_key(base)
        target_key = _opencode_model_key(target)
        is_free_or_agent = ('free' in base_key.lower()) or base_key.lower().endswith('-agent')
        has_effort_variant = bool(re.search(r'-(low|medium|high|xhigh|max)$', target_key, re.IGNORECASE)) and target_key != base_key

        if not is_free_or_agent:
            nine_router = cfg.setdefault('provider', {}).setdefault('9router', {})
            models = nine_router.setdefault('models', {})
            entry = models.get(target_key)
            if not isinstance(entry, dict):
                entry = {
                    'name': target_key,
                    'modalities': {'input': ['text', 'image'], 'output': ['text']}
                }
                models[target_key] = entry
                changed = True
            options = entry.get('options')
            if not isinstance(options, dict):
                options = {}
                entry['options'] = options

            if has_effort_variant:
                # Model id đã mang sẵn mức suy luận -> không cần options.reasoningEffort.
                if 'reasoningEffort' in options:
                    del options['reasoningEffort']
                    changed = True
            elif options.get('reasoningEffort') != effort:
                options['reasoningEffort'] = effort
                changed = True

        explorer = (cfg.get('agent') or {}).get('explorer')
        if isinstance(explorer, dict) and explorer.get('model') != target:
            explorer['model'] = target
            changed = True

        if changed:
            tmp_path = config_path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
            os.replace(tmp_path, config_path)
    except Exception:
        pass


def _gemini_display_name(model_id: str) -> str:
    """Chuyển 'gemini-3.8-flash' thành 'Gemini 3.8 Flash' để khớp settings.json của Gemini CLI."""
    parts = [p for p in re.split(r'[-_]+', str(model_id or '').strip()) if p]
    words = []
    for part in parts:
        if part.lower() == 'gemini':
            words.append('Gemini')
        elif re.fullmatch(r'\d+(?:\.\d+)*', part):
            words.append(part)
        elif re.fullmatch(r'[a-z]+\d+', part.lower()):
            words.append(part.upper())
        else:
            words.append(part.capitalize())
    return ' '.join(words)


def sync_gemini_cli_active_model(settings: dict):
    """
    Đồng bộ model + mức suy luận đang chọn vào ~/.gemini/antigravity-cli/settings.json
    để terminal `agy` mở thủ công cũng dùng đúng effort như trên UI Studio.
    Chỉ áp dụng cho các model Gemini (CLI lưu effort trong tên model, ví dụ
    'Gemini 3.8 Flash (High)').
    """
    try:
        if not isinstance(settings, dict):
            return
        model = str(settings.get('model') or '').strip()
        if not model or 'gemini' not in model.lower():
            return
        effort = str(settings.get('effort') or 'high').strip().lower()
        base = re.sub(r'-(low|medium|high|xhigh|max)$', '', model, flags=re.IGNORECASE)
        level = {'low': 'Low', 'medium': 'Medium', 'high': 'High'}.get(effort, 'High')
        target = f"{_gemini_display_name(base)} ({level})"

        settings_file = os.path.expanduser('~/.gemini/antigravity-cli/settings.json')
        if not os.path.exists(settings_file):
            return
        with open(settings_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict) or cfg.get('model') == target:
            return
        cfg['model'] = target
        tmp_path = settings_file + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, settings_file)
    except Exception:
        pass


def _opencode_state_model_path() -> str:
    return os.path.expanduser('~/.local/state/opencode/model.json')


def get_opencode_model_variant(model_id: str) -> str:
    """
    Đọc mức suy luận (variant/effort) người dùng đã chọn trong OpenCode TUI.
    OpenCode lưu lựa chọn này trong ~/.local/state/opencode/model.json tại khóa
    'variant', dạng {'9router/ds/deepseek-v4.1-flash': 'medium'}.
    """
    try:
        state_path = _opencode_state_model_path()
        if not os.path.exists(state_path):
            return ''
        with open(state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        variants = data.get('variant') if isinstance(data, dict) else None
        if not isinstance(variants, dict):
            return ''

        valid = ('low', 'medium', 'high', 'xhigh', 'max')
        mid = str(model_id or '').strip()
        candidates = []
        if mid:
            normalized = normalize_9router_model_id(mid)
            candidates.extend([mid, normalized])
            stripped = re.sub(r'-(low|medium|high|xhigh|max)$', '', mid, flags=re.IGNORECASE)
            candidates.extend([stripped, normalize_9router_model_id(stripped) if stripped else stripped])
        for key in candidates:
            if not key:
                continue
            value = variants.get(key)
            if isinstance(value, str) and value.strip().lower() in valid:
                return value.strip().lower()
    except Exception:
        pass
    return ''


def save_opencode_model_variant(model_id: str, effort: str):
    """Ghi mức suy luận đang chọn vào state của OpenCode TUI để giao diện `opencode` khớp với Studio."""
    try:
        effort = str(effort or '').strip().lower()
        if effort not in ('low', 'medium', 'high', 'xhigh', 'max'):
            return
        mid = str(model_id or '').strip()
        if not mid:
            return
        state_path = _opencode_state_model_path()
        if not os.path.exists(state_path):
            return
        with open(state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return
        variants = data.get('variant')
        if not isinstance(variants, dict):
            variants = {}
            data['variant'] = variants

        normalized = normalize_9router_model_id(mid)
        keys = []
        for key in (mid, normalized):
            if key and key not in keys:
                keys.append(key)
        # Nếu state đang dùng khóa không có tiền tố provider, cập nhật luôn khóa đó.
        if mid.startswith('9router/'):
            bare = mid[len('9router/'):]
            if bare in variants and bare not in keys:
                keys.append(bare)

        changed = False
        for key in keys:
            if variants.get(key) != effort:
                variants[key] = effort
                changed = True
        if not changed:
            return

        tmp_path = state_path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, state_path)
    except Exception:
        pass


def detect_opencode_active_model() -> str:
    """
    Tự động nhận diện mô hình đang kích hoạt hoặc vừa được người dùng chuyển đổi trong OpenCode CLI.
    1. Kiểm tra trường 'model' trong ~/.config/opencode/opencode.json (nguồn cấu hình chính thức).
    2. Kiểm tra ~/.local/state/opencode/model.json (mô hình recent trong OpenCode TUI).
    3. Kiểm tra session mới nhất trong ~/.local/share/opencode/opencode.db theo time_updated.
    """
    detected_raw = ''
    cfg_path = os.path.expanduser('~/.config/opencode/opencode.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                d = json.load(f)
                if isinstance(d, dict) and d.get('model'):
                    m = d.get('model')
                    if isinstance(m, str) and m.strip():
                        detected_raw = m.strip()
                    elif isinstance(m, dict):
                        pid = str(m.get('providerID') or '').strip()
                        mid = str(m.get('model') or m.get('id') or '').strip()
                        if pid and mid:
                            detected_raw = f"{pid}/{mid}" if not mid.startswith(pid) else mid
                        else:
                            detected_raw = mid or pid
        except Exception:
            pass

    if not detected_raw:
        state_path = os.path.expanduser('~/.local/state/opencode/model.json')
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    recent = d.get('recent', [])
                    if recent and isinstance(recent, list) and isinstance(recent[0], dict):
                        pid = str(recent[0].get('providerID') or '').strip()
                        mid = str(recent[0].get('modelID') or '').strip()
                        if pid and mid:
                            detected_raw = mid if mid.startswith(f"{pid}/") else f"{pid}/{mid}"
                        elif mid:
                            detected_raw = mid
            except Exception:
                pass

    if not detected_raw:
        db_path = os.path.expanduser('~/.local/share/opencode/opencode.db')
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(db_path, timeout=1.0)
                c = conn.cursor()
                c.execute('SELECT model FROM session_v2 WHERE model IS NOT NULL ORDER BY time_updated DESC LIMIT 1')
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    raw_m = str(row[0]).strip()
                    if raw_m.startswith('{'):
                        parsed = json.loads(raw_m)
                        mid = parsed.get('id', '')
                        provider = parsed.get('providerID', '')
                        if provider and mid:
                            detected_raw = mid if mid.startswith(f"{provider}/") else f"{provider}/{mid}"
                        elif mid:
                            detected_raw = mid
                    else:
                        detected_raw = raw_m
            except Exception:
                pass

    return normalize_9router_model_id(detected_raw) if detected_raw else ''


def get_opencode_models() -> list:
    """Truy vấn danh sách mô hình thực tế hiện tại từ 9router proxy và OpenCode, loại bỏ hậu tố suy luận (-low/-medium/-high) để hiển thị base model tinh gọn."""
    global _9ROUTER_RAW_MODELS
    models_map = {}
    raw_models_set = set()

    # 1. Truy vấn trực tiếp từ proxy 9router (cổng 20128)
    if is_nine_router_online():
        try:
            req = urllib.request.Request('http://127.0.0.1:20128/v1/models', headers={'User-Agent': 'EasySalon'})
            with urllib.request.urlopen(req, timeout=1.5) as r:
                d = json.loads(r.read())
                for m in d.get('data', []):
                    mid = m.get('id', '').strip()
                    if not mid:
                        continue
                    raw_models_set.add(mid)
                    clean_mid = mid.replace('9router/', '')
                    # Chuẩn hóa loại bỏ các hậu tố suy luận: -low, -medium, -high, -xhigh, -max
                    base_mid = re.sub(r'-(low|medium|high|xhigh|max)$', '', clean_mid, flags=re.IGNORECASE)
                    full_id = f'9router/{base_mid}'
                    is_gemini = ('gemini' in base_mid.lower())
                    is_free = ('free' in base_mid.lower())
                    caps = m.get('capabilities') or {}
                    effort_supported = bool(caps.get('thinkingEffortSupported'))

                    if full_id not in models_map:
                        models_map[full_id] = {
                            'id': full_id,
                            'name': base_mid,
                            'provider': '9router',
                            'is_gemini': is_gemini and not is_free,
                            'is_free': is_free,
                            'effort_supported': False,
                            'raw_variants': set()
                        }
                    models_map[full_id]['raw_variants'].add(clean_mid)
                    if effort_supported:
                        models_map[full_id]['effort_supported'] = True
        except Exception:
            pass

    # 2. CHỈ KHI 9router không hoạt động mới fallback sang opencode CLI models
    if not models_map:
        from config import get_opencode_bin
        opencode_bin = get_opencode_bin()
        if shutil.which(opencode_bin) or (os.path.exists(opencode_bin) and os.access(opencode_bin, os.X_OK)):
            try:
                res = subprocess.run([opencode_bin, 'models'], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    for line in res.stdout.strip().splitlines():
                        mid = line.strip()
                        if not mid:
                            continue
                        # Bỏ qua các model không hợp lệ bị sync nhầm trước đây (như bare gemini-3.8-flash dưới 9router)
                        if mid.startswith('9router/'):
                            sub = mid[len('9router/'):]
                            if any(sub.startswith(p) for p in ('gemini-', 'claude-', 'gpt-oss-')) and not sub.startswith('ag/'):
                                continue
                        elif mid.startswith('opencode/'):
                            sub = mid[len('opencode/'):]
                            if sub.startswith('gemini-'):
                                continue
                        raw_models_set.add(mid)
                        clean_mid = mid.replace('9router/', '').replace('opencode/', '')
                        base_mid = re.sub(r'-(low|medium|high|xhigh|max)$', '', clean_mid, flags=re.IGNORECASE)
                        if mid.startswith('opencode/'):
                            full_id = f'opencode/{base_mid}'
                            provider = 'opencode'
                        else:
                            full_id = f'9router/{base_mid}'
                            provider = '9router'
                        is_gemini = ('gemini' in base_mid.lower())
                        is_free = ('free' in base_mid.lower())

                        if full_id not in models_map:
                            models_map[full_id] = {
                                'id': full_id,
                                'name': base_mid,
                                'provider': provider,
                                'is_gemini': is_gemini and not is_free,
                                'is_free': is_free,
                                'effort_supported': False,
                                'raw_variants': set()
                            }
                        models_map[full_id]['raw_variants'].add(clean_mid)
            except Exception:
                pass

    _9ROUTER_RAW_MODELS = raw_models_set
    sync_opencode_provider_models(raw_models_set)

    result = []
    for m in models_map.values():
        item = dict(m)
        item['raw_variants'] = sorted(list(m['raw_variants']))
        result.append(item)

    def _model_sort_key(m):
        mid = m['id'].lower()
        if 'gemini-3.8' in mid:
            return (0, 0, mid)
        if 'gemini-3.7' in mid:
            return (0, 1, mid)
        if 'gemini-3.6' in mid:
            return (0, 2, mid)
        if 'gemini-4' in mid or 'argon' in mid:
            return (0, 3, mid)
        if 'gemini-3.1' in mid:
            return (0, 4, mid)
        if 'gemini' in mid:
            return (0, 5, mid)
        if 'claude-sonnet-5' in mid:
            return (1, 0, mid)
        if 'claude-opus-5' in mid:
            return (1, 1, mid)
        if 'claude' in mid:
            return (1, 2, mid)
        if m.get('is_free'):
            return (2, 0, mid)
        return (3, 0, mid)

    result.sort(key=_model_sort_key)
    return result


def get_gemini_cli_models() -> list:
    """Truy vấn danh sách mô hình được hỗ trợ bởi Gemini CLI (Antigravity agy models)."""
    from config import get_agy_bin
    agy_bin = get_agy_bin()
    models = []
    seen = set()

    if shutil.which(agy_bin) or (os.path.exists(agy_bin) and os.access(agy_bin, os.X_OK)):
        try:
            res = subprocess.run([agy_bin, 'models'], capture_output=True, text=True, timeout=2.5)
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    line = line.strip()
                    if not line or line.startswith('Fetching') or line.startswith('Listing'):
                        continue
                    parts = line.split('\t', 1)
                    mid = parts[0].strip()
                    if not mid or mid in seen:
                        continue
                    name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else mid
                    seen.add(mid)
                    is_gemini = ('gemini' in mid.lower())
                    is_claude = ('claude' in mid.lower())
                    is_openai = ('gpt' in mid.lower() or 'openai' in mid.lower() or 'o3' in mid.lower() or 'o1' in mid.lower())
                    provider = 'google' if is_gemini else ('anthropic' if is_claude else ('openai' if is_openai else 'antigravity'))

                    eff_match = re.search(r'-(low|medium|high|xhigh|max)$', mid, re.IGNORECASE)
                    effort_level = eff_match.group(1).lower() if eff_match else ''
                    base_mid = re.sub(r'-(low|medium|high|xhigh|max)$', '', mid, flags=re.IGNORECASE)

                    models.append({
                        'id': mid,
                        'name': name,
                        'provider': provider,
                        'is_gemini': is_gemini,
                        'is_claude': is_claude,
                        'is_openai': is_openai,
                        'effort': effort_level,
                        'base_model': base_mid,
                    })
        except Exception:
            pass

    if not models:
        defaults = [
            ('gemini-3.8-flash-high', 'Gemini 3.8 Flash (High)', 'google', True, False, False, 'high', 'gemini-3.8-flash'),
            ('gemini-3.8-flash-medium', 'Gemini 3.8 Flash (Medium)', 'google', True, False, False, 'medium', 'gemini-3.8-flash'),
            ('gemini-3.8-flash-low', 'Gemini 3.8 Flash (Low)', 'google', True, False, False, 'low', 'gemini-3.8-flash'),
            ('claude-sonnet-4-6', 'Claude Sonnet 4.6 (Thinking)', 'anthropic', False, True, False, '', 'claude-sonnet-4-6'),
            ('claude-opus-4-6-thinking', 'Claude Opus 4.6 (Thinking)', 'anthropic', False, True, False, '', 'claude-opus-4-6-thinking'),
            ('gpt-oss-120b-medium', 'GPT-OSS 120B (Medium)', 'openai', False, False, True, 'medium', 'gpt-oss-120b'),
        ]
        for mid, name, prov, is_g, is_c, is_o, eff, base in defaults:
            models.append({
                'id': mid,
                'name': name,
                'provider': prov,
                'is_gemini': is_g,
                'is_claude': is_c,
                'is_openai': is_o,
                'effort': eff,
                'base_model': base,
            })

    return models


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

        daemon_active = False
        try:
            res_d = subprocess.run(['systemctl', '--user', 'is-active', 'antigravity-cli-daemon.service'], capture_output=True, text=True, timeout=1.0)
            if res_d.returncode == 0 and res_d.stdout.strip() == 'active':
                daemon_active = True
            elif installed:
                res_rc = subprocess.run([agy_bin, 'remote-control', 'status'], capture_output=True, text=True, timeout=1.5)
                if 'status: active' in (res_rc.stdout or '').lower():
                    daemon_active = True
        except Exception:
            pass

        # Lệnh thực thi phải phản ánh ĐÚNG effort/model đang chọn trên UI,
        # không được hardcode '--effort high' (gây hiển thị lệch với cài đặt thật).
        studio_settings = load_settings()
        active_effort = str(studio_settings.get('effort') or 'high').strip().lower()
        active_model = str(studio_settings.get('model') or '').strip()
        exec_command = f"{agy_bin} --dangerously-skip-permissions --mode accept-edits"
        if active_effort:
            exec_command += f" --effort {active_effort}"
        if active_model:
            exec_command += f" --model {active_model}"
        exec_command += " --output-format stream-json"

        return {
            'installed': installed,
            'logged_in': logged_in,
            'ready': installed and logged_in,
            'daemon_active': daemon_active,
            'exec_command': exec_command,
            'active_effort': active_effort,
            'active_model': active_model,
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
            'active_effort': '',
            'active_model': '',
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

        # Đồng bộ và ưu tiên các API Key mô hình
        sync_all_api_keys_and_providers(curr)

        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(curr, f, ensure_ascii=False, indent=2)

        # Đồng bộ effort/model sang cấu hình toàn cục của OpenCode CLI
        # để terminal `opencode` mở tay không bị lệch mức suy luận so với UI.
        sync_opencode_active_model(curr)
        # Đồng bộ effort/model sang Gemini CLI (Antigravity settings.json)
        # để terminal `agy` mở tay cũng dùng đúng mức suy luận.
        sync_gemini_cli_active_model(curr)

        try:
            import config
            if hasattr(config, 'refresh_workspaces'):
                config.refresh_workspaces()
            else:
                if curr.get('fe_workspace'):
                    config.FE_WORKSPACE = os.path.expanduser(str(curr['fe_workspace']).strip())
                if curr.get('be_workspace'):
                    config.BE_WORKSPACE = os.path.expanduser(str(curr['be_workspace']).strip())
        except Exception:
            pass

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
    'latest_api_error': None,
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
