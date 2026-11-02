#!/usr/bin/env python3
"""Quản lý AI Terminal ngầm (FE & BE), thực thi Làm Task / Fix Bug và Hàng đợi (FIFO Queue)."""

import atexit
import datetime
import json
import os
import re
import subprocess
import threading
import time
import uuid

from config import FE_WORKSPACE, BE_WORKSPACE, BRAIN_DIR, HISTORY_FILE, get_agy_bin, get_opencode_bin, get_fe_workspace, get_be_workspace, get_workspace
from studio.state import (
    app_state,
    state_lock,
    save_queue_state_unlocked,
    load_messages,
    save_messages,
    load_settings,
)

background_terminals = {}
task_terminals = {}
task_terminal_locks = {}
terminal_meta_lock = threading.Lock()


def _get_terminal_key(role: str, task_id: str = None) -> str:
    tid = str(task_id or '').strip()
    return f"{tid}_{role}" if tid else role


def _get_terminal_lock(key: str) -> threading.RLock:
    with terminal_meta_lock:
        if key not in task_terminal_locks:
            task_terminal_locks[key] = threading.RLock()
        return task_terminal_locks[key]


def cleanup_background_terminals():
    """Dọn dẹp sạch sẽ toàn bộ terminal ngầm của các tác vụ khi server thoát."""
    global task_terminals, background_terminals
    for key, info in list(task_terminals.items()):
        proc = info.get('proc')
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    task_terminals.clear()
    background_terminals.clear()


atexit.register(cleanup_background_terminals)


def close_task_terminals(task_id: str):
    """
    Đóng và dọn dẹp sạch sẽ AI Terminal ngầm của một tác vụ khi người dùng xóa tác vụ đó.
    Context của tác vụ chỉ bị hủy khi người dùng bấm Xóa tác vụ.
    """
    global task_terminals, background_terminals
    if not task_id:
        return
    tid = str(task_id).strip()
    clean_tid = tid.replace('queued_', '')
    keys_to_remove = [
        k for k in list(task_terminals.keys())
        if k.startswith(f"{tid}_") or k.startswith(f"{clean_tid}_") or k in (tid, clean_tid)
    ]
    for key in keys_to_remove:
        lock = _get_terminal_lock(key)
        with lock:
            info = task_terminals.pop(key, None)
            if info:
                proc = info.get('proc')
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=1.5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                print(f"[STUDIO] Đã đóng terminal ngầm và giải phóng context của tác vụ [{tid}] (key: {key})")


_MODEL_VARIANT_RE = re.compile(r'-(low|medium|high|xhigh|max)$', re.IGNORECASE)
_EFFORT_FALLBACK_ORDER = ('high', 'medium', 'low', 'xhigh', 'max')
_AVAILABLE_MODELS_CACHE = {'ts': 0.0, 'ids': set()}
_AVAILABLE_MODELS_TTL = 60.0


def _split_provider_prefix(model_id: str):
    """Tách tiền tố provider ('9router/' hoặc 'opencode/') khỏi id model thô."""
    mid = str(model_id or '').strip()
    for prefix in ('9router/', 'opencode/'):
        if mid.startswith(prefix):
            return prefix, mid[len(prefix):]
    return '', mid


def _available_opencode_model_ids(force: bool = False) -> set:
    """Tập id model thô (không kèm tiền tố provider) đang có thật trên 9router/OpenCode."""
    now = time.time()
    cached = _AVAILABLE_MODELS_CACHE['ids']
    if not force and cached and (now - _AVAILABLE_MODELS_CACHE['ts']) < _AVAILABLE_MODELS_TTL:
        return cached

    ids = set()
    try:
        from studio.state import _9ROUTER_RAW_MODELS, get_opencode_models
        if force or not _9ROUTER_RAW_MODELS:
            get_opencode_models()
        for mid in (_9ROUTER_RAW_MODELS or set()):
            mid = str(mid or '').strip()
            if not mid:
                continue
            _prefix, raw = _split_provider_prefix(mid)
            ids.add(raw)
    except Exception:
        pass

    _AVAILABLE_MODELS_CACHE['ids'] = ids
    _AVAILABLE_MODELS_CACHE['ts'] = now
    return ids


def resolve_effective_opencode_model(base_model: str, effort: str = None) -> str:
    """
    Resolve model OpenCode kết hợp với mức độ suy luận (effort) được chọn từ card bên dưới.
    Ví dụ: '9router/ag/gemini-3.8-flash' + effort='high' -> '9router/ag/gemini-3.8-flash-high'.
    Nếu model không có variant (ví dụ '9router/ag/gemini-pro-agent') thì giữ nguyên base model.
    Luôn đối chiếu với danh sách model thật từ 9router để tránh lỗi ModelUnavailable.
    """
    prefix, raw = _split_provider_prefix(base_model or '9router/ag/gemini-3.8-flash')
    effort_str = str(effort or 'high').strip().lower()

    if raw.lower().endswith('-agent'):
        target_raw = raw
        siblings = {raw}
    else:
        base_raw = _MODEL_VARIANT_RE.sub('', raw) or raw
        available = _available_opencode_model_ids()
        siblings = {m for m in available if _MODEL_VARIANT_RE.sub('', m) == base_raw}
        candidate = f"{base_raw}-{effort_str}"

        if available:
            if candidate in available:
                target_raw = candidate
            elif base_raw in available:
                target_raw = base_raw
            else:
                target_raw = next(
                    (f"{base_raw}-{e}" for e in _EFFORT_FALLBACK_ORDER if f"{base_raw}-{e}" in available),
                    base_raw,
                )
        else:
            target_raw = candidate

    target = f"{prefix}{target_raw}"

    try:
        from studio.state import sync_opencode_provider_models
        # Đăng ký luôn mọi biến thể effort của model nền để lần đổi effort sau không bị ModelUnavailable.
        sync_opencode_provider_models({f"{prefix}{m}" for m in siblings} | {target})
    except Exception:
        pass

    return target


def sync_active_task_models(settings: dict = None):
    """Đồng bộ model/effort hiển thị của các session đang có theo cấu hình mới nhất.

    Trước đây khi đổi Effort/Model trong Settings, header AI Terminal vẫn giữ giá trị cũ
    (ví dụ '-high') trong khi Settings hiển thị giá trị mới ('-medium'). Hàm này ghi đè
    snapshot của từng session để UI và terminal luôn khớp nhau.
    """
    try:
        cfg = settings if isinstance(settings, dict) and settings else app_state.get('settings') or {}
        engine = str(cfg.get('engine') or 'gemini_cli').strip().lower()
        effort = str(cfg.get('effort') or 'high').strip()
        base_model = str(cfg.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip()
        if engine == 'opencode':
            effective_model = resolve_effective_opencode_model(base_model, effort)
        else:
            effective_model = str(cfg.get('model') or '').strip()

        with state_lock:
            for ts in (app_state.get('active_tasks') or {}).values():
                if not isinstance(ts, dict):
                    continue
                ts['engine'] = engine
                ts['effort'] = effort
                ts['model'] = effective_model
                sess = ts.get('session')
                if isinstance(sess, dict):
                    sess['engine'] = engine
                    sess['effort'] = effort
                    sess['model'] = effective_model
        return effective_model
    except Exception:
        return ''


def get_or_start_background_terminal(role: str, task_id: str = None, verbose: bool = True):
    """
    Lấy hoặc khởi tạo cấu hình/tiến trình AI Terminal ngầm cho từng tác vụ (task_id) trên FE hoặc BE.
    Hỗ trợ chuyển đổi mượt mà giữa:
      1. Gemini CLI (Antigravity / `agy`) với persistent stream-json
      2. 9router OpenCode CLI (`opencode`) với auto-approved streaming và lưu session ID
    Mỗi tác vụ duy trì session/terminal riêng để giữ nguyên ngữ cảnh (context) khi trao đổi tiếp.
    Khi đổi mức suy luận (effort) hoặc engine giữa chừng, hệ thống tự động kế thừa session cũ.
    """
    global task_terminals, background_terminals
    key = _get_terminal_key(role, task_id)
    lock = _get_terminal_lock(key)
    with lock:
        existing = task_terminals.get(key)
        settings = app_state.get('settings', {}) if isinstance(app_state.get('settings'), dict) else load_settings()
        target_engine = str(settings.get('engine') or 'gemini_cli').strip().lower()
        target_effort = str(settings.get('effort') or 'high').strip()
        base_opencode_model = str(settings.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip()
        target_opencode_model = resolve_effective_opencode_model(base_opencode_model, target_effort)
        target_model = target_opencode_model if target_engine == 'opencode' else str(settings.get('model') or '').strip()

        last_cid = None
        if existing:
            last_cid = existing.get('conversation_id')
            curr_engine = existing.get('engine') or 'gemini_cli'
            curr_effort = existing.get('effort') or 'high'
            curr_model = existing.get('model') or ''
            is_alive = bool(existing.get('proc') and existing['proc'].poll() is None and existing.get('stdin_pipe'))

            # Nếu cấu hình không đổi và (nếu là gemini_cli thì tiến trình vẫn sống)
            if curr_engine == target_engine and curr_effort == target_effort and curr_model == target_model:
                if target_engine == 'opencode' or is_alive:
                    return existing

            # Nếu tiến trình cũ đang chạy mà cần đổi engine / effort / model:
            if is_alive:
                old_proc = existing.get('proc')
                try:
                    old_proc.terminate()
                    old_proc.wait(timeout=1.5)
                except Exception:
                    try:
                        old_proc.kill()
                    except Exception:
                        pass
                if verbose:
                    print(f"[STUDIO] Thay đổi cấu hình [{key}]: Engine={curr_engine}->{target_engine}, Effort={curr_effort}->{target_effort} (giữ conversation_id: {last_cid})")

        # Tìm conversation_id từ active_tasks nếu existing chưa lưu
        if not last_cid and task_id:
            tid = str(task_id).strip()
            clean_tid = tid.replace('queued_', '')
            ts = app_state.get('active_tasks', {}).get(tid) or app_state.get('active_tasks', {}).get(clean_tid)
            if ts and ts.get('session'):
                last_cid = ts['session'].get('conversation_id')

        ws = get_workspace(role)
        label = 'Frontend (easysalon-webapp)' if role == 'fe' else 'Backend (easysalon-api)'
        if task_id:
            label += f" [{task_id}]"

        # TRƯỜNG HỢP 1: 9router OpenCode Engine
        if target_engine == 'opencode':
            opencode_model = target_opencode_model
            info = {
                'key': key,
                'role': role,
                'task_id': task_id,
                'engine': 'opencode',
                'workspace': ws,
                'label': label,
                'effort': target_effort,
                'model': opencode_model,
                'conversation_id': last_cid,
                'proc': None,
                'stdin_pipe': None,
                'stdout_pipe': None,
                'started_at': datetime.datetime.now().strftime('%H:%M:%S')
            }
            task_terminals[key] = info
            background_terminals[role] = info
            resumed_str = f" (Nối tiếp session {last_cid[:8]}...)" if last_cid else " (Session mới)"
            if verbose:
                print(f"[STUDIO] Đã cấu hình 9router OpenCode cho {label} [Model: {opencode_model}]{resumed_str}")
            return info

        # TRƯỜNG HỢP 2: Google Gemini CLI (Antigravity Engine với streaming realtime theo lượt)
        info = {
            'key': key,
            'role': role,
            'task_id': task_id,
            'engine': 'gemini_cli',
            'pid': None,
            'proc': None,
            'stdin_pipe': None,
            'stdout_pipe': None,
            'workspace': ws,
            'label': label,
            'effort': target_effort,
            'model': target_model,
            'conversation_id': last_cid,
            'started_at': datetime.datetime.now().strftime('%H:%M:%S')
        }
        task_terminals[key] = info
        background_terminals[role] = info
        resumed_str = f" (Nối tiếp cuộc hội thoại {last_cid[:8]}... với Effort: {target_effort.upper()})" if last_cid else f" (Effort: {target_effort.upper()})"
        if verbose:
            print(f"[STUDIO] Đã cấu hình Gemini CLI ngầm cho {label}{resumed_str}")
        return info


def restart_background_terminal(role: str, task_id: str = None):
    """Làm mới tiến trình AI Terminal ngầm của một tác vụ cụ thể."""
    global task_terminals
    key = _get_terminal_key(role, task_id)
    lock = _get_terminal_lock(key)
    with lock:
        existing = task_terminals.pop(key, None)
        if existing and existing.get('proc'):
            proc = existing['proc']
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=1.5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        return get_or_start_background_terminal(role, task_id=task_id)


def ensure_background_terminals(verbose: bool = False):
    """Tự động kiểm tra/khởi tạo terminal ngầm mặc định cho FE & BE."""
    for role in ('fe', 'be'):
        get_or_start_background_terminal(role, verbose=verbose)


def build_fallback_cli_cmd(prompt_str: str, conversation_id: str = None) -> list:
    """Tạo lệnh CLI chạy đơn lượt fallback nếu không dùng persistent streaming."""
    settings = app_state.get('settings', {}) if isinstance(app_state.get('settings'), dict) else load_settings()
    engine = str(settings.get('engine') or 'gemini_cli').strip().lower()
    if engine == 'opencode':
        opencode_bin = get_opencode_bin()
        base_opencode_model = str(settings.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip()
        effort = str(settings.get('effort') or 'high').strip()
        opencode_model = resolve_effective_opencode_model(base_opencode_model, effort)
        cmd = [opencode_bin, 'run', '--format', 'json', '--auto']
        if opencode_model:
            cmd.extend(['--model', opencode_model])
        if conversation_id:
            cmd.extend(['--session', conversation_id])
        cmd.append(prompt_str)
        return cmd

    agy_bin = get_agy_bin()
    effort = str(settings.get('effort') or 'high').strip()
    model = str(settings.get('model') or '').strip()
    cmd = [
        agy_bin,
        '--dangerously-skip-permissions',
        '--mode', 'accept-edits',
        '--effort', effort,
        '--output-format', 'stream-json'
    ]
    if conversation_id:
        cmd.extend(['--conversation', conversation_id])
    if model:
        cmd.extend(['--model', model])
    cmd.extend(['-p', prompt_str])
    return cmd


def format_step_terminal_action(tool_name: str, params: dict, output: str = '') -> dict:
    """
    Chuẩn hóa log thao tác tool trên AI Terminal ngầm sang format bullet terminal trực quan:
    ● Ran (grep -i "room" ai-boundary/CATALOG.md | head -n 30)
    ● Explored 6 files (BedRoomManagerController.cs, ...)
    ● Ran (grep -rn "bed-room" ...)
    ● Explored 1 file (BedRoomManagerActionFormButton.tsx)
    ● Edited BedRoomPositionFormButton.tsx
    """
    tname = (tool_name or '').lower().strip()
    cmd = str(params.get('CommandLine') or params.get('command') or params.get('cmd') or '').strip()
    path = str(params.get('Path') or params.get('path') or params.get('filePath') or params.get('file_path') or params.get('TargetFile') or '').strip()
    pattern = str(params.get('query') or params.get('pattern') or '').strip()
    fname = os.path.basename(path) if path else ''

    if tname in ('run_command', 'command', 'bash', 'sh') or cmd:
        action_type = 'ran'
        short_cmd = cmd[:140] + ('...' if len(cmd) > 140 else '') if cmd else tname
        display_title = f"Ran ({short_cmd})"
    elif tname in ('read_file', 'view_file', 'read'):
        action_type = 'explored'
        display_title = f"Explored 1 file ({fname})" if fname else "Explored 1 file"
    elif tname in ('grep_search', 'search', 'grep'):
        action_type = 'ran'
        q = pattern or cmd or fname or 'text'
        display_title = f"Ran (grep \"{q}\")"
    elif tname in ('find_by_name', 'list_dir', 'ls', 'explore', 'glob'):
        action_type = 'explored'
        display_title = f"Explored ({pattern or fname or path or '.'})"
    elif tname in ('replace_file_content', 'multi_replace_file_content', 'edit_file', 'write_file', 'edit', 'write', 'sed_file', 'patch', 'apply_diff'):
        action_type = 'edited'
        display_title = f"Edited {fname}" if fname else "Edited file"
    else:
        action_type = 'ran'
        summary = cmd or fname or pattern or ", ".join([f"{k}: {v}" for k, v in list(params.items())[:2]])
        display_title = f"Ran {tool_name} ({summary[:80]})" if summary else f"Ran {tool_name}"

    return {
        'action_type': action_type,
        'display_title': display_title,
        'command': cmd,
        'path': path,
        'file_name': fname
    }



def get_terminal_feed(workspace, limit=14):
    """Đọc trực tiếp transcript phiên làm việc thực tế của Terminal tương ứng từ Brain folder."""
    cid = None
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        if item.get('workspace') == workspace and item.get('conversationId'):
                            cid = item['conversationId']
                    except Exception:
                        pass
        except Exception:
            pass

    if not cid:
        # Fallback to newest folder in BRAIN_DIR
        return {'status': 'OFFLINE', 'cid': None, 'messages': []}

    t_file = os.path.join(BRAIN_DIR, cid, '.system_generated', 'logs', 'transcript.jsonl')
    t_full = os.path.join(BRAIN_DIR, cid, '.system_generated', 'logs', 'transcript_full.jsonl')

    if not os.path.exists(t_file):
        return {'status': 'IDLE', 'cid': cid, 'messages': []}

    messages = []
    lines = []
    try:
        with open(t_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        pass

    full_lines = None

    for i, line in enumerate(lines):
        try:
            s = json.loads(line)
            stype = s.get('type')
            source = s.get('source')
            created_at = s.get('created_at', '')

            if stype == 'USER_INPUT' or (source == 'USER_EXPLICIT' and s.get('content')):
                raw = s.get('content', '').strip()
                m = re.search(r'<USER_REQUEST>(.*?)</USER_REQUEST>', raw, re.DOTALL)
                clean_text = m.group(1).strip() if m else raw
                messages.append({
                    'role': 'user',
                    'content': clean_text,
                    'timestamp': created_at,
                    'step': s.get('step_index', i)
                })

            elif stype == 'PLANNER_RESPONSE':
                content = s.get('content') or ''
                if 'content' in s.get('truncated_fields', []) and os.path.exists(t_full):
                    if full_lines is None:
                        try:
                            with open(t_full, 'r', encoding='utf-8') as ff:
                                full_lines = ff.readlines()
                        except Exception:
                            full_lines = []
                    if i < len(full_lines):
                        try:
                            fs = json.loads(full_lines[i])
                            content = fs.get('content') or content
                        except Exception:
                            pass

                tools = []
                for tc in s.get('tool_calls', []):
                    tname = tc.get('name', '')
                    args = tc.get('args', {})
                    if tname == 'read_file':
                        p = args.get('Path', '').strip('"')
                        tools.append(f'Đọc file: {os.path.basename(p)}')
                    elif tname == 'run_command':
                        tsum = args.get('toolSummary', '') or args.get('CommandLine', '')[:35]
                        clean_sum = tsum.strip('"').strip("'")
                        tools.append(f'Lệnh: {clean_sum}')
                    elif tname in ('edit_file', 'write_file'):
                        p = args.get('Path', '').strip('"').strip("'")
                        tools.append(f'Sửa file: {os.path.basename(p)}')
                    else:
                        tools.append(f'Tool: {tname}')

                if content or tools:
                    messages.append({
                        'role': 'assistant',
                        'content': content,
                        'tools': tools,
                        'timestamp': created_at,
                        'step': s.get('step_index', i)
                    })
        except Exception:
            pass

    completed_result = None
    for m in reversed(messages):
        if m.get('role') == 'assistant' and m.get('content'):
            completed_result = {
                'content': m['content'],
                'timestamp': m.get('timestamp', ''),
                'step': m.get('step')
            }
            break

    if not completed_result:
        try:
            work_logs = load_messages()
            role = 'fe' if os.path.abspath(workspace) == os.path.abspath(get_fe_workspace()) else 'be'
            for log in reversed(work_logs):
                target = log.get('target', '')
                if target in (role, 'both') and (log.get('result') or log.get('turns')):
                    c = log.get('result', '')
                    if not c and log.get('turns'):
                        c = log['turns'][-1].get('content', '')
                    if c:
                        completed_result = {
                            'content': c,
                            'timestamp': log.get('created_at', ''),
                            'title': log.get('title') or log.get('prompt', '')
                        }
                        break
        except Exception:
            pass

    return {
        'status': 'ONLINE',
        'cid': cid,
        'messages': messages[-limit:],
        'completed_result': completed_result
    }



def format_slash_skills_prefix(skill_input) -> str:
    """Chuyển đổi danh sách skill thành chuỗi slash command: chọn skill a -> /a"""
    if isinstance(skill_input, list):
        skill_list = [str(s).strip() for s in skill_input if str(s).strip()]
    elif isinstance(skill_input, str):
        skill_list = [s.strip() for s in skill_input.split(',') if s.strip()]
    else:
        skill_list = []

    slash_items = []
    for s in skill_list:
        s_clean = s.strip().lstrip('/')
        if not s_clean:
            continue
        slash_items.append(f"/{s_clean}")
    return " ".join(slash_items)


def build_skill_directive(skill_input) -> str:
    if isinstance(skill_input, list):
        skill_list = [str(s).strip() for s in skill_input if str(s).strip()]
    elif isinstance(skill_input, str):
        skill_list = [s.strip() for s in skill_input.split(',') if s.strip()]
    else:
        skill_list = []

    if not skill_list:
        return ""

    formatted = []
    for s in skill_list:
        sc = s.strip().lstrip('/')
        if not sc:
            continue
        formatted.append(sc if sc.startswith('skill-') else f'skill-{sc}')

    bullet_points = [
        f"- Áp dụng skill '/{s}' (tài liệu '.agents/skills/{s}/SKILL.md' trong workspace)"
        for s in formatted
    ]
    return "\n" + "\n".join(bullet_points) + "\n"


def collect_workspace_changes(workspace: str, repo_label: str, touched_paths=None, preexisting_paths=None):
    """Quét git status & git diff của workspace để lấy danh sách file thay đổi + diff chi tiết."""
    changes = []
    if not os.path.isdir(workspace):
        return changes

    touched_rel = set()
    if touched_paths:
        for tp in touched_paths:
            if not tp:
                continue
            try:
                rel = os.path.relpath(tp, workspace) if os.path.isabs(tp) else tp
                if not rel.startswith('..'):
                    touched_rel.add(rel.replace('\\', '/').lstrip('./'))
            except Exception:
                pass

    preexisting_rel = set()
    if preexisting_paths:
        for pp in preexisting_paths:
            if not pp:
                continue
            try:
                rel = os.path.relpath(pp, workspace) if os.path.isabs(pp) else pp
                if not rel.startswith('..'):
                    preexisting_rel.add(rel.replace('\\', '/').lstrip('./'))
            except Exception:
                pass

    try:
        st_out = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=workspace,
            stderr=subprocess.DEVNULL,
            timeout=5
        ).decode('utf-8', errors='replace')
    except Exception:
        st_out = ''

    numstat_map = {}
    try:
        ns_out = subprocess.check_output(
            ['git', 'diff', '--numstat', 'HEAD'],
            cwd=workspace,
            stderr=subprocess.DEVNULL,
            timeout=5
        ).decode('utf-8', errors='replace')
        for line in ns_out.splitlines():
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                adds = int(parts[0]) if parts[0].isdigit() else 0
                dels = int(parts[1]) if parts[1].isdigit() else 0
                numstat_map[parts[2].strip()] = (adds, dels)
    except Exception:
        pass

    seen_files = set()
    raw_entries = []
    for line in st_out.splitlines():
        if len(line) < 4:
            continue
        status_code = line[:2].strip() or 'M'
        fpath = line[3:].strip().strip('"')
        if ' -> ' in fpath:
            fpath = fpath.split(' -> ')[-1].strip()
        seen_files.add(fpath)
        raw_entries.append((status_code, fpath))

    for tr in touched_rel:
        if tr not in seen_files and os.path.exists(os.path.join(workspace, tr)):
            raw_entries.append(('M', tr))
            seen_files.add(tr)

    # Ưu tiên các file vừa được AI tool chạm tới lên đầu
    raw_entries.sort(key=lambda item: (0 if (item[1] in touched_rel or item[1].lstrip('./') in touched_rel) else 1, item[1]))

    for status_code, fpath in raw_entries[:25]:
        adds, dels = numstat_map.get(fpath, (0, 0))
        diff_text = ''
        try:
            if status_code == '??':
                full_p = os.path.join(workspace, fpath)
                if os.path.isfile(full_p) and os.path.getsize(full_p) < 80000:
                    with open(full_p, 'r', encoding='utf-8', errors='replace') as fp:
                        file_lines = fp.read().splitlines()[:120]
                    adds = len(file_lines)
                    diff_text = "\n".join([f"+ {l}" for l in file_lines])
            else:
                diff_out = subprocess.check_output(
                    ['git', 'diff', 'HEAD', '--', fpath],
                    cwd=workspace,
                    stderr=subprocess.DEVNULL,
                    timeout=4
                ).decode('utf-8', errors='replace')
                if not diff_out.strip():
                    diff_out = subprocess.check_output(
                        ['git', 'diff', '--', fpath],
                        cwd=workspace,
                        stderr=subprocess.DEVNULL,
                        timeout=4
                    ).decode('utf-8', errors='replace')
                diff_lines = diff_out.splitlines()
                if len(diff_lines) > 160:
                    diff_text = "\n".join(diff_lines[:160]) + f"\n... (còn {len(diff_lines) - 160} dòng)"
                else:
                    diff_text = "\n".join(diff_lines)
        except Exception:
            diff_text = ''

        fpath_norm = fpath.replace('\\', '/').lstrip('./')
        is_touched = (fpath_norm in touched_rel) or (fpath in touched_rel)
        if preexisting_paths is not None:
            is_pre = ((fpath_norm in preexisting_rel) or (fpath in preexisting_rel)) and not is_touched
        else:
            is_pre = not is_touched

        changes.append({
            'repo': repo_label,
            'path': fpath,
            'status': 'A' if status_code == '??' else status_code,
            'additions': adds,
            'deletions': dels,
            'touched_by_ai': is_touched,
            'is_preexisting': is_pre,
            'diff': diff_text
        })

    return changes


# -------------------------------------------------------------
# WORKER: LÀM TASK & FIX BUG (AI TERMINAL STREAMING + QUEUE)
# -------------------------------------------------------------
def stream_process_turn(cmd, cwd, turn_data, timeout=360, task_state=None, repo_label='FE'):
    """Đưa trực tiếp prompt (/skill + prompt) xuống AI Terminal ngầm đang chạy (FE/BE) và stream realtime từng tool call + code changes."""
    t0 = time.time()
    proc = None
    turn_data.setdefault('step_logs', [])
    turn_data.setdefault('content', '')
    turn_data.setdefault('changed_files', [])
    touched_paths = set()
    last_git_scan_time = 0.0
    role = 'fe' if os.path.abspath(cwd) == os.path.abspath(get_fe_workspace()) else 'be'
    prompt_text = cmd[-1] if isinstance(cmd, (list, tuple)) and cmd else str(cmd)

    # Ghi nhận các file đã có thay đổi trước đó (dirty files) trong workspace trước khi AI thực thi lượt này
    preexisting_paths = set()
    try:
        st_pre = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            timeout=4
        ).decode('utf-8', errors='replace')
        for line in st_pre.splitlines():
            if len(line) >= 4:
                p_f = line[3:].strip().strip('"')
                if ' -> ' in p_f:
                    p_f = p_f.split(' -> ')[-1].strip()
                preexisting_paths.add(p_f.replace('\\', '/').lstrip('./'))
    except Exception:
        pass

    task_id = None
    if task_state and isinstance(task_state, dict):
        task_id = task_state.get('task_id') or (task_state.get('session') or {}).get('task_id')

    settings = app_state.get('settings', {}) if isinstance(app_state.get('settings'), dict) else load_settings()
    engine = str(settings.get('engine') or 'gemini_cli').strip().lower()
    is_opencode = (engine == 'opencode')
    target_effort = str(settings.get('effort') or 'high').strip()
    base_opencode_model = str(settings.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip()
    opencode_model = resolve_effective_opencode_model(base_opencode_model, target_effort)
    engine_label = 'OpenCode CLI' if is_opencode else 'Gemini CLI'
    active_model = opencode_model if is_opencode else str(settings.get('model') or '')

    turn_data['engine'] = engine
    turn_data['engine_label'] = engine_label
    turn_data['model'] = active_model
    turn_data['effort'] = target_effort
    if task_state and isinstance(task_state, dict):
        task_state['engine'] = engine
        task_state['engine_label'] = engine_label
        task_state['model'] = active_model
        task_state['effort'] = target_effort
        if task_state.get('session') and isinstance(task_state['session'], dict):
            task_state['session']['engine'] = engine
            task_state['session']['engine_label'] = engine_label
            task_state['session']['model'] = active_model
            task_state['session']['effort'] = target_effort

    key = _get_terminal_key(role, task_id)
    role_lock = _get_terminal_lock(key)
    with role_lock:
        try:
            bg_info = get_or_start_background_terminal(role, task_id=task_id)
            last_cid = None
            if task_state and isinstance(task_state, dict):
                sess = task_state.get('session') or {}
                last_cid = sess.get('conversation_id')
            if not last_cid and bg_info:
                last_cid = bg_info.get('conversation_id')
            if not last_cid:
                last_cid = turn_data.get('conversation_id')

            if is_opencode:
                opencode_bin = get_opencode_bin()
                clean_tid = re.sub(r'[^a-zA-Z0-9_]', '_', str(task_id or 'task'))
                opencode_session_id = last_cid or f"ses_{clean_tid}_{role}"
                turn_data['conversation_id'] = opencode_session_id
                if bg_info:
                    bg_info['conversation_id'] = opencode_session_id
                opencode_cmd = [
                    opencode_bin,
                    'run',
                    '--format', 'json',
                    '--model', opencode_model,
                    '--auto',
                    '--session', opencode_session_id,
                    prompt_text
                ]
                print(f"[STUDIO] AI Terminal [{role.upper()}] thực thi lượt mới qua OpenCode (9router) [Model: {opencode_model}, Effort: {target_effort.upper()}]...")
                proc = subprocess.Popen(
                    opencode_cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                stdout_pipe = proc.stdout
            else:
                cli_cmd = build_fallback_cli_cmd(prompt_text, conversation_id=last_cid)
                eff_flag = ""
                if "--effort" in cli_cmd:
                    try:
                        idx = cli_cmd.index("--effort")
                        if idx + 1 < len(cli_cmd):
                            eff_flag = f" [Effort: {cli_cmd[idx + 1].upper()}]"
                    except Exception:
                        pass
                print(f"[STUDIO] AI Terminal [{role.upper()}] thực thi lượt mới{eff_flag}...")
                proc = subprocess.Popen(
                    cli_cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                stdout_pipe = proc.stdout

            with state_lock:
                if task_state is not None:
                    task_state['current_process'] = proc
                app_state['current_process'] = proc

            content_parts = []
            for line in iter(stdout_pipe.readline, ''):
                if not line:
                    break
                line_str = line.strip()
                if not line_str:
                    continue

                # Phân tích NDJSON streaming từ AI Terminal ngầm (--output-format stream-json hoặc opencode --format json)
                if line_str.startswith('{') and line_str.endswith('}'):
                    try:
                        event_data = json.loads(line_str, strict=False)

                        # --- 1. XỬ LÝ EVENT TỪ OPENCODE (type: step_start, tool_use, text, step_finish, error) ---
                        if is_opencode or ('type' in event_data and event_data.get('type') in ('step_start', 'tool_use', 'text', 'step_finish', 'error')):
                            ev_type = event_data.get('type')
                            if ev_type == 'step_start':
                                cid = event_data.get('sessionID')
                                if cid:
                                    with state_lock:
                                        turn_data['conversation_id'] = cid
                                    if bg_info:
                                        bg_info['conversation_id'] = cid
                                    if task_state and isinstance(task_state, dict) and task_state.get('session'):
                                        task_state['session']['conversation_id'] = cid

                            elif ev_type == 'tool_use':
                                part = event_data.get('part', {})
                                tname = part.get('tool', 'tool')
                                st_obj = part.get('state', {})
                                params = st_obj.get('input', {}) or {}
                                output = st_obj.get('output', '') or ''
                                step_id = part.get('id') or part.get('partID') or (len(turn_data['step_logs']) + 1)
                                state_status = st_obj.get('status', 'completed')
                                state_str = 'DONE' if state_status == 'completed' else state_status.upper()

                                param_summary = ''
                                p_cmd = params.get('CommandLine') or params.get('command') or params.get('cmd')
                                p_path = params.get('Path') or params.get('path') or params.get('filePath') or params.get('file_path') or params.get('TargetFile')
                                p_pattern = params.get('query') or params.get('pattern')
                                if p_cmd:
                                    param_summary = str(p_cmd)
                                elif p_path:
                                    param_summary = str(p_path)
                                    if tname in ('edit', 'write', 'edit_file', 'write_file', 'patch', 'apply_diff'):
                                        touched_paths.add(str(p_path))
                                elif p_pattern:
                                    param_summary = str(p_pattern)
                                elif params:
                                    param_summary = ", ".join([f"{k}: {v}" for k, v in list(params.items())[:2]])

                                is_edit_done = (tname in ('edit', 'write', 'edit_file', 'write_file', 'patch', 'apply_diff'))
                                latest_changes = None
                                now = time.time()
                                if is_edit_done and touched_paths and (now - last_git_scan_time > 3.0):
                                    latest_changes = collect_workspace_changes(cwd, repo_label, touched_paths, preexisting_paths=preexisting_paths)
                                    last_git_scan_time = now

                                act_info = format_step_terminal_action(tname, params, output)
                                with state_lock:
                                    existing = next((s for s in turn_data['step_logs'] if s.get('step_id') == step_id), None)
                                    if existing:
                                        existing['state'] = state_str
                                        existing['display_title'] = act_info['display_title']
                                        existing['action_type'] = act_info['action_type']
                                        if output:
                                            existing['output'] = output
                                    else:
                                        turn_data['step_logs'].append({
                                            'step_id': step_id,
                                            'step_index': len(turn_data['step_logs']) + 1,
                                            'tool_name': tname,
                                            'display_title': act_info['display_title'],
                                            'action_type': act_info['action_type'],
                                            'param_summary': param_summary,
                                            'params': params,
                                            'state': state_str,
                                            'output': output,
                                            'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
                                        })
                                    if latest_changes is not None:
                                        turn_data['changed_files'] = latest_changes
                                    turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                                    if task_state is not None:
                                        task_state['status_text'] = f"[OpenCode] ● {act_info['display_title']}"

                            elif ev_type == 'text':
                                part = event_data.get('part', {})
                                text_chunk = part.get('text', '')
                                if text_chunk:
                                    content_parts.append(text_chunk)
                                    with state_lock:
                                        turn_data['content'] = "".join(content_parts)
                                        turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                                        if task_state is not None:
                                            snippet = "".join(content_parts)[-50:].strip().replace('\n', ' ')
                                            task_state['status_text'] = f"[OpenCode • {role.upper()}] ⢿ {snippet}" if snippet else f"[OpenCode • {role.upper()}] ⢿ Đang phản hồi..."

                            elif ev_type == 'error':
                                err_obj = event_data.get('error', {})
                                err_msg = err_obj.get('message') if isinstance(err_obj, dict) else str(err_obj)
                                if err_msg:
                                    content_parts.append(f"\n[Lỗi OpenCode]: {err_msg}")
                                    with state_lock:
                                        turn_data['content'] = "".join(content_parts)
                                break

                        # --- 2. XỬ LÝ EVENT TỪ GEMINI CLI (AGY) ---
                        else:
                            event_type = event_data.get('event')

                            if event_type == 'init':
                                cid = event_data.get('conversation_id') or event_data.get('init', {}).get('conversation_id')
                                if cid:
                                    with state_lock:
                                        turn_data['conversation_id'] = cid
                                    if bg_info:
                                        bg_info['conversation_id'] = cid
                                    if task_state and isinstance(task_state, dict) and task_state.get('session'):
                                        task_state['session']['conversation_id'] = cid

                            elif event_type == 'step_update':
                                su = event_data.get('step_update', {})
                                step_type = su.get('step_type')

                                if step_type == 'tool':
                                    tname = su.get('tool_name') or su.get('tool_info', {}).get('name', 'tool')
                                    params = su.get('tool_info', {}).get('parameters', {}) or {}
                                    state = su.get('state', 'ACTIVE')
                                    output = su.get('tool_info', {}).get('output') or ''
                                    duration = su.get('duration_seconds')
                                    step_idx = su.get('step_index')

                                    param_summary = ''
                                    if 'CommandLine' in params:
                                        param_summary = str(params['CommandLine'])
                                    elif 'Path' in params:
                                        param_summary = str(params['Path'])
                                        if tname in ('edit_file', 'write_file', 'replace_file_content', 'multi_replace_file_content'):
                                            touched_paths.add(str(params['Path']))
                                    elif 'TargetFile' in params:
                                        param_summary = str(params['TargetFile'])
                                        touched_paths.add(str(params['TargetFile']))
                                    elif 'query' in params:
                                        param_summary = str(params['query'])
                                    elif params:
                                        param_summary = ", ".join([f"{k}: {v}" for k, v in list(params.items())[:2]])

                                    is_edit_done = (
                                        state != 'ACTIVE'
                                        and tname in ('edit_file', 'write_file', 'replace_file_content', 'multi_replace_file_content')
                                    )
                                    latest_changes = None
                                    now = time.time()
                                    if is_edit_done and touched_paths and (now - last_git_scan_time > 3.0):
                                        latest_changes = collect_workspace_changes(cwd, repo_label, touched_paths, preexisting_paths=preexisting_paths)
                                        last_git_scan_time = now

                                    act_info = format_step_terminal_action(tname, params, output)
                                    with state_lock:
                                        existing = next((s for s in turn_data['step_logs'] if s.get('step_index') == step_idx and s.get('tool_name') == tname), None)
                                        if existing:
                                            existing['state'] = state
                                            existing['display_title'] = act_info['display_title']
                                            existing['action_type'] = act_info['action_type']
                                            if output:
                                                existing['output'] = output
                                            if duration is not None:
                                                existing['duration'] = round(duration, 2)
                                        else:
                                            turn_data['step_logs'].append({
                                                'step_index': step_idx,
                                                'tool_name': tname,
                                                'display_title': act_info['display_title'],
                                                'action_type': act_info['action_type'],
                                                'param_summary': param_summary,
                                                'params': params,
                                                'state': state,
                                                'output': output,
                                                'duration': round(duration, 2) if duration else None,
                                                'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
                                            })
                                        if latest_changes is not None:
                                            turn_data['changed_files'] = latest_changes
                                        turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                                        if task_state is not None:
                                            task_state['status_text'] = f"[Gemini CLI] ● {act_info['display_title']}"

                                elif step_type == 'agent_response':
                                    text_delta = su.get('text_delta')
                                    if text_delta:
                                        content_parts.append(text_delta)
                                        with state_lock:
                                            turn_data['content'] = "".join(content_parts)
                                            turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                                            if task_state is not None:
                                                snippet = "".join(content_parts)[-50:].strip().replace('\n', ' ')
                                                task_state['status_text'] = f"[Gemini CLI • {role.upper()}] ⢿ {snippet}" if snippet else f"[Gemini CLI • {role.upper()}] ⢿ Đang phản hồi..."

                            elif event_type == 'result':
                                res = event_data.get('result', {})
                                final_resp = res.get('response')
                                if final_resp:
                                    with state_lock:
                                        turn_data['content'] = final_resp
                                        turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                                break

                            elif event_type == 'error':
                                err_obj = event_data.get('error', {})
                                err_msg = err_obj.get('message') if isinstance(err_obj, dict) else str(err_obj)
                                if err_msg:
                                    content_parts.append(f"\n[Lỗi từ AI Terminal]: {err_msg}")
                                    with state_lock:
                                        turn_data['content'] = "".join(content_parts)
                                break

                    except Exception:
                        content_parts.append(line)
                        with state_lock:
                            turn_data['content'] = "".join(content_parts)
                            turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                else:
                    content_parts.append(line)
                    with state_lock:
                        turn_data['content'] = "".join(content_parts)
                        turn_data['elapsed_sec'] = round(time.time() - t0, 1)

            if proc:
                try:
                    proc.wait(timeout=10)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

            elapsed = round(time.time() - t0, 1)
            final_changes = collect_workspace_changes(cwd, repo_label, touched_paths, preexisting_paths=preexisting_paths)
            with state_lock:
                if not turn_data.get('content') and content_parts:
                    turn_data['content'] = "".join(content_parts).strip()
                turn_data['changed_files'] = final_changes
                turn_data['elapsed_sec'] = elapsed
                turn_data['is_streaming'] = False
                save_queue_state_unlocked()
            return turn_data.get('content', ''), elapsed

        except subprocess.TimeoutExpired:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            final_changes = collect_workspace_changes(cwd, repo_label, touched_paths, preexisting_paths=preexisting_paths)
            with state_lock:
                turn_data['content'] = turn_data.get('content', '') + "\n[Hết giờ]: Agent không phản hồi sau thời gian quy định."
                turn_data['changed_files'] = final_changes
                turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                turn_data['is_streaming'] = False
                save_queue_state_unlocked()
            return turn_data.get('content', ''), turn_data['elapsed_sec']
        except Exception as e:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            final_changes = collect_workspace_changes(cwd, repo_label, touched_paths, preexisting_paths=preexisting_paths)
            with state_lock:
                turn_data['content'] = turn_data.get('content', '') + f"\n[Lỗi]: {str(e)}"
                turn_data['changed_files'] = final_changes
                turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                turn_data['is_streaming'] = False
                save_queue_state_unlocked()
            return turn_data.get('content', ''), turn_data['elapsed_sec']
        finally:
            with state_lock:
                if task_state is not None:
                    task_state['current_process'] = None
                if app_state.get('current_process') == proc:
                    app_state['current_process'] = None


# -------------------------------------------------------------
# ACTION DIRECTIVES & CONVERSATION CONTEXT FORMATTER
# -------------------------------------------------------------
CODE_ACTION_DIRECTIVE = """
[YÊU CẦU BẮT BUỘC VỀ HÀNH ĐỘNG CODE - ACTION MANDATE]:
1. BẮT BUỘC PHẢI SỬA CODE TRỰC TIẾP VÀO FILE: Bạn phải sử dụng các công cụ chỉnh sửa (edit_file, write_file) để trực tiếp sửa/tạo code trong file mã nguồn thuộc workspace ngay trong lượt này.
2. TUYỆT ĐỐI KHÔNG CHỈ DỪNG LẠI Ở GIẢI THÍCH SUÔNG: Không được chỉ trả lời giải thích nguyên nhân lý thuyết hoặc chỉ in code block mẫu trong phản hồi Markdown. Bạn phải gọi tool để thay đổi file thực tế! Việc giải thích chỉ là phần tóm tắt ngắn SAU KHI bạn đã sửa file xong.
3. Nếu đã có nguyên nhân hoặc ngữ cảnh điều tra từ các lượt trước: Tiến hành sửa ngay vào các file liên quan mà không cần hỏi lại hay chần chừ.
""".strip()

EXPLAIN_ONLY_DIRECTIVE = """
[YÊU CẦU GIẢI THÍCH - EXPLAIN ONLY]:
Người dùng chỉ yêu cầu giải thích/phân tích/trả lời câu hỏi lý thuyết. Bạn hãy giải thích logic và nguyên nhân bằng văn bản markdown cặn kẽ mà KHÔNG CẦN gọi tool sửa code vào file.
""".strip()


def is_explanation_only_request(prompt: str) -> bool:
    """
    Kiểm tra xem yêu cầu có thực sự CHỈ muốn giải thích / phân tích lý thuyết mà không muốn sửa code không.
    Nếu người dùng yêu cầu sửa lỗi, làm task, viết code, tối ưu hoặc kiểm tra và sửa: Luôn trả về False (bắt buộc sửa code).
    """
    if not prompt:
        return False
    p = prompt.lower()

    # 1. Các cụm từ phủ định rõ ràng việc sửa code -> chắc chắn CHỈ GIẢI THÍCH
    has_negated_code = any(neg in p for neg in [
        'không cần sửa', 'khong can sua',
        'không sửa', 'khong sua',
        'không cần code', 'khong can code',
        'không code', 'khong code',
        'không sửa code', 'khong sua code',
        'đừng sửa', 'dung sua',
        'no code', 'without code'
    ])
    if has_negated_code:
        return True

    # 2. Các cụm từ thể hiện mục đích hỏi đáp, tìm nguyên nhân, kiểm tra phân tích
    explain_first_patterns = [
        'check lại cho tôi nguyên nhân', 'check nguyen nhan', 'check lại nguyên nhân',
        'tìm nguyên nhân', 'tim nguyen nhan', 'phân tích nguyên nhân', 'phan tich nguyen nhan',
        'kiểm tra nguyên nhân', 'kiem tra nguyen nhan', 'nguyên nhân là gì', 'nguyen nhan la gi',
        'nguyên nhân do đâu', 'nguyen nhan do dau',
        'chỉ giải thích', 'chi giai thich',
        'chỉ phân tích', 'chi phan tich',
        'chỉ cần giải thích', 'chi can giai thich',
        'tại sao', 'tai sao',
        'vì sao', 'vi sao',
        'lý do tại sao', 'ly do tai sao'
    ]
    if any(pat in p for pat in explain_first_patterns):
        return True

    # 3. Các từ khóa hành động code / sửa lỗi -> BẮT BUỘC SỬA CODE (trả về False)
    has_action_intent = any(act in p for act in [
        'sửa', 'sua', 'fix', 'code', 'triển khai', 'trien khai',
        'viết', 'viet', 'cập nhật', 'cap nhat', 'thay đổi', 'thay doi',
        'chỉnh', 'chinh', 'xử lý', 'xu ly', 'hoàn thiện', 'hoan thien',
        'tạo', 'tao', 'làm', 'lam', 'thêm', 'them', 'refactor', 'debug'
    ])
    if has_action_intent:
        return False

    # 4. Các cụm từ thể hiện mục đích thuần túy hỏi đáp / giải thích
    explain_only_patterns = [
        'giải thích', 'giai thich',
        'lý do', 'ly do',
        'hỏi', 'hoi',
        'explain', 'why'
    ]
    return any(pat in p for pat in explain_only_patterns)


def format_conversation_context(turns: list) -> str:
    """Format ngữ cảnh đoạn chat của các lượt trước để agent nắm toàn bộ diễn biến và các file đã phân tích."""
    if not turns:
        return ""
    lines = []
    for t in turns:
        lbl = t.get('label') or (t.get('speaker', '').upper() + ' Agent')
        round_num = t.get('round', '?')
        content = (t.get('content') or '').strip()
        step_logs = t.get('step_logs', [])
        touched = []
        for s in step_logs:
            p = s.get('params', {})
            path = p.get('Path') or p.get('TargetFile')
            if path and path not in touched:
                touched.append(path)
        touched_str = f" (Các file đã thao tác/kiểm tra: {', '.join(touched[:4])})" if touched else ""

        if content:
            if len(content) > 1800:
                content = content[:800] + "\n...[lược bớt đoạn giữa]...\n" + content[-800:]
            lines.append(f"--- [LƯỢT {round_num} - {lbl}]{touched_str} ---\n{content}")
    if not lines:
        return ""
    return "[NGỮ CẢNH ĐOẠN CHAT & KẾT QUẢ ĐÃ ĐIỀU TRA Ở CÁC LƯỢT TRƯỚC]:\n" + "\n\n".join(lines)


def run_task_worker(task_id: str, prompt: str, target: str, starter: str, rounds: int, skill: str, original_prompt: str = ''):
    global app_state

    agy_bin = get_agy_bin()
    session_id = f"task_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time = time.time()

    role_meta = {
        'fe': {
            'label': 'Frontend Agent',
            'sub': 'webapp (React/TypeScript)',
            'repo_label': 'Frontend (easysalon-webapp)',
            'color': '#06b6d4',
            'workspace': get_fe_workspace(),
            'desc': 'Frontend React / TypeScript / Ant Design Engineer tại easysalon-webapp'
        },
        'be': {
            'label': 'Backend Agent',
            'sub': 'api (.NET/C#)',
            'repo_label': 'Backend (easysalon-api)',
            'color': '#10b981',
            'workspace': get_be_workspace(),
            'desc': 'Backend .NET / C# Web API Engineer tại easysalon-api'
        }
    }

    target = target.lower()
    if target not in ('fe', 'be', 'both'):
        target = 'both'

    current_role = starter.lower() if starter.lower() in ('fe', 'be') else 'fe'
    max_rounds = 1 if target in ('fe', 'be') else max(1, int(rounds))
    slash_prefix = format_slash_skills_prefix(skill)
    converted_prompt = f"{slash_prefix} {prompt}".strip() if slash_prefix else prompt.strip()

    with state_lock:
        settings = app_state.get('settings', {}) if isinstance(app_state.get('settings'), dict) else load_settings()
        target_engine = str(settings.get('engine') or 'gemini_cli').strip().lower()
        target_effort = str(settings.get('effort') or 'high').strip()
        base_opencode_model = str(settings.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip()
        target_opencode_model = resolve_effective_opencode_model(base_opencode_model, target_effort)
        target_model = target_opencode_model if target_engine == 'opencode' else str(settings.get('model') or '').strip()
        target_engine_label = 'OpenCode CLI' if target_engine == 'opencode' else 'Gemini CLI'

        task_state = app_state['active_tasks'].get(task_id)
        existing_session = task_state.get('session') if task_state else None
        existing_turns = list(existing_session.get('turns', [])) if existing_session else []
        existing_changes = list(existing_session.get('changed_files', [])) if existing_session else []
        base_round = len(existing_turns)
        session_obj = {
            'id': existing_session.get('id', session_id) if existing_session else session_id,
            'task_id': task_id,
            'type': 'TASK',
            'target': target,
            'prompt': prompt,
            'converted_prompt': converted_prompt,
            'skill': skill,
            'engine': target_engine,
            'engine_label': target_engine_label,
            'model': target_model,
            'effort': target_effort,
            'starter': current_role,
            'total_rounds': base_round + max_rounds,
            'turns': existing_turns,
            'changed_files': existing_changes,
            'status': 'RUNNING',
            'created_at': existing_session.get('created_at', datetime.datetime.now().strftime('%H:%M:%S')) if existing_session else datetime.datetime.now().strftime('%H:%M:%S')
        }
        if not task_state:
            task_state = {
                'task_id': task_id,
                'title': f"Làm task: {prompt[:35]}",
                'mode': 'task',
                'queue_status': 'running',
                'is_running': True,
                'engine': target_engine,
                'engine_label': target_engine_label,
                'model': target_model,
                'effort': target_effort,
                'current_process': None,
                'active_round': base_round,
                'total_rounds': base_round + max_rounds,
                'active_speaker': target if target != 'both' else current_role,
                'status_text': f"Đang gửi lệnh '{converted_prompt[:45]}...' xuống AI Terminal...",
                'session': session_obj
            }
            app_state['active_tasks'][task_id] = task_state
        else:
            task_state['is_running'] = True
            task_state['queue_status'] = 'running'
            task_state['mode'] = 'task'
            task_state['engine'] = target_engine
            task_state['engine_label'] = target_engine_label
            task_state['model'] = target_model
            task_state['effort'] = target_effort
            task_state['total_rounds'] = base_round + max_rounds
            task_state['active_round'] = base_round
            task_state['active_speaker'] = target if target != 'both' else current_role
            task_state['status_text'] = f"Đang gửi lệnh '{converted_prompt[:45]}...' xuống AI Terminal..."
            task_state['session'] = session_obj

        for q_item in app_state.get('task_queue', []):
            if q_item.get('id') == task_id:
                q_item['status'] = 'running'
                q_item['isRunning'] = True

        app_state['is_running'] = True
        app_state['current_session'] = task_state['session']
        app_state['status_text'] = task_state['status_text']
        save_queue_state_unlocked()

    history = list(existing_turns)
    is_consensus_reached = False

    if target in ('fe', 'be'):
        active_role = target
        curr_info = role_meta[active_role]
        curr_round_num = base_round + 1

        with state_lock:
            task_state['active_round'] = curr_round_num
            task_state['active_speaker'] = active_role
            task_state['status_text'] = f"[{curr_info['label']}] đang thực thi: {converted_prompt[:55]}..."
            app_state['status_text'] = task_state['status_text']

        # Chuyển đổi trực tiếp: /<skill> + prompt đưa xuống AI terminal ngầm đang chạy
        is_explain = is_explanation_only_request(prompt)
        directive = EXPLAIN_ONLY_DIRECTIVE if is_explain else CODE_ACTION_DIRECTIVE

        context_str = format_conversation_context(existing_turns) if base_round > 0 else ""
        prompt_parts = []
        if slash_prefix:
            prompt_parts.append(slash_prefix)
        orig_goal = original_prompt.strip() or ((existing_session.get('prompt') or existing_session.get('description') or '').strip() if existing_session else '')
        if orig_goal and orig_goal != prompt.strip():
            prompt_parts.append(f"[MỤC TIÊU BAN ĐẦU CỦA TASK]:\n{orig_goal}")
        if context_str:
            prompt_parts.append(context_str)
            prompt_parts.append(f"[YÊU CẦU TIẾP THEO CỦA NGƯỜI DÙNG]:\n{prompt.strip()}")
        else:
            prompt_parts.append(f"[YÊU CẦU CỦA NGƯỜI DÙNG]:\n{prompt.strip()}")
        prompt_parts.append(directive)

        agent_prompt = "\n\n".join(prompt_parts)

        cmd = build_fallback_cli_cmd(agent_prompt)
        turn_data = {
            'round': curr_round_num,
            'speaker': active_role,
            'label': curr_info['label'],
            'sub': curr_info['sub'],
            'prompt_sent': agent_prompt,
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
            'elapsed_sec': 0,
            'step_logs': [],
            'changed_files': [],
            'content': '',
            'is_streaming': True,
            'engine': target_engine,
            'engine_label': target_engine_label,
            'model': target_model,
            'effort': target_effort
        }
        with state_lock:
            for prev_t in task_state.get('session', {}).get('turns', []):
                prev_t['is_streaming'] = False
            if task_state.get('session'):
                task_state['session']['turns'].append(turn_data)
            save_queue_state_unlocked()

        response_text, elapsed = stream_process_turn(
            cmd, curr_info['workspace'], turn_data, timeout=360, task_state=task_state, repo_label=curr_info['repo_label']
        )
        history.append(turn_data)

    else:
        for round_idx in range(1, max_rounds + 1):
            curr_round_num = base_round + round_idx
            with state_lock:
                if not task_state['is_running']:
                    break
                task_state['active_round'] = curr_round_num
                task_state['active_speaker'] = current_role
                curr_info = role_meta[current_role]
                other_role = 'be' if current_role == 'fe' else 'fe'
                other_info = role_meta[other_role]
                task_state['status_text'] = f"[{curr_info['label']}] đang xử lý (Lượt {curr_round_num}/{base_round + max_rounds}): {converted_prompt[:45]}..."
                app_state['status_text'] = task_state['status_text']

            is_explain = is_explanation_only_request(prompt)
            directive = EXPLAIN_ONLY_DIRECTIVE if is_explain else CODE_ACTION_DIRECTIVE

            context_str = format_conversation_context(existing_turns) if base_round > 0 else ""
            orig_goal = original_prompt.strip() or ((existing_session.get('prompt') or existing_session.get('description') or '').strip() if existing_session else '')
            orig_part = f"\n\n[MỤC TIÊU BAN ĐẦU CỦA TASK]:\n{orig_goal}" if (orig_goal and orig_goal != prompt.strip()) else ""
            context_part = f"\n\n{context_str}" if context_str else ""

            if round_idx == 1:
                agent_prompt = (
                    f"{converted_prompt}{orig_part}{context_part}\n\n"
                    f"[Phối hợp FE & BE - Lượt {curr_round_num}/{base_round + max_rounds} ({curr_info['label']})]:\n"
                    f"- Thực thi yêu cầu trên trong workspace của bạn ({curr_info['repo_label']}).\n"
                    f"- Nêu rõ API/DTO hoặc thay đổi liên quan cho {other_info['label']}.\n\n"
                    f"{directive}"
                )
            else:
                last_turn = history[-1]
                prev_summary = format_conversation_context(history)
                agent_prompt = (
                    f"{converted_prompt}{orig_part}\n\n"
                    f"{prev_summary}\n\n"
                    f"PHẢN HỒI MỚI NHẤT TỪ {other_info['label'].upper()}:\n"
                    f"\"\"\"\n{last_turn['content']}\n\"\"\"\n\n"
                    f"HƯỚNG DẪN LƯỢT {curr_round_num}/{base_round + max_rounds} ({curr_info['label']}):\n"
                    f"- Đối chiếu và thực thi các thay đổi cần thiết tại workspace của bạn ({curr_info['repo_label']}).\n"
                    f"- NẾU PHÍA BẠN KHÔNG CẦN THAY ĐỔI GÌ (ví dụ yêu cầu thuần túy thuộc về phía {other_info['label']}): Hãy nêu tóm tắt ngắn gọn xác nhận 'Phía {curr_info['label']} không cần thay đổi gì' và kết thúc ngay bằng '[ĐÃ THỐNG NHẤT - HOÀN TẤT]', TUYỆT ĐỐI KHÔNG gọi tool tìm kiếm hay sửa code lan man.\n"
                    f"- Chỉ gọi tool sửa file nếu phía bạn thực sự cần bổ sung/cập nhật code tương ứng.\n"
                    f"- Khi đã hoàn tất các thay đổi cần thiết, kết thúc bằng '[ĐÃ THỐNG NHẤT - HOÀN TẤT]'.\n"
                )

            cmd = build_fallback_cli_cmd(agent_prompt)
            turn_data = {
                'round': curr_round_num,
                'speaker': current_role,
                'label': curr_info['label'],
                'sub': curr_info['sub'],
                'prompt_sent': converted_prompt if round_idx == 1 else f"{converted_prompt} (Lượt {curr_round_num})",
                'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
                'elapsed_sec': 0,
                'step_logs': [],
                'changed_files': [],
                'content': '',
                'is_streaming': True,
                'engine': target_engine,
                'engine_label': target_engine_label,
                'model': target_model,
                'effort': target_effort
            }
            with state_lock:
                for prev_t in task_state.get('session', {}).get('turns', []):
                    prev_t['is_streaming'] = False
                if task_state.get('session'):
                    task_state['session']['turns'].append(turn_data)
                save_queue_state_unlocked()

            response_text, elapsed = stream_process_turn(
                cmd, curr_info['workspace'], turn_data, timeout=300, task_state=task_state, repo_label=curr_info['repo_label']
            )
            history.append(turn_data)

            if any(sig in response_text for sig in ['[ĐÃ THỐNG NHẤT - HOÀN TẤT]', '[THỐNG NHẤT: HOÀN TẤT]']) and round_idx >= 2:
                is_consensus_reached = True
                break

            current_role = other_role

    total_time = round(time.time() - start_time, 1)
    all_changes = []
    seen_change_keys = set()
    for h in history:
        for ch in h.get('changed_files', []):
            k = f"{ch.get('repo')}:{ch.get('path')}"
            if k not in seen_change_keys:
                seen_change_keys.add(k)
                all_changes.append(ch)

    with state_lock:
        was_stopped = (task_state.get('session', {}).get('status') == 'STOPPED')
        task_state['is_running'] = False
        task_state['queue_status'] = 'stopped' if was_stopped else 'done'
        task_state['active_speaker'] = ''
        task_state['status_text'] = 'Đã dừng tác vụ.' if was_stopped else 'Đã hoàn tất task!'
        if task_state.get('session'):
            if not was_stopped:
                task_state['session']['status'] = 'COMPLETED'
            task_state['session']['consensus_reached'] = is_consensus_reached
            task_state['session']['total_duration_sec'] = total_time
            task_state['session']['changed_files'] = all_changes
            for trn in task_state['session'].get('turns', []):
                trn['is_streaming'] = False

        for q_item in app_state.get('task_queue', []):
            if q_item.get('id') == task_id:
                q_item['status'] = 'stopped' if was_stopped else 'done'
                q_item['isRunning'] = False

        app_state['is_running'] = any(t.get('is_running') for t in app_state['active_tasks'].values())
        save_queue_state_unlocked()

    messages = load_messages()
    messages.append({
        'id': session_id,
        'task_id': task_id,
        'type': 'TASK',
        'title': task_state.get('title') or f"Làm task: {prompt[:100]}",
        'status': 'STOPPED' if was_stopped else 'COMPLETED',
        'target': target,
        'created_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y'),
        'prompt': prompt,
        'converted_prompt': converted_prompt,
        'module': skill,
        'consensus_reached': is_consensus_reached,
        'total_duration_sec': total_time,
        'duration_sec': total_time,
        'total_turns': len(history),
        'changed_files': all_changes,
        'turns': history
    })
    save_messages(messages)

    if not was_stopped:
        try:
            from studio.telegram_bot import notify_task_completed
            threading.Thread(
                target=notify_task_completed,
                kwargs={
                    'task_id': task_id,
                    'title': task_state.get('title') or f"Làm task: {prompt[:100]}",
                    'task_type': 'TASK',
                    'duration': total_time,
                    'changed_files': all_changes
                },
                daemon=True
            ).start()
        except Exception:
            pass


# -------------------------------------------------------------
# WORKER: FIX BUG (SURGICAL DEBUG & FIX PROTOCOL)
# -------------------------------------------------------------
def run_fixbug_worker(task_id: str, skill, scope: str, description: str, error_log: str, original_prompt: str = ''):
    global app_state

    agy_bin = get_agy_bin()
    session_id = f"fix_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time = time.time()

    if isinstance(skill, list):
        skill_list = [str(s).strip() for s in skill if str(s).strip()]
    elif isinstance(skill, str):
        skill_list = [s.strip() for s in skill.split(',') if s.strip()]
    else:
        skill_list = []

    if not skill_list:
        skill_list = ['skill-debug-fixbug']

    formatted_skills = [s.lstrip('/') for s in skill_list if s.strip()]
    skill_clean = ', '.join(formatted_skills)
    slash_prefix = format_slash_skills_prefix(formatted_skills)
    scope = scope.lower() if scope.lower() in ('fe', 'be', 'both') else 'both'

    role_meta = {
        'fe': {
            'label': 'Frontend Debugger',
            'sub': 'webapp (React/TypeScript)',
            'repo_label': 'Frontend (easysalon-webapp)',
            'workspace': get_fe_workspace(),
            'desc': 'Frontend React Debugger tại easysalon-webapp, chuyên sâu về Formik, Yup validation, API client và state.'
        },
        'be': {
            'label': 'Backend Debugger',
            'sub': 'api (.NET/C#)',
            'repo_label': 'Backend (easysalon-api)',
            'workspace': get_be_workspace(),
            'desc': 'Backend .NET / EF Core Debugger tại easysalon-api, chuyên sâu về Controller, DTO, LINQ query, MySQL và Transaction.'
        }
    }

    max_rounds = 2 if scope == 'both' else 1
    preview_cmd = f"{slash_prefix} {description}".strip() if slash_prefix else description.strip()

    with state_lock:
        settings = app_state.get('settings', {}) if isinstance(app_state.get('settings'), dict) else load_settings()
        target_engine = str(settings.get('engine') or 'gemini_cli').strip().lower()
        target_effort = str(settings.get('effort') or 'high').strip()
        base_opencode_model = str(settings.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip()
        target_opencode_model = resolve_effective_opencode_model(base_opencode_model, target_effort)
        target_model = target_opencode_model if target_engine == 'opencode' else str(settings.get('model') or '').strip()
        target_engine_label = 'OpenCode CLI' if target_engine == 'opencode' else 'Gemini CLI'

        task_state = app_state['active_tasks'].get(task_id)
        existing_session = task_state.get('session') if task_state else None
        existing_turns = list(existing_session.get('turns', [])) if existing_session else []
        existing_changes = list(existing_session.get('changed_files', [])) if existing_session else []
        base_round = len(existing_turns)
        session_obj = {
            'id': existing_session.get('id', session_id) if existing_session else session_id,
            'task_id': task_id,
            'type': 'FIX_BUG',
            'skill': skill_clean,
            'scope': scope,
            'description': description,
            'converted_prompt': preview_cmd,
            'error_log': error_log,
            'engine': target_engine,
            'engine_label': target_engine_label,
            'model': target_model,
            'effort': target_effort,
            'total_rounds': base_round + max_rounds,
            'turns': existing_turns,
            'changed_files': existing_changes,
            'status': 'RUNNING',
            'created_at': existing_session.get('created_at', datetime.datetime.now().strftime('%H:%M:%S')) if existing_session else datetime.datetime.now().strftime('%H:%M:%S')
        }
        if not task_state:
            task_state = {
                'task_id': task_id,
                'title': f"Fix bug: {description[:35]}" if description else f"Fix bug ({skill_clean})",
                'mode': 'fixbug',
                'queue_status': 'running',
                'is_running': True,
                'engine': target_engine,
                'engine_label': target_engine_label,
                'model': target_model,
                'effort': target_effort,
                'current_process': None,
                'active_round': base_round,
                'total_rounds': base_round + max_rounds,
                'active_speaker': 'fe' if scope in ('fe', 'both') else 'be',
                'status_text': f"Đang chạy Fix Bug: {preview_cmd[:50]}...",
                'session': session_obj
            }
            app_state['active_tasks'][task_id] = task_state
        else:
            task_state['is_running'] = True
            task_state['queue_status'] = 'running'
            task_state['mode'] = 'fixbug'
            task_state['engine'] = target_engine
            task_state['engine_label'] = target_engine_label
            task_state['model'] = target_model
            task_state['effort'] = target_effort
            task_state['total_rounds'] = base_round + max_rounds
            task_state['active_round'] = base_round
            task_state['active_speaker'] = 'fe' if scope in ('fe', 'both') else 'be'
            task_state['status_text'] = f"Đang chạy Fix Bug: {preview_cmd[:50]}..."
            task_state['session'] = session_obj

        for q_item in app_state.get('task_queue', []):
            if q_item.get('id') == task_id:
                q_item['status'] = 'running'
                q_item['isRunning'] = True

        app_state['is_running'] = True
        app_state['current_session'] = task_state['session']
        app_state['status_text'] = task_state['status_text']
        save_queue_state_unlocked()

    history = list(existing_turns)
    roles_to_run = ['fe', 'be'] if scope == 'both' else [scope]

    for round_idx, r_role in enumerate(roles_to_run, start=1):
        curr_info = role_meta[r_role]
        curr_round_num = base_round + round_idx

        with state_lock:
            if not task_state['is_running']:
                break
            task_state['active_round'] = curr_round_num
            task_state['active_speaker'] = r_role
            task_state['status_text'] = f"[{curr_info['label']}] đang chẩn đoán và sửa lỗi: {preview_cmd[:45]}..."
            app_state['status_text'] = task_state['status_text']

        is_explain = is_explanation_only_request(description)
        directive = EXPLAIN_ONLY_DIRECTIVE if is_explain else CODE_ACTION_DIRECTIVE

        context_str = format_conversation_context(history) if history else ""
        orig_desc = original_prompt.strip() or ((existing_session.get('description') or '').strip() if existing_session else "")
        orig_err = (existing_session.get('error_log') or '').strip() if existing_session else ""

        prompt_parts = []
        if slash_prefix:
            prompt_parts.append(slash_prefix)

        if orig_desc and orig_desc != description.strip():
            prompt_parts.append(f"[MỤC TIÊU BAN ĐẦU CỦA BUG]:\n{orig_desc}")

        if context_str:
            prompt_parts.append(context_str)

        if description.strip():
            prompt_parts.append(f"[MÔ TẢ LỖI / YÊU CẦU CẦN XỬ LÝ]:\n{description.strip()}")

        active_err = error_log.strip() or orig_err
        if active_err:
            prompt_parts.append(f"[LOG LỖI / STACK TRACE / CONSOLE]:\n{active_err}")

        prompt_parts.append(directive)
        prompt_body = "\n\n".join(prompt_parts)

        cmd = build_fallback_cli_cmd(prompt_body)
        turn_data = {
            'round': curr_round_num,
            'speaker': r_role,
            'label': curr_info['label'],
            'sub': curr_info['sub'],
            'prompt_sent': prompt_body,
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
            'elapsed_sec': 0,
            'step_logs': [],
            'changed_files': [],
            'content': '',
            'is_streaming': True,
            'engine': target_engine,
            'engine_label': target_engine_label,
            'model': target_model,
            'effort': target_effort
        }
        with state_lock:
            for prev_t in task_state.get('session', {}).get('turns', []):
                prev_t['is_streaming'] = False
            if task_state.get('session'):
                task_state['session']['turns'].append(turn_data)
            save_queue_state_unlocked()

        response_text, elapsed = stream_process_turn(
            cmd, curr_info['workspace'], turn_data, timeout=360, task_state=task_state, repo_label=curr_info['repo_label']
        )
        history.append(turn_data)

    total_time = round(time.time() - start_time, 1)
    all_changes = []
    seen_change_keys = set()
    for h in history:
        for ch in h.get('changed_files', []):
            k = f"{ch.get('repo')}:{ch.get('path')}"
            if k not in seen_change_keys:
                seen_change_keys.add(k)
                all_changes.append(ch)

    with state_lock:
        was_stopped = (task_state.get('session', {}).get('status') == 'STOPPED')
        task_state['is_running'] = False
        task_state['queue_status'] = 'stopped' if was_stopped else 'done'
        task_state['active_speaker'] = ''
        task_state['status_text'] = 'Đã dừng tác vụ.' if was_stopped else 'Đã hoàn tất quy trình chẩn đoán & fix bug!'
        if task_state.get('session'):
            if not was_stopped:
                task_state['session']['status'] = 'COMPLETED'
            task_state['session']['total_duration_sec'] = total_time
            task_state['session']['changed_files'] = all_changes
            for trn in task_state['session'].get('turns', []):
                trn['is_streaming'] = False

        for q_item in app_state.get('task_queue', []):
            if q_item.get('id') == task_id:
                q_item['status'] = 'stopped' if was_stopped else 'done'
                q_item['isRunning'] = False

        app_state['is_running'] = any(t.get('is_running') for t in app_state['active_tasks'].values())
        save_queue_state_unlocked()

    messages = load_messages()
    messages.append({
        'id': session_id,
        'task_id': task_id,
        'type': 'FIX_BUG',
        'title': task_state.get('title') or f"Fix bug ({skill_clean}): {description[:90]}",
        'status': 'STOPPED' if was_stopped else 'COMPLETED',
        'target': scope,
        'module': skill_clean,
        'scope': scope,
        'created_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y'),
        'description': description,
        'converted_prompt': preview_cmd,
        'total_duration_sec': total_time,
        'duration_sec': total_time,
        'changed_files': all_changes,
        'turns': history
    })
    save_messages(messages)

    if not was_stopped:
        try:
            from studio.telegram_bot import notify_task_completed
            threading.Thread(
                target=notify_task_completed,
                kwargs={
                    'task_id': task_id,
                    'title': task_state.get('title') or f"Fix bug ({skill_clean}): {description[:90]}",
                    'task_type': 'FIX_BUG',
                    'duration': total_time,
                    'changed_files': all_changes
                },
                daemon=True
            ).start()
        except Exception:
            pass


# -------------------------------------------------------------
# SEQUENTIAL QUEUE WORKER (FIFO QUEUE MANAGER)
# -------------------------------------------------------------
queue_cond = threading.Condition()


def enqueue_task_item(item_dict: dict) -> dict:
    """Đưa tác vụ vào hàng đợi (Queue) và đánh thức worker xử lý tuần tự."""
    task_id = item_dict['id']
    mode = item_dict.get('mode', 'task')
    default_title = 'Refactor code' if mode == 'refactor' else ('Fix bug' if mode == 'fixbug' else 'Làm task')
    title = item_dict.get('title') or default_title
    prompt = item_dict.get('prompt', '')
    skills = item_dict.get('skills', [])
    skill_str = ', '.join(skills) if isinstance(skills, list) else str(skills or '')
    slash_prefix = format_slash_skills_prefix(skills)
    raw_text = prompt if mode in ('task', 'refactor') else item_dict.get('fix_desc', '')

    # Chuẩn hóa tiền tố mở đầu theo loại tác vụ: Làm task / Fix bug / Refactor code
    action_phrase = 'Refactor code:' if mode == 'refactor' else ('Fix bug:' if mode == 'fixbug' else 'Làm task:')
    prefix_clean = re.sub(r'^(?:làm\s*task|thực\s*hiện\s*task|fix\s*bug|sửa\s*lỗi|refactor\s*code|tái\s*cấu\s*trúc(?:\s*mã\s*nguồn)?)(?:\s*[:\-]\s*|\s+)', '', raw_text.strip(), flags=re.IGNORECASE) if raw_text else ''
    clean_text = f"{action_phrase} {prefix_clean}".strip() if prefix_clean else raw_text.strip()
    converted_prompt = f"{slash_prefix} {clean_text}".strip() if slash_prefix else clean_text

    with state_lock:
        any_running = any(t.get('is_running') for t in app_state['active_tasks'].values())
        queue_pos = sum(1 for q in app_state.get('task_queue', []) if q.get('status') in ('queued', 'running')) + 1
        initial_status = 'queued' if any_running else 'running'

        q_entry = None
        for q in app_state['task_queue']:
            if q.get('id') == task_id:
                q.update(item_dict)
                q['status'] = 'queued'
                q['isRunning'] = False
                q['converted_prompt'] = converted_prompt
                q_entry = q
                break
        if not q_entry:
            q_entry = dict(item_dict)
            q_entry['status'] = 'queued'
            q_entry['isRunning'] = False
            q_entry['converted_prompt'] = converted_prompt
            app_state['task_queue'].append(q_entry)

        existing_task = app_state['active_tasks'].get(task_id)
        existing_session = existing_task.get('session') if existing_task else None
        existing_turns = list(existing_session.get('turns', [])) if existing_session else []
        existing_changes = list(existing_session.get('changed_files', [])) if existing_session else []

        settings = app_state.get('settings', {}) if isinstance(app_state.get('settings'), dict) else load_settings()
        target_engine = str(item_dict.get('engine') or settings.get('engine') or 'gemini_cli').strip().lower()
        target_effort = str(item_dict.get('effort') or settings.get('effort') or 'high').strip()
        base_opencode_model = str(settings.get('opencode_model') or '9router/ag/gemini-3.8-flash').strip()
        target_opencode_model = resolve_effective_opencode_model(base_opencode_model, target_effort)
        target_model = target_opencode_model if target_engine == 'opencode' else str(settings.get('model') or '').strip()
        target_engine_label = 'OpenCode CLI' if target_engine == 'opencode' else 'Gemini CLI'

        session_obj = {
            'id': existing_session.get('id', f"queued_{task_id}") if existing_session else f"queued_{task_id}",
            'task_id': task_id,
            'type': 'REFACTOR' if mode == 'refactor' else ('FIX_BUG' if mode == 'fixbug' else 'TASK'),
            'target': item_dict.get('target', 'both') if mode in ('task', 'refactor') else item_dict.get('scope', 'both'),
            'prompt': prompt,
            'description': item_dict.get('fix_desc', ''),
            'converted_prompt': converted_prompt,
            'skill': skill_str,
            'engine': target_engine,
            'engine_label': target_engine_label,
            'model': target_model,
            'effort': target_effort,
            'turns': existing_turns,
            'changed_files': existing_changes,
            'status': 'QUEUED',
            'created_at': existing_session.get('created_at', datetime.datetime.now().strftime('%H:%M:%S')) if existing_session else datetime.datetime.now().strftime('%H:%M:%S')
        }
        app_state['active_tasks'][task_id] = {
            'task_id': task_id,
            'title': title,
            'mode': mode,
            'engine': target_engine,
            'engine_label': target_engine_label,
            'model': target_model,
            'effort': target_effort,
            'queue_status': 'queued',
            'is_running': False,
            'current_process': None,
            'active_round': len(existing_turns),
            'total_rounds': len(existing_turns) + 1,
            'active_speaker': '',
            'status_text': f"Đang chờ trong hàng đợi (Vị trí #{queue_pos})..." if any_running else "Đang chuẩn bị khởi chạy từ hàng đợi...",
            'session': session_obj
        }
        save_queue_state_unlocked()

    with queue_cond:
        queue_cond.notify_all()

    return {
        'task_id': task_id,
        'queue_status': initial_status,
        'queue_position': queue_pos,
        'converted_prompt': converted_prompt
    }


def queue_worker_loop():
    """Background daemon tuần tự lấy từng tác vụ 'queued' trong hàng đợi ra chạy."""
    while True:
        next_item = None
        with state_lock:
            any_running = any(t.get('is_running') for t in app_state['active_tasks'].values())
            if not any_running:
                for q in app_state.get('task_queue', []):
                    if q.get('status') == 'queued':
                        next_item = dict(q)
                        q['status'] = 'running'
                        q['isRunning'] = True
                        save_queue_state_unlocked()
                        break

        if next_item:
            tid = next_item['id']
            mode = next_item.get('mode', 'task')
            skills = next_item.get('skills', [])
            skill_str = ', '.join(skills) if isinstance(skills, list) else str(skills or '')
            try:
                orig_p = (next_item.get('original_prompt') or '').strip()
                if mode in ('task', 'refactor'):
                    prompt = (next_item.get('prompt') or '').strip()
                    err = (next_item.get('error_log') or '').strip()
                    full_prompt = prompt
                    if err:
                        full_prompt = f"{prompt}\n\n[Mã lỗi / Console log / Exception đính kèm]:\n```\n{err}\n```" if prompt else f"[Mã lỗi / Console log / Exception cần xử lý]:\n```\n{err}\n```"
                    run_task_worker(
                        tid,
                        full_prompt,
                        next_item.get('target', 'both'),
                        next_item.get('starter', 'fe'),
                        next_item.get('rounds', 4),
                        skill_str,
                        original_prompt=orig_p
                    )
                else:
                    run_fixbug_worker(
                        tid,
                        skill_str,
                        next_item.get('scope', 'both'),
                        (next_item.get('fix_desc') or '').strip(),
                        (next_item.get('fix_err') or '').strip(),
                        original_prompt=orig_p
                    )
            except Exception as e:
                print(f"[Queue Worker] Error executing task {tid}: {e}")
                with state_lock:
                    for q in app_state.get('task_queue', []):
                        if q.get('id') == tid:
                            q['status'] = 'stopped'
                            q['isRunning'] = False
                    if tid in app_state['active_tasks']:
                        app_state['active_tasks'][tid]['is_running'] = False
                        app_state['active_tasks'][tid]['queue_status'] = 'stopped'
                    save_queue_state_unlocked()
            continue

        with queue_cond:
            queue_cond.wait(timeout=1.5)


def start_queue_worker():
    if not app_state.get('queue_worker_started'):
        app_state['queue_worker_started'] = True
        t = threading.Thread(target=queue_worker_loop, daemon=True)
        t.start()

