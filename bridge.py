#!/usr/bin/env python3
"""
EasySalon FE <-> BE Agent Bridge
Công cụ cầu nối giao tiếp song phương giữa 2 phiên chat Gemini CLI:
- Terminal Frontend (easysalon-webapp)
- Terminal Backend (easysalon-api)
"""

import argparse
import datetime
import fcntl
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time
import unicodedata
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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


MESSAGES_FILE = _resolve_storage_file('messages.json')
ACTIVE_DIALOGUE_FILE = _resolve_storage_file('active_dialogue.json')
DAEMON_PID_FILE = os.path.join(BASE_DIR, '.daemon.pid')

from config import (
    FE_WORKSPACE,
    BE_WORKSPACE,
    get_fe_workspace,
    get_be_workspace,
    get_workspace,
    WEB_PORT,
    WEB_HOST,
    get_agy_bin,
)

ANSI_RE = re.compile(r'\033\[[0-9;]*[a-zA-Z]')


def get_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def safe_parse_content(content_str):
    if not isinstance(content_str, str):
        return content_str
    try:
        return json.loads(content_str)
    except Exception:
        return content_str


def load_messages() -> list:
    if not os.path.exists(MESSAGES_FILE):
        return []
    with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
        except Exception:
            return []
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def save_messages(messages: list) -> None:
    temp_file = MESSAGES_FILE + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    os.replace(temp_file, MESSAGES_FILE)


def load_active_dialogue() -> dict:
    if os.path.exists(ACTIVE_DIALOGUE_FILE):
        try:
            with open(ACTIVE_DIALOGUE_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except Exception:
            pass

    messages = load_messages()
    if messages:
        last = messages[-1]
        result_body = last.get('result') or ''
        if not result_body and last.get('reply'):
            reply_obj = last.get('reply')
            result_body = reply_obj.get('content') if isinstance(reply_obj, dict) else reply_obj

        created_str = last.get('created_at', '')
        time_display = created_str
        if 'T' in created_str:
            try:
                dt = datetime.datetime.fromisoformat(created_str)
                time_display = dt.strftime('%H:%M:%S')
            except Exception:
                pass

        return {
            'id': last.get('id', ''),
            'from': last.get('from', 'fe'),
            'to': last.get('to', 'be'),
            'prompt': last.get('prompt') or last.get('content') or '',
            'prompt_time': time_display,
            'status': last.get('status', 'COMPLETED'),
            'result': result_body,
            'reply_time': '',
            'task': last.get('task', ''),
            'updated_at': time.time()
        }
    return {}


def save_active_dialogue(dialogue: dict) -> None:
    temp_file = ACTIVE_DIALOGUE_FILE + '.tmp'
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(dialogue, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, ACTIVE_DIALOGUE_FILE)
    except Exception:
        pass


def char_width(c: str) -> int:
    if unicodedata.combining(c):
        return 0
    w = unicodedata.east_asian_width(c)
    if w in ('F', 'W'):
        return 2
    cp = ord(c)
    if (0x1F300 <= cp <= 0x1F9FF) or (0x2600 <= cp <= 0x27BF) or (0x2B00 <= cp <= 0x2BFF):
        return 2
    return 1


def str_visual_width(s: str) -> int:
    s_clean = ANSI_RE.sub('', s)
    return sum(char_width(c) for c in s_clean)


def wrap_line(text: str, max_w: int) -> list:
    words = text.split(' ')
    lines = []
    cur = ''
    for w in words:
        cand = (cur + ' ' + w) if cur else w
        if str_visual_width(cand) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            while str_visual_width(w) > max_w:
                part = ''
                for c in w:
                    if str_visual_width(part + c) <= max_w:
                        part += c
                    else:
                        break
                lines.append(part)
                w = w[len(part):]
            cur = w
    if cur:
        lines.append(cur)
    return lines or ['']


def format_speech_bubble(role: str, avatar: str, title: str, body: str, timestamp: str, color_code: str, cols: int = 80, max_body_lines: int = 15) -> str:
    box_w = min(max(cols - 4, 46), 120)
    inner_w = box_w - 4

    left_tag = f" {avatar} {role} "
    right_tag = f" [{timestamp}] " if timestamp else ""
    dash_len = box_w - 2 - str_visual_width(left_tag) - str_visual_width(right_tag)
    if dash_len < 2:
        dash_len = 2
        box_w = str_visual_width(left_tag) + str_visual_width(right_tag) + 4
        inner_w = box_w - 4

    top_border = f"╭─{left_tag}" + ("─" * dash_len) + f"{right_tag}─╮"
    bot_border = "╰" + ("─" * (box_w - 2)) + "╯"

    raw_lines = str(body).strip().splitlines()
    body_wrapped = []
    for rl in raw_lines:
        if not rl.strip():
            body_wrapped.append("")
        else:
            body_wrapped.extend(wrap_line(rl, inner_w))

    if max_body_lines is not None and len(body_wrapped) > max_body_lines:
        rem = len(body_wrapped) - max_body_lines
        body_wrapped = body_wrapped[:max_body_lines]
        body_wrapped.append(f"... (còn {rem} dòng, xem chi tiết đầy đủ tại bên gọi) ...")

    content_lines = []
    if title:
        content_lines.append(f"\033[1m{title}\033[0m")
        content_lines.append("")
    content_lines.extend(body_wrapped)

    out = [f"\033[1;{color_code}m{top_border}\033[0m"]
    for line in content_lines:
        cw = str_visual_width(line)
        pad = " " * max(0, inner_w - cw)
        out.append(f"\033[1;{color_code}m│\033[0m {line}{pad} \033[1;{color_code}m│\033[0m")
    out.append(f"\033[1;{color_code}m{bot_border}\033[0m")

    return "\n".join(out)


def render_dialogue(msg: dict, cols: int = 80) -> str:
    from_role = msg.get('from', 'fe').lower()

    if from_role == 'fe':
        sender_label = 'FRONTEND AGENT (webapp)'
        sender_avatar = '👨‍💻'
        receiver_label = 'BACKEND AGENT (api)'
        receiver_avatar = '🤖'
    else:
        sender_label = 'BACKEND AGENT (api)'
        sender_avatar = '🤖'
        receiver_label = 'FRONTEND AGENT (webapp)'
        receiver_avatar = '👨‍💻'

    prompt_body = msg.get('prompt') or msg.get('content') or ''
    if not isinstance(prompt_body, str):
        prompt_body = json.dumps(prompt_body, ensure_ascii=False, indent=2)

    prompt_time = msg.get('prompt_time') or msg.get('created_at', '')
    if 'T' in str(prompt_time):
        try:
            dt = datetime.datetime.fromisoformat(prompt_time)
            prompt_time = dt.strftime('%H:%M:%S')
        except Exception:
            pass

    b1 = format_speech_bubble(
        role=sender_label,
        avatar=sender_avatar,
        title="YÊU CẦU NGHIỆP VỤ",
        body=prompt_body,
        timestamp=str(prompt_time),
        color_code='36',
        cols=cols,
        max_body_lines=12
    )

    connector = "      \033[1;33m│\033[0m\n      \033[1;33m▼\033[0m"

    status = msg.get('status', 'RUNNING')
    if status in ('PENDING', 'RUNNING'):
        b2 = format_speech_bubble(
            role=receiver_label,
            avatar=receiver_avatar,
            title="TIẾN TRÌNH",
            body="⏳ Đang phân tích codebase và thực thi...",
            timestamp="ĐANG XỬ LÝ",
            color_code='33',
            cols=cols,
            max_body_lines=8
        )
    else:
        reply_body = msg.get('result') or msg.get('reply') or 'Đã hoàn tất.'
        if isinstance(reply_body, dict) and 'content' in reply_body:
            reply_body = reply_body['content']
        if not isinstance(reply_body, str):
            reply_body = json.dumps(reply_body, ensure_ascii=False, indent=2)

        reply_time = msg.get('reply_time') or ''
        if not reply_time and msg.get('reply') and isinstance(msg['reply'], dict):
            r_at = msg['reply'].get('replied_at', '')
            if 'T' in r_at:
                try:
                    dt = datetime.datetime.fromisoformat(r_at)
                    reply_time = dt.strftime('%H:%M:%S')
                except Exception:
                    pass

        b2 = format_speech_bubble(
            role=receiver_label,
            avatar=receiver_avatar,
            title="KẾT LUẬN & DỮ LIỆU",
            body=reply_body,
            timestamp=str(reply_time) or "HOÀN TẤT",
            color_code='32',
            cols=cols,
            max_body_lines=16
        )

    return f"\n{b1}\n{connector}\n{b2}\n"


def format_chat_card(sender: str, receiver: str, title: str, body: str, color_code: str = '35', max_lines: int = 15) -> str:
    avatar = '👨‍💻' if sender.lower() == 'fe' else '🤖'
    role = f"{sender.upper()} ➔ {receiver.upper()}"
    now_time = datetime.datetime.now().strftime('%H:%M:%S')
    return "\n" + format_speech_bubble(role, avatar, title, body, now_time, color_code, cols=80, max_body_lines=max_lines) + "\n"


def get_tty_size(tty_path: str) -> tuple:
    try:
        fd = os.open(tty_path, os.O_RDONLY | os.O_NOCTTY)
        try:
            res = fcntl.ioctl(fd, termios.TIOCGWINSZ, b'\0' * 8)
            return struct.unpack('HHHH', res)[:2]
        finally:
            os.close(fd)
    except Exception:
        return (0, 0)


def write_tty(tty_path: str, text: str) -> bool:
    # Disabled: writing raw bytes into active external TTYs corrupts readline,
    # breaks Ink TUI in Gemini CLI / agy, and causes terminal screens to jump and flicker violently.
    return False


def find_target_ttys(target_dir: str) -> list:
    return []


def broadcast_to_ttys(ttys: list, text: str) -> None:
    pass


def broadcast_dialogue(target_dir: str, dialogue: dict) -> None:
    # Disabled to prevent terminal screen jitter and cursor displacement
    pass


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def get_daemon_pid() -> int:
    if os.path.exists(DAEMON_PID_FILE):
        try:
            with open(DAEMON_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
                if is_pid_alive(pid):
                    return pid
        except Exception:
            pass
    return 0


def ensure_daemon():
    # Daemon auto-start disabled to prevent background terminal pollution
    return 0


def run_daemon():
    # Background daemon disabled
    return

    def cleanup(signum=None, frame=None):
        if os.path.exists(DAEMON_PID_FILE):
            try:
                os.remove(DAEMON_PID_FILE)
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    tty_tracking = {}

    while True:
        try:
            current_ttys = set(find_target_ttys(get_be_workspace()) + find_target_ttys(get_fe_workspace()))

            for tty in list(tty_tracking.keys()):
                if tty not in current_ttys:
                    del tty_tracking[tty]

            dialogue = load_active_dialogue()
            if not dialogue:
                time.sleep(0.2)
                continue

            dialogue_key = f"{dialogue.get('id')}:{dialogue.get('status')}:{dialogue.get('updated_at')}"
            now = time.time()

            for tty in current_ttys:
                rows, cols = get_tty_size(tty)
                if rows == 0 or cols == 0:
                    continue

                if tty not in tty_tracking:
                    rendered = render_dialogue(dialogue, cols=cols)
                    write_tty(tty, rendered)
                    tty_tracking[tty] = {
                        'rows': rows,
                        'cols': cols,
                        'last_seen': (rows, cols),
                        'debounce_until': 0,
                        'rendered_key': dialogue_key
                    }
                    continue

                info = tty_tracking[tty]

                if info['rendered_key'] != dialogue_key:
                    rendered = render_dialogue(dialogue, cols=cols)
                    write_tty(tty, rendered)
                    info['rendered_key'] = dialogue_key
                    info['rows'] = rows
                    info['cols'] = cols
                    info['last_seen'] = (rows, cols)
                    info['debounce_until'] = 0
                    continue

                last_seen = info.get('last_seen', (info['rows'], info['cols']))
                if (rows, cols) != last_seen:
                    info['last_seen'] = (rows, cols)
                    info['debounce_until'] = now + 0.15
                elif info['debounce_until'] != 0 and now >= info['debounce_until']:
                    if (rows, cols) != (info['rows'], info['cols']):
                        rendered = render_dialogue(dialogue, cols=cols)
                        write_tty(tty, rendered)
                        info['rows'] = rows
                        info['cols'] = cols
                    info['debounce_until'] = 0

            time.sleep(0.08)

        except Exception:
            time.sleep(0.2)


def check_loop_guard(messages: list, from_role: str, target_role: str, window_seconds: int = 120, max_calls: int = 5) -> bool:
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_calls = 0
    for m in reversed(messages):
        created_str = m.get('created_at')
        if not created_str:
            continue
        try:
            created_dt = datetime.datetime.fromisoformat(created_str)
            if (now - created_dt).total_seconds() <= window_seconds:
                if m.get('from') == from_role and m.get('to') == target_role:
                    recent_calls += 1
            else:
                break
        except Exception:
            continue
    return recent_calls >= max_calls


def is_folder_open_in_vscode(folder_path: str) -> bool:
    try:
        res = subprocess.run(['code', '--status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if res.returncode == 0:
            folder_name = os.path.basename(folder_path.rstrip('/'))
            return folder_name in res.stdout
    except Exception:
        pass
    return False


def cmd_send(args):
    messages = load_messages()
    msg_id = f"msg_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    now_time = datetime.datetime.now().strftime('%H:%M:%S')

    new_msg = {
        'id': msg_id,
        'from': args.sender,
        'to': args.receiver,
        'topic': args.topic or 'GENERAL',
        'task': args.task or '',
        'status': 'PENDING',
        'created_at': get_timestamp(),
        'content': safe_parse_content(args.content),
        'reply': None
    }

    messages.append(new_msg)
    save_messages(messages)

    target_dir = get_workspace(args.receiver)
    active_dialogue = {
        'id': msg_id,
        'from': args.sender,
        'to': args.receiver,
        'task': args.task or '',
        'prompt': args.content,
        'prompt_time': now_time,
        'status': 'PENDING',
        'result': None,
        'reply_time': None,
        'updated_at': time.time()
    }
    save_active_dialogue(active_dialogue)
    ensure_daemon()
    broadcast_dialogue(target_dir, active_dialogue)

    res = {
        'success': True,
        'msg_id': msg_id,
        'status': 'PENDING',
        'from': args.sender,
        'to': args.receiver,
        'topic': new_msg['topic'],
        'task': new_msg['task'],
        'created_at': new_msg['created_at'],
        'message': f"Message sent from {args.sender.upper()} to {args.receiver.upper()} successfully."
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_read(args):
    messages = load_messages()
    target_role = args.role.lower()

    incoming = []
    replies_for_me = []

    for m in messages:
        if args.topic and m.get('topic') != args.topic:
            continue
        if args.task and m.get('task') != args.task:
            continue

        if m.get('to', '').lower() == target_role:
            if args.unread_only and m.get('status') != 'PENDING':
                continue
            incoming.append(m)

        elif m.get('from', '').lower() == target_role and m.get('status') == 'REPLIED' and m.get('reply') is not None:
            replies_for_me.append(m)

    res = {
        'success': True,
        'role': target_role,
        'unread_only': args.unread_only,
        'incoming_count': len(incoming),
        'replies_count': len(replies_for_me),
        'incoming': incoming,
        'replies': replies_for_me
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_reply(args):
    messages = load_messages()
    target_id = args.msg_id
    now_time = datetime.datetime.now().strftime('%H:%M:%S')

    found = False
    updated_msg = None
    for m in messages:
        if m.get('id') == target_id:
            m['status'] = 'REPLIED'
            m['reply'] = {
                'from': args.sender,
                'replied_at': get_timestamp(),
                'content': safe_parse_content(args.content)
            }
            found = True
            updated_msg = m
            break

    if not found:
        res = {
            'success': False,
            'error': 'NOT_FOUND',
            'message': f"Message with ID '{target_id}' not found."
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(1)

    save_messages(messages)

    receiver = updated_msg.get('from', 'fe')
    target_dir = get_workspace(receiver)

    active_dialogue = load_active_dialogue()
    active_dialogue['status'] = 'REPLIED'
    active_dialogue['result'] = args.content
    active_dialogue['reply_time'] = now_time
    active_dialogue['updated_at'] = time.time()
    save_active_dialogue(active_dialogue)

    ensure_daemon()
    broadcast_dialogue(target_dir, active_dialogue)

    res = {
        'success': True,
        'msg_id': target_id,
        'status': 'REPLIED',
        'from': args.sender,
        'reply': updated_msg['reply'],
        'message': f"Reply sent successfully for message '{target_id}'."
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_wait(args):
    target_id = args.msg_id
    timeout = args.timeout
    interval = args.interval

    start_time = time.time()
    while time.time() - start_time < timeout:
        messages = load_messages()
        for m in messages:
            if m.get('id') == target_id:
                if m.get('status') == 'REPLIED' and m.get('reply') is not None:
                    res = {
                        'success': True,
                        'status': 'REPLIED',
                        'msg_id': target_id,
                        'wait_duration_sec': round(time.time() - start_time, 2),
                        'reply': m['reply'],
                        'original_message': m
                    }
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                    sys.exit(0)
        time.sleep(interval)

    res = {
        'success': False,
        'error': 'TIMEOUT',
        'msg_id': target_id,
        'timeout_sec': timeout,
        'message': f"Timed out after {timeout} seconds waiting for reply to message '{target_id}'."
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(1)


def cmd_history(args):
    messages = load_messages()
    if args.task:
        messages = [m for m in messages if m.get('task') == args.task]
    limit = args.limit
    if limit > 0:
        messages = messages[-limit:]

    res = {
        'success': True,
        'count': len(messages),
        'history': messages
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_clear(args):
    if os.path.exists(MESSAGES_FILE):
        save_messages([])
    if os.path.exists(ACTIVE_DIALOGUE_FILE):
        try:
            os.remove(ACTIVE_DIALOGUE_FILE)
        except Exception:
            pass
    res = {
        'success': True,
        'status': 'CLEARED',
        'message': 'Message mailbox and active dialogue cleared successfully.'
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_open_terminal(args):
    target = args.target.lower()
    target_dir = get_workspace(target)
    role_name = 'Backend' if target == 'be' else 'Frontend'
    agy_bin = get_agy_bin()

    ensure_daemon()

    is_open_vscode = is_folder_open_in_vscode(target_dir)

    if is_open_vscode:
        try:
            subprocess.run(['code', '--reuse-window', target_dir], timeout=5)
        except Exception:
            pass

    gnome_term = shutil.which('gnome-terminal')
    if gnome_term:
        shell_cmd = f"cd '{target_dir}' && '{agy_bin}' --dangerously-skip-permissions --mode accept-edits; exec bash"
        title = f"Gemini {role_name} - EasySalon"
        subprocess.Popen([
            gnome_term,
            f"--working-directory={target_dir}",
            f"--title={title}",
            "--",
            "bash", "-c", shell_cmd
        ])
        res = {
            'success': True,
            'target': target,
            'target_dir': target_dir,
            'is_open_in_vscode': is_open_vscode,
            'action': 'FOCUSED_VSCODE_AND_LAUNCHED_TERMINAL' if is_open_vscode else 'LAUNCHED_DESKTOP_TERMINAL',
            'message': f"Đã kích hoạt {'cửa sổ VS Code và ' if is_open_vscode else ''}terminal Gemini {role_name} chạy agy --dangerously-skip-permissions --mode accept-edits."
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        res = {
            'success': False,
            'error': 'NO_TERMINAL_EMULATOR',
            'message': 'Không tìm thấy gnome-terminal trên máy.'
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_call(args):
    target_role = args.target.lower()
    target_dir = get_workspace(target_role)
    if target_role == 'be':
        from_role = 'fe'
        expert_desc = "Backend .NET/C# Expert của EasySalon (sử dụng các skill backend)"
    else:
        from_role = 'be'
        expert_desc = "Frontend React/TypeScript/Ant Design Expert của EasySalon (sử dụng 25 skills frontend)"

    agy_bin = get_agy_bin()
    if not os.path.exists(agy_bin):
        res = {
            'success': False,
            'error': 'AGY_NOT_FOUND',
            'message': f"Cannot find agy executable at '{agy_bin}'."
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not os.path.exists(target_dir):
        res = {
            'success': False,
            'error': 'WORKSPACE_NOT_FOUND',
            'message': f"Target workspace '{target_dir}' does not exist."
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(1)

    messages = load_messages()
    if check_loop_guard(messages, from_role, target_role, window_seconds=120, max_calls=5):
        warning_msg = (
            f"PHÁT HIỆN DẤU HIỆU VÒNG LẶP: Đã có 5 lượt gọi liên tiếp giữa {from_role.upper()} và {target_role.upper()} trong 2 phút qua. "
            "Dừng tiến trình để chống vòng lặp vô tận và bảo vệ Token/Quota!"
        )
        res = {
            'success': False,
            'error': 'LOOP_DETECTED',
            'message': warning_msg
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(1)

    call_id = f"call_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time = time.time()
    now_time = datetime.datetime.now().strftime('%H:%M:%S')

    active_dialogue = {
        'id': call_id,
        'from': from_role,
        'to': target_role,
        'task': args.task or '',
        'prompt': args.prompt,
        'prompt_time': now_time,
        'status': 'RUNNING',
        'result': None,
        'reply_time': None,
        'updated_at': time.time()
    }
    save_active_dialogue(active_dialogue)

    ensure_daemon()
    broadcast_dialogue(target_dir, active_dialogue)

    system_wrapper = (
        f"Bạn là {expert_desc}. Đối tác ở terminal đối diện vừa gọi bạn qua Agent Bridge để giải quyết nghiệp vụ.\n\n"
        f"QUY TẮC PHẢN HỒI BẮT BUỘC (CHỐNG VÒNG LẶP & TIẾT KIỆM TOKEN):\n"
        f"1. CÓ KẾT LUẬN RÕ RÀNG: Mở đầu phản hồi bằng phần 'KẾT LUẬN:' (tối đa 2-3 gạch đầu dòng tóm tắt nghiệp vụ chính xác, dứt khoát).\n"
        f"2. CẤU TRÚC JSON GỌN GÀNG: Trả về block JSON chuẩn gồm endpoint, method, DTO, schema cần thiết. Tuyệt đối không giải thích dông dài ngoài lề.\n"
        f"3. DỨT ĐIỂM HOÀN TẤT (TERMINATE): Mỗi yêu cầu là 1 phiên xử lý dứt khoát. Tuyệt đối KHÔNG hỏi ngược lại những câu mở xã giao ('bạn cần gì thêm không?'). Dòng cuối cùng của phản hồi bắt buộc là: '[KẾT LUẬN: HOÀN TẤT]'.\n\n"
        f"YÊU CẦU NGHIỆP VỤ:\n{args.prompt}"
    )

    cmd = [
        agy_bin,
        '--dangerously-skip-permissions',
        '--mode', 'accept-edits',
        '-p', system_wrapper
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=args.timeout
        )

        duration = round(time.time() - start_time, 2)
        stdout_clean = proc.stdout.strip()
        stderr_clean = proc.stderr.strip()
        parsed_result = safe_parse_content(stdout_clean)

        reply_time = datetime.datetime.now().strftime('%H:%M:%S')
        result_str = stdout_clean if stdout_clean else "Đã thực hiện xong."

        active_dialogue['status'] = 'COMPLETED' if proc.returncode == 0 else 'ERROR'
        active_dialogue['result'] = result_str
        active_dialogue['reply_time'] = reply_time
        active_dialogue['updated_at'] = time.time()
        save_active_dialogue(active_dialogue)

        broadcast_dialogue(target_dir, active_dialogue)

        messages = load_messages()
        log_entry = {
            'id': call_id,
            'from': from_role,
            'to': target_role,
            'type': 'AUTONOMOUS_CALL',
            'task': args.task or '',
            'status': 'COMPLETED' if proc.returncode == 0 else 'ERROR',
            'created_at': get_timestamp(),
            'prompt': args.prompt,
            'duration_sec': duration,
            'result': parsed_result,
            'stderr': stderr_clean if proc.returncode != 0 else ''
        }
        messages.append(log_entry)
        save_messages(messages)

        res = {
            'success': proc.returncode == 0,
            'call_id': call_id,
            'target': target_role,
            'target_dir': target_dir,
            'duration_sec': duration,
            'result': parsed_result,
            'raw_output': stdout_clean if not isinstance(parsed_result, (dict, list)) else None
        }
        if proc.returncode != 0:
            res['error'] = 'SUBPROCESS_ERROR'
            res['stderr'] = stderr_clean

        print(json.dumps(res, ensure_ascii=False, indent=2))

    except subprocess.TimeoutExpired:
        active_dialogue['status'] = 'ERROR'
        active_dialogue['result'] = f"Timeout sau {args.timeout} giây không có phản hồi."
        active_dialogue['updated_at'] = time.time()
        save_active_dialogue(active_dialogue)
        broadcast_dialogue(target_dir, active_dialogue)

        res = {
            'success': False,
            'error': 'TIMEOUT',
            'message': f"Headless agy call timed out after {args.timeout} seconds."
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        active_dialogue['status'] = 'ERROR'
        active_dialogue['result'] = str(e)
        active_dialogue['updated_at'] = time.time()
        save_active_dialogue(active_dialogue)
        broadcast_dialogue(target_dir, active_dialogue)

        res = {
            'success': False,
            'error': 'EXCEPTION',
            'message': str(e)
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(1)


def cmd_show(args):
    dialogue = load_active_dialogue()
    if not dialogue:
        print("Chưa có cuộc hội thoại nào giữa Frontend và Backend.")
        return
    cols = shutil.get_terminal_size((80, 24)).columns
    print(render_dialogue(dialogue, cols=cols))


def cmd_daemon(args):
    action = args.action
    if action == 'run':
        run_daemon()
    elif action == 'start':
        pid = ensure_daemon()
        print(f"Agent Bridge Daemon started (PID: {pid}).")
    elif action == 'stop':
        pid = get_daemon_pid()
        if pid > 0:
            os.kill(pid, signal.SIGTERM)
            if os.path.exists(DAEMON_PID_FILE):
                try:
                    os.remove(DAEMON_PID_FILE)
                except Exception:
                    pass
            print(f"Agent Bridge Daemon stopped (PID: {pid}).")
        else:
            print("Agent Bridge Daemon is not running.")
    elif action == 'status':
        pid = get_daemon_pid()
        if pid > 0:
            print(f"Agent Bridge Daemon is running (PID: {pid}).")
        else:
            print("Agent Bridge Daemon is not running.")


def save_discussion_transcript(discuss_id: str, prompt: str, history: list, consensus: bool, total_time: float):
    messages = load_messages()
    record = {
        'id': discuss_id,
        'type': 'MULTI_TURN_DISCUSSION',
        'created_at': get_timestamp(),
        'prompt': prompt,
        'consensus_reached': consensus,
        'total_duration_sec': total_time,
        'total_turns': len(history),
        'turns': history
    }
    messages.append(record)
    save_messages(messages)

    summary_path = os.path.join(BASE_DIR, 'LATEST_DISCUSSION.md')
    try:
        md_lines = [
            "# 💬 Biên Bản Thảo Luận Kỹ Thuật (Frontend ↔ Backend)",
            "",
            f"- **Mã phiên:** `{discuss_id}`",
            f"- **Thời gian:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Tổng thời gian xử lý:** {total_time} giây ({len(history)} lượt trao đổi)",
            f"- **Trạng thái:** {'✅ ĐÃ ĐẠT ĐƯỢC THỐNG NHẤT' if consensus else 'ℹ ĐÃ HOÀN TẤT SỐ LƯỢT QUY ĐỊNH'}",
            "",
            "---",
            "",
            "## 📌 Yêu Cầu / Chủ Đề Từ Bạn",
            "",
            f"> {prompt}",
            "",
            "---",
            "",
            "## 🗣️ Diễn Biến Cuộc Thảo Luận",
            ""
        ]

        for turn in history:
            is_fe = turn['speaker'] == 'fe'
            label = "👨‍💻 FRONTEND AGENT (easysalon-webapp)" if is_fe else "🤖 BACKEND AGENT (easysalon-api)"
            md_lines.append(f"### [Lượt {turn['round']}] {label} - {turn['timestamp']} ({turn['elapsed_sec']}s)")
            md_lines.append("")
            md_lines.append(turn['content'])
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(md_lines))
        print(f"\n\033[1;34m📄 Toàn bộ biên bản thảo luận đã được lưu tại:\033[0m {summary_path}")
    except Exception:
        pass


def cmd_discuss(args):
    user_prompt = args.prompt.strip()
    if not user_prompt:
        print("Lỗi: Vui lòng nhập nội dung cần thảo luận qua --prompt hoặc -p.")
        sys.exit(1)

    max_rounds = max(1, args.rounds)
    starter = args.starter.lower()
    if starter not in ('fe', 'be'):
        starter = 'fe'

    agy_bin = get_agy_bin()
    if not os.path.exists(agy_bin):
        print(f"Lỗi: Không tìm thấy agy executable tại '{agy_bin}'.")
        sys.exit(1)

    fe_ws = get_fe_workspace()
    be_ws = get_be_workspace()

    if not os.path.exists(fe_ws):
        print(f"Lỗi: Không tìm thấy thư mục Frontend tại '{fe_ws}'.")
        sys.exit(1)

    if not os.path.exists(be_ws):
        print(f"Lỗi: Không tìm thấy thư mục Backend tại '{be_ws}'.")
        sys.exit(1)

    cols = shutil.get_terminal_size((80, 24)).columns
    box_cols = min(max(cols - 4, 60), 120)

    header = (
        f"\n\033[1;35m{'=' * box_cols}\033[0m\n"
        f"\033[1;35m💬 [PHIÊN THẢO LUẬN TỰ ĐỘNG GIỮA FRONTEND & BACKEND]\033[0m\n"
        f"\033[1;37m📌 YÊU CẦU / CHỦ ĐỀ:\033[0m {user_prompt}\n"
        f"\033[1;34m🔄 TỐI ĐA:\033[0m {max_rounds} lượt trao đổi | \033[1;34m🎯 BẮT ĐẦU TỪ:\033[0m {starter.upper()}\n"
        f"\033[1;35m{'=' * box_cols}\033[0m\n"
    )
    print(header)

    current_role = starter
    history = []
    discuss_id = f"disc_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_total_time = time.time()

    role_meta = {
        'fe': {
            'label': 'FRONTEND AGENT (webapp)',
            'avatar': '👨‍💻',
            'color': '36',
            'workspace': fe_ws,
            'desc': 'Frontend React / TypeScript / Ant Design Engineer tại easysalon-webapp'
        },
        'be': {
            'label': 'BACKEND AGENT (api)',
            'avatar': '🤖',
            'color': '32',
            'workspace': be_ws,
            'desc': 'Backend .NET / C# Web API Engineer tại easysalon-api'
        }
    }

    is_consensus_reached = False

    module_arg = getattr(args, 'module', '') or ''
    if module_arg.strip():
        mod_clean = module_arg.strip().replace('skill-', '')
        module_directive = (
            f"\n🎯 YÊU CẦU ĐẶC BIỆT VỀ MODULE: Phiên thảo luận này tập trung vào module '{mod_clean}'. "
            f"Bạn BẮT BUỘC phải đọc tài liệu skill nghiệp vụ tại '.agents/skills/skill-{mod_clean}/SKILL.md' (nếu có) "
            f"để áp dụng đúng kiến trúc, danh sách file, component, DTO, bảng biểu và quy chuẩn nghiệp vụ đã được định nghĩa sẵn của module này.\n"
        )
    else:
        module_directive = (
            "\n💡 TỰ ĐỘNG NẠP SKILL MODULE: Hãy chủ động rà soát thư mục '.agents/skills/' trong workspace của bạn "
            "xem có skill nào trực tiếp liên quan đến chủ đề thảo luận (ví dụ: skill-booking-bedroom, skill-commission, "
            "skill-warehouse, skill-pos-cashier, skill-customer-crm, skill-controller, skill-service, v.v.). "
            "Nếu có, hãy đọc ngay file SKILL.md đó để nắm chắc kiến trúc và quy chuẩn nghiệp vụ của module trước khi phát biểu.\n"
        )

    for round_idx in range(1, max_rounds + 1):
        other_role = 'be' if current_role == 'fe' else 'fe'
        curr_info = role_meta[current_role]
        other_info = role_meta[other_role]

        print(f"\033[1;33m⏳ [LƯỢT {round_idx}/{max_rounds}] {curr_info['avatar']} {curr_info['label']} đang phân tích codebase và chuẩn bị ý kiến...\033[0m")
        sys.stdout.flush()

        if round_idx == 1:
            agent_prompt = (
                f"Bạn là {curr_info['desc']}.\n\n"
                f"Người dùng vừa bắt đầu một phiên thảo luận kỹ thuật giữa bạn và {other_info['label']}.\n"
                f"YÊU CẦU / CHỦ ĐỀ TỪ NGƯỜI DÙNG:\n"
                f"\"\"\"\n{user_prompt}\n\"\"\"\n"
                f"{module_directive}\n"
                f"HƯỚNG DẪN DÀNH CHO LƯỢT PHÁT BIỂU ĐẦU TIÊN CỦA BẠN:\n"
                f"- Bám sát chính xác chủ đề và phong cách người dùng đã yêu cầu.\n"
                f"- Tra cứu codebase thực tế và skill module của bạn tại workspace hiện tại.\n"
                f"- Trình bày góc nhìn kỹ thuật, phân tích tình hình, đặt câu hỏi hoặc đưa ra đề xuất cụ thể gửi cho {other_info['label']}.\n"
                f"- Phản hồi tự nhiên, chuyên sâu, đi thẳng vào vấn đề."
            )
        else:
            last_turn = history[-1]
            prev_turns_summary = ""
            for h in history:
                speaker_tag = "FRONTEND" if h['speaker'] == 'fe' else "BACKEND"
                prev_turns_summary += f"--- [Lượt {h['round']} - {speaker_tag}] ---\n{h['content']}\n\n"

            agent_prompt = (
                f"Bạn là {curr_info['desc']}.\n\n"
                f"Bạn và {other_info['label']} đang thảo luận theo yêu cầu của người dùng:\n"
                f"\"\"\"\n{user_prompt}\n\"\"\"\n"
                f"{module_directive}\n"
                f"DIỄN BIẾN THẢO LUẬN TỪ ĐẦU ĐẾN NAY:\n"
                f"{prev_turns_summary.strip()}\n\n"
                f"Ý KIẾN MỚI NHẤT TỪ {other_info['label'].upper()} Ở LƯỢT TRƯỚC:\n"
                f"\"\"\"\n{last_turn['content']}\n\"\"\"\n\n"
                f"HƯỚNG DẪN DÀNH CHO LƯỢT CỦA BẠN (LƯỢT {round_idx}/{max_rounds}):\n"
                f"- Đọc codebase thực tế và skill module của bạn nếu cần đối chiếu logic, DTO, entity, form, endpoint.\n"
                f"- Phản hồi trực tiếp các ý kiến, thắc mắc hoặc đề xuất của {other_info['label']}.\n"
                f"- Tiếp tục bàn luận, làm rõ khúc mắc hoặc thống nhất giải pháp.\n"
                f"- Nếu mọi vấn đề kỹ thuật đã được giải quyết rõ ràng và hai bên đã thống nhất xong giải pháp: hãy tóm tắt kết luận cốt lõi và kết thúc bằng dòng '[ĐÃ THỐNG NHẤT - HOÀN TẤT]'. Nếu vẫn còn điểm cần làm rõ thêm, hãy tiếp tục đặt câu hỏi/đối chiếu."
            )

        cmd = [
            agy_bin,
            '--dangerously-skip-permissions',
            '--mode', 'accept-edits',
            '-p', agent_prompt
        ]

        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=curr_info['workspace'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=args.timeout
            )
            elapsed = round(time.time() - t0, 1)
            response_text = proc.stdout.strip()
            if proc.returncode != 0 and not response_text:
                response_text = f"[LỖI TIẾN TRÌNH {proc.returncode}]: {proc.stderr.strip()}"
        except subprocess.TimeoutExpired:
            response_text = f"[HẾT GIỜ]: Agent không phản hồi sau {args.timeout} giây."
            elapsed = args.timeout
        except Exception as e:
            response_text = f"[LỖI]: {str(e)}"
            elapsed = 0

        now_time = datetime.datetime.now().strftime('%H:%M:%S')
        speech_bubble = format_speech_bubble(
            role=f"{curr_info['label']} - LƯỢT {round_idx}/{max_rounds}",
            avatar=curr_info['avatar'],
            title="",
            body=response_text,
            timestamp=f"{now_time} ({elapsed}s)",
            color_code=curr_info['color'],
            cols=box_cols,
            max_body_lines=None
        )
        print("\n" + speech_bubble + "\n")
        sys.stdout.flush()

        history.append({
            'round': round_idx,
            'speaker': current_role,
            'timestamp': now_time,
            'elapsed_sec': elapsed,
            'content': response_text
        })

        stop_signals = ['[ĐÃ THỐNG NHẤT - HOÀN TẤT]', '[THỐNG NHẤT: HOÀN TẤT]', '[KẾT LUẬN: HOÀN TẤT]']
        if any(sig in response_text for sig in stop_signals) and round_idx >= 2:
            is_consensus_reached = True
            break

        current_role = other_role

    total_time = round(time.time() - start_total_time, 1)

    conclusion_box = (
        f"\033[1;32m{'=' * box_cols}\033[0m\n"
        f"\033[1;32m🎉 [KẾT THÚC PHIÊN THẢO LUẬN] (Tổng thời gian: {total_time}s | {len(history)} lượt)\033[0m\n"
        f"{'✔ Hai bên đã đạt được sự thống nhất về kỹ thuật!' if is_consensus_reached else 'ℹ Đã hoàn tất số lượt trao đổi theo yêu cầu.'}\n"
        f"\033[1;32m{'=' * box_cols}\033[0m\n"
    )
    print(conclusion_box)

    save_discussion_transcript(discuss_id, user_prompt, history, is_consensus_reached, total_time)


def cmd_web(args):
    web_script = os.path.join(BASE_DIR, 'easysalon_studio.py')
    port = args.port
    host = args.host
    cmd = [sys.executable, web_script, '--port', str(port), '--host', host]
    if getattr(args, 'watch', True):
        cmd.append('--watch')
    else:
        cmd.append('--no-watch')
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(
        description='EasySalon FE <-> BE Agent Bridge CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands')

    # Discuss (Autonomous multi-turn discussion driven dynamically by user prompt)
    p_discuss = subparsers.add_parser(
        'discuss',
        help='Khởi chạy phiên thảo luận tự động đa lượt giữa FE và BE dựa theo prompt của bạn'
    )
    p_discuss.add_argument(
        '-p', '--prompt', '--topic',
        dest='prompt',
        required=True,
        help='Chủ đề, câu hỏi hoặc yêu cầu nghiệp vụ bạn muốn 2 bên bàn luận'
    )
    p_discuss.add_argument(
        '--starter',
        choices=['fe', 'be'],
        default='fe',
        help='Bên nào phát biểu đầu tiên (fe hoặc be, mặc định: fe)'
    )
    p_discuss.add_argument(
        '--rounds',
        type=int,
        default=4,
        help='Số lượt trao đổi tối đa giữa 2 bên (mặc định: 4)'
    )
    p_discuss.add_argument(
        '--module', '--skill',
        dest='module',
        default='',
        help='Tên module hoặc skill nghiệp vụ cụ thể (ví dụ: booking-bedroom, commission, warehouse, customer-crm...)'
    )
    p_discuss.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Thời gian tối đa (giây) cho mỗi lượt phát biểu (mặc định: 300s)'
    )
    p_discuss.set_defaults(func=cmd_discuss)

    # Web Studio UI
    p_web = subparsers.add_parser('web', help='Mở giao diện Web UI tương tác trực quan trên trình duyệt (localhost)')
    p_web.add_argument('--port', type=int, default=WEB_PORT, help=f'Cổng port để lắng nghe (mặc định: {WEB_PORT})')
    p_web.add_argument('--host', default=WEB_HOST, help=f'Host để lắng nghe (mặc định: {WEB_HOST})')
    p_web.add_argument('-w', '--watch', dest='watch', action='store_true', default=True, help='Tự động phát hiện code mới và Hot Reload giao diện (mặc định: Bật)')
    p_web.add_argument('--no-watch', dest='watch', action='store_false', help='Tắt chế độ tự động theo dõi file (watch)')
    p_web.set_defaults(func=cmd_web)

    # Call (Autonomous Headless Trigger via agy)
    p_call = subparsers.add_parser('call', help='Directly invoke agy on the target workspace non-interactively')
    p_call.add_argument('--to', dest='target', required=True, choices=['fe', 'be'], help='Target workspace agent (be or fe)')
    p_call.add_argument('--prompt', required=True, help='Question or task prompt for the target agent')
    p_call.add_argument('--task', default='', help='Jira task ID or ticket code')
    p_call.add_argument('--timeout', type=int, default=300, help='Max timeout seconds (default 300s)')
    p_call.set_defaults(func=cmd_call)

    # Open Terminal (Interactive window: Focus VS Code or Launch Terminal)
    p_open = subparsers.add_parser('open-terminal', help='Open/focus VS Code window and launch interactive terminal running agy')
    p_open.add_argument('--target', required=True, choices=['fe', 'be'], help='Target workspace (be or fe)')
    p_open.set_defaults(func=cmd_open_terminal)

    # Send
    p_send = subparsers.add_parser('send', help='Send a message to the other agent')
    p_send.add_argument('--from', dest='sender', required=True, choices=['fe', 'be'], help='Sender role (fe or be)')
    p_send.add_argument('--to', dest='receiver', required=True, choices=['fe', 'be'], help='Receiver role (fe or be)')
    p_send.add_argument('--topic', default='GENERAL', help='Message topic (e.g. CRUD_BEDROOM, GET_DTO)')
    p_send.add_argument('--task', default='', help='Jira task ID or ticket code (e.g. EAS-12373)')
    p_send.add_argument('--content', required=True, help='Message content (JSON string or plain text)')
    p_send.set_defaults(func=cmd_send)

    # Read
    p_read = subparsers.add_parser('read', help='Read incoming messages for a role')
    p_read.add_argument('--for', dest='role', required=True, choices=['fe', 'be'], help='Role to read messages for')
    p_read.add_argument('--unread-only', action='store_true', default=False, help='Only fetch pending/unread messages')
    p_read.add_argument('--topic', default=None, help='Filter by topic')
    p_read.add_argument('--task', default=None, help='Filter by task ID')
    p_read.set_defaults(func=cmd_read)

    # Reply
    p_reply = subparsers.add_parser('reply', help='Reply to a specific message')
    p_reply.add_argument('--msg-id', required=True, help='ID of the message being replied to')
    p_reply.add_argument('--from', dest='sender', required=True, choices=['fe', 'be'], help='Replier role')
    p_reply.add_argument('--content', required=True, help='Reply payload (JSON string or plain text)')
    p_reply.set_defaults(func=cmd_reply)

    # Wait
    p_wait = subparsers.add_parser('wait', help='Wait for a reply to a message (blocking polling)')
    p_wait.add_argument('--msg-id', required=True, help='ID of the message to wait for')
    p_wait.add_argument('--timeout', type=int, default=180, help='Max seconds to wait before timeout (default 180s)')
    p_wait.add_argument('--interval', type=float, default=2.0, help='Polling interval in seconds (default 2s)')
    p_wait.set_defaults(func=cmd_wait)

    # History
    p_history = subparsers.add_parser('history', help='View message history')
    p_history.add_argument('--limit', type=int, default=20, help='Number of messages to display')
    p_history.add_argument('--task', default=None, help='Filter by task ID')
    p_history.set_defaults(func=cmd_history)

    # Clear
    p_clear = subparsers.add_parser('clear', help='Clear mailbox')
    p_clear.set_defaults(func=cmd_clear)

    # Show (Display latest dialogue)
    p_show = subparsers.add_parser('show', help='Display the active dialogue on terminal')
    p_show.set_defaults(func=cmd_show)

    # Daemon (Persistent terminal watcher)
    p_daemon = subparsers.add_parser('daemon', help='Manage background terminal watcher daemon')
    p_daemon.add_argument('action', choices=['start', 'stop', 'status', 'run'], help='Daemon action')
    p_daemon.set_defaults(func=cmd_daemon)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
