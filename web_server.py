#!/usr/bin/env python3
"""
EasySalon Multi-Agent Studio - Dual-Terminal Live Dashboard & Autonomous Hub
Giám sát thời gian thực 2 Terminal (FE & BE), điều phối Làm Task, Fix Bug và Sơ đồ kiến trúc liên kết.
"""

import atexit
from concurrent.futures import ThreadPoolExecutor
import datetime
import glob
import html
import http.server
import json
import os
import pty
import re
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(BASE_DIR, 'messages.json')

from config import (
    FE_WORKSPACE,
    BE_WORKSPACE,
    get_fe_workspace,
    get_be_workspace,
    get_workspace,
    BRAIN_DIR,
    HISTORY_FILE,
    WEB_PORT,
    WEB_HOST,
    get_agy_bin,
)

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
    'diagram_cache': None,
    'diagram_cache_key': None
}

background_terminals = {}


def cleanup_background_terminals():
    """Dọn dẹp sạch sẽ chỉ 2 terminal do chính server tạo ra khi thoát."""
    global background_terminals
    for role, info in list(background_terminals.items()):
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
    background_terminals.clear()


atexit.register(cleanup_background_terminals)


def ensure_background_terminals():
    """
    Tự động khởi tạo 2 terminal ngầm RIÊNG BIỆT của Web Studio.
    Hoàn toàn không can thiệp, không liên quan đến terminal người dùng tự mở trong dự án.
    """
    global background_terminals
    agy_bin = get_agy_bin()

    # Đọc cấu hình hiện tại để terminal ngầm chạy ĐÚNG effort/model đang chọn trên UI.
    # Nếu không truyền --effort/--model, agy sẽ dùng mặc định trong
    # ~/.gemini/antigravity-cli/settings.json (thường là High) -> lệch với UI.
    try:
        from studio.state import load_settings
        cur_settings = load_settings()
    except Exception:
        cur_settings = {}
    cur_effort = str(cur_settings.get('effort') or 'high').strip().lower()
    cur_model = str(cur_settings.get('model') or '').strip()

    base_cmd = [agy_bin, '--dangerously-skip-permissions', '--mode', 'accept-edits']
    if cur_effort:
        base_cmd += ['--effort', cur_effort]
    if cur_model:
        base_cmd += ['--model', cur_model]

    targets = [
        ('fe', get_fe_workspace(), 'Frontend (easysalon-webapp)'),
        ('be', get_be_workspace(), 'Backend (easysalon-api)')
    ]

    for role, ws, label in targets:
        # Nếu server đã có tiến trình ngầm riêng đang sống thì giữ nguyên
        existing = background_terminals.get(role)
        if existing and existing.get('proc') and existing['proc'].poll() is None:
            continue

        try:
            m_fd, s_fd = pty.openpty()
            proc = subprocess.Popen(
                base_cmd,
                cwd=ws,
                stdin=s_fd,
                stdout=s_fd,
                stderr=s_fd,
                close_fds=True
            )
            background_terminals[role] = {
                'pid': proc.pid,
                'proc': proc,
                'pty': (m_fd, s_fd),
                'workspace': ws
            }
            print(f"[STUDIO] Đã mở Terminal ngầm riêng cho {label} (PID: {proc.pid}, Effort: {cur_effort.upper() or 'DEFAULT'}, Model: {cur_model or 'DEFAULT'})")
        except Exception as e:
            print(f"[WARN] Không thể mở Terminal ngầm cho {label}: {e}")


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


def get_custom_skills():
    """Quét thư mục .agents/skills/ của cả Frontend và Backend để lấy các skill thực tế."""
    def scan_skills_dir(workspace, role):
        skills_dir = os.path.join(workspace, '.agents', 'skills')
        results = []
        if os.path.isdir(skills_dir):
            for name in sorted(os.listdir(skills_dir)):
                full_path = os.path.join(skills_dir, name)
                if os.path.isdir(full_path):
                    skill_md = os.path.join(full_path, 'SKILL.md')
                    desc = ''
                    if os.path.isfile(skill_md):
                        try:
                            with open(skill_md, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'description:' in content:
                                    part = content.split('description:', 1)[1]
                                    if part.strip().startswith('>-') or part.strip().startswith('>'):
                                        d_lines = []
                                        for line in part.splitlines()[1:]:
                                            if line.strip() == '---':
                                                break
                                            d_lines.append(line.strip())
                                        desc = ' '.join(d_lines)
                                    else:
                                        desc = part.splitlines()[0].strip()
                        except Exception:
                            pass
                    results.append({
                        'name': name,
                        'desc': desc,
                        'role': role
                    })
        return results

    fe_skills = scan_skills_dir(get_fe_workspace(), 'fe')
    be_skills = scan_skills_dir(get_be_workspace(), 'be')
    return {
        'fe': fe_skills,
        'be': be_skills
    }


def get_git_stash_list(workspace):
    """Lấy danh sách các bản git stash của workspace kèm thông tin branch tương ứng."""
    stashes = []
    try:
        res = subprocess.run(
            ['git', 'stash', 'list', '--format=%gd|%gs|%cr'],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10
        )
        if res.returncode != 0:
            return []

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split('|', 2)
            if len(parts) < 2:
                continue
            idx = parts[0].strip()
            subj = parts[1].strip()
            date = format_git_relative_date(parts[2].strip()) if len(parts) > 2 else ''

            # Phân tích branch từ subject: "WIP on <branch>: ..." hoặc "On <branch>: ..."
            m = re.match(r'^(?:WIP on|On)\s+([^:]+):(?:\s*(.*))?$', subj)
            if m:
                b_name = m.group(1).strip()
                msg = (m.group(2) or '').strip()
            else:
                b_name = ''
                msg = subj

            stashes.append({
                'index': idx,
                'branch': b_name,
                'message': msg,
                'date': date,
                'raw_subject': subj
            })
    except Exception:
        pass
    return stashes


def get_git_repo_details(workspace):
    """Lấy thông tin chi tiết git: nhánh hiện tại, commit, trạng thái working directory, đồng bộ remote và danh sách nhánh."""
    try:
        curr_branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip() or 'HEAD detached'
    except Exception:
        curr_branch = 'unknown'

    try:
        commit_info = subprocess.check_output(
            ['git', 'log', '-1', '--format=%h|%s|%cr'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip().split('|')
        commit_hash = commit_info[0] if len(commit_info) > 0 else ''
        commit_msg = commit_info[1] if len(commit_info) > 1 else ''
        commit_date = commit_info[2] if len(commit_info) > 2 else ''
    except Exception:
        commit_hash, commit_msg, commit_date = '', '', ''

    try:
        status_raw = subprocess.check_output(
            ['git', 'status', '--short'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty_count = len([l for l in status_raw.splitlines() if l.strip()])
    except Exception:
        dirty_count = 0
        status_raw = ''

    # Kiểm tra upstream tracking và số commit ahead / behind (cần pull)
    upstream = ''
    behind_count = 0
    ahead_count = 0
    needs_pull = False
    try:
        upstream = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', '@{u}'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        try:
            res_ver = subprocess.run(
                ['git', 'rev-parse', '--verify', f'origin/{curr_branch}'],
                cwd=workspace, capture_output=True, text=True
            )
            if res_ver.returncode == 0:
                upstream = f'origin/{curr_branch}'
        except Exception:
            upstream = ''

    if upstream:
        try:
            counts = subprocess.check_output(
                ['git', 'rev-list', '--left-right', '--count', f'HEAD...{upstream}'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip().split()
            if len(counts) >= 2:
                ahead_count = int(counts[0])
                behind_count = int(counts[1])
                needs_pull = behind_count > 0
        except Exception:
            pass

    branches = []
    try:
        branch_lines = subprocess.check_output(
            ['git', 'branch', '--format=%(refname:short)|%(authordate:relative)|%(subject)'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip().splitlines()

        for line in branch_lines:
            if not line.strip():
                continue
            parts = line.split('|', 2)
            b_name = parts[0].strip()
            branches.append({
                'name': b_name,
                'date': parts[1] if len(parts) > 1 else '',
                'subject': parts[2] if len(parts) > 2 else '',
                'is_current': b_name == curr_branch
            })
    except Exception:
        pass

    # Lấy tên nhánh trước đó (@{-1} đến @{-5}) khác với nhánh hiện tại
    prev_branch = ''
    try:
        for i in range(1, 6):
            pb_raw = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', f'@{{-{i}}}'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if pb_raw and not pb_raw.startswith('fatal:') and pb_raw != 'HEAD' and pb_raw != curr_branch:
                prev_branch = pb_raw
                break
    except Exception:
        prev_branch = ''

    # Lấy thông tin stash và danh sách stash của nhánh hiện tại
    stash_list = get_git_stash_list(workspace)
    branch_stashes = [s for s in stash_list if s.get('branch') == curr_branch]

    return {
        'current_branch': curr_branch,
        'prev_branch': prev_branch,
        'commit_hash': commit_hash,
        'commit_message': commit_msg,
        'commit_date': commit_date,
        'dirty_count': dirty_count,
        'status_raw': status_raw,
        'upstream': upstream,
        'ahead_count': ahead_count,
        'behind_count': behind_count,
        'needs_pull': needs_pull,
        'branches': branches,
        'stash_list': stash_list,
        'branch_stashes': branch_stashes,
        'has_branch_stash': len(branch_stashes) > 0,
        'latest_branch_stash': branch_stashes[0] if branch_stashes else None
    }


def pull_git_branch(workspace):
    """Thực hiện git pull cho repository được chỉ định."""
    try:
        curr_branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip()

        res = subprocess.run(
            ['git', 'pull'],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=40
        )
        msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            return {
                'success': True,
                'branch': curr_branch,
                'message': msg or 'Already up to date.'
            }
        else:
            return {
                'success': False,
                'branch': curr_branch,
                'message': msg or 'Git pull thất bại.'
            }
    except subprocess.TimeoutExpired:
        return {'success': False, 'branch': '', 'message': 'Git pull quá thời gian quy định (timeout 40s).'}
    except Exception as e:
        return {'success': False, 'branch': '', 'message': str(e)}


def switch_git_branch(workspace, branch_name, create_new=False, base_branch='', switch_branch=True):
    """
    Chuyển nhánh git hoặc tạo nhánh mới nếu yêu cầu (git checkout hoặc git checkout -b hoặc git branch).
    Tự động hỗ trợ tracking nhánh remote nếu nhánh chưa có ở local.
    Hỗ trợ tạo nhánh mới từ nhánh gốc base_branch (git checkout -b <branch> <base_branch>).
    """
    try:
        branch_name = branch_name.strip()
        base_branch = (base_branch or '').strip()
        if not branch_name:
            return False, "Tên nhánh không được để trống."

        # Trường hợp 1: Người dùng yêu cầu tạo nhánh mới (-b)
        if create_new:
            if not switch_branch:
                cmd = ['git', 'branch', branch_name]
                if base_branch:
                    cmd.append(base_branch)
                res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=25)
                msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
                if res.returncode == 0:
                    from_info = f" từ nhánh '{base_branch}'" if base_branch else ""
                    return True, f"Đã tạo nhánh '{branch_name}'{from_info} thành công (vẫn giữ nhánh hiện tại)."
                if base_branch and ('not a valid object name' in msg or 'fatal: Cannot update paths' in msg or 'fatal: invalid reference' in msg):
                    cmd_rem = ['git', 'branch', branch_name, f'origin/{base_branch}']
                    res_rem = subprocess.run(cmd_rem, cwd=workspace, capture_output=True, text=True, timeout=25)
                    if res_rem.returncode == 0:
                        return True, f"Đã tạo nhánh '{branch_name}' từ remote 'origin/{base_branch}' thành công (vẫn giữ nhánh hiện tại)."
                if 'already exists' in msg:
                    return False, f"Nhánh '{branch_name}' đã tồn tại sẵn."
                return False, f"Không thể tạo nhánh mới '{branch_name}'. Chi tiết: {msg}"

            cmd = ['git', 'checkout', '-b', branch_name]
            if base_branch:
                cmd.append(base_branch)

            res = subprocess.run(
                cmd,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=25
            )
            msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
            if res.returncode == 0:
                from_info = f" từ nhánh '{base_branch}'" if base_branch else ""
                return True, f"Đã tạo mới và chuyển sang nhánh '{branch_name}'{from_info} thành công."

            # Nếu base_branch không tìm thấy ở local, thử với origin/<base_branch>
            if base_branch and ('not a valid object name' in msg or 'fatal: Cannot update paths' in msg or 'fatal: invalid reference' in msg):
                cmd_rem = ['git', 'checkout', '-b', branch_name, f'origin/{base_branch}']
                res_rem = subprocess.run(cmd_rem, cwd=workspace, capture_output=True, text=True, timeout=25)
                if res_rem.returncode == 0:
                    return True, f"Đã tạo mới và chuyển sang nhánh '{branch_name}' từ remote 'origin/{base_branch}' thành công."

            # Nếu nhánh đã tồn tại, thử checkout thông thường
            if 'already exists' in msg:
                res2 = subprocess.run(
                    ['git', 'checkout', branch_name],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=25
                )
                if res2.returncode == 0:
                    return True, f"Nhánh '{branch_name}' đã tồn tại sẵn. Đã chuyển nhánh thành công."

            return False, f"Không thể tạo nhánh mới '{branch_name}'. Chi tiết: {msg}"

        # Trường hợp 2: Checkout nhánh có sẵn (local hoặc '-')
        res = subprocess.run(
            ['git', 'checkout', branch_name],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=25
        )
        msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            try:
                curr = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, text=True).strip()
            except Exception:
                curr = branch_name
            if branch_name == '-':
                return True, f"Đã quay về nhánh '{curr}' thành công."
            return True, f"Đã chuyển sang nhánh '{curr or branch_name}' thành công."

        # Trường hợp 3: Thử tracking nhánh remote origin/<branch>
        if branch_name != '-':
            res_track = subprocess.run(
                ['git', 'checkout', '--track', f'origin/{branch_name}'],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=25
            )
            if res_track.returncode == 0:
                return True, f"Đã checkout và track từ remote 'origin/{branch_name}' thành công."

        return False, f"Không thể chuyển sang nhánh '{branch_name}'. Chi tiết: {msg}"
    except Exception as e:
        return False, str(e)


def rename_git_branch(workspace, new_name, old_name=''):
    """
    Đổi tên nhánh git (git branch -m [old_name] <new_name>).
    Nếu old_name rỗng hoặc 'HEAD' hoặc 'CURRENT', đổi tên nhánh hiện tại:
    git branch -m <new_name>
    Nếu old_name được cung cấp, đổi tên nhánh old_name:
    git branch -m <old_name> <new_name>
    """
    try:
        new_name = (new_name or '').strip()
        old_name = (old_name or '').strip()
        if not new_name:
            return False, "Tên nhánh mới không được để trống."

        is_from_head = not old_name or old_name.upper() in ('HEAD', 'CURRENT', 'CURRENT_BRANCH')

        curr_branch = ""
        try:
            curr_branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, text=True).strip()
        except Exception:
            pass

        target_old = curr_branch if is_from_head else old_name

        if target_old and target_old == new_name:
            return False, f"Tên nhánh mới '{new_name}' trùng với tên nhánh hiện tại."

        cmd = ['git', 'branch', '-m']
        if not is_from_head:
            cmd.append(old_name)
        cmd.append(new_name)

        res = subprocess.run(
            cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=25
        )
        msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            old_desc = f"'{target_old}'" if target_old else "nhánh hiện tại"
            return True, f"Đã đổi tên nhánh {old_desc} thành '{new_name}' thành công."

        if 'already exists' in msg:
            return False, f"Nhánh '{new_name}' đã tồn tại sẵn trong repository."
        if 'not a valid object name' in msg or 'fatal: invalid reference' in msg or 'error: refname' in msg:
            return False, f"Tên nhánh '{new_name}' không hợp lệ hoặc không tìm thấy nhánh nguồn '{target_old or old_name}'."

        return False, f"Không thể đổi tên nhánh. Chi tiết: {msg}"
    except subprocess.TimeoutExpired:
        return False, "Lệnh git branch -m quá thời gian chờ (timeout)."
    except Exception as e:
        return False, f"Lỗi hệ thống khi đổi tên nhánh: {str(e)}"


def get_git_commits(workspace, branch='HEAD', limit=300):
    """Lấy danh sách commit của một nhánh cụ thể (hỗ trợ phân trang và nhận diện tác giả)."""
    try:
        branch = (branch or 'HEAD').strip()
        limit_int = int(limit) if limit else 300
        limit_val = 500 if limit_int <= 0 else max(1, min(500, limit_int))

        current_author = ""
        try:
            current_author = subprocess.check_output(['git', 'config', 'user.name'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            pass

        cmd = ['git', 'log', f'-n{limit_val}', '--format=%H|%h|%an|%ar|%s', branch]
        res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            if not branch.startswith('origin/'):
                cmd_orig = ['git', 'log', f'-n{limit_val}', '--format=%H|%h|%an|%ar|%s', f'origin/{branch}']
                res_orig = subprocess.run(cmd_orig, cwd=workspace, capture_output=True, text=True, timeout=15)
                if res_orig.returncode == 0:
                    res = res_orig

        if res.returncode != 0:
            return {'success': False, 'message': res.stderr.strip() or 'Không thể tải danh sách commit.', 'commits': []}

        commits = []
        for line in res.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split('|', 4)
            if len(parts) >= 5:
                author_name = parts[2]
                is_me = bool(
                    current_author and (
                        current_author.lower() in author_name.lower() or
                        author_name.lower() in current_author.lower() or
                        'thiết' in author_name.lower() or
                        'thiet' in author_name.lower()
                    )
                )
                commits.append({
                    'hash': parts[0],
                    'short_hash': parts[1],
                    'author': author_name,
                    'is_me': is_me,
                    'date': parts[3],
                    'subject': parts[4]
                })
        return {'success': True, 'branch': branch, 'commits': commits, 'current_author': current_author}
    except Exception as e:
        return {'success': False, 'message': str(e), 'commits': []}


def execute_git_stash(workspace, message=""):
    """Thực hiện git stash để cất các thay đổi dở dang trước khi pull hoặc chuyển nhánh."""
    try:
        msg = (message or f"Tự động stash thay đổi dở dang trước khi pull {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}").strip()
        cmd = ['git', 'stash', 'push', '-u', '-m', msg]
        res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=30)
        output = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            return {'success': True, 'message': 'Đã git stash thành công các thay đổi dở dang.', 'output': output}
        else:
            return {'success': False, 'message': f'Git stash thất bại: {output}', 'output': output}
    except Exception as e:
        return {'success': False, 'message': f'Lỗi khi thực hiện git stash: {str(e)}'}


def execute_git_stash_pop(workspace, stash_index=None):
    """Thực hiện git stash pop để khôi phục thay đổi từ stash."""
    try:
        stash_ref = (stash_index or 'stash@{0}').strip()
        if stash_ref and not stash_ref.startswith('stash@{'):
            if stash_ref.isdigit():
                stash_ref = f'stash@{{{stash_ref}}}'
            else:
                return {'success': False, 'message': f'Chỉ số stash không hợp lệ: {stash_ref}'}

        cmd = ['git', 'stash', 'pop', stash_ref]
        res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=30)
        output = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            return {
                'success': True,
                'message': f'Đã lấy code từ {stash_ref} thành công.',
                'output': output
            }
        else:
            has_conflict = 'conflict' in output.lower() or 'xung đột' in output.lower()
            return {
                'success': False,
                'conflict': has_conflict,
                'message': f'Lỗi khi lấy code từ {stash_ref}: {output}',
                'output': output
            }
    except Exception as e:
        return {'success': False, 'message': f'Lỗi khi thực hiện git stash pop: {str(e)}'}


def get_git_cherry_pick_status(workspace):
    """Kiểm tra xem repository có đang trong tiến trình cherry-pick hoặc xung đột không."""
    try:
        cherry_head = os.path.join(workspace, '.git', 'CHERRY_PICK_HEAD')
        in_progress = os.path.exists(cherry_head)

        status_raw = subprocess.check_output(['git', 'status', '--short'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
        conflicted_files = []
        for line in status_raw.splitlines():
            line_str = line.strip()
            if line_str.startswith(('UU ', 'AA ', 'UD ', 'DU ', 'DD ', 'AU ', 'UA ')) or line.startswith(('UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA')):
                conflicted_files.append(line[3:].strip())

        curr_branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()

        return {
            'in_progress': in_progress,
            'current_branch': curr_branch,
            'has_conflicts': len(conflicted_files) > 0,
            'conflicted_files': conflicted_files,
            'status_raw': status_raw
        }
    except Exception as e:
        return {
            'in_progress': False,
            'current_branch': '',
            'has_conflicts': False,
            'conflicted_files': [],
            'status_raw': str(e)
        }


def execute_git_cherry_pick(workspace, commits, no_commit=False, record_origin=True):
    """Thực hiện git cherry-pick cho một hoặc nhiều commit."""
    try:
        if isinstance(commits, str):
            commit_list = [c.strip() for c in commits.replace(',', ' ').split() if c.strip()]
        elif isinstance(commits, list):
            commit_list = [str(c).strip() for c in commits if str(c).strip()]
        else:
            commit_list = []

        if not commit_list:
            return {'success': False, 'message': 'Vui lòng cung cấp ít nhất một mã commit hash.'}

        curr_branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()

        cmd = ['git', 'cherry-pick']
        if no_commit:
            cmd.append('-n')
        if record_origin:
            cmd.append('-x')

        cmd.extend(commit_list)

        res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=60)
        output_msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()

        status_info = get_git_cherry_pick_status(workspace)
        if res.returncode == 0:
            head_msg = ''
            try:
                head_msg = subprocess.check_output(['git', 'log', '-1', '--pretty=%B'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
            except Exception:
                pass
            commit_ids_str = ', '.join([c[:8] if len(c) > 8 else c for c in commit_list])
            return {
                'success': True,
                'current_branch': curr_branch,
                'message': f"Đã cherry-pick commit {commit_ids_str} vào nhánh '{curr_branch}' thành công!",
                'commit_message': head_msg,
                'output': output_msg,
                'status': status_info
            }
        else:
            is_conflict = status_info['has_conflicts'] or ('conflict' in output_msg.lower()) or ('fix conflicts' in output_msg.lower())
            return {
                'success': False,
                'conflict': is_conflict,
                'current_branch': curr_branch,
                'conflicted_files': status_info['conflicted_files'],
                'message': output_msg or 'Lỗi khi thực hiện cherry-pick.',
                'output': output_msg,
                'status': status_info
            }
    except subprocess.TimeoutExpired:
        return {'success': False, 'conflict': False, 'message': 'Quá thời gian chờ (timeout 60s) khi cherry-pick.'}
    except Exception as e:
        return {'success': False, 'conflict': False, 'message': str(e)}


def abort_git_cherry_pick(workspace):
    """Hủy bỏ (abort) tiến trình cherry-pick đang dở dang."""
    try:
        res = subprocess.run(['git', 'cherry-pick', '--abort'], cwd=workspace, capture_output=True, text=True, timeout=20)
        msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        status_info = get_git_cherry_pick_status(workspace)
        if res.returncode == 0 or not status_info['in_progress']:
            return {'success': True, 'message': 'Đã hủy bỏ (abort) cherry-pick thành công, workspace đã an toàn.', 'status': status_info}
        return {'success': False, 'message': msg or 'Lỗi khi abort cherry-pick.', 'status': status_info}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def continue_git_cherry_pick(workspace):
    """Tiếp tục (continue) tiến trình cherry-pick sau khi đã giải quyết xung đột."""
    try:
        res = subprocess.run(['git', 'cherry-pick', '--continue'], cwd=workspace, capture_output=True, text=True, timeout=30)
        msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        status_info = get_git_cherry_pick_status(workspace)
        if res.returncode == 0:
            head_hash = ''
            try:
                head_hash = subprocess.check_output(
                    ['git', 'log', '-1', '--pretty=%h'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                pass
            curr_b = ''
            try:
                curr_b = subprocess.check_output(
                    ['git', 'branch', '--show-current'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                pass
            c_label = f" commit {head_hash}" if head_hash else ""
            b_label = f" vào nhánh '{curr_b}'" if curr_b else ""
            return {'success': True, 'message': f"Đã tiếp tục cherry-pick{c_label}{b_label} thành công!", 'status': status_info}
        return {'success': False, 'message': msg or 'Lỗi khi tiếp tục cherry-pick.', 'status': status_info}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def push_git_branch(workspace, branch_name=None, commit_message=None):
    """Đẩy commit lên nhánh remote (git push origin <branch>)."""
    try:
        curr_branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip()
        target_branch = (branch_name or '').strip() or curr_branch
        if not target_branch:
            return {'success': False, 'message': 'Không tìm thấy tên nhánh để push.'}

        # Nếu người dùng muốn sửa lại commit message trước khi push
        if commit_message and commit_message.strip():
            try:
                head_msg = subprocess.check_output(
                    ['git', 'log', '-1', '--pretty=%B'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                if head_msg != commit_message.strip():
                    amend_res = subprocess.run(
                        ['git', 'commit', '--amend', '-m', commit_message.strip()],
                        cwd=workspace, capture_output=True, text=True, timeout=30
                    )
                    if amend_res.returncode != 0:
                        return {'success': False, 'message': f"Lỗi khi cập nhật commit message: {amend_res.stderr.strip()}"}
            except Exception as e:
                return {'success': False, 'message': f"Lỗi khi amend commit: {str(e)}"}

        # Thực hiện git push origin <target_branch>
        push_res = subprocess.run(
            ['git', 'push', 'origin', target_branch],
            cwd=workspace, capture_output=True, text=True, timeout=60
        )
        msg = (push_res.stdout.strip() + '\n' + push_res.stderr.strip()).strip()
        if push_res.returncode == 0:
            return {
                'success': True,
                'branch': target_branch,
                'message': f"Đã push code lên nhánh remote '{target_branch}' thành công!\n{msg}".strip()
            }
        else:
            return {
                'success': False,
                'branch': target_branch,
                'message': msg or f"Push code lên nhánh '{target_branch}' thất bại."
            }
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Quá thời gian quy định (timeout 60s) khi git push.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def sync_pull_branch(workspace, target_branch, return_to_current=False):
    """
    Checkout nhánh target_branch (staging hoặc master) và thực hiện git pull.
    Nếu return_to_current=True, sau khi pull thành công sẽ tự động checkout quay lại nhánh ban đầu.
    Nếu có conflict hoặc lỗi, ghi nhận và trả về chi tiết các file bị conflict.
    """
    try:
        target_branch = target_branch.strip()
        if not target_branch:
            return {'success': False, 'conflict': False, 'message': 'Tên nhánh không được để trống.'}

        # 1. Kiểm tra uncommitted changes ở working tree
        status_res = subprocess.run(['git', 'status', '--porcelain'], cwd=workspace, capture_output=True, text=True, timeout=10)
        dirty_files = [l.strip() for l in status_res.stdout.splitlines() if l.strip()]

        # 2. Checkout sang nhánh đích
        curr_branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
        if curr_branch != target_branch:
            # Kiểm tra xem nhánh đã có ở local chưa
            branches_raw = subprocess.check_output(['git', 'branch', '--list', target_branch], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
            if branches_raw:
                checkout_cmd = ['git', 'checkout', target_branch]
            else:
                checkout_cmd = ['git', 'checkout', '-b', target_branch, f'origin/{target_branch}']

            chk_res = subprocess.run(checkout_cmd, cwd=workspace, capture_output=True, text=True, timeout=30)
            if chk_res.returncode != 0:
                err_msg = (chk_res.stdout.strip() + '\n' + chk_res.stderr.strip()).strip()
                return {
                    'success': False,
                    'conflict': False,
                    'needs_stash': True,
                    'current_branch': curr_branch,
                    'target_branch': target_branch,
                    'message': f"Không thể chuyển sang nhánh '{target_branch}'. Vui lòng commit hoặc stash các thay đổi dở dang trước khi pull.\nChi tiết: {err_msg}",
                    'dirty_files': dirty_files
                }

        # 3. Pull từ remote
        pull_res = subprocess.run(['git', 'pull', 'origin', target_branch], cwd=workspace, capture_output=True, text=True, timeout=60)
        pull_output = (pull_res.stdout.strip() + '\n' + pull_res.stderr.strip()).strip()

        # 4. Kiểm tra conflict sau khi pull
        post_status = subprocess.run(['git', 'status', '--porcelain'], cwd=workspace, capture_output=True, text=True, timeout=10)
        conflicted_files = []
        for line in post_status.stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith(('UU ', 'AA ', 'UD ', 'DU ', 'DD ', 'AU ', 'UA ')) or line.startswith(('UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA')):
                conflicted_files.append(line[3:].strip())

        is_conflict = len(conflicted_files) > 0 or ('conflict' in pull_output.lower()) or ('fix conflicts' in pull_output.lower())

        if pull_res.returncode == 0 and not is_conflict:
            head_commit = subprocess.check_output(['git', 'log', '-1', '--oneline'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
            final_branch = target_branch
            if return_to_current and curr_branch and curr_branch != target_branch:
                ret_res = subprocess.run(['git', 'checkout', curr_branch], cwd=workspace, capture_output=True, text=True, timeout=30)
                if ret_res.returncode == 0:
                    final_branch = curr_branch
            return {
                'success': True,
                'conflict': False,
                'target_branch': target_branch,
                'final_branch': final_branch,
                'returned_to_initial': (final_branch == curr_branch and curr_branch != target_branch),
                'message': 'Đã pull thành công',
                'output': pull_output or 'Already up to date.',
                'head_commit': head_commit
            }
        else:
            return {
                'success': False,
                'conflict': is_conflict,
                'target_branch': target_branch,
                'conflicted_files': conflicted_files,
                'message': f"Xảy ra xung đột (Conflict) khi pull nhánh '{target_branch}'!" if is_conflict else f"Pull nhánh '{target_branch}' thất bại.",
                'output': pull_output
            }
    except subprocess.TimeoutExpired:
        return {'success': False, 'conflict': False, 'message': f"Quá thời gian quy định (timeout 60s) khi pull nhánh '{target_branch}'."}
    except Exception as e:
        return {'success': False, 'conflict': False, 'message': str(e)}


def abort_git_merge(workspace):
    """Hủy bỏ (git merge --abort) khi gặp xung đột lúc pull."""
    try:
        res = subprocess.run(['git', 'merge', '--abort'], cwd=workspace, capture_output=True, text=True, timeout=20)
        msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            return {'success': True, 'message': 'Đã hủy bỏ merge thành công, workspace an toàn.'}
        return {'success': False, 'message': msg or 'Lỗi khi hủy bỏ merge.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def format_git_relative_date(raw_date: str) -> str:
    """Chuẩn hóa thời gian tương đối Git sang tiếng Việt ngắn gọn."""
    if not raw_date:
        return ''
    s = str(raw_date).strip()
    if not s:
        return ''

    is_ago = bool(re.search(r'\bago\b', s, re.IGNORECASE)) or ('trước' in s)
    clean_s = re.sub(r'\bago\b', '', s, flags=re.IGNORECASE)
    clean_s = re.sub(r'\btrước\b', '', clean_s, flags=re.IGNORECASE).strip()

    m_h_m = re.search(r'(\d+)\s*(?:hours?|giờ|hrs?|h)\s*(?:,?\s*and\s*)?,?\s*(\d+)\s*(?:minutes?|phút|mins?|min|m|p)?(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_h_m:
        h = int(m_h_m.group(1))
        m = int(m_h_m.group(2))
        h += m // 60
        m = m % 60
        res = f"{h}h{m:02d}" if m > 0 else f"{h}h"
        return f"{res} trước" if is_ago else res

    m_h = re.search(r'(\d+)\s*(?:hours?|giờ|hrs?|h)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_h:
        h = int(m_h.group(1))
        res = f"{h}h"
        return f"{res} trước" if is_ago else res

    m_m = re.search(r'(\d+)\s*(?:minutes?|phút|mins?|min|m|p)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_m:
        m = int(m_m.group(1))
        if m >= 60:
            h = m // 60
            rem_m = m % 60
            res = f"{h}h{rem_m:02d}" if rem_m > 0 else f"{h}h"
        else:
            res = f"{m} phút"
        return f"{res} trước" if is_ago else res

    # Case 4: Seconds (>= 60s -> 1p25s)
    m_s = re.search(r'(\d+)\s*(?:seconds?|giây|secs?|s)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_s:
        sec = int(m_s.group(1))
        if sec >= 60:
            m = sec // 60
            rem_s = sec % 60
            res = f"{m}p{rem_s}s" if rem_s > 0 else f"{m}p"
        else:
            res = f"{sec}s"
        return f"{res} trước" if is_ago else res

    m_d = re.search(r'(\d+)\s*(?:days?|ngày)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_d:
        d = int(m_d.group(1))
        res = f"{d} ngày"
        return f"{res} trước" if is_ago else res

    m_w = re.search(r'(\d+)\s*(?:weeks?|tuần)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_w:
        w = int(m_w.group(1))
        res = f"{w} tuần"
        return f"{res} trước" if is_ago else res

    m_mo = re.search(r'(\d+)\s*(?:months?|tháng)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_mo:
        mo = int(m_mo.group(1))
        res = f"{mo} tháng"
        return f"{res} trước" if is_ago else res

    m_y = re.search(r'(\d+)\s*(?:years?|năm)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_y:
        y = int(m_y.group(1))
        res = f"{y} năm"
        return f"{res} trước" if is_ago else res

    return s


def check_sync_pull_status(workspace, branches=('staging', 'master', 'beta'), do_fetch=True):
    """Kiểm tra commit mới cần pull từ remote cho các nhánh chỉ định."""
    results = {}
    if not workspace or not os.path.exists(workspace):
        return results

    current_author = ""
    try:
        current_author = subprocess.check_output(['git', 'config', 'user.name'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        pass

    def _is_me(name):
        if not name:
            return False
        n_low = name.lower()
        return bool(
            (current_author and current_author.lower() in n_low) or
            'thiết' in n_low or
            'thiet' in n_low
        )

    if do_fetch:
        try:
            fetch_targets = [b.strip() for b in branches if b.strip()]
            subprocess.run(
                ['git', 'fetch', '-q', 'origin'] + fetch_targets,
                cwd=workspace, capture_output=True, timeout=12
            )
        except Exception:
            pass

    for br in branches:
        br = br.strip()
        if not br:
            continue
        branch_res = {
            'branch': br,
            'exists': False,
            'remote_exists': False,
            'needs_pull': False,
            'behind_count': 0,
            'ahead_count': 0,
            'diff_stat': '',
            'commits': [],
            'latest_commit': None
        }

        rem_check = subprocess.run(
            ['git', 'rev-parse', '--verify', f'origin/{br}'],
            cwd=workspace, capture_output=True, text=True
        )
        if rem_check.returncode == 0:
            branch_res['remote_exists'] = True
        else:
            results[br] = branch_res
            continue

        try:
            latest_raw = subprocess.check_output(
                ['git', 'log', '-1', '--format=%h|%s|%an|%cr', f'origin/{br}'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if latest_raw:
                p = latest_raw.split('|', 3)
                author_val = p[2].strip() if len(p) > 2 else ''
                branch_res['latest_commit'] = {
                    'hash': p[0].strip(),
                    'subject': p[1].strip() if len(p) > 1 else '',
                    'author': author_val,
                    'is_me': _is_me(author_val),
                    'date': format_git_relative_date(p[3].strip()) if len(p) > 3 else ''
                }
        except Exception:
            pass

        loc_check = subprocess.run(
            ['git', 'rev-parse', '--verify', br],
            cwd=workspace, capture_output=True, text=True
        )
        if loc_check.returncode == 0:
            branch_res['exists'] = True
        else:
            branch_res['exists'] = False
            branch_res['needs_pull'] = True
            try:
                c_out = subprocess.check_output(
                    ['git', 'rev-list', '--count', f'origin/{br}'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                branch_res['behind_count'] = int(c_out) if c_out.isdigit() else 1
            except Exception:
                branch_res['behind_count'] = 1
            results[br] = branch_res
            continue

        try:
            counts = subprocess.check_output(
                ['git', 'rev-list', '--left-right', '--count', f'{br}...origin/{br}'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip().split()
            if len(counts) >= 2:
                branch_res['ahead_count'] = int(counts[0])
                branch_res['behind_count'] = int(counts[1])
                branch_res['needs_pull'] = branch_res['behind_count'] > 0
        except Exception:
            pass

        if branch_res['needs_pull']:
            try:
                stat_raw = subprocess.check_output(
                    ['git', 'diff', '--shortstat', f'{br}..origin/{br}'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                branch_res['diff_stat'] = stat_raw
            except Exception:
                pass

            try:
                commits_raw = subprocess.check_output(
                    ['git', 'log', f'{br}..origin/{br}', '--format=%h|%s|%an|%cr', '-n', '15'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip().splitlines()
                commit_list = []
                for line in commits_raw:
                    if not line.strip():
                        continue
                    p = line.split('|', 3)
                    h = p[0].strip()
                    subject_val = p[1].strip() if len(p) > 1 else ''
                    author_val = p[2].strip() if len(p) > 2 else ''
                    date_val = p[3].strip() if len(p) > 3 else ''

                    # Chi tiết các file thay đổi riêng trong commit này
                    c_files = []
                    try:
                        ns_commit = subprocess.check_output(
                            ['git', 'show', '-m', '--first-parent', '--numstat', '--format=', h],
                            cwd=workspace, text=True, stderr=subprocess.DEVNULL
                        ).strip().splitlines()
                        for c_line in ns_commit:
                            parts = c_line.strip().split('\t')
                            if len(parts) >= 3:
                                c_files.append({
                                    'path': parts[2].strip(),
                                    'additions': int(parts[0]) if parts[0].isdigit() else 0,
                                    'deletions': int(parts[1]) if parts[1].isdigit() else 0,
                                })
                    except Exception:
                        pass

                    # Diff riêng của commit này
                    c_diff = ''
                    try:
                        c_diff = subprocess.check_output(
                            ['git', 'show', '-m', '--first-parent', '-U3', '--format=', h],
                            cwd=workspace, text=True, stderr=subprocess.DEVNULL
                        )
                        if len(c_diff) > 40000:
                            c_diff = c_diff[:40000] + "\n\n... (Diff commit quá dài, đã rút gọn) ..."
                    except Exception:
                        c_diff = ''

                    commit_list.append({
                        'hash': h,
                        'subject': subject_val,
                        'author': author_val,
                        'is_me': _is_me(author_val),
                        'date': format_git_relative_date(date_val),
                        'files': c_files,
                        'diff': c_diff
                    })
                branch_res['commits'] = commit_list
            except Exception:
                pass

            # Lấy danh sách chi tiết các file đã sửa (+adds -dels) và diff để hiển thị khi người dùng mở rộng
            try:
                ns_raw = subprocess.check_output(
                    ['git', 'diff', '--numstat', f'{br}..origin/{br}'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip().splitlines()
                file_diffs = []
                for n_line in ns_raw:
                    parts = n_line.strip().split('\t')
                    if len(parts) >= 3:
                        file_diffs.append({
                            'path': parts[2].strip(),
                            'additions': int(parts[0]) if parts[0].isdigit() else 0,
                            'deletions': int(parts[1]) if parts[1].isdigit() else 0,
                        })
                branch_res['files'] = file_diffs
            except Exception:
                branch_res['files'] = []

            try:
                diff_text = subprocess.check_output(
                    ['git', 'diff', '-U3', f'{br}..origin/{br}'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                )
                if len(diff_text) > 80000:
                    diff_text = diff_text[:80000] + "\n\n... (Diff quá dài, đã rút gọn) ..."
                branch_res['diff'] = diff_text
            except Exception:
                branch_res['diff'] = ''

        results[br] = branch_res

    return results


def parse_git_conflict_content(content):
    """Phân tích nội dung file tìm các khối xung đột Git (conflict blocks)."""
    pattern = re.compile(
        r'(<<<<<<<[^\n]*\n)([\s\S]*?)(?:\|\|\|\|\|\|\|[^\n]*\n[\s\S]*?)?(=======\n)([\s\S]*?)(>>>>>>>[^\n]*(?:\n|$))'
    )
    blocks = []
    lines_before = 1
    last_end = 0
    for idx, m in enumerate(pattern.finditer(content)):
        lines_before += content[last_end:m.start()].count('\n')
        current_header = m.group(1).strip()
        current_code = m.group(2)
        incoming_code = m.group(4)
        incoming_footer = m.group(5).strip()
        blocks.append({
            'index': idx,
            'start_line': lines_before,
            'current_header': current_header,
            'current_code': current_code,
            'incoming_code': incoming_code,
            'incoming_footer': incoming_footer,
            'start': m.start(),
            'end': m.end()
        })
        lines_before += m.group(0).count('\n')
        last_end = m.end()
    return blocks


def resolve_conflict_content(content, action, block_index=None):
    """
    Giải quyết khối conflict trong content:
    - action: 'accept_current' | 'accept_incoming' | 'accept_both'
    - block_index: int (chỉ giải quyết 1 khối cụ thể) hoặc None/'all' (giải quyết tất cả các khối)
    """
    pattern = re.compile(
        r'(<<<<<<<[^\n]*\n)([\s\S]*?)(?:\|\|\|\|\|\|\|[^\n]*\n[\s\S]*?)?(=======\n)([\s\S]*?)(>>>>>>>[^\n]*(?:\n|$))'
    )
    matches = list(pattern.finditer(content))
    if not matches:
        return content

    if block_index is not None and str(block_index).lower() != 'all':
        try:
            idx = int(block_index)
        except (ValueError, TypeError):
            idx = -1
        if 0 <= idx < len(matches):
            m = matches[idx]
            cur = m.group(2)
            inc = m.group(4)
            if action == 'accept_current':
                repl = cur
            elif action == 'accept_incoming':
                repl = inc
            elif action == 'accept_both':
                repl = cur + inc
            else:
                return content
            return content[:m.start()] + repl + content[m.end():]
        return content

    def repl_all(m):
        cur = m.group(2)
        inc = m.group(4)
        if action == 'accept_current':
            return cur
        elif action == 'accept_incoming':
            return inc
        elif action == 'accept_both':
            return cur + inc
        return m.group(0)

    return pattern.sub(repl_all, content)


def get_git_active_conflict_status(workspace):
    """Kiểm tra xem workspace có đang trong tình trạng xung đột hoặc dở dang merge/cherry-pick không."""
    if not workspace or not os.path.exists(workspace):
        return {'in_conflict': False, 'operation': None, 'conflicted_files': []}

    git_dir = os.path.join(workspace, '.git')
    is_merge = os.path.exists(os.path.join(git_dir, 'MERGE_HEAD'))
    is_cherry = os.path.exists(os.path.join(git_dir, 'CHERRY_PICK_HEAD'))
    is_rebase = os.path.exists(os.path.join(git_dir, 'rebase-merge')) or os.path.exists(os.path.join(git_dir, 'rebase-apply'))

    operation = None
    if is_cherry:
        operation = 'cherry_pick'
    elif is_merge:
        operation = 'merge'
    elif is_rebase:
        operation = 'rebase'

    conflicted_files = []
    try:
        status_raw = subprocess.check_output(
            ['git', 'status', '--short'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip()
        for line in status_raw.splitlines():
            line_str = line.strip()
            if line_str.startswith(('UU ', 'AA ', 'UD ', 'DU ', 'DD ', 'AU ', 'UA ')) or line.startswith(('UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA')):
                conflicted_files.append(line[3:].strip())
    except Exception:
        pass

    in_conflict = bool(conflicted_files) or bool(operation)
    return {
        'in_conflict': in_conflict,
        'operation': operation,
        'conflicted_files': conflicted_files
    }


def get_git_conflict_file_info(workspace, file_path):
    """Đọc và phân tích chi tiết các khối conflict trong 1 file cụ thể."""
    if not workspace or not file_path:
        return {'success': False, 'message': 'Thiếu workspace hoặc đường dẫn file.'}

    clean_path = os.path.normpath(file_path).lstrip('/')
    abs_file = os.path.abspath(os.path.join(workspace, clean_path))
    abs_ws = os.path.abspath(workspace)
    if not abs_file.startswith(abs_ws):
        return {'success': False, 'message': 'Đường dẫn file không hợp lệ (path traversal).'}
    if not os.path.exists(abs_file):
        return {'success': False, 'message': f'Không tìm thấy file: {clean_path}'}

    try:
        with open(abs_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {'success': False, 'message': f'Không thể đọc file: {str(e)}'}

    blocks = parse_git_conflict_content(content)
    lines = content.splitlines()

    return {
        'success': True,
        'file_path': clean_path,
        'has_conflicts': len(blocks) > 0,
        'conflict_count': len(blocks),
        'total_lines': len(lines),
        'blocks': blocks,
        'raw_content': content
    }


def resolve_git_conflict_file(workspace, file_path, action, block_index=None):
    """
    Thực hiện giải quyết xung đột (Current/Incoming/Both) trên 1 file và tự động git add nếu đã hết conflict.
    """
    if not workspace or not file_path:
        return {'success': False, 'message': 'Thiếu workspace hoặc đường dẫn file.'}

    clean_path = os.path.normpath(file_path).lstrip('/')
    abs_file = os.path.abspath(os.path.join(workspace, clean_path))
    abs_ws = os.path.abspath(workspace)
    if not abs_file.startswith(abs_ws):
        return {'success': False, 'message': 'Đường dẫn file không hợp lệ.'}
    if not os.path.exists(abs_file):
        return {'success': False, 'message': f'Không tìm thấy file: {clean_path}'}

    try:
        with open(abs_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {'success': False, 'message': f'Không thể đọc file: {str(e)}'}

    new_content = resolve_conflict_content(content, action, block_index=block_index)
    try:
        with open(abs_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        return {'success': False, 'message': f'Không thể ghi file: {str(e)}'}

    rem_blocks = parse_git_conflict_content(new_content)
    file_staged = False
    if len(rem_blocks) == 0:
        try:
            subprocess.run(['git', 'add', clean_path], cwd=workspace, check=True, capture_output=True)
            file_staged = True
        except Exception:
            pass

    status_info = get_git_active_conflict_status(workspace)

    return {
        'success': True,
        'file_path': clean_path,
        'action_applied': action,
        'block_index': block_index,
        'remaining_conflicts_in_file': len(rem_blocks),
        'file_staged': file_staged,
        'all_conflicts_resolved': len(status_info['conflicted_files']) == 0,
        'conflicted_files': status_info['conflicted_files'],
        'updated_blocks': rem_blocks,
        'raw_content': new_content
    }


def abort_git_conflict(workspace):
    """Hủy bỏ thao tác Git đang gặp xung đột (tự động phân biệt merge hoặc cherry-pick)."""
    status = get_git_active_conflict_status(workspace)
    op = status.get('operation')
    if op == 'cherry_pick':
        return abort_git_cherry_pick(workspace)
    return abort_git_merge(workspace)


def continue_git_conflict(workspace, commit_message=None):
    """Tiếp tục hoàn tất thao tác Git sau khi đã giải quyết xung đột (tự động phân biệt merge hoặc cherry-pick)."""
    status = get_git_active_conflict_status(workspace)
    op = status.get('operation')
    if op == 'cherry_pick':
        return continue_git_cherry_pick(workspace)
    return continue_git_merge(workspace, commit_message=commit_message)



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


def build_skill_directive(skill_input) -> str:
    if isinstance(skill_input, list):
        skill_list = [str(s).strip() for s in skill_input if str(s).strip()]
    elif isinstance(skill_input, str):
        skill_list = [s.strip() for s in skill_input.split(',') if s.strip()]
    else:
        skill_list = []

    if not skill_list:
        return (
            "\n[SKILL DIRECTIVE] Tự động nạp: Hãy chủ động rà soát thư mục '.agents/skills/' trong workspace của bạn "
            "để áp dụng đúng kiến trúc, DTO, entity, validation và luồng nghiệp vụ tương ứng trước khi xử lý.\n"
        )

    formatted = []
    for s in skill_list:
        sc = s.strip().lstrip('/')
        if not sc:
            continue
        formatted.append(sc)

    bullet_points = [
        f"- Đọc và tuân thủ tài liệu hướng dẫn nghiệp vụ/kiến trúc tại '.agents/skills/{s}/SKILL.md' (hoặc gọi tool skill '{s}') trong workspace."
        for s in formatted
    ]

    return (
        f"\n[SKILL DIRECTIVE] Tác vụ này áp dụng các skill trọng tâm: {', '.join(formatted)}.\n"
        f"Yêu cầu thực thi:\n" + "\n".join(bullet_points) + "\n"
        f"để áp dụng đúng chuẩn kiến trúc, danh sách file, component, DTO, bảng biểu, entity và quy tắc nghiệp vụ đã định nghĩa sẵn.\n"
    )


# -------------------------------------------------------------
# WORKER: LÀM TASK (TASK EXECUTION)
# -------------------------------------------------------------
def stream_process_turn(cmd, cwd, turn_data, timeout=360, task_state=None):
    """Thực thi tiến trình CLI agy với stream-json và stream realtime từng tool call, log ngầm vào turn_data."""
    t0 = time.time()
    proc = None
    turn_data.setdefault('step_logs', [])
    turn_data.setdefault('content', '')

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True
        )
        with state_lock:
            if task_state is not None:
                task_state['current_process'] = proc
            app_state['current_process'] = proc

        content_parts = []
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            line_str = line.strip()
            if not line_str:
                continue

            # Phân tích NDJSON streaming từ CLI agy (--output-format stream-json)
            if line_str.startswith('{') and line_str.endswith('}'):
                try:
                    event_data = json.loads(line_str, strict=False)
                    event_type = event_data.get('event')

                    if event_type == 'step_update':
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
                            elif 'query' in params:
                                param_summary = str(params['query'])
                            elif params:
                                param_summary = ", ".join([f"{k}: {v}" for k, v in list(params.items())[:2]])

                            with state_lock:
                                existing = next((s for s in turn_data['step_logs'] if s.get('step_index') == step_idx and s.get('tool_name') == tname), None)
                                if existing:
                                    existing['state'] = state
                                    if output:
                                        existing['output'] = output
                                    if duration is not None:
                                        existing['duration'] = round(duration, 2)
                                else:
                                    turn_data['step_logs'].append({
                                        'step_index': step_idx,
                                        'tool_name': tname,
                                        'param_summary': param_summary,
                                        'params': params,
                                        'state': state,
                                        'output': output,
                                        'duration': round(duration, 2) if duration else None,
                                        'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
                                    })
                                turn_data['elapsed_sec'] = round(time.time() - t0, 1)
                                if task_state is not None:
                                    short_cmd = param_summary[:50] + ('...' if len(param_summary) > 50 else '')
                                    task_state['status_text'] = f"Đang chạy [{tname}]: {short_cmd}" if short_cmd else f"Đang chạy tool: {tname}"

                        elif step_type == 'agent_response':
                            text_delta = su.get('text_delta')
                            if text_delta:
                                content_parts.append(text_delta)
                                with state_lock:
                                    turn_data['content'] = "".join(content_parts)
                                    turn_data['elapsed_sec'] = round(time.time() - t0, 1)

                    elif event_type == 'result':
                        res = event_data.get('result', {})
                        final_resp = res.get('response')
                        if final_resp:
                            with state_lock:
                                turn_data['content'] = final_resp
                                turn_data['elapsed_sec'] = round(time.time() - t0, 1)

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

        proc.wait(timeout=15)
        elapsed = round(time.time() - t0, 1)
        with state_lock:
            if not turn_data.get('content') and content_parts:
                turn_data['content'] = "".join(content_parts).strip()
            turn_data['elapsed_sec'] = elapsed
            turn_data['is_streaming'] = False
        return turn_data.get('content', ''), elapsed

    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
        with state_lock:
            turn_data['content'] = turn_data.get('content', '') + "\n[Hết giờ]: Agent không phản hồi sau thời gian quy định."
            turn_data['elapsed_sec'] = round(time.time() - t0, 1)
            turn_data['is_streaming'] = False
        return turn_data.get('content', ''), turn_data['elapsed_sec']
    except Exception as e:
        with state_lock:
            turn_data['content'] = turn_data.get('content', '') + f"\n[Lỗi]: {str(e)}"
            turn_data['elapsed_sec'] = round(time.time() - t0, 1)
            turn_data['is_streaming'] = False
        return turn_data.get('content', ''), turn_data['elapsed_sec']
    finally:
        with state_lock:
            if task_state is not None:
                task_state['current_process'] = None
            if app_state.get('current_process') == proc:
                app_state['current_process'] = None


def run_task_worker(task_id: str, prompt: str, target: str, starter: str, rounds: int, skill: str):
    global app_state

    agy_bin = get_agy_bin()
    session_id = f"task_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time = time.time()

    role_meta = {
        'fe': {
            'label': 'Frontend Agent',
            'sub': 'webapp (React/TypeScript)',
            'color': '#06b6d4',
            'workspace': get_fe_workspace(),
            'desc': 'Frontend React / TypeScript / Ant Design Engineer tại easysalon-webapp'
        },
        'be': {
            'label': 'Backend Agent',
            'sub': 'api (.NET/C#)',
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

    with state_lock:
        task_state = app_state['active_tasks'].get(task_id)
        if not task_state:
            task_state = {
                'task_id': task_id,
                'title': f"Làm task: {prompt[:35]}",
                'mode': 'task',
                'is_running': True,
                'current_process': None,
                'active_round': 0,
                'total_rounds': max_rounds,
                'active_speaker': target if target != 'both' else current_role,
                'status_text': 'Khởi tạo tác vụ...',
                'session': {
                    'id': session_id,
                    'task_id': task_id,
                    'type': 'TASK',
                    'target': target,
                    'prompt': prompt,
                    'skill': skill,
                    'starter': current_role,
                    'total_rounds': max_rounds,
                    'turns': [],
                    'status': 'RUNNING',
                    'created_at': datetime.datetime.now().strftime('%H:%M:%S')
                }
            }
            app_state['active_tasks'][task_id] = task_state
        else:
            task_state['is_running'] = True
            task_state['mode'] = 'task'
            task_state['total_rounds'] = max_rounds
            task_state['active_round'] = 0
            task_state['active_speaker'] = target if target != 'both' else current_role
            task_state['status_text'] = 'Khởi tạo tác vụ...'
            task_state['session'] = {
                'id': session_id,
                'task_id': task_id,
                'type': 'TASK',
                'target': target,
                'prompt': prompt,
                'skill': skill,
                'starter': current_role,
                'total_rounds': max_rounds,
                'turns': [],
                'status': 'RUNNING',
                'created_at': datetime.datetime.now().strftime('%H:%M:%S')
            }

        app_state['is_running'] = True
        app_state['current_session'] = task_state['session']
        app_state['status_text'] = task_state['status_text']

    skill_directive = build_skill_directive(skill)
    history = []
    is_consensus_reached = False

    if target in ('fe', 'be'):
        active_role = target
        curr_info = role_meta[active_role]

        with state_lock:
            task_state['active_round'] = 1
            task_state['active_speaker'] = active_role
            task_state['status_text'] = f"[{curr_info['label']}] đang đọc codebase và xử lý task..."
            app_state['status_text'] = task_state['status_text']

        agent_prompt = (
            f"Bạn là {curr_info['desc']}.\n\n"
            f"YÊU CẦU TASK CỦA NGƯỜI DÙNG:\n"
            f"\"\"\"\n{prompt}\n\"\"\"\n"
            f"{skill_directive}\n"
            f"HƯỚNG DẪN THỰC HIỆN:\n"
            f"- Đọc codebase thực tế trong workspace của bạn để nắm cấu trúc file, DTO, component.\n"
            f"- Trực tiếp thực hiện task, sửa/tạo code cần thiết hoặc đưa ra hướng giải quyết chi tiết, chính xác.\n"
            f"- Trình bày kết quả rõ ràng, súc tích, chuyên nghiệp."
        )

        cmd = [agy_bin, '--dangerously-skip-permissions', '--mode', 'accept-edits', '--output-format', 'stream-json', '-p', agent_prompt]
        turn_data = {
            'round': 1,
            'speaker': active_role,
            'label': curr_info['label'],
            'sub': curr_info['sub'],
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
            'elapsed_sec': 0,
            'step_logs': [],
            'content': '',
            'is_streaming': True
        }
        with state_lock:
            if task_state.get('session'):
                task_state['session']['turns'].append(turn_data)

        response_text, elapsed = stream_process_turn(cmd, curr_info['workspace'], turn_data, timeout=360, task_state=task_state)
        history.append(turn_data)

    else:
        for round_idx in range(1, max_rounds + 1):
            with state_lock:
                if not task_state['is_running']:
                    break
                task_state['active_round'] = round_idx
                task_state['active_speaker'] = current_role
                curr_info = role_meta[current_role]
                other_role = 'be' if current_role == 'fe' else 'fe'
                other_info = role_meta[other_role]
                task_state['status_text'] = f"[{curr_info['label']}] đang đọc codebase và xử lý (Lượt {round_idx}/{max_rounds})..."
                app_state['status_text'] = task_state['status_text']

            if round_idx == 1:
                agent_prompt = (
                    f"Bạn là {curr_info['desc']}.\n\n"
                    f"Người dùng vừa giao một task phối hợp kỹ thuật giữa bạn và {other_info['label']}.\n"
                    f"YÊU CẦU TASK TỪ NGƯỜI DÙNG:\n"
                    f"\"\"\"\n{prompt}\n\"\"\"\n"
                    f"{skill_directive}\n"
                    f"HƯỚNG DẪN DÀNH CHO LƯỢT ĐẦU TIÊN CỦA BẠN:\n"
                    f"- Bám sát yêu cầu người dùng, kiểm tra file code và skill module thực tế tại workspace của bạn.\n"
                    f"- Trình bày góc nhìn kỹ thuật, các DTO/API cần thiết hoặc đưa ra đề xuất triển khai gửi cho {other_info['label']}.\n"
                    f"- Đi thẳng vào vấn đề, mạch lạc và cụ thể."
                )
            else:
                last_turn = history[-1]
                prev_summary = "".join([f"--- [Lượt {h['round']} - {h['label']}] ---\n{h['content']}\n\n" for h in history])
                agent_prompt = (
                    f"Bạn là {curr_info['desc']}.\n\n"
                    f"Bạn và {other_info['label']} đang cùng phối hợp giải quyết task:\n"
                    f"\"\"\"\n{prompt}\n\"\"\"\n"
                    f"{skill_directive}\n"
                    f"TIẾN TRÌNH TỪ ĐẦU ĐẾN NAY:\n{prev_summary.strip()}\n\n"
                    f"Ý KIẾN MỚI NHẤT TỪ {other_info['label'].upper()}:\n"
                    f"\"\"\"\n{last_turn['content']}\n\"\"\"\n\n"
                    f"HƯỚNG DẪN DÀNH CHO BẠN (LƯỢT {round_idx}/{max_rounds}):\n"
                    f"- Đối chiếu codebase, DTO, entity, API endpoint để phản hồi trực tiếp các điểm của {other_info['label']}.\n"
                    f"- Thống nhất giải pháp. Nếu đã giải quyết xong và thống nhất hoàn toàn: tóm tắt ngắn gọn và kết thúc bằng '[ĐÃ THỐNG NHẤT - HOÀN TẤT]'."
                )

            cmd = [agy_bin, '--dangerously-skip-permissions', '--mode', 'accept-edits', '--output-format', 'stream-json', '-p', agent_prompt]
            turn_data = {
                'round': round_idx,
                'speaker': current_role,
                'label': curr_info['label'],
                'sub': curr_info['sub'],
                'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
                'elapsed_sec': 0,
                'step_logs': [],
                'content': '',
                'is_streaming': True
            }
            with state_lock:
                if task_state.get('session'):
                    task_state['session']['turns'].append(turn_data)

            response_text, elapsed = stream_process_turn(cmd, curr_info['workspace'], turn_data, timeout=300, task_state=task_state)
            history.append(turn_data)

            if any(sig in response_text for sig in ['[ĐÃ THỐNG NHẤT - HOÀN TẤT]', '[THỐNG NHẤT: HOÀN TẤT]']) and round_idx >= 2:
                is_consensus_reached = True
                break

            current_role = other_role

    total_time = round(time.time() - start_time, 1)

    with state_lock:
        task_state['is_running'] = False
        task_state['active_speaker'] = ''
        task_state['status_text'] = 'Đã hoàn tất task!'
        if task_state.get('session'):
            task_state['session']['status'] = 'COMPLETED'
            task_state['session']['consensus_reached'] = is_consensus_reached
            task_state['session']['total_duration_sec'] = total_time
        app_state['is_running'] = any(t.get('is_running') for t in app_state['active_tasks'].values())

    messages = load_messages()
    messages.append({
        'id': session_id,
        'task_id': task_id,
        'type': 'TASK',
        'title': task_state.get('title') or f"Làm task: {prompt[:100]}",
        'status': 'COMPLETED',
        'target': target,
        'created_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y'),
        'prompt': prompt,
        'module': skill,
        'consensus_reached': is_consensus_reached,
        'total_duration_sec': total_time,
        'duration_sec': total_time,
        'total_turns': len(history),
        'turns': history
    })
    save_messages(messages)


# -------------------------------------------------------------
# WORKER: FIX BUG (SURGICAL DEBUG & FIX PROTOCOL)
# -------------------------------------------------------------
def run_fixbug_worker(task_id: str, skill, scope: str, description: str, error_log: str):
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

    formatted_skills = [s if s.startswith('skill-') else f'skill-{s}' for s in skill_list]
    skill_clean = ', '.join(formatted_skills)
    scope = scope.lower() if scope.lower() in ('fe', 'be', 'both') else 'both'

    role_meta = {
        'fe': {
            'label': 'Frontend Debugger',
            'sub': 'webapp (React/TypeScript)',
            'workspace': get_fe_workspace(),
            'desc': 'Frontend React Debugger tại easysalon-webapp, chuyên sâu về Formik, Yup validation, API client và state.'
        },
        'be': {
            'label': 'Backend Debugger',
            'sub': 'api (.NET/C#)',
            'workspace': get_be_workspace(),
            'desc': 'Backend .NET / EF Core Debugger tại easysalon-api, chuyên sâu về Controller, DTO, LINQ query, MySQL và Transaction.'
        }
    }

    max_rounds = 2 if scope == 'both' else 1

    with state_lock:
        task_state = app_state['active_tasks'].get(task_id)
        if not task_state:
            task_state = {
                'task_id': task_id,
                'title': f"Fix bug: {description[:35]}" if description else f"Fix bug ({skill_clean})",
                'mode': 'fixbug',
                'is_running': True,
                'current_process': None,
                'active_round': 0,
                'total_rounds': max_rounds,
                'active_speaker': 'fe' if scope in ('fe', 'both') else 'be',
                'status_text': f"Kích hoạt Fix Bug theo skill '{skill_clean}'...",
                'session': {
                    'id': session_id,
                    'task_id': task_id,
                    'type': 'FIX_BUG',
                    'skill': skill_clean,
                    'scope': scope,
                    'description': description,
                    'error_log': error_log,
                    'total_rounds': max_rounds,
                    'turns': [],
                    'status': 'RUNNING',
                    'created_at': datetime.datetime.now().strftime('%H:%M:%S')
                }
            }
            app_state['active_tasks'][task_id] = task_state
        else:
            task_state['is_running'] = True
            task_state['mode'] = 'fixbug'
            task_state['total_rounds'] = max_rounds
            task_state['active_round'] = 0
            task_state['active_speaker'] = 'fe' if scope in ('fe', 'both') else 'be'
            task_state['status_text'] = f"Kích hoạt Fix Bug theo skill '{skill_clean}'..."
            task_state['session'] = {
                'id': session_id,
                'task_id': task_id,
                'type': 'FIX_BUG',
                'skill': skill_clean,
                'scope': scope,
                'description': description,
                'error_log': error_log,
                'total_rounds': max_rounds,
                'turns': [],
                'status': 'RUNNING',
                'created_at': datetime.datetime.now().strftime('%H:%M:%S')
            }

        app_state['is_running'] = True
        app_state['current_session'] = task_state['session']
        app_state['status_text'] = task_state['status_text']

    skills_doc_refs = " và ".join([f"'.agents/skills/{s}/SKILL.md'" for s in formatted_skills if s != 'skill-debug-fixbug'])
    extra_docs = f" và {skills_doc_refs}" if skills_doc_refs else ""

    history = []
    roles_to_run = ['fe', 'be'] if scope == 'both' else [scope]

    for round_idx, r_role in enumerate(roles_to_run, start=1):
        curr_info = role_meta[r_role]

        with state_lock:
            if not task_state['is_running']:
                break
            task_state['active_round'] = round_idx
            task_state['active_speaker'] = r_role
            task_state['status_text'] = f"[{curr_info['label']}] đang chẩn đoán và khoanh vùng lỗi..."
            app_state['status_text'] = task_state['status_text']

        context_from_previous = ""
        if round_idx > 1 and history:
            context_from_previous = f"\nKẾT QUẢ PHÂN TÍCH TỪ FRONTEND Ở BƯỚC TRƯỚC:\n{history[0]['content']}\n"

        slash_skills = []
        for s in formatted_skills:
            s_clean = s.strip()
            if not s_clean:
                continue
            if not s_clean.startswith('/'):
                s_clean = f"/{s_clean}"
            slash_skills.append(s_clean)
        skills_prefix = " ".join(slash_skills)

        prompt_parts = []
        if skills_prefix:
            prompt_parts.append(skills_prefix)

        if description.strip():
            prompt_parts.append(f"Mô tả hiện tượng lỗi / Triệu chứng:\n{description.strip()}")

        if error_log.strip():
            prompt_parts.append(f"Log lỗi / Stack trace / Console (nếu có):\n{error_log.strip()}")

        if context_from_previous.strip():
            prompt_parts.append(f"Kết quả phân tích từ bước trước:\n{context_from_previous.strip()}")

        prompt_body = "\n\n".join(prompt_parts)

        cmd = [agy_bin, '--dangerously-skip-permissions', '--mode', 'accept-edits', '--output-format', 'stream-json', '-p', prompt_body]
        turn_data = {
            'round': round_idx,
            'speaker': r_role,
            'label': curr_info['label'],
            'sub': curr_info['sub'],
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S'),
            'elapsed_sec': 0,
            'step_logs': [],
            'content': '',
            'is_streaming': True
        }
        with state_lock:
            if task_state.get('session'):
                task_state['session']['turns'].append(turn_data)

        response_text, elapsed = stream_process_turn(cmd, curr_info['workspace'], turn_data, timeout=360, task_state=task_state)
        history.append(turn_data)

    total_time = round(time.time() - start_time, 1)

    with state_lock:
        task_state['is_running'] = False
        task_state['active_speaker'] = ''
        task_state['status_text'] = 'Đã hoàn tất quy trình chẩn đoán & fix bug!'
        if task_state.get('session'):
            task_state['session']['status'] = 'COMPLETED'
            task_state['session']['total_duration_sec'] = total_time
        app_state['is_running'] = any(t.get('is_running') for t in app_state['active_tasks'].values())

    messages = load_messages()
    messages.append({
        'id': session_id,
        'task_id': task_id,
        'type': 'FIX_BUG',
        'title': task_state.get('title') or f"Fix bug ({skill_clean}): {description[:90]}",
        'status': 'COMPLETED',
        'target': scope,
        'module': skill_clean,
        'scope': scope,
        'created_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y'),
        'description': description,
        'total_duration_sec': total_time,
        'duration_sec': total_time,
        'turns': history
    })
    save_messages(messages)


# -------------------------------------------------------------
# DYNAMIC CODEBASE SCANNER (FE & BE AUTO-DISCOVERY PER BRANCH)
# -------------------------------------------------------------
CORE_MODULE_CONFIGS = [
    {
        'id': 'booking-bedroom',
        'title': 'Phòng & Sơ đồ giường (BedRoom)',
        'name': 'Phòng & Sơ đồ giường (BedRoom)',
        'category': 'core',
        'skill': 'skill-booking-bedroom',
        'primary_route': '/bed-room-position',
        'primary_resource': 'src/scripts/restful/resources/bed-room/bedRoomPosition.ts',
        'fe_routes': [
            'src/scripts/routes/setting/bed-room',
            'src/scripts/routes/setting/bed-room-manager'
        ],
        'fe_forms': [
            'src/scripts/forms/bed-room',
            'src/scripts/forms/bed-room-manager'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/bed-room/bedRoomPosition.ts',
            'src/scripts/restful/resources/bed-room/bedRoomManager.ts'
        ],
        'fe_dirs': ['bed-room'],
        'be_controllers': ['BedRoomPositionController', 'BedRoomManagerController'],
        'default_desc': 'Quản lý bản đồ sơ đồ giường, trạng thái ghế bận/trống realtime, phân bổ dịch vụ và cấu hình vị trí giường.'
    },
    {
        'id': 'pos-cashier',
        'title': 'Thu ngân & Bán hàng (POS / Invoice)',
        'name': 'Thu ngân & Bán hàng (POS / Invoice)',
        'category': 'core',
        'skill': 'skill-pos-cashier',
        'primary_route': '/invoices',
        'primary_resource': 'src/scripts/restful/resources/invoice.ts',
        'fe_routes': [
            'src/scripts/routes/cashier',
            'src/scripts/routes/invoice'
        ],
        'fe_forms': [
            'src/scripts/forms/invoice'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/invoice.ts',
            'src/scripts/restful/resources/invoiceDetail.ts',
            'src/scripts/restful/resources/invoiceDetailProductUsage.ts'
        ],
        'fe_dirs': ['invoice', 'invoice-detail'],
        'be_controllers': ['InvoicesController', 'CashiersController', 'InvoiceStaffArrangementsController'],
        'default_desc': 'Màn hình thu ngân POS, chọn dịch vụ/sản phẩm/combo, áp khuyến mãi, chia bill, in phiếu hóa đơn.'
    },
    {
        'id': 'calendar-schedule',
        'title': 'Lịch hẹn & Ca làm việc (Booking / Calendar)',
        'name': 'Lịch hẹn & Ca làm việc (Booking / Calendar)',
        'category': 'core',
        'skill': 'skill-calendar-schedule',
        'primary_route': '/bookings',
        'primary_resource': 'src/scripts/restful/resources/booking/booking.ts',
        'fe_routes': [
            'src/scripts/routes/booking',
            'src/scripts/routes/setting/booking-site'
        ],
        'fe_forms': [
            'src/scripts/forms/booking'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/booking/booking.ts',
            'src/scripts/restful/resources/bookingPlatformLimit.ts',
            'src/scripts/restful/resources/bookingPortalSetting.ts'
        ],
        'fe_dirs': ['booking', 'booking-detail'],
        'be_controllers': ['BookingsController', 'BookingAvailableStaffsController'],
        'default_desc': 'Lịch biểu đặt hẹn theo nhân viên, khung giờ, check-in khách đến salon và đẩy vào danh sách chờ.'
    },
    {
        'id': 'customer-crm',
        'title': 'Khách hàng & Hạng thẻ VIP (Customer CRM)',
        'name': 'Khách hàng & Hạng thẻ VIP (Customer CRM)',
        'category': 'core',
        'skill': 'skill-customer-crm',
        'primary_route': '/customers',
        'primary_resource': 'src/scripts/restful/resources/customer/customer.ts',
        'fe_routes': [
            'src/scripts/routes/customer',
            'src/scripts/routes/setting/customer-rank',
            'src/scripts/routes/setting/customer-group',
            'src/scripts/routes/setting/customer-source',
            'src/scripts/routes/setting/customer-channel'
        ],
        'fe_forms': [
            'src/scripts/forms/customer',
            'src/scripts/forms/customer-debt-transaction',
            'src/scripts/forms/customer-rank'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/customer/customer.ts',
            'src/scripts/restful/resources/customer/customerDebt.ts',
            'src/scripts/restful/resources/customer/customerRank.ts'
        ],
        'fe_dirs': ['customer', 'customer-care-history', 'customer-channel'],
        'be_controllers': ['CustomersController', 'CustomerDebtsController', 'CustomerRanksController'],
        'default_desc': 'Hồ sơ khách hàng, phân hạng thẻ VIP, tích lũy điểm thưởng, quản lý công nợ và lịch sử làm đẹp.'
    },
    {
        'id': 'warehouse-inventory',
        'title': 'Kho hàng & Nhập xuất tồn (Warehouse)',
        'name': 'Kho hàng & Nhập xuất tồn (Warehouse)',
        'category': 'core',
        'skill': 'skill-warehouse-inventory',
        'primary_route': '/warehouses',
        'primary_resource': 'src/scripts/restful/resources/warehouse/warehouse.ts',
        'fe_routes': [
            'src/scripts/routes/product-service/warehouse',
            'src/scripts/routes/product-service/warehouse-detail'
        ],
        'fe_forms': [
            'src/scripts/forms/warehouse-transaction',
            'src/scripts/forms/warehouse-transaction-detail'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/warehouse/warehouse.ts',
            'src/scripts/restful/resources/warehouse/warehouseTransaction.ts',
            'src/scripts/restful/resources/warehouse/warehouseTransactionDetail.ts'
        ],
        'fe_dirs': ['warehouse-transaction'],
        'be_controllers': ['WarehousesController', 'WarehouseTransactionsController', 'V2_WarehouseTransactionDetailsController'],
        'default_desc': 'Xuất nhập tồn, trừ kho hàng bán & định mức tiêu hao nguyên vật liệu, kiểm kê, cảnh báo tồn tối thiểu.'
    },
    {
        'id': 'commission-setup',
        'title': 'Hoa hồng & Chiết khấu KTV (Commission)',
        'name': 'Hoa hồng & Chiết khấu KTV (Commission)',
        'category': 'core',
        'skill': 'skill-commission-setup',
        'primary_route': '/commission-arrangements',
        'primary_resource': 'src/scripts/restful/resources/commissionArrange.ts',
        'fe_routes': [
            'src/scripts/routes/setting/commission',
            'src/scripts/routes/setting/commission-new'
        ],
        'fe_forms': [
            'src/scripts/forms/commission'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/commissionArrange.ts',
            'src/scripts/restful/resources/commission/commissionProduct.ts',
            'src/scripts/restful/resources/commission/commissionService.ts'
        ],
        'fe_dirs': ['commission-setup', 'commission-product', 'commission-service', 'commission-cashcard'],
        'be_controllers': ['CommissionArrangementsController', 'CommissionProductsController'],
        'default_desc': 'Cấu hình hoa hồng theo bậc nhân viên, dịch vụ, bán sản phẩm, làm tour; tính thưởng tức thì theo bill.'
    },
    {
        'id': 'revenue-expenditure',
        'title': 'Thu chi & Sổ quỹ tiền mặt (Cashbook)',
        'name': 'Thu chi & Sổ quỹ tiền mặt (Cashbook)',
        'category': 'core',
        'skill': 'skill-revenue-expenditure',
        'primary_route': '/cash-book-transactions',
        'primary_resource': 'src/scripts/restful/resources/cashbook/cashbookTransaction.ts',
        'fe_routes': [
            'src/scripts/routes/revenue-expenditure'
        ],
        'fe_forms': [
            'src/scripts/forms/cashbook-transaction',
            'src/scripts/forms/cashbook-setting'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/cashbook/cashbookTransaction.ts',
            'src/scripts/restful/resources/cashbook/cashbookSetting.ts'
        ],
        'fe_dirs': ['cashbook-transaction', 'cashbook-setting'],
        'be_controllers': ['CashBookTransactionsController', 'CashBooksController'],
        'default_desc': 'Tổng hợp phiếu thu bán lẻ, phiếu chi nhập kho, phiếu chi lương; theo dõi dòng tiền mặt và ngân hàng.'
    },
    {
        'id': 'service-package-combo',
        'title': 'Gói liệu trình & Thẻ combo (Package)',
        'name': 'Gói liệu trình & Thẻ combo (Package)',
        'category': 'core',
        'skill': 'skill-service-package-combo',
        'primary_route': '/customer-packages',
        'primary_resource': 'src/scripts/restful/resources/package/package.ts',
        'fe_routes': [
            'src/scripts/routes/product-service/package',
            'src/scripts/routes/product-service/treatment'
        ],
        'fe_forms': [
            'src/scripts/forms/package',
            'src/scripts/forms/customer-treatment'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/package/package.ts',
            'src/scripts/restful/resources/customer/customerPackage.ts',
            'src/scripts/restful/resources/customer-treatment/customerTreatment.ts'
        ],
        'fe_dirs': ['package', 'customer-treatment'],
        'be_controllers': ['CustomerPackagesController', 'CustomerTreatmentController', 'PackagesController'],
        'default_desc': 'Bán gói liệu trình nhiều buổi, trừ buổi tự động khi khách làm tại giường, gia hạn thẻ liệu trình.'
    },
    {
        'id': 'tax-einvoice',
        'title': 'Hóa đơn điện tử (E-Invoice)',
        'name': 'Hóa đơn điện tử (E-Invoice)',
        'category': 'core',
        'skill': 'skill-tax-einvoice',
        'primary_route': '/electronic-invoices',
        'primary_resource': 'src/scripts/restful/resources/e-invoice/electronicInvoice.ts',
        'fe_routes': [
            'src/scripts/routes/tax-accounting',
            'src/scripts/routes/setting/electronic-invoice'
        ],
        'fe_forms': [
            'src/scripts/forms/electronic-invoice',
            'src/scripts/forms/tax-accounting'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/e-invoice/electronicInvoice.ts',
            'src/scripts/restful/resources/e-invoice/electronicInvoicePartner.ts',
            'src/scripts/restful/resources/tax-accounting/tax-declaration-management/taxPeriod.ts'
        ],
        'fe_dirs': ['electronic-invoice'],
        'be_controllers': ['ElectronicInvoicesController', 'ElectronicInvoicePartnersController'],
        'default_desc': 'Kết nối VNPT, Viettel, MISA phát hành hóa đơn điện tử hợp lệ theo quy định của Tổng cục Thuế.'
    },
    {
        'id': 'payroll-timesheet',
        'title': 'Chấm công & Bảng lương (Payroll)',
        'name': 'Chấm công & Bảng lương (Payroll)',
        'category': 'core',
        'skill': 'skill-payroll-timesheet',
        'primary_route': '/time-sheets',
        'primary_resource': 'src/scripts/restful/resources/time-sheets/timeSheet.ts',
        'fe_routes': [
            'src/scripts/routes/worker-management'
        ],
        'fe_forms': [
            'src/scripts/forms/time-sheet',
            'src/scripts/forms/worker'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/time-sheets/timeSheet.ts',
            'src/scripts/restful/resources/time-sheets/timeSheetSetting.ts',
            'src/scripts/restful/resources/worker/worker.ts'
        ],
        'fe_dirs': ['time-sheet'],
        'be_controllers': ['TimeSheetsController'],
        'default_desc': 'Tổng hợp ngày công, ca kíp, phạt đi muộn và tiền hoa hồng trong tháng để chốt phiếu lương nhân viên.'
    },
    {
        'id': 'report-analytics',
        'title': 'Báo cáo & Thống kê (Analytics)',
        'name': 'Báo cáo & Thống kê (Analytics)',
        'category': 'core',
        'skill': 'skill-report-analytics',
        'primary_route': '/report',
        'primary_resource': 'src/scripts/restful/resources/report/reportRevenue.ts',
        'fe_routes': [
            'src/scripts/routes/reports'
        ],
        'fe_forms': [],
        'fe_resources': [
            'src/scripts/restful/resources/report/reportRevenue.ts',
            'src/scripts/restful/resources/report/reportInvoice.ts',
            'src/scripts/restful/resources/report/reportCustomer.ts'
        ],
        'fe_dirs': ['report'],
        'be_controllers': ['ReportController', 'InvoiceReportController'],
        'default_desc': 'Dashboard doanh thu bán lẻ, tỷ lệ lấp đầy giường, hiệu suất kỹ thuật viên và lợi nhuận gộp.'
    }
]

# -------------------------------------------------------------
# VERIFIED 11-MODULE ARCHITECTURE CATALOG (EasySalon WebApp & API)
# -------------------------------------------------------------
MODULE_VERIFIED_DATA = {
    'booking-bedroom': {
        'screens': ['RouteBedRoomPosition.tsx', 'RouteBedRoomManager.tsx'],
        'components': ['BedRoomContainer.tsx', 'BedRoomPositionTable.tsx', 'BedRoomPositionForm.tsx'],
        'resources': ['bedRoomPosition.ts', 'bedRoomManager.ts', 'booking.ts'],
        'route': '/bed-room-position',
        'endpoints': [
            {'method': 'GET', 'path': '/bed-room-position', 'note': 'Lấy danh sách vị trí giường'},
            {'method': 'POST', 'path': '/bed-room-position', 'note': 'Tạo vị trí giường mới'},
            {'method': 'PUT', 'path': '/bed-room-position/{id}', 'note': 'Cập nhật cấu hình giường'},
            {'method': 'DELETE', 'path': '/bed-room-position/{id}', 'note': 'Xóa vị trí giường'}
        ],
        'controller': 'BedRoomPositionController',
        'service': 'BedRoomPositionService',
        'manager': 'BedRoomPositionManager',
        'entities': ['BedRoomPosition', 'BedRoom']
    },
    'pos-cashier': {
        'screens': ['RouteCashier.tsx', 'RouteInvoiceList.tsx'],
        'components': ['InvoiceContent.tsx', 'InvoiceDetails.tsx', 'InvoiceFooter.tsx'],
        'resources': ['invoice.ts', 'invoiceDetail.ts'],
        'route': '/invoices',
        'endpoints': [
            {'method': 'GET', 'path': '/invoices', 'note': 'Tra cứu danh sách hóa đơn'},
            {'method': 'POST', 'path': '/invoices', 'note': 'Khởi tạo bill mới tại quầy'},
            {'method': 'PUT', 'path': '/invoices/pay-invoice/{id}', 'note': 'Thanh toán hóa đơn đa phương thức'},
            {'method': 'PUT', 'path': '/cashiers/invoice/{invoiceId}', 'note': 'Cập nhật giỏ hàng thu ngân POS'}
        ],
        'controller': 'InvoicesController',
        'service': 'InvoiceService',
        'manager': 'InvoiceManager',
        'entities': ['Invoice', 'InvoiceDetail', 'InvoicePayment']
    },
    'calendar-schedule': {
        'screens': ['RouteBooking.tsx'],
        'components': ['BookingsFetcher.tsx', 'BookingFormControl.tsx', 'BookingDetailServiceItem.tsx'],
        'resources': ['booking.ts', 'bookingAvailableStaff.ts'],
        'route': '/bookings',
        'endpoints': [
            {'method': 'GET', 'path': '/bookings', 'note': 'Lấy danh sách lịch hẹn theo khung giờ'},
            {'method': 'POST', 'path': '/bookings', 'note': 'Tạo lịch hẹn mới'},
            {'method': 'PUT', 'path': '/bookings/{id}', 'note': 'Cập nhật thông tin / đổi giờ hẹn'},
            {'method': 'PUT', 'path': '/bookings/checkin/{id}', 'note': 'Check-in khách đến salon'}
        ],
        'controller': 'BookingsController',
        'service': 'BookingService',
        'manager': 'BookingManager',
        'entities': ['Booking', 'BookingDetail', 'BookingDetailStaff']
    },
    'customer-crm': {
        'screens': ['RouteCustomer.tsx', 'RouteCustomerDetail.tsx'],
        'components': ['CustomerTable.tsx', 'CustomerFilter.tsx', 'CustomerFormButton.tsx'],
        'resources': ['customer.ts', 'customerDebt.ts', 'customerRank.ts'],
        'route': '/customers',
        'endpoints': [
            {'method': 'GET', 'path': '/customers', 'note': 'Tìm kiếm và phân trang hồ sơ khách'},
            {'method': 'POST', 'path': '/customers', 'note': 'Tạo hồ sơ khách hàng mới (Unicode FormC)'},
            {'method': 'PUT', 'path': '/customers/{id}', 'note': 'Cập nhật thông tin khách hàng'},
            {'method': 'GET', 'path': '/customers/debts', 'note': 'Tra cứu công nợ khách hàng'}
        ],
        'controller': 'CustomersController',
        'service': 'CustomerService',
        'manager': 'CustomerManager',
        'entities': ['Customer', 'CustomerDebt', 'CustomerRank']
    },
    'warehouse-inventory': {
        'screens': ['RouteWarehouse.tsx', 'RouteWarehouseDetail.tsx'],
        'components': ['WarehouseTransactionTable.tsx', 'WarehouseTransactionForm.tsx'],
        'resources': ['warehouse.ts', 'warehouseTransaction.ts'],
        'route': '/warehouses',
        'endpoints': [
            {'method': 'GET', 'path': '/warehouses', 'note': 'Tồn kho thực tế theo sản phẩm'},
            {'method': 'GET', 'path': '/warehouses/product/inventories', 'note': 'Tồn kho sản phẩm theo chi nhánh'},
            {'method': 'GET', 'path': '/warehouse-transactions', 'note': 'Danh sách phiếu nhập / xuất kho'},
            {'method': 'POST', 'path': '/warehouse-transactions', 'note': 'Tạo phiếu nhập/xuất kho'}
        ],
        'controller': 'WarehousesController',
        'service': 'WarehouseService',
        'manager': 'WarehouseManager',
        'entities': ['Warehouse', 'WarehouseTransaction', 'WarehouseTransactionDetail']
    },
    'commission-setup': {
        'screens': ['RouteCommission.tsx'],
        'components': ['CommissionTableContainer.tsx', 'CommissionServiceFormControl.tsx', 'CommissionProductFormControl.tsx'],
        'resources': ['commissionArrange.ts', 'commissionService.ts', 'commissionProduct.ts'],
        'route': '/commission-arrangements',
        'endpoints': [
            {'method': 'GET', 'path': '/commission-arrangements', 'note': 'Tra cứu hoa hồng theo hóa đơn'},
            {'method': 'PUT', 'path': '/commission-arrangements/{id}', 'note': 'Lưu chia hoa hồng KTV cho hóa đơn'},
            {'method': 'GET', 'path': '/commission-services', 'note': 'Cấu hình hoa hồng dịch vụ'},
            {'method': 'PUT', 'path': '/commission-products', 'note': 'Lưu cấu hình hoa hồng sản phẩm'}
        ],
        'controller': 'CommissionArrangementsController',
        'service': 'CommissionArrangementService',
        'manager': 'CommissionArrangementManager',
        'entities': ['CommissionArrangement', 'CommissionService', 'CommissionProduct']
    },
    'revenue-expenditure': {
        'screens': ['RouteCashbook.tsx', 'RouteBankBook.tsx'],
        'components': ['CashbookTransactionTable.tsx', 'CashbookTransactionFormButton.tsx'],
        'resources': ['cashbookTransaction.ts', 'cashbookSetting.ts'],
        'route': '/cash-book-transactions',
        'endpoints': [
            {'method': 'GET', 'path': '/cash-book-transactions', 'note': 'Danh sách phiếu thu / phiếu chi'},
            {'method': 'POST', 'path': '/cash-book-transactions', 'note': 'Lập phiếu thu chi mới'},
            {'method': 'PUT', 'path': '/cash-book-transactions/{id}', 'note': 'Cập nhật chứng từ thu chi'},
            {'method': 'GET', 'path': '/cash-books', 'note': 'Số dư và tồn quỹ tiền mặt'}
        ],
        'controller': 'CashBookTransactionsController',
        'service': 'CashBookTransactionService',
        'manager': 'CashBookTransactionManager',
        'entities': ['CashBookTransaction', 'CashBook', 'BankBook']
    },
    'service-package-combo': {
        'screens': ['RoutePackage.tsx', 'RouteCustomerTreatment.tsx'],
        'components': ['PackageTable.tsx', 'CustomerTreatmentUseForm.tsx'],
        'resources': ['package.ts', 'customerTreatment.ts', 'customerPackage.ts'],
        'route': '/customer-packages',
        'endpoints': [
            {'method': 'GET', 'path': '/customer-packages', 'note': 'Danh sách các gói combo và thẻ liệu trình'},
            {'method': 'POST', 'path': '/customer-packages', 'note': 'Tạo gói dịch vụ combo mới'},
            {'method': 'GET', 'path': '/customer-treatments/by-customer/{customerId}', 'note': 'Tra cứu số buổi liệu trình của khách'},
            {'method': 'POST', 'path': '/customer-treatments/{id}/use', 'note': 'Trừ buổi liệu trình khi làm dịch vụ tại giường'}
        ],
        'controller': 'CustomerPackagesController',
        'service': 'CustomerPackageService',
        'manager': 'CustomerPackageManager',
        'entities': ['CustomerPackage', 'CustomerTreatment', 'Package']
    },
    'tax-einvoice': {
        'screens': ['RouteEInvoiceList.tsx', 'RouteElectronicInvoicePartner.tsx'],
        'components': ['ElectronicInvoiceTable.tsx', 'ElectronicInvoiceHandleButton.tsx'],
        'resources': ['electronicInvoice.ts', 'electronicInvoicePartner.ts'],
        'route': '/electronic-invoices',
        'endpoints': [
            {'method': 'GET', 'path': '/electronic-invoices', 'note': 'Danh sách hóa đơn điện tử đã phát hành'},
            {'method': 'POST', 'path': '/electronic-invoices', 'note': 'Ký số và phát hành HĐĐT chính thức'},
            {'method': 'POST', 'path': '/electronic-invoices/draft', 'note': 'Xuất bản HĐĐT nháp (Draft)'},
            {'method': 'GET', 'path': '/electronic-invoice-partners', 'note': 'Danh sách kết nối đối tác VNPT, Viettel, MISA'}
        ],
        'controller': 'ElectronicInvoicesController',
        'service': 'ElectronicInvoiceService',
        'manager': 'ElectronicInvoiceManager',
        'entities': ['ElectronicInvoice', 'ElectronicInvoicePartner']
    },
    'payroll-timesheet': {
        'screens': ['RouteTimeSheet.tsx', 'RoutePayroll.tsx'],
        'components': ['TimeSheetContainer.tsx', 'TimeSheetActionFormButton.tsx'],
        'resources': ['timeSheet.ts', 'worker.ts'],
        'route': '/time-sheets',
        'endpoints': [
            {'method': 'GET', 'path': '/time-sheets', 'note': 'Bảng chấm công tổng hợp trong kỳ'},
            {'method': 'GET', 'path': '/time-sheets/overview', 'note': 'Tổng kết ngày công, đi muộn, về sớm'},
            {'method': 'POST', 'path': '/time-sheets', 'note': 'Chốt công thủ công cho nhân viên'},
            {'method': 'GET', 'path': '/worker-advance-payments', 'note': 'Danh sách tạm ứng lương nhân viên'}
        ],
        'controller': 'TimeSheetsController',
        'service': 'TimeSheetService',
        'manager': 'TimeSheetManager',
        'entities': ['TimeSheet', 'Worker', 'WorkerAdvancePayment']
    },
    'report-analytics': {
        'screens': ['RouteReportRevenue.tsx', 'RouteReportCustomer.tsx'],
        'components': ['ReportRevenueInvoiceDetail.tsx', 'ReportRevenueServiceDetail.tsx'],
        'resources': ['reportRevenue.ts', 'reportCustomer.ts'],
        'route': '/report',
        'endpoints': [
            {'method': 'GET', 'path': '/report/revenue-invoice-detail', 'note': 'Chi tiết doanh thu theo hóa đơn'},
            {'method': 'GET', 'path': '/report/revenue-service-detail', 'note': 'Doanh thu phân tích theo dịch vụ'},
            {'method': 'GET', 'path': '/report/revenue-payment-method-general', 'note': 'Cơ cấu doanh thu theo phương thức thanh toán'},
            {'method': 'GET', 'path': '/report/customer-frequency', 'note': 'Tần suất khách quay lại salon'}
        ],
        'controller': 'ReportController',
        'service': 'ReportService',
        'manager': 'ReportManager',
        'entities': ['Invoice View', 'Customer View', 'Staff View']
    }
}


def get_git_info(workspace):
    try:
        branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, timeout=3).decode().strip()
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=workspace, timeout=3).decode().strip()
        return branch or 'detached', commit
    except Exception:
        return 'unknown', 'unknown'


def parse_resource_file(file_path):
    """
    Trích xuất toàn bộ tên hàm/property Resource, HTTP Method và URL endpoint thực tế từ file Resource TypeScript.
    Phân tích cú pháp:
    - [function_name]: new Resource<...>({ method: '...', url: '...' })
    - const/let/var [function_name] = new Resource<...>({ method: '...', url: '...' })
    """
    endpoints = []
    if not os.path.isfile(file_path):
        return endpoints
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()

        matches = re.finditer(
            r'(?:(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*|([a-zA-Z0-9_$]+)\s*:\s*)?new\s+Resource(?:<[\s\S]*?>)?\s*\(\s*\{([\s\S]*?)\}\s*\)',
            content
        )
        for m in matches:
            fe_func = m.group(1) or m.group(2) or ''
            body = m.group(3)
            url_m = re.search(r'url\s*:\s*[`\'"]([^`\'"]+)[`\'"]', body)
            if not url_m:
                continue
            raw_url = url_m.group(1).strip()

            # Chuẩn hóa URL path
            if raw_url.startswith('./'):
                url = raw_url[1:]
            elif not raw_url.startswith('/'):
                url = '/' + raw_url
            else:
                url = raw_url
            url = url.replace('/./', '/')
            url = re.sub(r'/+', '/', url)
            url = re.sub(r':([a-zA-Z_0-9]+)', r'{\1}', url)

            method_m = re.search(r'method\s*:\s*[\'"](GET|POST|PUT|DELETE|PATCH)[\'"]', body, re.IGNORECASE)
            method = method_m.group(1).upper() if method_m else 'GET'

            if not fe_func:
                fe_func = infer_fe_func(method, url)

            note = ''
            if '{id}' in url:
                if method == 'GET': note = 'Lấy chi tiết theo ID'
                elif method == 'PUT': note = 'Cập nhật bản ghi theo ID'
                elif method == 'DELETE': note = 'Xóa bản ghi theo ID'
            elif method == 'GET': note = 'Lấy danh sách dữ liệu'
            elif method == 'POST': note = 'Tạo mới bản ghi'
            elif method == 'PUT': note = 'Cập nhật thông tin'
            elif method == 'DELETE': note = 'Xóa thông tin'

            if not any(e['method'] == method and e['path'] == url for e in endpoints):
                endpoints.append({'method': method, 'path': url, 'fe_func': fe_func, 'note': note})
    except Exception:
        pass
    return endpoints


def scan_fe_directory(base_dir, target):
    """
    Quét động cấu trúc mã nguồn Frontend (React) từ easysalon-webapp:
    - Screens: Các file Route*.tsx, Router*.tsx từ src/scripts/routes/
    - Components: Các React component tương tác từ routes/ và forms/
    - Resources: Định nghĩa RESTful Resource từ src/scripts/restful/resources/
    - Endpoints: Danh sách API contract thực tế với HTTP verb và route
    """
    if isinstance(target, dict):
        cfg = target
        routes_dirs = cfg.get('fe_routes', [])
        forms_dirs = cfg.get('fe_forms', [])
        res_targets = cfg.get('fe_resources', [])
        primary_res_preset = cfg.get('primary_resource', '')
        primary_route_preset = cfg.get('primary_route', '')
        mod_id = cfg.get('id', '')
    elif isinstance(target, (list, tuple)):
        routes_dirs = [f'src/scripts/routes/{d}' for d in target] + [f'src/scripts/business/{d}' for d in target]
        forms_dirs = [f'src/scripts/forms/{d}' for d in target]
        res_targets = [f'src/scripts/restful/resources/{d}' for d in target] + [f'src/scripts/restful/resources/{d}.ts' for d in target]
        primary_res_preset = ''
        primary_route_preset = ''
        mod_id = target[0] if target else 'module'
    else:
        routes_dirs, forms_dirs, res_targets = [], [], []
        primary_res_preset, primary_route_preset, mod_id = '', '', 'module'

    screens = []
    components = []
    resources = []
    found_paths = []
    imports = set()
    exports = set()
    endpoints = []
    primary_resource = primary_res_preset
    primary_path = ''

    # 1. Quét Routes
    for r_dir in routes_dirs:
        full_dir = os.path.join(base_dir, r_dir)
        if os.path.exists(full_dir):
            if not primary_path:
                primary_path = r_dir
            found_paths.append(r_dir)
            for root, _, files in os.walk(full_dir):
                for f in sorted(files):
                    if f.endswith(('.tsx', '.ts')) and not f.startswith('index'):
                        file_path = os.path.join(root, f)
                        if f.startswith(('Route', 'Router')):
                            screens.append(f)
                        else:
                            components.append(f)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                                content = fp.read()
                                for m in re.finditer(r"from\s+['\"](@/[^'\"]+|libs/[^'\"]+)['\"]", content):
                                    imports.add(m.group(1))
                                for m in re.finditer(r"export\s+(?:default\s+)?(?:const|function|class|interface|type)\s+([A-Za-z0-9_]+)", content):
                                    exports.add(m.group(1))
                        except Exception:
                            pass

    # 2. Quét Forms
    for f_dir in forms_dirs:
        full_dir = os.path.join(base_dir, f_dir)
        if os.path.exists(full_dir):
            found_paths.append(f_dir)
            for root, _, files in os.walk(full_dir):
                for f in sorted(files):
                    if f.endswith(('.tsx', '.ts')) and not f.startswith('index'):
                        file_path = os.path.join(root, f)
                        components.append(f)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                                content = fp.read()
                                for m in re.finditer(r"from\s+['\"](@/[^'\"]+|libs/[^'\"]+)['\"]", content):
                                    imports.add(m.group(1))
                                for m in re.finditer(r"export\s+(?:default\s+)?(?:const|function|class|interface|type)\s+([A-Za-z0-9_]+)", content):
                                    exports.add(m.group(1))
                        except Exception:
                            pass

    # 3. Quét Resources & Trích xuất Endpoints
    for res_target in res_targets:
        full_target = os.path.join(base_dir, res_target)
        if os.path.isfile(full_target):
            rel_res = res_target
            if not primary_resource:
                primary_resource = rel_res
            resources.append(os.path.basename(full_target))
            endpoints.extend(parse_resource_file(full_target))
        elif os.path.isdir(full_target):
            for root, _, files in os.walk(full_target):
                for f in sorted(files):
                    if f.endswith('.ts') and not f.startswith('index'):
                        fpath = os.path.join(root, f)
                        rel_res = os.path.relpath(fpath, base_dir)
                        if not primary_resource:
                            primary_resource = rel_res
                        resources.append(f)
                        endpoints.extend(parse_resource_file(fpath))

    screens = sorted(list(set(screens)))
    components = sorted(list(set(components)))
    resources = sorted(list(set(resources)))

    if primary_route_preset:
        primary_route = primary_route_preset
    elif endpoints:
        primary_route = endpoints[0]['path']
    else:
        primary_route = f'/{mod_id}'

    primary_clean = '/' + primary_route.strip('/').split('/')[0]
    def ep_rank(ep):
        p = ep['path']
        m = ep['method']
        score = 10
        if p.rstrip('/') == primary_clean:
            if m == 'GET': score = 1
            elif m == 'POST': score = 2
        elif p.rstrip('/') == f'{primary_clean}/{{id}}':
            if m == 'PUT': score = 3
            elif m == 'DELETE': score = 4
            elif m == 'GET': score = 5
        return (score, p, m)

    sorted_endpoints = sorted(endpoints, key=ep_rank)

    return {
        'screens': screens,
        'components': components,
        'resources': resources,
        'endpoints': sorted_endpoints,
        'route': primary_route,
        'paths': found_paths,
        'path': primary_path or (found_paths[0] if found_paths else f'src/scripts/routes/{mod_id}'),
        'resource': primary_resource or f'src/scripts/restful/resources/{mod_id}.ts',
        'imports': sorted(list(imports))[:8],
        'exports': sorted(list(exports))[:8]
    }


def to_kebab_case(s):
    """Converts PascalCase / CamelCase string to kebab-case."""
    if not s:
        return ''
    s = re.sub(r'(?:Base)?Controller$', '', s)
    s = re.sub(r'^V\d+_', '', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', s).lower()
    return s


def resolve_controller_route(content, controller_name):
    """
    Extracts and resolves base route from ASP.NET Core controller C# content.
    Handles:
    - [Route("path")]
    - [Route("[controller]")] -> replaces with kebab-case controller name
    - Multiple [Route] attributes (filters obsolete routes, selects kebab-case)
    """
    route_matches = re.findall(r'\[Route\("([^"]+)"\)(?:\s*//\s*(Obsolete))?', content, re.IGNORECASE)
    if route_matches:
        valid_routes = [r[0] for r in route_matches if not r[1]]
        if not valid_routes:
            valid_routes = [r[0] for r in route_matches]

        kebab_candidates = [r for r in valid_routes if '-' in r or r.islower()]
        chosen_route = kebab_candidates[0] if kebab_candidates else valid_routes[0]

        if '[controller]' in chosen_route.lower():
            kebab_cname = to_kebab_case(controller_name)
            chosen_route = re.sub(r'\[controller\]', kebab_cname, chosen_route, flags=re.IGNORECASE)
        elif not chosen_route.startswith('/') and not chosen_route.startswith('api/'):
            if chosen_route.isalnum() and any(c.isupper() for c in chosen_route):
                chosen_route = to_kebab_case(chosen_route)

        return chosen_route.strip('/')

    return to_kebab_case(controller_name)


def generate_endpoint_note(action_name, verb, path):
    """Generates natural, accurate Vietnamese descriptions for API endpoints."""
    act = action_name.lower()
    if 'cancel' in act:
        return 'Hủy trạng thái giao dịch'
    if 'export' in act:
        return 'Xuất báo cáo dữ liệu Excel'
    if 'print' in act:
        return 'Dữ liệu in chứng từ / phiếu'
    if 'draft' in act:
        return 'Tạo bản ghi nháp (Draft)'
    if 'preview' in act:
        return 'Xem trước mẫu chứng từ'
    if 'revenue' in act:
        return 'Báo cáo phân tích doanh thu'
    if 'checkin' in act:
        return 'Khách check-in tại quầy'
    if 'nearest' in act:
        return 'Lấy lịch hẹn gần nhất'
    if 'search' in act or 'bymobile' in act:
        return 'Tìm kiếm nhanh theo từ khóa / SĐT'
    if 'group' in act:
        return 'Tổng hợp theo nhóm danh mục'
    if 'overview' in act:
        return 'Báo cáo tổng quan số liệu'
    if 'pay' in act and 'paymentmethod' not in act:
        return 'Thanh toán giao dịch hóa đơn'

    if verb == 'GET':
        if '{id}' in path or act.endswith('byid'):
            return 'Xem chi tiết theo mã ID'
        if 'bycustomer' in act or 'by-customer' in path:
            return 'Tra cứu lịch sử theo khách hàng'
        return 'Truy vấn danh sách dữ liệu'
    elif verb == 'POST':
        return 'Tạo mới bản ghi'
    elif verb == 'PUT':
        if '{id}' in path:
            return 'Cập nhật thông tin bản ghi'
        return 'Cập nhật dữ liệu'
    elif verb == 'DELETE':
        return 'Xóa bản ghi khỏi hệ thống'
    return f'{action_name} action'


def extract_action_endpoints(content, base_route):
    """
    Extracts HTTP verb attributes, action method names, and constructs genuine endpoint paths.
    Eliminates artificial /{route}/{action_name} concatenation.
    """
    action_pattern = re.compile(
        r'\[Http(Get|Post|Put|Delete|Patch)(?:\(\s*["\']([^"\']*)["\']\s*\))?[^\]]*\]'
        r'(?:[\s\r\n]*\[[^\]]+\])*'
        r'[\s\r\n]*public\s+(?:async\s+)?(?:Task<)?([^\s>]+)>?\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)',
        re.MULTILINE
    )

    endpoints = []
    seen = set()

    for m in action_pattern.finditer(content):
        verb = m.group(1).upper()
        tpl = (m.group(2) or '').strip()
        action_name = m.group(4)

        # Resolve true path template without method name concatenation
        if not tpl:
            path = '/' + base_route.strip('/')
        elif tpl.startswith('/') or tpl.startswith('~/'):
            path = '/' + tpl.lstrip('~/')
        else:
            path = '/' + base_route.strip('/') + '/' + tpl.strip('/')

        path = re.sub(r':([a-zA-Z_0-9]+)', r'{\1}', path)
        if '[controller]' in path.lower():
            path = re.sub(r'\[controller\]', base_route.strip('/'), path, flags=re.IGNORECASE)

        key = (verb, path)
        if key in seen:
            continue
        seen.add(key)

        note = generate_endpoint_note(action_name, verb, path)
        endpoints.append({
            'method': verb,
            'path': path,
            'action': action_name,
            'be_action': action_name,
            'note': note
        })

    return endpoints


def trace_downstream_chain(base_dir, controller_name, controller_content, injections):
    """
    Traces Controller -> ApplicationService<T> -> Domain Manager -> Entity
    from the .NET project layout in SALON_HAIR_CORE and SALON_HAIR_ENTITY.
    """
    base_name = controller_name.replace('Controller', '')
    base_name = re.sub(r'^V\d+_', '', base_name)
    singular = base_name.rstrip('s') if base_name.endswith('s') and not base_name.endswith('ss') else base_name

    candidates = [f"{base_name}Service", f"{singular}Service", f"{base_name}Manager", f"{singular}Manager"]
    service_name = None
    for cand in candidates:
        if cand in injections:
            service_name = cand
            break
    if not service_name:
        for cand in candidates:
            if cand.endswith('Service') and glob.glob(os.path.join(base_dir, 'SALON_HAIR_CORE/Services/**/' + cand + '.cs'), recursive=True):
                service_name = cand
                break
    if not service_name:
        for inj in injections:
            if inj.endswith('Service') and inj not in ('UserService', 'ValuesService', 'AppModulePermissionService', 'SalonBranchService', 'StreamExcelService', 'ExcelService', 'FirebaseDatabaseService'):
                service_name = inj
                break
    if not service_name:
        service_name = f"{singular}Service"

    entity_name = singular
    manager_name = f"{singular}Manager"

    smatches = glob.glob(os.path.join(base_dir, 'SALON_HAIR_CORE/Services/**/' + service_name + '.cs'), recursive=True)
    if smatches:
        try:
            with open(smatches[0], 'r', encoding='utf-8', errors='ignore') as fp:
                scontent = fp.read()
            em = re.search(r'ApplicationService<([A-Za-z0-9_]+)>', scontent)
            if em:
                entity_name = em.group(1)

            mgr_candidates = [f"{base_name}Manager", f"{singular}Manager", f"{entity_name}Manager"]
            for mc in mgr_candidates:
                if mc in scontent:
                    manager_name = mc
                    break
            if not manager_name or manager_name == f"{singular}Manager":
                sm = re.search(r'public\s+' + service_name + r'\s*\((.*?)\)', scontent, re.DOTALL)
                if sm:
                    for p in sm.group(1).split(','):
                        parts = p.strip().split()
                        if len(parts) >= 2 and parts[0].endswith('Manager') and parts[0] not in ('DomainService', 'Manager'):
                            manager_name = parts[0]
                            break
        except Exception:
            pass

    ent_dir = os.path.join(base_dir, 'SALON_HAIR_ENTITY/Entities')
    known_entities = set()
    if os.path.exists(ent_dir):
        try:
            for f in os.listdir(ent_dir):
                if f.endswith('.cs'):
                    known_entities.add(f[:-3])
        except Exception:
            pass

    entities = [entity_name] if entity_name in known_entities else [singular]
    for e in sorted(known_entities):
        if e != entities[0] and (e.startswith(entities[0]) or entities[0] in e) and len(entities) < 4:
            entities.append(e)

    return {
        'service': service_name,
        'manager': manager_name,
        'entity': entities[0],
        'entities': entities,
        'be_stack_str': f"{controller_name} → {service_name} → {entities[0]} Entity"
    }


def scan_be_controllers(base_dir, controller_names):
    """
    Scans backend controllers in SALON_HAIR_API, resolves exact routes,
    parses true action endpoints, and traces downstream services/managers/entities.
    """
    found_controllers = []
    primary_controller = controller_names[0] if controller_names else ''
    primary_path = ''
    primary_route = ''
    all_injections = set()
    primary_injections = []
    endpoints = []
    primary_content = ''

    for idx, cname in enumerate(controller_names):
        pattern = os.path.join(base_dir, 'SALON_HAIR_API/**/' + cname + '.cs')
        matches = glob.glob(pattern, recursive=True)
        if matches:
            fpath = matches[0]
            rel_path = fpath.replace(base_dir.rstrip('/') + '/', '')
            found_controllers.append(cname)
            if not primary_path:
                primary_path = rel_path
                primary_controller = cname

            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()

                if not primary_content and idx == 0:
                    primary_content = content

                c_route = resolve_controller_route(content, cname)
                if not primary_route:
                    primary_route = c_route

                ctor_match = re.search(r'public\s+' + cname + r'\s*\((.*?)\)', content, re.DOTALL)
                if not ctor_match:
                    ctor_match = re.search(r'public\s+(?:[A-Za-z0-9_]+)\s*\((.*?)\)', content, re.DOTALL)

                c_injections = []
                if ctor_match:
                    params = ctor_match.group(1).split(',')
                    for p in params:
                        parts = p.strip().split()
                        if len(parts) >= 2 and not parts[0].startswith('//'):
                            all_injections.add(parts[0])
                            c_injections.append(parts[0])

                if idx == 0:
                    primary_injections = c_injections

                c_endpoints = extract_action_endpoints(content, c_route)
                if idx == 0:
                    endpoints.extend(c_endpoints)
                else:
                    for ep in c_endpoints:
                        if not any(e['path'] == ep['path'] and e['method'] == ep['method'] for e in endpoints):
                            endpoints.append(ep)
            except Exception:
                pass

    if not primary_route and controller_names:
        primary_route = to_kebab_case(controller_names[0])

    chain = trace_downstream_chain(base_dir, primary_controller, primary_content, primary_injections)

    return {
        'controllers': found_controllers,
        'primary_controller': primary_controller,
        'path': primary_path or f'SALON_HAIR_API/Controllers/{primary_controller}.cs',
        'route': primary_route,
        'injections': sorted(list(all_injections))[:8],
        'actions': [f"{ep['method']} {ep['action']}()" for ep in endpoints][:8],
        'endpoints': endpoints,
        'service': chain['service'],
        'manager': chain['manager'],
        'entity': chain['entity'],
        'entities': chain['entities'],
        'be_stack_str': chain['be_stack_str']
    }


def build_mermaid_code(modules, fe_branch, be_branch):
    """
    Tự động xây dựng mã Mermaid Flowchart động dựa trên mã nguồn thực tế của nhánh hiện tại.
    Liên kết 3 tầng: Frontend Screens -> API Contracts (có HTTP verbs) -> Backend Controllers/Services.
    Bảo đảm 100% cú pháp Mermaid v10, giữ nguyên quy tắc ID để click highlight mượt mà.
    """
    def clean(s):
        if not s:
            return ''
        s = str(s).replace('"', "'")
        s = re.sub(r'[\r\n]+', ' ', s)
        s = s.replace('[', '(').replace(']', ')')
        s = s.replace('{', '(').replace('}', ')')
        return re.sub(r'\s+', ' ', s).strip()

    lines = [
        'flowchart LR',
        f'    subgraph FE ["FRONTEND ({clean(fe_branch)})"]',
        '        direction TB'
    ]
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        nid = f'FE_{token}'
        title = clean(m.get('title', m['id']).split('(')[0].strip())
        screens = m.get('fe', {}).get('screens', [])
        screen_sub = clean(screens[0]) if screens else clean(m.get('fe', {}).get('path', ''))
        res = m.get('fe', {}).get('resources', [])
        res_sub = clean(res[0]) if res else ''
        sub_text = f'{screen_sub}' + (f'<br/><i>{res_sub}</i>' if res_sub else '')
        lines.append(f'        {nid}["<b>{title}</b><br/>{sub_text}"]')
    lines.append('    end')

    lines.append('    subgraph API ["RESTful API CONTRACTS"]')
    lines.append('        direction TB')
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        nid = f'API_{token}'
        route = clean(m.get('api', {}).get('route', f'/{m["id"]}'))
        endpoints = m.get('api', {}).get('endpoints', [])
        verbs = []
        for ep in endpoints:
            v = clean(ep.get('method', 'GET').upper().replace('HTTP', ''))
            badge = f'[{v}]'
            if badge not in verbs:
                verbs.append(badge)
        verbs_str = ' '.join(verbs[:4]) if verbs else '[GET] [POST]'
        first_note = clean(endpoints[0].get('note', '')) if endpoints else ''
        lines.append(f'        {nid}["<b>{route}</b><br/>{verbs_str}<br/><i>{first_note}</i>"]')
    lines.append('    end')

    lines.append(f'    subgraph BE ["BACKEND ({clean(be_branch)})"]')
    lines.append('        direction TB')
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        nid = f'BE_{token}'
        controller = clean(m.get('be', {}).get('controller', '').split(':')[0].strip().split()[0])
        service = clean(m.get('be', {}).get('service', '')) or (controller.replace('Controller', '') + 'Service')
        entities = m.get('be', {}).get('entities', [])
        ent_str = clean(', '.join(entities[:2])) if isinstance(entities, list) else clean(str(entities))
        lines.append(f'        {nid}["<b>{controller}</b><br/>↳ {service}<br/><i>Entity: {ent_str}</i>"]')
    lines.append('    end')

    lines.append('    %% Liên kết kết nối 2 đầu Frontend <==> Backend')
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        fe_nid = f'FE_{token}'
        api_nid = f'API_{token}'
        be_nid = f'BE_{token}'
        lines.append(f'    {fe_nid} ==>|gọi RESTful API| {api_nid}')
        lines.append(f'    {api_nid} ==>|xử lý Controller & Service| {be_nid}')

    return '\n'.join(lines)


def build_tree_nodes(modules):
    """
    Xây dựng cấu trúc cây phân cấp 4 tầng nghiệp vụ hoàn chỉnh (Feature 5 / R2):
      - Cấp 1 (Gốc/Module): type='module', id='tree-{mod_id}'
      - Cấp 2 (Màn hình / Component FE): type='fe_component', id='tree-fe-{mod_id}-{g_idx}'
      - Cấp 3 (API Contract): type='api_contract', id='tree-api-{mod_id}-{g_idx}-{ep_idx}-{method}'
      - Cấp 4 (Backend .NET Stack): type='be_stack', id='tree-be-{mod_id}-{g_idx}-{ep_idx}-{method}'
    Bảo đảm 100% ID node là duy nhất toàn cục và đầy đủ liên kết.
    """
    tree_nodes = []
    seen_ids = set()

    for m in modules:
        mod_id = m['id']
        mod_name = m.get('title') or m.get('name', mod_id)
        l1_id = f'tree-{mod_id}'
        l1_node = {
            'id': l1_id,
            'name': mod_name,
            'type': 'module',
            'category': m.get('category', 'core'),
            'children': []
        }
        seen_ids.add(l1_id)

        fe = m.get('fe', {})
        screens = fe.get('screens', [])
        components = fe.get('components', [])

        api = m.get('api', {})
        endpoints = api.get('endpoints', [])
        base_route = api.get('route', f'/{mod_id}')
        if not endpoints:
            endpoints = [{'method': 'GET', 'path': base_route, 'note': 'Truy vấn danh sách'}]

        be = m.get('be', {})
        controller = be.get('controller', f'{mod_id.capitalize()}Controller')
        controller_clean = controller.split(':')[0].strip().split()[0]
        service = be.get('service') or (controller_clean.replace('Controller', '') + 'Service')
        entities = be.get('entities') or [controller_clean.replace('Controller', '')]
        entity_str = ', '.join(entities[:2]) if isinstance(entities, list) else str(entities)

        if len(screens) >= 2:
            half = max(1, len(endpoints) // 2)
            c1 = components[0] if components else ''
            c2 = components[1] if len(components) > 1 else ''
            groups = [
                (f'Frontend: {screens[0]}' + (f' / {c1}' if c1 else ''), endpoints[:half], 0),
                (f'Frontend: {screens[1]}' + (f' / {c2}' if c2 else ''), endpoints[half:], 1)
            ]
        else:
            s_name = screens[0] if screens else f'Route{controller_clean.replace("Controller", "")}.tsx'
            c_name = components[0] if components else 'Container.tsx'
            groups = [(f'Frontend: {s_name} / {c_name}', endpoints, 0)]

        for fe_name, ep_list, g_idx in groups:
            if not ep_list:
                ep_list = endpoints
            l2_id = f'tree-fe-{mod_id}-{g_idx}'
            l2_node = {
                'id': l2_id,
                'name': fe_name,
                'type': 'fe_component',
                'children': []
            }
            seen_ids.add(l2_id)

            for ep_idx, ep in enumerate(ep_list):
                method = ep.get('method', 'GET').upper().replace('HTTP', '')
                path = ep.get('path', base_route)
                note = ep.get('note', '')
                l3_id = f'tree-api-{mod_id}-{g_idx}-{ep_idx}-{method.lower()}'
                suffix = 0
                orig_l3_id = l3_id
                while l3_id in seen_ids:
                    suffix += 1
                    l3_id = f'{orig_l3_id}-{suffix}'
                seen_ids.add(l3_id)

                l3_node = {
                    'id': l3_id,
                    'name': f'[{method}] {path}',
                    'method': method,
                    'path': path,
                    'note': note,
                    'type': 'api_contract',
                    'children': []
                }

                l4_id = f'tree-be-{mod_id}-{g_idx}-{ep_idx}-{method.lower()}'
                if suffix > 0:
                    l4_id = f'{l4_id}-{suffix}'
                while l4_id in seen_ids:
                    suffix += 1
                    l4_id = f'tree-be-{mod_id}-{g_idx}-{ep_idx}-{method.lower()}-{suffix}'
                seen_ids.add(l4_id)

                be_stack_name = f'{controller_clean} → {service} → {entity_str} Entity'
                l4_node = {
                    'id': l4_id,
                    'name': be_stack_name,
                    'controller': controller_clean,
                    'service': service,
                    'type': 'be_stack',
                    'children': []
                }

                l3_node['children'].append(l4_node)
                l2_node['children'].append(l3_node)

            l1_node['children'].append(l2_node)

        tree_nodes.append(l1_node)

    return tree_nodes


def normalize_endpoint_path(p):
    if not p:
        return '', ''
    p = p.strip()
    if p.startswith('./'):
        p = p[1:]
    if not p.startswith('/'):
        p = '/' + p
    p = re.sub(r'/+', '/', p)
    p = re.sub(r':([a-zA-Z0-9_]+)', r'{\1}', p)
    p_generic = re.sub(r'\{[a-zA-Z0-9_]+\}', r'{id}', p)
    p_norm = p_generic.lower().replace('-', '').replace('_', '')
    return p, p_norm


def infer_fe_func(verb, path):
    v = verb.upper()
    has_id = '{id}' in path.lower() or ':id' in path.lower()
    p_lower = path.lower()
    if v == 'GET':
        if 'search' in p_lower: return 'search'
        if 'print' in p_lower: return 'getPrint'
        if 'group' in p_lower: return 'getGroup'
        if 'nearest' in p_lower: return 'getNearest'
        if 'export' in p_lower: return 'export'
        return 'getById' if has_id else 'getAll'
    elif v == 'POST':
        if 'import' in p_lower: return 'importSingle'
        if 'upload' in p_lower: return 'upload'
        return 'create'
    elif v == 'PUT':
        if 'restore' in p_lower: return 'restore'
        if 'cancel' in p_lower: return 'cancelPayment'
        if 'pay' in p_lower: return 'payInvoice'
        if 'avatar' in p_lower: return 'updateAvatar'
        return 'update'
    elif v == 'DELETE':
        return 'delete'
    return 'execute'


def infer_be_action(verb, path, controller_name=''):
    base_name = controller_name.replace('Controller', '') if controller_name else 'Item'
    base_name = re.sub(r'^V\d+_', '', base_name)
    v = verb.upper()
    has_id = '{id}' in path.lower() or ':id' in path.lower()
    p_lower = path.lower()
    if v == 'GET':
        if 'search' in p_lower: return f'Get{base_name}BySearch'
        if 'print' in p_lower: return f'Get{base_name}Print'
        if 'group' in p_lower: return f'Get{base_name}Group'
        if 'nearest' in p_lower: return f'Get{base_name}Nearest'
        if 'export' in p_lower: return f'Export{base_name}s'
        return f'Get{base_name}ById' if has_id else f'Get{base_name}'
    elif v == 'POST':
        if 'import' in p_lower: return f'Import{base_name}'
        return f'Post{base_name}'
    elif v == 'PUT':
        if 'restore' in p_lower: return f'Restore{base_name}'
        if 'cancel' in p_lower: return f'Cancel{base_name}'
        return f'Put{base_name}'
    elif v == 'DELETE':
        return f'Delete{base_name}'
    return f'Execute{base_name}'


def merge_module_endpoints(fe_endpoints, be_endpoints, base_route='', primary_controller='', vdata=None):
    merged = []
    seen = set()

    # Build FE lookup
    fe_items = []
    for ep in fe_endpoints:
        m = ep.get('method', 'GET').upper().replace('HTTP', '')
        raw_p = ep.get('path', '')
        p_clean, p_norm = normalize_endpoint_path(raw_p)
        fe_items.append({
            'method': m,
            'path': p_clean,
            'p_norm': p_norm,
            'fe_func': ep.get('fe_func') or infer_fe_func(m, p_clean),
            'note': ep.get('note', '')
        })

    # Build BE lookup
    be_items = []
    for ep in be_endpoints:
        m = ep.get('method', 'GET').upper().replace('HTTP', '')
        raw_p = ep.get('path', '')
        p_clean, p_norm = normalize_endpoint_path(raw_p)
        action = ep.get('be_action') or ep.get('action') or ''
        be_items.append({
            'method': m,
            'path': p_clean,
            'p_norm': p_norm,
            'be_action': action or infer_be_action(m, p_clean, primary_controller),
            'note': ep.get('note', '')
        })

    # 1. Match BE with FE
    for be in be_items:
        m = be['method']
        key = (m, be['p_norm'])
        if key in seen:
            continue
        seen.add(key)

        matched_fe = None
        for fe in fe_items:
            if fe['method'] == m and (fe['p_norm'] == be['p_norm'] or be['p_norm'].endswith(fe['p_norm']) or fe['p_norm'].endswith(be['p_norm'])):
                matched_fe = fe
                break

        if not matched_fe:
            has_id = '{id}' in be['p_norm']
            for fe in fe_items:
                if fe['method'] == m and ('{id}' in fe['p_norm']) == has_id:
                    matched_fe = fe
                    break

        fe_func = matched_fe['fe_func'] if matched_fe else infer_fe_func(m, be['path'])
        note = be['note'] or (matched_fe['note'] if matched_fe else '') or generate_endpoint_note(be['be_action'], m, be['path'])

        merged.append({
            'method': m,
            'path': be['path'],
            'fe_func': fe_func,
            'be_action': be['be_action'],
            'note': note
        })

    # 2. Add remaining FE endpoints
    for fe in fe_items:
        m = fe['method']
        key = (m, fe['p_norm'])
        if key in seen:
            continue
        seen.add(key)

        matched_be = None
        for be in be_items:
            if be['method'] == m and (be['p_norm'] == fe['p_norm'] or be['p_norm'].endswith(fe['p_norm']) or fe['p_norm'].endswith(be['p_norm'])):
                matched_be = be
                break

        be_action = matched_be['be_action'] if matched_be else infer_be_action(m, fe['path'], primary_controller)
        note = fe['note'] or (matched_be['note'] if matched_be else '') or generate_endpoint_note(be_action, m, fe['path'])

        merged.append({
            'method': m,
            'path': fe['path'],
            'fe_func': fe['fe_func'],
            'be_action': be_action,
            'note': note
        })

    # 3. Add vdata fallback endpoints if merged is empty
    if not merged and vdata and vdata.get('endpoints'):
        for vep in vdata['endpoints']:
            m = vep.get('method', 'GET').upper().replace('HTTP', '')
            p = vep.get('path', base_route)
            merged.append({
                'method': m,
                'path': p,
                'fe_func': infer_fe_func(m, p),
                'be_action': infer_be_action(m, p, primary_controller),
                'note': vep.get('note', '')
            })

    # 4. Ensure all 4 CRUD methods (GET, POST, PUT, DELETE) are present
    crud_methods = ['GET', 'POST', 'PUT', 'DELETE']
    present_methods = {e['method'] for e in merged}
    clean_base = base_route or f"/{to_kebab_case(primary_controller)}"
    if not clean_base.startswith('/'):
        clean_base = '/' + clean_base

    for cm in crud_methods:
        if cm not in present_methods:
            p = f"{clean_base}/{{id}}" if cm in ('PUT', 'DELETE') else clean_base
            fe_func = infer_fe_func(cm, p)
            be_action = infer_be_action(cm, p, primary_controller)
            merged.append({
                'method': cm,
                'path': p,
                'fe_func': fe_func,
                'be_action': be_action,
                'note': generate_endpoint_note(be_action, cm, p)
            })

    # Prioritize CRUD order: GET (list), POST, PUT, DELETE, GET (details / others)
    def priority_sort(e):
        m = e['method']
        has_id = '{id}' in e['path'].lower()
        if m == 'GET' and not has_id: return 1
        if m == 'POST': return 2
        if m == 'PUT': return 3
        if m == 'DELETE': return 4
        if m == 'GET' and has_id: return 5
        return 6

    merged.sort(key=priority_sort)
    return merged


def get_diagram_data(force=False):
    fe_ws = get_fe_workspace()
    be_ws = get_be_workspace()
    fe_branch, fe_commit = get_git_info(fe_ws)
    be_branch, be_commit = get_git_info(be_ws)
    cache_key = f"{fe_branch}@{fe_commit}|{be_branch}@{be_commit}"

    with state_lock:
        if not force and app_state.get('diagram_cache') and app_state.get('diagram_cache_key') == cache_key:
            return app_state['diagram_cache']

    ctrl_path = os.path.join(be_ws, 'SALON_HAIR_API')
    existing_cs = {f[:-3] for root, _, files in os.walk(ctrl_path) for f in files if f.endswith('.cs')} if os.path.isdir(ctrl_path) else set()
    modules = []
    for cfg in CORE_MODULE_CONFIGS:
        mid = cfg['id']
        vdata = MODULE_VERIFIED_DATA.get(mid, {})

        fe_info = scan_fe_directory(fe_ws, cfg)
        be_info = scan_be_controllers(be_ws, cfg['be_controllers'])

        # Controllers & services
        primary_c = be_info.get('primary_controller') or (cfg['be_controllers'][0] if cfg.get('be_controllers') else vdata.get('controller', f"{mid.capitalize()}Controller"))
        if primary_c not in existing_cs:
            fallback_controllers = ['BookingsController'] if 'booking' in mid else []
            for fb_c in fallback_controllers:
                if fb_c in existing_cs:
                    primary_c = fb_c
                    break

        # Merge / fallback for routes & endpoints
        route = be_info.get('route') or fe_info.get('route') or vdata.get('route', f"/{mid}")
        if '[controller]' in route.lower():
            route = to_kebab_case(primary_c)
        api_route = '/' + route.lstrip('/')

        # Merge endpoints from BE and FE with Frontend function and Backend action matching
        endpoints = merge_module_endpoints(
            fe_info.get('endpoints', []),
            be_info.get('endpoints', []),
            base_route=api_route,
            primary_controller=primary_c,
            vdata=vdata
        )

        # Select representative endpoints guaranteeing all 4 CRUD methods (GET, POST, PUT, DELETE)
        selected_endpoints = []
        for target_verb in ['GET', 'POST', 'PUT', 'DELETE']:
            for ep in endpoints:
                if ep['method'] == target_verb and ep not in selected_endpoints:
                    selected_endpoints.append(ep)
                    break
        for ep in endpoints:
            if ep['method'] == 'GET' and ('{id}' in ep['path'].lower() or ':id' in ep['path'].lower()) and ep not in selected_endpoints:
                selected_endpoints.append(ep)
                break
        for ep in endpoints:
            if len(selected_endpoints) >= 6:
                break
            if ep not in selected_endpoints:
                selected_endpoints.append(ep)

        # Screens & components
        screens = fe_info.get('screens') or vdata.get('screens', [f"Route{mid.capitalize()}.tsx"])
        components = fe_info.get('components') or vdata.get('components', ['Container.tsx'])
        resources = fe_info.get('resources') or vdata.get('resources', [f"{mid}.ts"])

        # Controllers & services
        service = be_info.get('service') or (('BookingService' if primary_c == 'BookingsController' else None) or vdata.get('service', f"{primary_c.replace('Controller', '')}Service"))
        manager = be_info.get('manager') or (('BookingManager' if primary_c == 'BookingsController' else None) or vdata.get('manager', f"{primary_c.replace('Controller', '')}Manager"))
        entity = be_info.get('entity') or (('Booking' if primary_c == 'BookingsController' else None) or (vdata.get('entities', [primary_c.replace('Controller', '')])[0]))
        entities = be_info.get('entities') or (['Booking', 'BookingDetail'] if primary_c == 'BookingsController' else vdata.get('entities', [entity]))
        be_stack_str = be_info.get('be_stack_str') or f"{primary_c} → {service} → {entity} Entity"

        # Construct be_links
        be_links = [service, manager, f"{entity} Entity"]
        for extra_c in cfg['be_controllers']:
            if extra_c != primary_c and extra_c not in be_links:
                be_links.append(extra_c)

        mod = {
            'id': mid,
            'title': cfg['title'],
            'name': cfg.get('name', cfg['title']),
            'category': cfg.get('category', 'core'),
            'skill': cfg['skill'],
            'api': {
                'route': api_route,
                'endpoints': selected_endpoints
            },
            'fe': {
                'screens': screens[:12],
                'components': components[:15],
                'resources': resources,
                'path': fe_info.get('path') or (cfg['fe_routes'][0] if cfg.get('fe_routes') else f"src/scripts/routes/{mid}"),
                'resource': fe_info.get('resource') or (cfg['fe_resources'][0] if cfg.get('fe_resources') else f"src/scripts/restful/resources/{mid}.ts"),
                'desc': cfg['default_desc'],
                'imports': fe_info.get('imports') or ['@/restful', '@/components/common'],
                'exports': fe_info.get('exports') or ['Container', 'Actions']
            },
            'be': {
                'path': be_info.get('path') or f"SALON_HAIR_API/Controllers/{primary_c}.cs",
                'controller': primary_c,
                'controller_full': f"{primary_c} : SalonControllerBase",
                'controllers': cfg['be_controllers'],
                'service': service,
                'manager': manager,
                'entity': entity,
                'entities': entities,
                'be_stack_str': be_stack_str,
                'desc': f"Xử lý Controller nghiệp vụ cho {cfg['title']}, tích hợp Service Layer và MySQL.",
                'injections': be_info.get('injections') or ['IUnitOfWork', 'ISalonContext', service],
                'exports': be_info.get('actions') or [f"{ep['method']} {ep['path']}" for ep in endpoints[:4]],
                'links': be_links
            }
        }
        modules.append(mod)

    mermaid_code = build_mermaid_code(modules, fe_branch, be_branch)
    tree_nodes = build_tree_nodes(modules)

    result = {
        'fe_branch': fe_branch,
        'fe_commit': fe_commit,
        'be_branch': be_branch,
        'be_commit': be_commit,
        'scanned_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y'),
        'modules': modules,
        'tree_nodes': tree_nodes,
        'mermaid_code': mermaid_code
    }

    with state_lock:
        app_state['diagram_cache'] = result
        app_state['diagram_cache_key'] = cache_key

    return result


# -------------------------------------------------------------
# HTTP REQUEST HANDLER
# -------------------------------------------------------------
class AgentStudioHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        PAGE_ROUTES = {
            '/',
            '/index.html',
            '/task',
            '/tasks',
            '/git-control',
            '/branch',
            '/branches',
            '/cherry-pick',
            '/cherry',
            '/git/cherry-pick',
            '/git',
            '/history',
            '/log',
            '/logs',
            '/diagram',
            '/architecture',
            '/jira',
            '/jira-tasks',
            '/jira-tickets',
            '/settings',
            '/setting',
            '/effort',
            '/model',
            '/models',
            '/engine',
            '/account',
            '/env',
            '/environment',
            '/api-settings',
            '/api-keys',
            '/settings/effort',
            '/settings/model',
            '/settings/models',
            '/settings/engine',
            '/settings/account',
            '/settings/api',
            '/settings/api-keys',
            '/settings/mcp',
            '/mcp',
            '/mcp-servers',
            '/settings/env',
            '/settings/environment',
        }

        is_html_route = (
            path in PAGE_ROUTES
            or path.startswith('/git-control')
            or path.startswith('/git/')
            or (path.startswith('/settings') and path != '/api/settings')
            or path.startswith('/setting')
            or (path.endswith('/settings') and path != '/api/settings')
            or path.endswith('/setting')
        )

        if is_html_route:
            self.serve_html()
        elif path == '/logo-my.png':
            self.serve_logo()
        elif path in ('/favicon.ico', '/favicon.png', '/images/logo.png', '/images/favicon.png', '/frontend/images/logo.png'):
            self.serve_favicon()
        elif path.startswith('/modules/'):
            mod_name = os.path.basename(path)
            mod_path = os.path.join(BASE_DIR, 'frontend', 'modules', mod_name)
            if os.path.exists(mod_path):
                with open(mod_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)
        elif path == '/api/status':
            with state_lock:
                tasks_out = {}
                for tid, ts in app_state['active_tasks'].items():
                    tasks_out[tid] = {
                        'task_id': ts.get('task_id'),
                        'title': ts.get('title', ''),
                        'mode': ts.get('mode', 'task'),
                        'is_running': ts.get('is_running', False),
                        'active_round': ts.get('active_round', 0),
                        'total_rounds': ts.get('total_rounds', 0),
                        'active_speaker': ts.get('active_speaker', ''),
                        'status_text': ts.get('status_text', ''),
                        'session': ts.get('session')
                    }

                latest_session = app_state.get('current_session')
                latest_mode = app_state.get('mode', 'task')
                latest_status = app_state.get('status_text', 'Sẵn sàng')

                active_list = [t for t in app_state['active_tasks'].values() if t.get('is_running')]
                if active_list:
                    latest_session = active_list[-1].get('session')
                    latest_mode = active_list[-1].get('mode', 'task')
                    latest_status = active_list[-1].get('status_text')

                data = {
                    'is_running': any(t.get('is_running') for t in app_state['active_tasks'].values()) or app_state.get('is_running', False),
                    'tasks': tasks_out,
                    'mode': latest_mode,
                    'active_round': app_state.get('active_round', 0),
                    'total_rounds': app_state.get('total_rounds', 0),
                    'active_speaker': app_state.get('active_speaker', ''),
                    'status_text': latest_status,
                    'current_session': latest_session
                }
            self.send_json(data)
        elif path == '/api/terminals':
            fe_feed = get_terminal_feed(get_fe_workspace(), limit=14)
            be_feed = get_terminal_feed(get_be_workspace(), limit=14)
            self.send_json({
                'fe': fe_feed,
                'be': be_feed,
                'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
            })
        elif path == '/api/history':
            messages = load_messages()
            self.send_json(list(reversed(messages[-25:])))
        elif path == '/api/diagram-data':
            qs = urllib.parse.parse_qs(parsed.query)
            force = qs.get('force', ['0'])[0] in ('1', 'true', 'True')
            data = get_diagram_data(force=force)
            self.send_json(data)
        elif path == '/api/skills':
            skills = get_custom_skills()
            self.send_json(skills)
        elif path == '/api/git/info':
            fe_info = get_git_repo_details(get_fe_workspace())
            be_info = get_git_repo_details(get_be_workspace())
            self.send_json({
                'fe': fe_info,
                'be': be_info
            })
        elif path == '/api/git/commits':
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('target', ['fe'])[0]
            branch = qs.get('branch', ['HEAD'])[0]
            limit = int(qs.get('limit', ['30'])[0])
            ws = get_workspace(target)
            data = get_git_commits(ws, branch=branch, limit=limit)
            self.send_json(data)
        elif path == '/api/git/cherry-pick/status':
            fe_status = get_git_cherry_pick_status(get_fe_workspace())
            be_status = get_git_cherry_pick_status(get_be_workspace())
            self.send_json({
                'fe': fe_status,
                'be': be_status
            })
        elif path == '/api/git/stash/list':
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('target', ['fe'])[0]
            ws = get_workspace(target)
            stashes = get_git_stash_list(ws)
            self.send_json({
                'success': True,
                'target': target,
                'stashes': stashes
            })
        elif path == '/api/git/conflict/status':
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('target', ['fe'])[0]
            ws = get_workspace(target)
            data = get_git_active_conflict_status(ws)
            self.send_json(data)
        elif path == '/api/git/conflict/file':
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('target', ['fe'])[0]
            file_path = qs.get('file', [''])[0]
            ws = get_workspace(target)
            data = get_git_conflict_file_info(ws, file_path)
            self.send_json(data)
        elif path in ('/api/git/sync-check', '/api/git/sync-pull/check'):
            qs = urllib.parse.parse_qs(parsed.query)
            do_fetch = qs.get('fetch', ['1'])[0] not in ('0', 'false', 'no')
            fe_ws = get_fe_workspace()
            be_ws = get_be_workspace()
            with ThreadPoolExecutor(max_workers=2) as executor:
                fe_future = executor.submit(check_sync_pull_status, fe_ws, ('staging', 'master', 'beta'), do_fetch)
                be_future = executor.submit(check_sync_pull_status, be_ws, ('staging', 'master', 'beta'), do_fetch)
                fe_res = fe_future.result()
                be_res = be_future.result()
            self.send_json({
                'success': True,
                'last_checked': datetime.datetime.now().strftime('%H:%M:%S'),
                'fe': fe_res,
                'be': be_res
            })
        elif path == '/api/logs':
            messages = load_messages()
            self.send_json(list(reversed(messages)))
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            body = {}

        if path in ('/api/task', '/api/discuss'):
            prompt = body.get('prompt', '').strip()
            error_log = body.get('error_log', '').strip()
            task_id = body.get('task_id', '').strip() or f"task_{datetime.datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}"
            task_title = body.get('title', '').strip() or f"Làm task: {prompt[:35]}"

            with state_lock:
                if task_id in app_state['active_tasks'] and app_state['active_tasks'][task_id].get('is_running'):
                    self.send_json({'success': False, 'message': f'Tác vụ [{task_title}] đang chạy. Vui lòng chờ hoàn tất hoặc dừng trước khi chạy lại.'}, 400)
                    return

            if not prompt and not error_log:
                self.send_json({'success': False, 'message': 'Vui lòng nhập nội dung task hoặc mã lỗi.'}, 400)
                return

            full_prompt = prompt
            if error_log:
                if full_prompt:
                    full_prompt += f"\n\n[Mã lỗi / Console log / Exception đính kèm]:\n```\n{error_log}\n```"
                else:
                    full_prompt = f"[Mã lỗi / Console log / Exception cần xử lý]:\n```\n{error_log}\n```"

            target = body.get('target', 'both')
            starter = body.get('starter', 'fe')
            rounds = body.get('rounds', 4)
            skills_raw = body.get('skills', None) or body.get('skill', None) or body.get('module', '')
            if isinstance(skills_raw, list):
                skill = ', '.join([str(s).strip() for s in skills_raw if str(s).strip()])
            else:
                skill = str(skills_raw).strip()

            t = threading.Thread(target=run_task_worker, args=(task_id, full_prompt, target, starter, rounds, skill), daemon=True)
            t.start()
            self.send_json({'success': True, 'task_id': task_id, 'message': f'Đã khởi chạy tác vụ [{task_title}] thành công.'})

        elif path == '/api/fixbug':
            task_id = body.get('task_id', '').strip() or f"fix_{datetime.datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}"
            task_title = body.get('title', '').strip() or "Fix bug"

            with state_lock:
                if task_id in app_state['active_tasks'] and app_state['active_tasks'][task_id].get('is_running'):
                    self.send_json({'success': False, 'message': f'Tác vụ [{task_title}] đang chạy.'}, 400)
                    return

            skills_raw = body.get('skills', None) or body.get('skill', None) or body.get('module', '')
            if isinstance(skills_raw, list):
                skill = ', '.join([str(s).strip() for s in skills_raw if str(s).strip()])
            else:
                skill = str(skills_raw).strip()
            scope = body.get('scope', 'both')
            description = body.get('description', '').strip()
            error_log = body.get('error_log', '').strip()

            if not description and not error_log:
                self.send_json({'success': False, 'message': 'Vui lòng nhập mô tả lỗi hoặc dán log lỗi.'}, 400)
                return

            t = threading.Thread(target=run_fixbug_worker, args=(task_id, skill, scope, description, error_log), daemon=True)
            t.start()
            self.send_json({'success': True, 'task_id': task_id, 'message': f'Đã khởi chạy quy trình Fix Bug [{task_title}].'})

        elif path == '/api/stop':
            task_id = body.get('task_id')
            with state_lock:
                if task_id and task_id != 'all' and task_id in app_state['active_tasks']:
                    ts = app_state['active_tasks'][task_id]
                    if ts.get('current_process'):
                        try:
                            ts['current_process'].kill()
                        except Exception:
                            pass
                    ts['is_running'] = False
                    ts['status_text'] = 'Đã dừng tác vụ.'
                    if ts.get('session'):
                        ts['session']['status'] = 'STOPPED'
                else:
                    for tid, ts in app_state['active_tasks'].items():
                        if ts.get('current_process'):
                            try:
                                ts['current_process'].kill()
                            except Exception:
                                pass
                        ts['is_running'] = False
                        ts['status_text'] = 'Đã dừng tác vụ.'
                        if ts.get('session'):
                            ts['session']['status'] = 'STOPPED'
                    if app_state.get('current_process'):
                        try:
                            app_state['current_process'].kill()
                        except Exception:
                            pass
                app_state['is_running'] = any(t.get('is_running') for t in app_state['active_tasks'].values())
                app_state['status_text'] = 'Đã dừng tiến trình.' if not app_state['is_running'] else 'Đang chạy'
            self.send_json({'success': True, 'message': 'Đã dừng tiến trình.'})

        elif path == '/api/git/checkout':
            target = body.get('target', 'fe')
            branch = body.get('branch', '').strip()
            create_new = bool(body.get('create_new', False))
            base_branch = body.get('base_branch', '').strip()
            switch_branch = bool(body.get('switch_branch', True))
            if not branch:
                self.send_json({'success': False, 'message': 'Vui lòng chọn hoặc nhập tên nhánh.'}, 400)
                return

            results = []
            all_ok = True
            action_name = "Tạo nhánh & chuyển" if (create_new and switch_branch) else ("Tạo nhánh" if create_new else "Chuyển nhánh")

            if target in ('fe', 'both'):
                ok, msg = switch_git_branch(get_fe_workspace(), branch, create_new=create_new, base_branch=base_branch, switch_branch=switch_branch)
                results.append(f"Frontend: {msg}")
                add_work_log('GIT_SWITCH', f"{action_name} Frontend sang '{branch}'", msg, 'SUCCESS' if ok else 'ERROR', target='fe')
                if not ok: all_ok = False

            if target in ('be', 'both'):
                ok, msg = switch_git_branch(get_be_workspace(), branch, create_new=create_new, base_branch=base_branch, switch_branch=switch_branch)
                results.append(f"Backend: {msg}")
                add_work_log('GIT_SWITCH', f"{action_name} Backend sang '{branch}'", msg, 'SUCCESS' if ok else 'ERROR', target='be')
                if not ok: all_ok = False

            # Xóa cache sơ đồ để lần quét kế tiếp bảo đảm 100% dữ liệu mới từ nhánh vừa checkout
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None

            self.send_json({
                'success': all_ok,
                'message': '\n'.join(results)
            })

        elif path == '/api/git/rename-branch':
            target = body.get('target', 'fe')
            old_branch = body.get('old_branch', '').strip()
            new_branch = body.get('new_branch', '').strip()
            if not new_branch:
                self.send_json({'success': False, 'message': 'Vui lòng nhập tên nhánh mới.'}, 400)
                return

            results = []
            all_ok = True

            if target in ('fe', 'both'):
                ok, msg = rename_git_branch(get_fe_workspace(), new_branch, old_name=old_branch)
                results.append(f"Frontend: {msg}")
                add_work_log('GIT_RENAME', f"Đổi tên nhánh Frontend thành '{new_branch}'", msg, 'SUCCESS' if ok else 'ERROR', target='fe')
                if not ok: all_ok = False

            if target in ('be', 'both'):
                ok, msg = rename_git_branch(get_be_workspace(), new_branch, old_name=old_branch)
                results.append(f"Backend: {msg}")
                add_work_log('GIT_RENAME', f"Đổi tên nhánh Backend thành '{new_branch}'", msg, 'SUCCESS' if ok else 'ERROR', target='be')
                if not ok: all_ok = False

            # Xóa cache sơ đồ
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None

            self.send_json({
                'success': all_ok,
                'message': '\n'.join(results)
            }, 200 if all_ok else 400)

        elif path == '/api/git/fetch':
            target = body.get('target', 'both')
            results = []
            if target in ('fe', 'both'):
                subprocess.run(['git', 'fetch'], cwd=get_fe_workspace(), capture_output=True, timeout=30)
                results.append("Frontend: Đã đồng bộ fetch remote")
            if target in ('be', 'both'):
                subprocess.run(['git', 'fetch'], cwd=get_be_workspace(), capture_output=True, timeout=30)
                results.append("Backend: Đã đồng bộ fetch remote")
            self.send_json({'success': True, 'message': ' | '.join(results)})

        elif path == '/api/git/pull':
            target = body.get('target', 'both')
            results = []
            all_ok = True
            if target in ('fe', 'both'):
                res_fe = pull_git_branch(get_fe_workspace())
                results.append(f"Frontend: {res_fe['message']}")
                if not res_fe['success']:
                    all_ok = False
                add_work_log('GIT_PULL', f"Git Pull Frontend ({res_fe.get('branch', '')})", res_fe['message'], 'SUCCESS' if res_fe['success'] else 'ERROR', target='fe')

            if target in ('be', 'both'):
                res_be = pull_git_branch(get_be_workspace())
                results.append(f"Backend: {res_be['message']}")
                if not res_be['success']:
                    all_ok = False
                add_work_log('GIT_PULL', f"Git Pull Backend ({res_be.get('branch', '')})", res_be['message'], 'SUCCESS' if res_be['success'] else 'ERROR', target='be')

            # Xóa cache sơ đồ nếu có mã nguồn thay đổi sau khi pull
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None

            self.send_json({'success': all_ok, 'message': '\n'.join(results)})

        elif path == '/api/git/cherry-pick':
            target = body.get('target', 'fe')
            commits = body.get('commits', [])
            no_commit = bool(body.get('no_commit', False))
            record_origin = bool(body.get('record_origin', True))
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'

            res = execute_git_cherry_pick(ws, commits, no_commit=no_commit, record_origin=record_origin)

            status_str = 'SUCCESS' if res['success'] else ('CONFLICT' if res.get('conflict') else 'ERROR')
            add_work_log(
                'GIT_CHERRY_PICK',
                f"Cherry-Pick {repo_label} ({res.get('current_branch', '')})",
                res.get('message', ''),
                status_str,
                target=target
            )
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None
            self.send_json(res)

        elif path == '/api/git/cherry-pick/abort':
            target = body.get('target', 'fe')
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'
            res = abort_git_cherry_pick(ws)
            add_work_log(
                'GIT_CHERRY_PICK_ABORT',
                f"Hủy (Abort) Cherry-Pick {repo_label}",
                res.get('message', ''),
                'SUCCESS' if res['success'] else 'ERROR',
                target=target
            )
            self.send_json(res)

        elif path == '/api/git/cherry-pick/continue':
            target = body.get('target', 'fe')
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'
            res = continue_git_cherry_pick(ws)
            add_work_log(
                'GIT_CHERRY_PICK_CONTINUE',
                f"Tiếp tục (Continue) Cherry-Pick {repo_label}",
                res.get('message', ''),
                'SUCCESS' if res['success'] else 'ERROR',
                target=target
            )
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None
            self.send_json(res)

        elif path == '/api/git/checkout-switch':
            data = body or {}
            current_branch = (data.get('current_branch') or '').strip()
            target_branch = (data.get('target_branch') or '').strip()
            target_workspace = (data.get('target_workspace') or 'both').strip()

            if not current_branch or not target_branch:
                self.send_json({'success': False, 'message': 'Thiếu thông tin nhánh current/target.'}, 400)
                return

            if current_branch.lower() == target_branch.lower():
                self.send_json({'success': False, 'message': 'Nhánh đích không được giống nhánh hiện tại.'}, 400)
                return

            results = []
            all_ok = True

            ws_fe = get_workspace('fe')
            ws_be = get_workspace('be')

            # Checkout Frontend
            if target_workspace in ('fe', 'both'):
                ok, msg = switch_git_branch(ws_fe, target_branch, base_branch=current_branch)
                label = 'Frontend' if target_workspace in ('fe', 'both') else ''
                results.append(f"{label}: {msg}")
                add_work_log('GIT_SWITCH', f'Checkout FE sang "{target_branch}" từ "{current_branch}"', msg, 'SUCCESS' if ok else 'ERROR', target='fe')
                if not ok: all_ok = False

            # Checkout Backend
            if target_workspace in ('be', 'both'):
                ok, msg = switch_git_branch(ws_be, target_branch, base_branch=current_branch)
                label = 'Backend' if target_workspace in ('be', 'both') else ''
                results.append(f"{label}: {msg}")
                add_work_log('GIT_SWITCH', f'Checkout BE sang "{target_branch}" từ "{current_branch}"', msg, 'SUCCESS' if ok else 'ERROR', target='be')
                if not ok: all_ok = False

            self.send_json({'success': all_ok, 'message': '\n'.join(results)})

        elif path == '/api/git/push':
            target = body.get('target', 'fe')
            branch = body.get('branch', '').strip()
            commit_message = body.get('commit_message', '').strip()
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'

            res = push_git_branch(ws, branch_name=branch, commit_message=commit_message)
            add_work_log(
                'GIT_PUSH',
                f"Push code {repo_label} ({res.get('branch', branch)})",
                res.get('message', ''),
                'SUCCESS' if res.get('success') else 'ERROR',
                target=target
            )
            self.send_json(res)

        elif path == '/api/git/sync-pull':
            target = body.get('target', 'both')
            branch = body.get('branch', 'staging').strip()
            return_to_current = bool(body.get('return_to_current', False))
            results = {}
            all_ok = True
            any_conflict = False

            if target in ('fe', 'both'):
                res_fe = sync_pull_branch(get_fe_workspace(), branch, return_to_current=return_to_current)
                results['fe'] = res_fe
                if not res_fe.get('success'):
                    all_ok = False
                if res_fe.get('conflict'):
                    any_conflict = True
                add_work_log(
                    'GIT_SYNC_PULL',
                    f"Pull {branch} Frontend" + (" (quay về nhánh cũ)" if return_to_current else ""),
                    res_fe.get('message', ''),
                    'SUCCESS' if res_fe.get('success') else ('CONFLICT' if res_fe.get('conflict') else 'ERROR'),
                    target='fe'
                )

            if target in ('be', 'both'):
                res_be = sync_pull_branch(get_be_workspace(), branch, return_to_current=return_to_current)
                results['be'] = res_be
                if not res_be.get('success'):
                    all_ok = False
                if res_be.get('conflict'):
                    any_conflict = True
                add_work_log(
                    'GIT_SYNC_PULL',
                    f"Pull {branch} Backend" + (" (quay về nhánh cũ)" if return_to_current else ""),
                    res_be.get('message', ''),
                    'SUCCESS' if res_be.get('success') else ('CONFLICT' if res_be.get('conflict') else 'ERROR'),
                    target='be'
                )

            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None

            any_needs_stash = any(r.get('needs_stash', False) for r in results.values() if isinstance(r, dict))
            self.send_json({
                'success': all_ok,
                'conflict': any_conflict,
                'needs_stash': any_needs_stash,
                'target': target,
                'branch': branch,
                'results': results,
                'message': '\n'.join([f"{'Frontend' if k=='fe' else 'Backend'}: {v.get('message')}" for k, v in results.items()])
            })

        elif path == '/api/git/stash':
            target = body.get('target', 'fe')
            results = {}
            if target in ('fe', 'both'):
                results['fe'] = execute_git_stash(get_fe_workspace())
            if target in ('be', 'both'):
                results['be'] = execute_git_stash(get_be_workspace())
            all_ok = all(r.get('success', False) for r in results.values() if isinstance(r, dict))
            add_work_log(
                'GIT_STASH',
                f"Git Stash {'Frontend & Backend' if target=='both' else ('Frontend' if target=='fe' else 'Backend')}",
                '\n'.join([f"{'Frontend' if k=='fe' else 'Backend'}: {v.get('message')}" for k, v in results.items()]),
                'SUCCESS' if all_ok else 'ERROR',
                target=target
            )
            self.send_json({
                'success': all_ok,
                'target': target,
                'results': results,
                'message': '\n'.join([f"{'Frontend' if k=='fe' else 'Backend'}: {v.get('message')}" for k, v in results.items()])
            })

        elif path == '/api/git/stash/pop':
            target = body.get('target', 'fe')
            stash_index = body.get('stash_index', None)
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'
            res = execute_git_stash_pop(ws, stash_index=stash_index)
            stash_ref = stash_index or 'stash@{0}'
            add_work_log(
                'GIT_STASH_POP',
                f"Lấy code từ Stash {repo_label} ({stash_ref})",
                res.get('message', ''),
                'SUCCESS' if res.get('success') else 'ERROR',
                target=target
            )
            self.send_json(res)

        elif path == '/api/git/merge/abort':
            target = body.get('target', 'fe')
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'
            res = abort_git_merge(ws)
            add_work_log(
                'GIT_MERGE_ABORT',
                f"Hủy merge (Abort) {repo_label}",
                res.get('message', ''),
                'SUCCESS' if res.get('success') else 'ERROR',
                target=target
            )
            self.send_json(res)

        elif path == '/api/git/conflict/resolve':
            target = body.get('target', 'fe')
            file_path = body.get('file', '').strip()
            action = body.get('action', 'accept_current')
            block_index = body.get('block_index')
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'
            res = resolve_git_conflict_file(ws, file_path, action, block_index=block_index)
            if res.get('file_staged'):
                add_work_log(
                    'GIT_CONFLICT_RESOLVED',
                    f"Giải quyết xong conflict file {file_path} ({repo_label})",
                    f"Đã giải quyết conflict ({action}) và tự động git add {file_path}",
                    'SUCCESS',
                    target=target
                )
            self.send_json(res)

        elif path == '/api/git/conflict/abort':
            target = body.get('target', 'fe')
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'
            res = abort_git_conflict(ws)
            add_work_log(
                'GIT_CONFLICT_ABORT',
                f"Hủy bỏ thao tác Git đang xung đột ({repo_label})",
                res.get('message', ''),
                'SUCCESS' if res.get('success') else 'ERROR',
                target=target
            )
            self.send_json(res)

        elif path == '/api/git/conflict/continue':
            target = body.get('target', 'fe')
            commit_message = body.get('commit_message')
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'
            res = continue_git_conflict(ws, commit_message=commit_message)
            add_work_log(
                'GIT_CONFLICT_CONTINUE',
                f"Tiếp tục sau xung đột ({repo_label})",
                res.get('message', ''),
                'SUCCESS' if res.get('success') else 'ERROR',
                target=target
            )
            self.send_json(res)

        elif path == '/api/logs/clear':
            save_messages([])
            self.send_json({'success': True, 'message': 'Đã xóa toàn bộ lịch sử log.'})
        else:
            self.send_error(404, "Not Found")

    def serve_logo(self):
        local_logo = os.path.join(get_fe_workspace(), 'static/assets/logo/logo-my.png')
        if os.path.exists(local_logo):
            with open(local_logo, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def serve_favicon(self):
        logo_path = os.path.join(BASE_DIR, 'frontend', 'images', 'logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def serve_html(self):
        rendered_html = (
            HTML_TEMPLATE
            .replace('{{FE_WORKSPACE}}', get_fe_workspace())
            .replace('{{BE_WORKSPACE}}', get_be_workspace())
        )
        html_code = rendered_html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Content-Length', str(len(html_code)))
        self.end_headers()
        self.wfile.write(html_code)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EasySalon Agent</title>
  <link rel="icon" type="image/png" href="/images/logo.png">
  <link rel="shortcut icon" type="image/png" href="/images/logo.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Be Vietnam Pro"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace']
          }
        }
      }
    };
    mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });

    window.TABS = ['task', 'branch', 'log', 'diagram'];
    window.TAB_ROUTES = {
      'task': '/task',
      'branch': '/git-control',
      'log': '/history',
      'diagram': '/diagram'
    };

    window.GIT_SUBTAB_ROUTES = {
      'pull_sync': '/git-control',
      'branch': '/git-control/checkout-branch',
      'switch': '/git-control/switch-branch',
      'cherry_pick': '/git-control/cherry-pick',
      'merge': '/git-control/merge'
    };

    window.ROUTE_TO_GIT_SUBTAB = {
      '/git-control': 'pull_sync',
      '/git-control/': 'pull_sync',
      '/git-control/pull-sync': 'pull_sync',
      '/git-control/sync': 'pull_sync',
      '/git-control/checkout-branch': 'branch',
      '/git-control/create-branch': 'branch',
      '/git-control/branch': 'branch',
      '/git-control/branches': 'branch',
      '/git-control/switch-branch': 'switch',
      '/git-control/switch': 'switch',
      '/git-control/checkout': 'switch',
      '/git-control/cherry-pick': 'cherry_pick',
      '/git-control/cherry': 'cherry_pick',
      '/git-control/merge': 'merge',
      '/branch': 'branch',
      '/branches': 'branch',
      '/switch': 'switch',
      '/switch-branch': 'switch',
      '/cherry-pick': 'cherry_pick',
      '/cherry': 'cherry_pick',
      '/git/cherry-pick': 'cherry_pick',
      '/merge': 'merge',
      '/git-merge': 'merge',
      '/git/merge': 'merge'
    };

    window.ROUTE_TO_TAB = {
      '/': 'task',
      '/index.html': 'task',
      '/task': 'task',
      '/tasks': 'task',
      '/git-control': 'branch',
      '/git': 'branch',
      '/branch': 'branch',
      '/branches': 'branch',
      '/cherry-pick': 'branch',
      '/cherry': 'branch',
      '/git/cherry-pick': 'branch',
      '/merge': 'branch',
      '/git-merge': 'branch',
      '/git/merge': 'branch',
      '/history': 'log',
      '/log': 'log',
      '/logs': 'log',
      '/diagram': 'diagram',
      '/architecture': 'diagram'
    };

    window.getTabFromUrl = function() {
      try {
        const pathname = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
        if (window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[pathname]) {
          window.initGitSubTab = window.ROUTE_TO_GIT_SUBTAB[pathname];
          return 'branch';
        }
        if (pathname.startsWith('/git-control')) {
          window.initGitSubTab = 'pull_sync';
          return 'branch';
        }
        if (window.ROUTE_TO_TAB[pathname]) return window.ROUTE_TO_TAB[pathname];
      } catch(e) {}
      return null;
    };

    // Xác định tab ban đầu ngay tại <head> để tránh giật giao diện (flicker)
    (function() {
      let initTab = window.getTabFromUrl();
      const path = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
      if (!initTab || path === '/' || path === '/index.html') {
        try {
          const saved = localStorage.getItem('activeAgentStudioTab');
          if (saved && window.TABS.includes(saved)) initTab = saved;
        } catch(e) {}
      }
      if (!initTab || !window.TABS.includes(initTab)) initTab = 'task';
      window.activeTab = initTab;

      // Nhúng style tức thì nếu tab không phải 'task'
      if (initTab !== 'task') {
        document.write('<style id="initialTabStyle">#view_task{display:none!important}#view_' + initTab + '{display:block!important}#tabBtn_task{background:transparent!important;color:#cbd5e1!important;font-weight:500!important}#tabBtn_' + initTab + '{background:#fff!important;color:#182c4f!important;font-weight:700!important}</style>');
      }
      if (initTab === 'branch') {
        const sub = (window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[path]) || window.initGitSubTab || 'pull_sync';
        window.initGitSubTab = sub;
        if (sub !== 'pull_sync') {
          document.write('<style id="initialGitSubTabStyle">#gitSubView_pull_sync{display:none!important}#gitSubView_' + sub + '{display:block!important}#gitSubTabBtn_pull_sync{background:transparent!important;color:#cbd5e1!important;font-weight:500!important}#gitSubTabBtn_' + sub + '{background:rgb(25,156,255)!important;color:#ffffff!important;font-weight:700!important}</style>');
        }
      }
    })();
  </script>
  <style id="studioMainStyles">
    body {
      font-family: 'Be Vietnam Pro', Inter, system-ui, -apple-system, sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      letter-spacing: -0.01em;
      line-height: 1.6;
    }
    pre, code, kbd, samp {
      font-family: 'JetBrains Mono', Consolas, monospace !important;
    }
    pre code {
      background-color: #070c18;
      color: #38bdf8;
      border-radius: 0.5rem;
      padding: 0.85rem 1.15rem;
      display: block;
      overflow-x: auto;
      font-size: 0.85rem;
      line-height: 1.65;
      border: 1px solid #1e293b;
    }
    p code, li code {
      background-color: #1e293b;
      color: #38bdf8;
      border-radius: 0.3rem;
      padding: 0.15rem 0.38rem;
      font-size: 0.84rem;
      font-weight: 500;
    }
    .markdown-body {
      font-family: 'Be Vietnam Pro', Inter, system-ui, sans-serif;
      font-size: 0.92rem;
      line-height: 1.82;
      letter-spacing: 0.012em;
      color: #f1f5f9;
    }
    .markdown-body p {
      margin-bottom: 0.9rem;
      line-height: 1.82;
    }
    .markdown-body ul {
      list-style-type: disc;
      margin-left: 1.5rem;
      margin-bottom: 0.9rem;
      line-height: 1.82;
    }
    .markdown-body ol {
      list-style-type: decimal;
      margin-left: 1.5rem;
      margin-bottom: 0.9rem;
      line-height: 1.82;
    }
    .markdown-body li {
      margin-bottom: 0.45rem;
      line-height: 1.8;
      color: #f1f5f9;
    }
    .markdown-body strong, .markdown-body b {
      font-weight: 700;
      color: #ffffff;
    }
    .markdown-body h1, .markdown-body h2, .markdown-body h3 {
      font-weight: 700;
      color: #ffffff;
      margin-top: 1.1rem;
      margin-bottom: 0.5rem;
      letter-spacing: -0.015em;
    }
    .markdown-body h2 { font-size: 1.08rem; }
    .markdown-body h3 { font-size: 0.98rem; }
    .markdown-body a {
      color: #38bdf8;
      text-decoration: underline;
      text-underline-offset: 2px;
      font-weight: 500;
    }
    .markdown-body a:hover {
      color: #7dd3fc;
    }
    .markdown-body :not(pre) > code {
      background: #1e1e1e;
      border: 1px solid #3c3c3c;
      color: #9cdcfe;
      padding: 0.15rem 0.42rem;
      border-radius: 4px;
      font-size: 0.82rem;
      font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
      font-weight: 500;
    }
    .markdown-body a :not(pre) > code {
      color: #38bdf8;
      border-color: rgba(56, 189, 248, 0.4);
    }
    .markdown-body blockquote {
      border-left: 3px solid #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 0.6rem 0.9rem;
      border-radius: 0 0.375rem 0.375rem 0;
      margin: 0.6rem 0;
      color: #f1f5f9;
    }

    /* ========================================================
       VS CODE DARK+ THEMED CODE BLOCKS & SYNTAX HIGHLIGHTER
       ======================================================== */
    .vscode-editor-card {
      background: #1e1e1e !important;
      border: 1px solid #2d2d2d !important;
      border-radius: 8px;
      overflow: hidden;
      margin: 0.85rem 0;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
      font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
      text-align: left;
    }
    .vscode-editor-card * {
      box-sizing: border-box;
    }
    .vscode-editor-header {
      background: #252526 !important;
      border-bottom: 1px solid #2d2d2d !important;
      padding: 0.35rem 0.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      user-select: none;
    }
    .vscode-mac-dots {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-right: 8px;
    }
    .vscode-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
    }
    .vscode-dot-red { background: #ff5f56; }
    .vscode-dot-yellow { background: #ffbd2e; }
    .vscode-dot-green { background: #27c93f; }

    .vscode-tab {
      background: #1e1e1e !important;
      border-top: 2px solid #007acc !important;
      border-left: 1px solid #2d2d2d;
      border-right: 1px solid #2d2d2d;
      padding: 0.2rem 0.65rem;
      border-radius: 4px 4px 0 0;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      color: #cccccc !important;
      font-size: 11px;
      font-weight: 500;
    }
    .vscode-copy-btn {
      background: #2d2d2d !important;
      border: 1px solid #3c3c3c !important;
      color: #cccccc !important;
      padding: 0.2rem 0.55rem;
      border-radius: 4px;
      font-size: 11px;
      display: flex;
      align-items: center;
      gap: 0.35rem;
      cursor: pointer;
      transition: all 0.15s ease;
      user-select: none;
    }
    .vscode-copy-btn:hover {
      background: #3e3e42 !important;
      color: #ffffff !important;
      border-color: #4f4f54 !important;
    }
    .vscode-copy-btn svg {
      width: 13px;
      height: 13px;
    }
    .vscode-editor-body {
      background: #1e1e1e !important;
      padding: 0.75rem 0.5rem;
      overflow-x: auto;
    }
    .vscode-code-wrap {
      display: flex;
      font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
      font-size: 12px;
      line-height: 1.65;
    }
    .vscode-line-numbers {
      user-select: none;
      text-align: right;
      padding-right: 0.85rem;
      padding-left: 0.35rem;
      color: #858585 !important;
      border-right: 1px solid #333333 !important;
      flex-shrink: 0;
      font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
      font-size: 12px;
      line-height: 1.65;
    }
    .vscode-code-content {
      padding-left: 0.85rem;
      flex: 1;
      overflow-x: auto;
      font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
      font-size: 12px;
      line-height: 1.65;
      white-space: pre;
    }
    .vscode-editor-card pre,
    .vscode-editor-card code {
      background: transparent !important;
      border: none !important;
      padding: 0 !important;
      margin: 0 !important;
      color: inherit !important;
      box-shadow: none !important;
      border-radius: 0 !important;
      font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
      font-size: 12px !important;
      line-height: 1.65 !important;
      white-space: pre !important;
      overflow: visible !important;
    }
    .vscode-code-content pre code {
      color: #d4d4d4 !important;
    }

    /* Scrollbars inside VS Code card */
    .vscode-editor-body::-webkit-scrollbar,
    .vscode-code-content::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    .vscode-editor-body::-webkit-scrollbar-track,
    .vscode-code-content::-webkit-scrollbar-track {
      background: #1e1e1e;
    }
    .vscode-editor-body::-webkit-scrollbar-thumb,
    .vscode-code-content::-webkit-scrollbar-thumb {
      background: #424242;
      border-radius: 4px;
    }
    .vscode-editor-body::-webkit-scrollbar-thumb:hover,
    .vscode-code-content::-webkit-scrollbar-thumb:hover {
      background: #4f4f4f;
    }

    /* Syntax Tokens - VS Code Dark+ */
    .vscode-editor-card .vsc-key { color: #9cdcfe !important; }
    .vscode-editor-card .vsc-string { color: #ce9178 !important; }
    .vscode-editor-card .vsc-number { color: #b5cea8 !important; }
    .vscode-editor-card .vsc-keyword { color: #569cd6 !important; font-weight: 600; }
    .vscode-editor-card .vsc-control { color: #c586c0 !important; font-weight: 600; }
    .vscode-editor-card .vsc-comment { color: #6a9955 !important; font-style: italic; }
    .vscode-editor-card .vsc-func { color: #dcdcaa !important; }
    .vscode-editor-card .vsc-type { color: #4ec9b0 !important; }
    .vscode-editor-card .vsc-bracket-1 { color: #ffd700 !important; }
    .vscode-editor-card .vsc-bracket-2 { color: #da70d6 !important; }
    .vscode-editor-card .vsc-bracket-3 { color: #179fff !important; }
    .vscode-editor-card .vsc-punct { color: #d4d4d4 !important; }

    /* Bảo vệ VS Code Dark Theme trong chế độ Sáng (Light Mode) */
    body.light-mode .vscode-editor-card {
      background: #1e1e1e !important;
      border-color: #2d2d2d !important;
    }
    body.light-mode .vscode-editor-header {
      background: #252526 !important;
      border-bottom-color: #2d2d2d !important;
    }
    body.light-mode .vscode-tab {
      background: #1e1e1e !important;
      color: #cccccc !important;
    }
    body.light-mode .vscode-editor-body {
      background: #1e1e1e !important;
      color: #d4d4d4 !important;
    }
    body.light-mode .vscode-line-numbers {
      color: #858585 !important;
      border-right-color: #333333 !important;
    }
    body.light-mode .vscode-editor-card pre,
    body.light-mode .vscode-editor-card code {
      background: transparent !important;
      background-color: transparent !important;
      border: none !important;
      color: #d4d4d4 !important;
    }
    body.light-mode .vscode-copy-btn {
      background: #2d2d2d !important;
      color: #cccccc !important;
      border-color: #3c3c3c !important;
    }
    body.light-mode .vscode-copy-btn:hover {
      background: #3e3e42 !important;
      color: #ffffff !important;
    }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* Ant Design Button & Form Component System */
    .ant-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      line-height: 1.5715;
      position: relative;
      font-weight: 500;
      white-space: nowrap;
      text-align: center;
      background-image: none;
      border: 1px solid #cbd5e1;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
      user-select: none;
      height: 34px;
      padding: 4px 14px;
      font-size: 13px;
      border-radius: 4px;
      outline: none;
      background-color: #ffffff;
      color: #334155;
      font-family: inherit;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
    .ant-btn:hover,
    .ant-btn:focus,
    .ant-btn:active {
      filter: none !important;
      transform: none !important;
    }
    .ant-btn-primary {
      color: #ffffff !important;
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      box-shadow: 0 2px 4px rgba(25, 156, 255, 0.25) !important;
    }
    .ant-btn-primary:hover, .ant-btn-primary:focus, .ant-btn-primary:active {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      transform: none !important;
    }
    .ant-btn-danger {
      color: #ef4444 !important;
      background-color: #fef2f2 !important;
      border-color: #fca5a5 !important;
    }
    .ant-btn-danger:hover, .ant-btn-danger:focus, .ant-btn-danger:active {
      color: #ef4444 !important;
      background-color: #fef2f2 !important;
      border-color: #fca5a5 !important;
      transform: none !important;
    }

    /* Đường mũi tên sơ đồ kiến trúc (Mermaid Architecture Diagram) */
    #mermaidDiagram svg .edgePath path.path,
    #mermaidDiagram svg .edgePaths path,
    #mermaidDiagram svg .flowchart-link,
    #mermaidDiagram svg g.edgePath > path,
    #mermaidDiagram svg path.flowchart-link {
      stroke: rgb(25, 156, 255) !important;
      stroke-width: 1.8px !important;
      stroke-linecap: round !important;
      stroke-linejoin: round !important;
    }

    /* Frontend sang API: Xanh Cyan nhạt */
    #mermaidDiagram svg g.edgePath[class*="FE_"] > path,
    #mermaidDiagram svg g.edgePath[id*="FE_"] > path {
      stroke: rgb(25, 156, 255) !important;
    }

    /* API sang Backend: Xanh Emerald */
    #mermaidDiagram svg g.edgePath[class*="API_"] > path,
    #mermaidDiagram svg g.edgePath[id*="API_"] > path {
      stroke: #059669 !important;
    }

    /* Đầu mũi tên (Arrowhead) */
    #mermaidDiagram svg marker path,
    #mermaidDiagram svg marker polygon,
    #mermaidDiagram svg .arrowMarkerPath {
      fill: rgb(25, 156, 255) !important;
      stroke: rgb(25, 156, 255) !important;
    }
    #mermaidDiagram svg marker[id*="API_"] path,
    #mermaidDiagram svg g.edgePath[class*="API_"] marker path {
      fill: #059669 !important;
      stroke: #059669 !important;
    }

    /* Nhãn văn bản trên mũi tên */
    #mermaidDiagram svg .edgeLabel {
      background: transparent !important;
    }
    #mermaidDiagram svg .edgeLabel span {
      background-color: #ffffff !important;
      color: rgb(25, 156, 255) !important;
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 11px !important;
      font-weight: 600 !important;
      padding: 2px 7px !important;
      border-radius: 4px !important;
      border: 1px solid #cbd5e1 !important;
      letter-spacing: 0.01em !important;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }

    /* Hover vào khối Node */
    #mermaidDiagram svg .node rect,
    #mermaidDiagram svg .node polygon,
    #mermaidDiagram svg .node circle {
      transition: all 0.2s ease !important;
    }
    #mermaidDiagram svg .node:hover rect,
    #mermaidDiagram svg .node:hover polygon {
      stroke: rgb(25, 156, 255) !important;
      stroke-width: 2px !important;
    }

    /* ====================================================================
       HỆ THỐNG GIAO DIỆN: SÁNG (LIGHT MODE) & TỐI (DARK MODE)
       HEADER LUÔN BẢO TOÀN TÔNG #182c4f
       ==================================================================== */
    body.light-mode {
      background-color: #f8fafc !important;
      color: #0f172a !important;
    }
    body.dark-mode {
      background-color: #0a1220 !important;
      color: #f1f5f9 !important;
    }

    /* Scrollbars theo Mode */
    body.light-mode ::-webkit-scrollbar-track { background: #f1f5f9 !important; }
    body.light-mode ::-webkit-scrollbar-thumb { background: #cbd5e1 !important; border-radius: 3px; }
    body.light-mode ::-webkit-scrollbar-thumb:hover { background: #94a3b8 !important; }

    body.dark-mode ::-webkit-scrollbar-track { background: #0a1220 !important; }
    body.dark-mode ::-webkit-scrollbar-thumb { background: #1e3a66 !important; border-radius: 3px; }
    body.dark-mode ::-webkit-scrollbar-thumb:hover { background: #2d5699 !important; }

    /* Buttons trong Light Mode */
    body.light-mode .ant-btn {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      color: #334155 !important;
    }
    body.light-mode .ant-btn:hover,
    body.light-mode .ant-btn:focus {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      color: #334155 !important;
    }
    body.light-mode .ant-btn-primary {
      color: #ffffff !important;
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      box-shadow: 0 2px 4px rgba(25, 156, 255, 0.25) !important;
    }
    body.light-mode .ant-btn-primary:hover,
    body.light-mode .ant-btn-primary:focus {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
    }

    /* Buttons trong Dark Mode */
    body.dark-mode .ant-btn {
      background-color: #101e38 !important;
      border-color: #244170 !important;
      color: #cbd5e1 !important;
    }
    body.dark-mode .ant-btn:hover,
    body.dark-mode .ant-btn:focus {
      background-color: #101e38 !important;
      border-color: #244170 !important;
      color: #cbd5e1 !important;
    }
    body.dark-mode .ant-btn-primary {
      color: #ffffff !important;
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      box-shadow: 0 2px 4px rgba(25, 156, 255, 0.25) !important;
    }
    body.dark-mode .ant-btn-primary:hover,
    body.dark-mode .ant-btn-primary:focus {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
    }

    /* Quy tắc Light Mode (#FFF và rgb(25, 156, 255)) */
    #notifDropdownMenu,
    body.light-mode #notifDropdownMenu {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
      color: #0f172a !important;
      width: 580px !important;
      max-width: calc(100vw - 24px) !important;
    }
    #notifFilterTabs,
    body.light-mode #notifFilterTabs {
      background-color: #ffffff !important;
      border-bottom-color: #e2e8f0 !important;
    }

    body.light-mode main .bg-\[\#101e38\],
    body.light-mode main .bg-\[\#13223f\],
    body.light-mode #antdModalCard {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05) !important;
    }

    body.light-mode main .bg-\[\#0e192c\],
    body.light-mode main .bg-\[\#0a1222\],
    body.light-mode main input[type="text"],
    body.light-mode main input[type="number"],
    body.light-mode main textarea,
    body.light-mode main select {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      color: #0f172a !important;
    }

    body.light-mode main input::placeholder,
    body.light-mode main textarea::placeholder {
      color: #94a3b8 !important;
    }

    body.light-mode main input:focus,
    body.light-mode main textarea:focus,
    body.light-mode main select:focus {
      border-color: rgb(25, 156, 255) !important;
      box-shadow: 0 0 0 3px rgba(25, 156, 255, 0.15) !important;
      outline: none !important;
    }

    /* Text màu tối cho nền trắng */
    body.light-mode main .text-white,
    body.light-mode main .text-slate-100,
    body.light-mode main .text-slate-200 {
      color: #0f172a !important;
    }
    body.light-mode main .text-slate-300,
    body.light-mode main .text-slate-400 {
      color: #475569 !important;
    }
    body.light-mode main .text-slate-500 {
      color: #64748b !important;
    }
    body.light-mode main .text-cyan-400,
    body.light-mode main .text-cyan-300,
    body.light-mode main .text-\[\#38bdf8\] {
      color: rgb(25, 156, 255) !important;
    }

    /* Đường kẻ viền */
    body.light-mode main .border-\[\#244170\],
    body.light-mode main .border-\[\#2e528f\],
    body.light-mode main .border-\[\#182c4f\] {
      border-color: #e2e8f0 !important;
    }

    /* Thanh sub-header hoặc thanh công cụ trong main */
    body.light-mode main .bg-\[\#182c4f\] {
      background-color: #f8fafc !important;
      border-color: #e2e8f0 !important;
    }

    /* Badges các loại */
    body.light-mode main .bg-cyan-950,
    body.light-mode main .bg-cyan-950\/80,
    body.light-mode main .bg-cyan-950\/70 {
      background-color: rgba(25, 156, 255, 0.08) !important;
      border-color: rgba(25, 156, 255, 0.3) !important;
      color: rgb(25, 156, 255) !important;
    }

    body.light-mode main .bg-emerald-950,
    body.light-mode main .bg-emerald-950\/80,
    body.light-mode main .bg-emerald-950\/70 {
      background-color: #ecfdf5 !important;
      border-color: #a7f3d0 !important;
      color: #059669 !important;
    }

    body.light-mode main .bg-amber-950,
    body.light-mode main .bg-amber-950\/70 {
      background-color: #fffbeb !important;
      border-color: #fde68a !important;
      color: #b45309 !important;
    }

    body.light-mode main .bg-purple-950,
    body.light-mode main .bg-purple-950\/80 {
      background-color: #faf5ff !important;
      border-color: #e9d5ff !important;
      color: #7e22ce !important;
    }

    body.light-mode main .bg-indigo-950,
    body.light-mode main .bg-indigo-950\/70,
    body.light-mode main .bg-indigo-950\/80 {
      background-color: #eef2ff !important;
      border-color: #c7d2fe !important;
      color: #4338ca !important;
    }

    /* Khối code trong feed */
    body.light-mode main pre code,
    body.light-mode main pre {
      background-color: #f8fafc !important;
      color: #0f172a !important;
      border-color: #e2e8f0 !important;
    }

    /* Dropdown chọn skill */
    body.light-mode #taskSkillPickerTrigger {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
    }
    body.light-mode #taskSkillPickerTrigger:hover {
      border-color: rgb(25, 156, 255) !important;
    }
    body.light-mode #taskSkillDropdown {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1) !important;
    }
    body.light-mode #taskSkillDropdown input {
      background-color: #f8fafc !important;
      border-color: #cbd5e1 !important;
      color: #0f172a !important;
    }

    /* Chat turn message cards trong feed */
    body.light-mode #taskFeed div[id^="turnCard_"],
    body.light-mode #taskFeed div[id^="taskTurnCard_"],
    body.light-mode #taskFeed div[id^="fixTurnCard_"] {
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
    }
    body.light-mode #taskFeed div[id^="turnCard_"].bg-\[\#0f172a\],
    body.light-mode #taskFeed div[id^="taskTurnCard_"].bg-\[\#0f172a\],
    body.light-mode #taskFeed div[id^="fixTurnCard_"].bg-\[\#0f172a\] {
      background-color: #f0f9ff !important;
      border-color: #bae6fd !important;
    }
    body.light-mode #taskFeed div[id^="turnCard_"].bg-\[\#091518\],
    body.light-mode #taskFeed div[id^="taskTurnCard_"].bg-\[\#091518\],
    body.light-mode #taskFeed div[id^="fixTurnCard_"].bg-\[\#091518\] {
      background-color: #f0fdf4 !important;
      border-color: #bbf7d0 !important;
    }
    body.light-mode #taskFeed div[id^="taskHeader_"],
    body.light-mode #taskFeed div[id^="fixHeader_"] {
      background-color: #ffffff !important;
      border-color: rgba(25, 156, 255, 0.3) !important;
    }

    /* Markdown body trong Light Mode */
    body.light-mode .markdown-body {
      color: #1e293b !important;
    }
    body.light-mode .markdown-body strong,
    body.light-mode .markdown-body b {
      color: #0f172a !important;
    }
    body.light-mode .markdown-body li {
      color: #1e293b !important;
    }
    body.light-mode .markdown-body h1,
    body.light-mode .markdown-body h2,
    body.light-mode .markdown-body h3 {
      color: #0f172a !important;
    }
    body.light-mode .markdown-body a {
      color: #0284c7 !important;
    }
    body.light-mode .markdown-body a:hover {
      color: #0369a1 !important;
    }
    body.light-mode .markdown-body :not(pre) > code {
      background: #f1f5f9 !important;
      border: 1px solid #cbd5e1 !important;
      color: #0284c7 !important;
    }
    body.light-mode .markdown-body a :not(pre) > code {
      color: #0284c7 !important;
      border-color: #93c5fd !important;
    }
    body.light-mode .markdown-body blockquote {
      border-left-color: #0284c7 !important;
      background: #f0f9ff !important;
      color: #334155 !important;
    }

    /* Thẻ log item */
    body.light-mode #logListContainer > div {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
      box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode #logListContainer > div:hover {
      border-color: rgb(25, 156, 255) !important;
      box-shadow: 0 4px 8px -1px rgba(25, 156, 255, 0.12) !important;
    }

    /* Sơ đồ Diagram toolbar & container */
    body.light-mode #mermaidDiagram {
      background-color: #ffffff !important;
    }
    body.light-mode .absolute.top-3.right-3 {
      background-color: rgba(255, 255, 255, 0.95) !important;
      border-color: #e2e8f0 !important;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }

    /* Diagram Module Detail light mode */
    @keyframes arrowStreamDash {
      0% {
        stroke-dashoffset: 56;
      }
      100% {
        stroke-dashoffset: 0;
      }
    }
    @keyframes arrowTipGlowFeApi {
      0%, 55%, 100% {
        stroke: rgba(56, 189, 248, 0.45);
        filter: none;
      }
      72%, 92% {
        stroke: #a855f7;
        filter: drop-shadow(0 0 4px rgba(168, 85, 247, 0.85));
      }
    }
    @keyframes arrowTipGlowApiBe {
      0%, 55%, 100% {
        stroke: rgba(168, 85, 247, 0.45);
        filter: none;
      }
      72%, 92% {
        stroke: #10b981;
        filter: drop-shadow(0 0 4px rgba(16, 185, 129, 0.85));
      }
    }
    .arrow-stream-line {
      stroke-dasharray: 28 28;
      animation: arrowStreamDash 1.2s linear infinite;
    }
    .arrow-head-fe-api {
      animation: arrowTipGlowFeApi 1.2s linear infinite;
    }
    .arrow-head-api-be {
      animation: arrowTipGlowApiBe 1.2s linear infinite;
    }

    body.light-mode #moduleLookupList .bg-\[\#0e192c\],
    body.light-mode #moduleLookupList .bg-\[\#101e38\] {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
    }
    body.light-mode #moduleLookupList .bg-\[\#0b1626\],
    body.light-mode #moduleLookupList .bg-\[\#0b1424\] {
      background-color: #f8fafc !important;
      border-color: #e2e8f0 !important;
    }
    body.light-mode #moduleLookupList .bg-\[\#121c33\] {
      background-color: #f5f3ff !important;
      border-color: #ddd6fe !important;
    }
    body.light-mode #moduleLookupList .text-cyan-300,
    body.light-mode #moduleLookupList .text-cyan-400 {
      color: #0284c7 !important;
    }
    body.light-mode #moduleLookupList .text-emerald-300,
    body.light-mode #moduleLookupList .text-emerald-400 {
      color: #059669 !important;
    }
    body.light-mode #moduleLookupList .text-purple-200,
    body.light-mode #moduleLookupList .text-purple-300 {
      color: #6b21a8 !important;
    }

    /* Hộp thông báo kết quả (Toast alert) */
    body.light-mode #gitActionAlert {
      background-color: rgba(25, 156, 255, 0.08) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #0369a1 !important;
    }

    /* Nút quay về nhánh trước đó */
    body.light-mode #btnPrevFe, 
    body.light-mode #btnPrevBe {
      background-color: rgba(25, 156, 255, 0.08) !important;
      border-color: rgba(25, 156, 255, 0.35) !important;
      color: rgb(25, 156, 255) !important;
    }
    body.light-mode #btnPrevFe:hover, 
    body.light-mode #btnPrevBe:hover {
      background-color: rgba(25, 156, 255, 0.16) !important;
      border-color: rgb(25, 156, 255) !important;
      color: rgb(15, 136, 235) !important;
    }
    body.light-mode #fePrevBranchLabel, 
    body.light-mode #bePrevBranchLabel {
      color: rgb(25, 156, 255) !important;
    }

    /* Tabs tác vụ song song & filter tabs trong Dark Mode & Light Mode */
    #parallelTaskTabs > div.active-task-tab {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      font-weight: 700 !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25) !important;
    }
    #parallelTaskTabs > div.active-task-tab * {
      color: #ffffff !important;
    }

    body.light-mode #parallelTaskTabs > div {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      color: #334155 !important;
    }
    body.light-mode #parallelTaskTabs > div:hover {
      border-color: rgb(25, 156, 255) !important;
      color: #0f172a !important;
    }
    body.light-mode #parallelTaskTabs > div.active-task-tab {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      font-weight: 700 !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15) !important;
    }
    body.light-mode #parallelTaskTabs > div.active-task-tab * {
      color: #ffffff !important;
    }

    #gitSubTabBtn_branch.active-git-subtab,
    #gitSubTabBtn_cherry_pick.active-git-subtab,
    #gitSubTabBtn_pull_sync.active-git-subtab,
    #gitSubTabBtn_merge.active-git-subtab,
    body.light-mode #gitSubTabBtn_branch.active-git-subtab,
    body.light-mode #gitSubTabBtn_cherry_pick.active-git-subtab,
    body.light-mode #gitSubTabBtn_pull_sync.active-git-subtab,
    body.light-mode #gitSubTabBtn_merge.active-git-subtab,
    body.dark-mode #gitSubTabBtn_branch.active-git-subtab,
    body.dark-mode #gitSubTabBtn_cherry_pick.active-git-subtab,
    body.dark-mode #gitSubTabBtn_pull_sync.active-git-subtab,
    body.dark-mode #gitSubTabBtn_merge.active-git-subtab {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      font-weight: 700 !important;
    }
    #gitSubTabBtn_branch.active-git-subtab *,
    #gitSubTabBtn_cherry_pick.active-git-subtab *,
    #gitSubTabBtn_pull_sync.active-git-subtab *,
    #gitSubTabBtn_merge.active-git-subtab *,
    body.light-mode #gitSubTabBtn_branch.active-git-subtab *,
    body.light-mode #gitSubTabBtn_cherry_pick.active-git-subtab *,
    body.light-mode #gitSubTabBtn_pull_sync.active-git-subtab *,
    body.light-mode #gitSubTabBtn_merge.active-git-subtab *,
    body.dark-mode #gitSubTabBtn_branch.active-git-subtab *,
    body.dark-mode #gitSubTabBtn_cherry_pick.active-git-subtab *,
    body.dark-mode #gitSubTabBtn_pull_sync.active-git-subtab *,
    body.dark-mode #gitSubTabBtn_merge.active-git-subtab * {
      color: #ffffff !important;
    }

    body.light-mode #gitSubTabBtn_branch,
    body.light-mode #gitSubTabBtn_cherry_pick,
    body.light-mode #gitSubTabBtn_pull_sync,
    body.light-mode #gitSubTabBtn_merge {
      border: 1px solid #cbd5e1 !important;
    }

    /* Đảm bảo chữ nút Tiếp tục task luôn là màu trắng #ffffff */
    #btnStartTask,
    #btnStartTask *,
    #btnStartTaskText,
    [id^="sessContinueBox_"] button,
    [id^="sessContinueBox_"] button *,
    body.light-mode #btnStartTask,
    body.light-mode #btnStartTask *,
    body.light-mode #btnStartTaskText,
    body.light-mode [id^="sessContinueBox_"] button,
    body.light-mode [id^="sessContinueBox_"] button * {
      color: #ffffff !important;
    }

    /* Nút Làm mới: Không đổi màu khi hover */
    #btnRefreshGit {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      transform: none !important;
      box-shadow: none !important;
    }
    #btnRefreshGit:hover,
    #btnRefreshGit:focus,
    #btnRefreshGit:active {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      transform: none !important;
      box-shadow: none !important;
    }

    /* Cherry-pick success & error boxes light mode */
    body.light-mode #feCherrySuccessBox,
    body.light-mode #beCherrySuccessBox {
      background-color: #f0fdf4 !important;
      border-color: #86efac !important;
      color: #166534 !important;
    }
    body.light-mode #feCherryErrorBox,
    body.light-mode #beCherryErrorBox {
      background-color: #fef2f2 !important;
      border-color: #fca5a5 !important;
      color: #991b1b !important;
    }
    body.light-mode #feCherryCommitMsgInput,
    body.light-mode #beCherryCommitMsgInput {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      color: #0f172a !important;
    }

    /* Pull Staging / Master - nút không đổi màu khi hover */
    .btn-pull-no-hover {
      transition: none !important;
      cursor: pointer;
      outline: none !important;
    }
    .btn-pull-no-hover:hover,
    .btn-pull-no-hover:active,
    .btn-pull-no-hover:focus {
      filter: none !important;
      transform: none !important;
      box-shadow: none !important;
      opacity: 1 !important;
    }

    .btn-pull-staging-theme,
    .btn-pull-master-theme {
      background-color: rgb(25, 156, 255) !important;
      border: 1px solid rgb(25, 156, 255) !important;
      color: #ffffff !important;
      border-radius: 4px !important;
    }
    .btn-pull-staging-theme:hover,
    .btn-pull-staging-theme:active,
    .btn-pull-staging-theme:focus,
    .btn-pull-master-theme:hover,
    .btn-pull-master-theme:active,
    .btn-pull-master-theme:focus {
      background-color: rgb(25, 156, 255) !important;
      border: 1px solid rgb(25, 156, 255) !important;
      color: #ffffff !important;
    }

    /* Log item active border màu xanh hệ thống khi mở xem chi tiết */
    .log-item-card.log-item-active,
    body.light-mode .log-item-card.log-item-active,
    body.dark-mode .log-item-card.log-item-active {
      border-color: rgb(25, 156, 255) !important;
      box-shadow: 0 0 0 1px rgb(25, 156, 255), 0 2px 8px rgba(25, 156, 255, 0.15) !important;
    }

    /* Tab lọc Lịch sử hoạt động: Nút active nền xanh chữ trắng font-bold */
    #logFilter_all.active-log-filter,
    #logFilter_TASK.active-log-filter,
    #logFilter_GIT.active-log-filter,
    body.light-mode #logFilter_all.active-log-filter,
    body.light-mode #logFilter_TASK.active-log-filter,
    body.light-mode #logFilter_GIT.active-log-filter,
    body.dark-mode #logFilter_all.active-log-filter,
    body.dark-mode #logFilter_TASK.active-log-filter,
    body.dark-mode #logFilter_GIT.active-log-filter {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      font-weight: 700 !important;
    }
    #logFilter_all.active-log-filter *,
    #logFilter_TASK.active-log-filter *,
    #logFilter_GIT.active-log-filter *,
    body.light-mode #logFilter_all.active-log-filter *,
    body.light-mode #logFilter_TASK.active-log-filter *,
    body.light-mode #logFilter_GIT.active-log-filter *,
    body.dark-mode #logFilter_all.active-log-filter *,
    body.dark-mode #logFilter_TASK.active-log-filter *,
    body.dark-mode #logFilter_GIT.active-log-filter * {
      color: #ffffff !important;
    }
    body.light-mode #view_log button[id^="logFilter_"]:not(.active-log-filter) {
      color: #475569 !important;
    }
    body.light-mode #view_log button[id^="logFilter_"]:not(.active-log-filter):hover {
      color: #0f172a !important;
      background-color: rgba(226, 232, 240, 0.6) !important;
    }
    body.dark-mode #view_log button[id^="logFilter_"]:not(.active-log-filter) {
      color: #cbd5e1 !important;
    }
    body.dark-mode #view_log button[id^="logFilter_"]:not(.active-log-filter):hover {
      color: #ffffff !important;
      background-color: rgba(255, 255, 255, 0.08) !important;
    }

    /* Icon thùng rác ở danh sách lịch sử: Nền đỏ, icon màu trắng */
    .log-item-delete-btn,
    body.light-mode .log-item-delete-btn,
    body.dark-mode .log-item-delete-btn {
      background-color: #ef4444 !important;
      color: #ffffff !important;
      border: 1px solid rgba(239, 68, 68, 0.5) !important;
    }
    .log-item-delete-btn:hover,
    body.light-mode .log-item-delete-btn:hover,
    body.dark-mode .log-item-delete-btn:hover {
      background-color: #dc2626 !important;
      border-color: #dc2626 !important;
    }
    .log-item-delete-btn svg,
    .log-item-delete-btn svg *,
    body.light-mode .log-item-delete-btn svg,
    body.light-mode .log-item-delete-btn svg *,
    body.dark-mode .log-item-delete-btn svg,
    body.dark-mode .log-item-delete-btn svg * {
      stroke: #ffffff !important;
      color: #ffffff !important;
    }

    /* Pull Staging / Master & Merge light mode */
    body.light-mode #gitSubView_pull_sync .bg-\[\#101e38\],
    body.light-mode #gitSubView_merge .bg-\[\#101e38\],
    body.light-mode #gitSubView_merge .merge-col-card,
    body.light-mode #gitSubView_merge .merge-info-card {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05) !important;
    }
    body.light-mode #gitSubView_pull_sync .bg-\[\#0e192c\],
    body.light-mode #gitSubView_merge .bg-\[\#0e192c\],
    body.light-mode #gitSubView_merge .merge-branch-box {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
    }
    body.light-mode #gitSubView_merge .border-amber-800\/60,
    body.light-mode #gitSubView_merge .border-cyan-800\/60,
    body.light-mode #gitSubView_merge .border-emerald-800\/60 {
      border-color: #e2e8f0 !important;
    }
    body.light-mode #gitSubView_merge .bg-amber-950 {
      background-color: #fef3c7 !important;
      color: #92400e !important;
      border-color: #fde68a !important;
    }
    body.light-mode #gitSubView_merge .bg-cyan-950 {
      background-color: #e0f2fe !important;
      color: #0369a1 !important;
      border-color: #bae6fd !important;
    }
    body.light-mode #gitSubView_merge .bg-emerald-950 {
      background-color: #dcfce7 !important;
      color: #15803d !important;
      border-color: #bbf7d0 !important;
    }
    body.light-mode #gitSubView_pull_sync .text-slate-100,
    body.light-mode #gitSubView_pull_sync .text-slate-200,
    body.light-mode #gitSubView_merge .text-slate-100,
    body.light-mode #gitSubView_merge .text-slate-200 {
      color: #0f172a !important;
    }
    body.light-mode #gitSubView_pull_sync .text-slate-300,
    body.light-mode #gitSubView_pull_sync .text-slate-400,
    body.light-mode #gitSubView_merge .text-slate-300,
    body.light-mode #gitSubView_merge .text-slate-400 {
      color: #475569 !important;
    }
    body.light-mode #gitSubView_merge input[type="text"],
    body.light-mode #gitSubView_merge select {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      color: #0f172a !important;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode #gitSubView_merge .merge-trigger-btn,
    body.light-mode #feMergeSourceTrigger,
    body.light-mode #feMergeTargetTrigger,
    body.light-mode #beMergeSourceTrigger,
    body.light-mode #beMergeTargetTrigger {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      color: #0f172a !important;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode #gitSubView_merge .merge-trigger-btn:hover,
    body.light-mode #feMergeSourceTrigger:hover,
    body.light-mode #feMergeTargetTrigger:hover,
    body.light-mode #beMergeSourceTrigger:hover,
    body.light-mode #beMergeTargetTrigger:hover {
      border-color: rgb(25, 156, 255) !important;
    }
    body.light-mode #feMergeSuccessBox,
    body.light-mode #beMergeSuccessBox {
      background-color: #ffffff !important;
      border: 1px solid #86efac !important;
      box-shadow: 0 2px 8px rgba(16, 185, 129, 0.08) !important;
    }
    body.light-mode #feMergeSuccessTitle,
    body.light-mode #beMergeSuccessTitle {
      color: #166534 !important;
    }
    body.light-mode #feMergeSuccessText,
    body.light-mode #beMergeSuccessText {
      color: #1e293b !important;
    }
    body.light-mode #feMergeReturnBranchWrap,
    body.light-mode #beMergeReturnBranchWrap,
    body.light-mode #feCherryReturnBranchWrap,
    body.light-mode #beCherryReturnBranchWrap {
      border-top-color: #e2e8f0 !important;
    }
    body.light-mode #feMergeReturnBranchWrap span,
    body.light-mode #beMergeReturnBranchWrap span,
    body.light-mode #feCherryReturnBranchWrap span,
    body.light-mode #beCherryReturnBranchWrap span {
      color: #166534 !important;
    }
    body.light-mode #feMergeConflictBox,
    body.light-mode #beMergeConflictBox {
      background-color: #ffffff !important;
      border: 1px solid #fcd34d !important;
      box-shadow: 0 2px 8px rgba(245, 158, 11, 0.08) !important;
    }
    body.light-mode #feMergeErrorBox,
    body.light-mode #beMergeErrorBox {
      background-color: #ffffff !important;
      border: 1px solid #fecdd3 !important;
      box-shadow: 0 2px 8px rgba(244, 63, 94, 0.08) !important;
    }
    body.light-mode #feSyncResultBox,
    body.light-mode #beSyncResultBox {
      background-color: #f0fdf4 !important;
      border-color: #86efac !important;
      color: #166534 !important;
    }
    body.light-mode #feSyncResultOutput,
    body.light-mode #beSyncResultOutput {
      background-color: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      color: #0f172a !important;
    }

    body.light-mode #feCherryBranchTrigger,
    body.light-mode #feCherrySourceBranchTrigger {
      background-color: #ffffff !important;
      border-color: rgba(25, 156, 255, 0.5) !important;
      color: rgb(15, 136, 235) !important;
    }
    body.light-mode #beCherryBranchTrigger,
    body.light-mode #beCherrySourceBranchTrigger {
      background-color: #ffffff !important;
      border-color: rgba(16, 185, 129, 0.5) !important;
      color: rgb(5, 150, 105) !important;
    }
    body.light-mode #feCherryBranchDropdownMenu,
    body.light-mode #beCherryBranchDropdownMenu,
    body.light-mode #feCherrySourceBranchDropdownMenu,
    body.light-mode #beCherrySourceBranchDropdownMenu,
    body.light-mode #feMergeTargetDropdownMenu,
    body.light-mode #beMergeTargetDropdownMenu,
    body.light-mode #feMergeSourceDropdownMenu,
    body.light-mode #beMergeSourceDropdownMenu {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
    }
    body.light-mode #feCherryBranchSearchInput,
    body.light-mode #beCherryBranchSearchInput,
    body.light-mode #feCherrySourceBranchSearchInput,
    body.light-mode #beCherrySourceBranchSearchInput,
    body.light-mode #feMergeTargetSearchInput,
    body.light-mode #beMergeTargetSearchInput,
    body.light-mode #feMergeSourceSearchInput,
    body.light-mode #beMergeSourceSearchInput {
      background-color: #f8fafc !important;
      border-color: #cbd5e1 !important;
      color: #0f172a !important;
    }
    body.light-mode .cherry-branch-opt,
    body.light-mode .merge-branch-opt {
      color: #334155 !important;
    }
    body.light-mode .cherry-branch-opt:hover,
    body.light-mode .merge-branch-opt:hover {
      background-color: #f1f5f9 !important;
      color: #0f172a !important;
    }
    body.light-mode .cherry-branch-opt.active-branch,
    body.light-mode .merge-branch-opt.active-branch {
      background-color: rgba(25, 156, 255, 0.12) !important;
      color: rgb(15, 136, 235) !important;
      font-weight: 700 !important;
    }

    body.dark-mode #feCherryBranchDropdownMenu,
    body.dark-mode #beCherryBranchDropdownMenu,
    body.dark-mode #feCherrySourceBranchDropdownMenu,
    body.dark-mode #beCherrySourceBranchDropdownMenu,
    body.dark-mode #feMergeTargetDropdownMenu,
    body.dark-mode #beMergeTargetDropdownMenu,
    body.dark-mode #feMergeSourceDropdownMenu,
    body.dark-mode #beMergeSourceDropdownMenu {
      background-color: #101e38 !important;
      border-color: #244170 !important;
      box-shadow: 0 15px 30px rgba(0, 0, 0, 0.5) !important;
    }
    body.dark-mode #feCherryBranchSearchInput,
    body.dark-mode #beCherryBranchSearchInput,
    body.dark-mode #feCherrySourceBranchSearchInput,
    body.dark-mode #beCherrySourceBranchSearchInput,
    body.dark-mode #feMergeTargetSearchInput,
    body.dark-mode #beMergeTargetSearchInput,
    body.dark-mode #feMergeSourceSearchInput,
    body.dark-mode #beMergeSourceSearchInput {
      background-color: #0e192c !important;
      border-color: #244170 !important;
      color: #f1f5f9 !important;
    }
    body.dark-mode .cherry-branch-opt,
    body.dark-mode .merge-branch-opt {
      color: #cbd5e1 !important;
    }
    body.dark-mode .cherry-branch-opt:hover,
    body.dark-mode .merge-branch-opt:hover {
      background-color: #182c4f !important;
      color: #ffffff !important;
    }
    body.dark-mode .cherry-branch-opt.active-branch,
    body.dark-mode .merge-branch-opt.active-branch {
      background-color: rgba(6, 182, 212, 0.2) !important;
      color: #38bdf8 !important;
      font-weight: 700 !important;
    }

    body.light-mode #feCherryTopBranch {
      background-color: rgba(25, 156, 255, 0.1) !important;
      border-color: rgba(25, 156, 255, 0.35) !important;
      color: rgb(15, 136, 235) !important;
    }
    body.light-mode #beCherryTopBranch {
      background-color: rgba(16, 185, 129, 0.1) !important;
      border-color: rgba(16, 185, 129, 0.35) !important;
      color: rgb(5, 150, 105) !important;
    }
    body.light-mode #feedTaskFilterTabs {
      background-color: #f1f5f9 !important;
      border-color: #cbd5e1 !important;
    }
    body.light-mode #feedTaskFilterTabs button {
      color: #475569 !important;
    }
    body.light-mode #feedTaskFilterTabs button.bg-\[\#199cff\] {
      background-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
    }

    /* Hover hoặc khi chọn các skill trong Thiết lập tác vụ: background màu xanh chủ đạo, chữ trắng */
    .skill-option-item:hover,
    .skill-option-item.is-selected,
    #taskSkillOptionList > div:hover,
    #taskSkillOptionList > div.is-selected,
    body.light-mode #taskSkillOptionList > div:hover,
    body.light-mode #taskSkillOptionList > div.is-selected {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
    }
    .skill-option-item:hover *,
    .skill-option-item.is-selected *,
    #taskSkillOptionList > div:hover *,
    #taskSkillOptionList > div.is-selected *,
    body.light-mode #taskSkillOptionList > div:hover *,
    body.light-mode #taskSkillOptionList > div.is-selected * {
      color: #ffffff !important;
    }
    .skill-option-item:hover .skill-group,
    .skill-option-item.is-selected .skill-group,
    #taskSkillOptionList > div:hover .skill-group,
    #taskSkillOptionList > div.is-selected .skill-group,
    body.light-mode #taskSkillOptionList > div:hover .skill-group,
    body.light-mode #taskSkillOptionList > div.is-selected .skill-group {
      background-color: rgba(255, 255, 255, 0.25) !important;
      border-color: rgba(255, 255, 255, 0.5) !important;
      color: #ffffff !important;
    }
    .skill-option-item:hover .skill-desc,
    .skill-option-item.is-selected .skill-desc,
    #taskSkillOptionList > div:hover .skill-desc,
    #taskSkillOptionList > div.is-selected .skill-desc,
    body.light-mode #taskSkillOptionList > div:hover .skill-desc,
    body.light-mode #taskSkillOptionList > div.is-selected .skill-desc {
      color: rgba(255, 255, 255, 0.9) !important;
    }

    body.light-mode #taskSkillOptionList > div:not(.is-selected):not(:hover) .skill-name {
      color: #0f172a !important;
    }
    body.light-mode #taskSkillOptionList > div:not(.is-selected):not(:hover) .skill-desc {
      color: #64748b !important;
    }

    /* Các tag được chọn trong Skill trọng tâm: background màu xanh, chữ trắng */
    #taskSelectedTags > span,
    body.light-mode #taskSelectedTags > span {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      box-shadow: 0 1px 3px rgba(25, 156, 255, 0.3) !important;
    }
    #taskSelectedTags > span *,
    body.light-mode #taskSelectedTags > span * {
      color: #ffffff !important;
    }
    #taskSelectedTags > span:hover,
    body.light-mode #taskSelectedTags > span:hover {
      background-color: rgb(15, 138, 235) !important;
      border-color: rgb(15, 138, 235) !important;
      color: #ffffff !important;
    }
    #taskSelectedTags > span button {
      color: rgba(255, 255, 255, 0.85) !important;
    }
    #taskSelectedTags > span button:hover {
      color: #ffffff !important;
      transform: scale(1.15);
    }

    /* Badge Đồng bộ Git (Pull) - GIT_SYNC_PULL */
    .badge-git-sync-pull {
      background-color: rgba(25, 156, 255, 0.18) !important;
      border: 1px solid rgba(25, 156, 255, 0.45) !important;
      color: #38bdf8 !important;
    }
    body.dark-mode .badge-git-sync-pull {
      background-color: rgba(25, 156, 255, 0.18) !important;
      border: 1px solid rgba(25, 156, 255, 0.45) !important;
      color: #38bdf8 !important;
    }
    body.light-mode .badge-git-sync-pull {
      background-color: #f0f9ff !important;
      border: 1px solid #bae6fd !important;
      color: #0284c7 !important;
    }

    /* Commits preview box trong Pull Staging / Master */
    .commit-item-card {
      border: 1px solid rgba(255, 255, 255, 0.08) !important;
      background-color: rgba(255, 255, 255, 0.02) !important;
    }
    .commit-item-card:hover {
      background-color: rgba(255, 255, 255, 0.05) !important;
    }
    .commit-detail-box {
      background-color: rgba(0, 0, 0, 0.3) !important;
      border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    .sync-file-item {
      background-color: rgba(0, 0, 0, 0.4) !important;
      border: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    .sync-file-path {
      color: #38bdf8 !important;
      transition: color 0.15s ease;
    }
    .sync-diff-wrapper {
      background-color: #1e1e1e !important;
      border: 1px solid #333333 !important;
      border-radius: 6px !important;
      max-height: 520px !important;
      min-height: 140px;
      overflow: auto !important;
      box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.4) !important;
    }

    body.light-mode .sync-diff-wrapper {
      background-color: #1e1e1e !important;
      border: 1px solid #333333 !important;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12), inset 0 1px 2px rgba(0, 0, 0, 0.3) !important;
    }

    .sync-diff-wrapper .git-diff-container,
    .sync-diff-wrapper .vscode-diff-editor,
    body.light-mode .sync-diff-wrapper .git-diff-container,
    body.light-mode .sync-diff-wrapper .vscode-diff-editor {
      background-color: #1e1e1e !important;
      border: none !important;
      border-radius: 0 !important;
      color: #d4d4d4 !important;
      font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
      font-size: 11.5px !important;
      line-height: 1.6 !important;
    }

    .sync-diff-wrapper .git-diff-hunk,
    body.light-mode .sync-diff-wrapper .git-diff-hunk {
      background-color: #252526 !important;
      color: #569cd6 !important;
      border-top: 1px solid #333333 !important;
      border-bottom: 1px solid #333333 !important;
      font-size: 11px !important;
      font-weight: 600 !important;
    }

    .sync-diff-wrapper .git-diff-row,
    body.light-mode .sync-diff-wrapper .git-diff-row {
      display: flex !important;
      align-items: stretch !important;
      min-width: 100% !important;
      width: max-content !important;
      font-family: 'JetBrains Mono', Consolas, monospace !important;
    }

    .sync-diff-wrapper .git-diff-row:hover,
    body.light-mode .sync-diff-wrapper .git-diff-row:hover {
      background-color: rgba(255, 255, 255, 0.05) !important;
    }

    .sync-diff-wrapper .git-diff-ln,
    body.light-mode .sync-diff-wrapper .git-diff-ln {
      width: 42px !important;
      min-width: 42px !important;
      padding: 0 8px !important;
      text-align: right !important;
      user-select: none !important;
      font-size: 11px !important;
      color: #858585 !important;
      border-right: 1px solid #2d2d2d !important;
      background-color: #1e1e1e !important;
    }

    .sync-diff-wrapper .git-diff-sign,
    body.light-mode .sync-diff-wrapper .git-diff-sign {
      width: 22px !important;
      min-width: 22px !important;
      text-align: center !important;
      user-select: none !important;
      font-weight: 700 !important;
      font-size: 12px !important;
      color: #858585 !important;
    }

    .sync-diff-wrapper .git-diff-code,
    body.light-mode .sync-diff-wrapper .git-diff-code {
      padding: 0 14px 0 6px !important;
      white-space: pre !important;
      flex: 1 !important;
      font-family: 'JetBrains Mono', Consolas, monospace !important;
      color: #d4d4d4 !important;
    }

    .sync-diff-wrapper .git-diff-ctx .git-diff-code,
    body.light-mode .sync-diff-wrapper .git-diff-ctx .git-diff-code {
      color: #d4d4d4 !important;
    }

    .sync-diff-wrapper .git-diff-add,
    body.light-mode .sync-diff-wrapper .git-diff-add {
      background-color: rgba(46, 160, 67, 0.18) !important;
      border-left: 3px solid #2ea043 !important;
    }
    .sync-diff-wrapper .git-diff-add .git-diff-ln,
    body.light-mode .sync-diff-wrapper .git-diff-add .git-diff-ln {
      background-color: rgba(46, 160, 67, 0.25) !important;
      color: #73c991 !important;
    }
    .sync-diff-wrapper .git-diff-add .git-diff-sign,
    body.light-mode .sync-diff-wrapper .git-diff-add .git-diff-sign {
      color: #73c991 !important;
    }
    .sync-diff-wrapper .git-diff-add .git-diff-code,
    body.light-mode .sync-diff-wrapper .git-diff-add .git-diff-code {
      color: #e6edf3 !important;
    }

    .sync-diff-wrapper .git-diff-del,
    body.light-mode .sync-diff-wrapper .git-diff-del {
      background-color: rgba(248, 81, 73, 0.18) !important;
      border-left: 3px solid #f85149 !important;
    }
    .sync-diff-wrapper .git-diff-del .git-diff-ln,
    body.light-mode .sync-diff-wrapper .git-diff-del .git-diff-ln {
      background-color: rgba(248, 81, 73, 0.25) !important;
      color: #ffa198 !important;
    }
    .sync-diff-wrapper .git-diff-del .git-diff-sign,
    body.light-mode .sync-diff-wrapper .git-diff-del .git-diff-sign {
      color: #ffa198 !important;
    }
    .sync-diff-wrapper .git-diff-del .git-diff-code,
    body.light-mode .sync-diff-wrapper .git-diff-del .git-diff-code {
      color: #e6edf3 !important;
    }

    .sync-diff-wrapper::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    .sync-diff-wrapper::-webkit-scrollbar-track {
      background: #1e1e1e;
    }
    .sync-diff-wrapper::-webkit-scrollbar-thumb {
      background: #424242;
      border-radius: 4px;
    }
    .sync-diff-wrapper::-webkit-scrollbar-thumb:hover {
      background: #555555;
    }

    .sync-file-view-btn {
      color: #38bdf8 !important;
    }
    body.light-mode .sync-file-view-btn {
      color: #0284c7 !important;
    }
    body.light-mode .sync-file-view-btn:hover {
      background-color: #f0f9ff !important;
      color: #0369a1 !important;
    }

    .sync-diff-view-full-btn {
      color: #38bdf8 !important;
      border-color: rgba(56, 189, 248, 0.3) !important;
    }
    body.light-mode .sync-diff-view-full-btn {
      color: #0284c7 !important;
      border-color: #bae6fd !important;
      background-color: #f0f9ff !important;
    }
    body.light-mode .sync-diff-view-full-btn:hover {
      background-color: #e0f2fe !important;
      color: #0369a1 !important;
    }

    body.light-mode #gitSubView_pull_sync .sync-commits-box {
      background-color: #f8fafc !important;
      border-color: #cbd5e1 !important;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode .commit-item-card {
      border: 1px solid #e2e8f0 !important;
      background-color: #ffffff !important;
      box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
    }
    body.light-mode .commit-item-card:hover {
      background-color: #f1f5f9 !important;
    }
    body.light-mode .commit-detail-box {
      background-color: #f8fafc !important;
      border-top: 1px solid #e2e8f0 !important;
    }
    body.light-mode .sync-file-item {
      background-color: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
    }
    body.light-mode .sync-file-path {
      color: #0958d9 !important;
      font-weight: 600 !important;
    }
    body.light-mode .sync-file-path:hover {
      color: #1677ff !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .text-amber-300,
    body.light-mode #gitSubView_pull_sync .sync-commits-box .text-amber-200,
    body.light-mode #gitSubView_pull_sync .sync-commit-header {
      color: #b45309 !important;
      font-weight: 700 !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .text-amber-400 {
      color: #d97706 !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .border-amber-500\/20,
    body.light-mode #gitSubView_pull_sync .sync-commits-box .border-amber-500\/30 {
      border-color: #fde68a !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .bg-cyan-950\/80 {
      background-color: #eff6ff !important;
      color: #1d4ed8 !important;
      border: 1px solid #bfdbfe !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .text-cyan-400 {
      color: #0284c7 !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .text-slate-200 {
      color: #0f172a !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .text-slate-300 {
      color: #334155 !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .text-slate-400 {
      color: #64748b !important;
    }
    body.light-mode #gitSubView_pull_sync .sync-commits-box .hover\:bg-white\/5:hover {
      background-color: rgba(0, 0, 0, 0.05) !important;
    }
    body.light-mode #syncCheckSummaryBadge {
      background-color: #f1f5f9 !important;
      border-color: #cbd5e1 !important;
      color: #334155 !important;
    }

    /* Container tiến trình xử lý ngầm trong Light Mode */
    body.light-mode .tool-step-box {
      background-color: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode .tool-step-box > div:first-child,
    body.light-mode .tool-step-header {
      background-color: #ffffff !important;
      border-bottom: 1px solid #f1f5f9 !important;
      color: #0f172a !important;
    }
    body.light-mode .tool-step-header span.text-white {
      color: #0f172a !important;
    }
    body.light-mode div[id^="stepLogsBody_"] {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
      color: #0f172a !important;
    }
    body.light-mode .tool-step-item,
    body.light-mode .terminal-step-item {
      background-color: #ffffff !important;
      border: 1px solid #f1f5f9 !important;
      color: #0f172a !important;
    }
    body.light-mode .terminal-step-item:hover {
      background-color: #fafbfc !important;
      border-color: #e2e8f0 !important;
    }
    body.light-mode .tool-step-item span.text-slate-200,
    body.light-mode .terminal-step-item span.text-slate-100 {
      color: #0f172a !important;
    }
    body.light-mode .terminal-step-item div[id^="step_out_"] {
      background-color: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      color: #1e293b !important;
      box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02) !important;
    }
    body.light-mode .step-out-header {
      border-bottom-color: #f1f5f9 !important;
    }
    body.light-mode .step-grep-row:hover {
      background-color: #f0f7ff !important;
    }
    body.light-mode .step-grep-file {
      color: #1677ff !important;
      font-weight: 600 !important;
    }
    body.light-mode .step-grep-line {
      background-color: #fffbe6 !important;
      border: 1px solid #ffe58f !important;
      color: #d48806 !important;
      font-weight: 700 !important;
    }
    body.light-mode .step-grep-code {
      color: #1e293b !important;
    }
    body.light-mode .streaming-step-preview {
      background-color: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
      color: #0958d9 !important;
    }
    body.light-mode .streaming-step-preview span.text-slate-200,
    body.light-mode .streaming-step-preview span.truncate {
      color: #334155 !important;
    }
    body.light-mode .streaming-step-preview .text-cyan-400 {
      color: #1677ff !important;
    }
    body.light-mode div[id$="_running"] {
      background-color: #ffffff !important;
      border: 1px solid #bfdbfe !important;
    }
    body.light-mode div[id$="_running"] .bg-\[\#060a12\] {
      background-color: #ffffff !important;
      border: 1px solid #e2e8f0 !important;
    }
    body.light-mode div[id$="_running"] .text-cyan-400,
    body.light-mode div[id$="_running"] .text-cyan-300 {
      color: #0284c7 !important;
    }
    body.light-mode div[id$="_running"] .text-slate-400 {
      color: #64748b !important;
    }
    body.light-mode div[id^="sessWrap_"] {
      background-color: transparent !important;
      border: none !important;
      padding: 0 !important;
      box-shadow: none !important;
    }
    div[id^="sessWrap_"] {
      background-color: transparent !important;
      border: none !important;
      padding: 0 !important;
      box-shadow: none !important;
    }
    div[id^="sessHeader_"],
    body.light-mode div[id^="sessHeader_"] {
      background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%) !important;
      border: 1px solid #1677ff !important;
      color: #ffffff !important;
      box-shadow: 0 4px 14px rgba(22, 119, 255, 0.2) !important;
    }
    body.light-mode div[id^="sessHeader_"] .text-slate-100,
    body.light-mode div[id^="sessHeader_"] .text-slate-200,
    body.light-mode div[id^="sessHeader_"] .text-slate-300,
    body.light-mode div[id^="sessHeader_"] .text-white {
      color: #ffffff !important;
    }

    /* Header Notification Bell & Dropdown in Light Mode */
    #notifBellBtn,
    body.light-mode #notifBellBtn {
      background-color: transparent !important;
      border: none !important;
      color: #ffffff !important;
      box-shadow: none !important;
    }
    #notifBellBtn:hover,
    body.light-mode #notifBellBtn:hover {
      background-color: rgba(255, 255, 255, 0.12) !important;
      color: #ffffff !important;
    }
    #notifBadge,
    body.light-mode #notifBadge {
      border-color: #182c4f !important;
    }
    body.light-mode #notifDropdownMenu,
    #notifDropdownMenu {
      background-color: #ffffff !important;
      border-color: #cbd5e1 !important;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08) !important;
      width: 580px !important;
      max-width: calc(100vw - 24px) !important;
    }
    #notifDropdownMenu > div:first-child {
      background-color: #f8fafc !important;
      border-color: #e2e8f0 !important;
    }
    #notifDropdownMenu > div:first-child span.text-black {
      color: #000000 !important;
      font-weight: 700 !important;
    }
    #notifFilterTabs {
      background-color: #ffffff !important;
      border-bottom-color: #e2e8f0 !important;
    }
    #notifItemsList {
      background-color: #ffffff !important;
    }
    #notifItemsList .notif-item {
      transition: background-color 0.15s ease;
    }
    #notifItemsList .notif-item:hover {
      background-color: #eef7ff !important;
    }
    #notifItemsList .notif-item.is-unread:hover {
      background-color: #e0f0ff !important;
    }
    #notifItemsList .text-black {
      color: #000000 !important;
      font-weight: 700 !important;
    }
    .notif-tag-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      flex-shrink: 0;
      cursor: pointer;
      user-select: none;
      transition: all 0.15s ease;
    }
    .notif-tag-done {
      background-color: #f6ffed !important;
      border: 1px solid #b7eb8f !important;
      color: #389e0d !important;
    }
    .notif-tag-done:hover {
      background-color: #d9f7be !important;
    }
    .notif-tag-running {
      background-color: #fffbe6 !important;
      border: 1px solid #ffe58f !important;
      color: #d48806 !important;
    }
    .notif-tag-running:hover {
      background-color: #fff1b8 !important;
    }
    .notif-tag-stopped {
      background-color: #e6f4ff !important;
      border: 1px solid #91caff !important;
      color: #1677ff !important;
    }
    .notif-tag-stopped:hover {
      background-color: #bae0ff !important;
    }
    .notif-tag-default {
      background-color: #f1f5f9 !important;
      border: 1px solid #cbd5e1 !important;
      color: #475569 !important;
    }
    .notif-tag-git-pull {
      background-color: #fffbe6 !important;
      border: 1px solid #ffe58f !important;
      color: #d48806 !important;
    }
    .notif-tag-git-pull:hover {
      background-color: #fff1b8 !important;
    }
    .notif-tag-git-done {
      background-color: #f6ffed !important;
      border: 1px solid #b7eb8f !important;
      color: #389e0d !important;
    }
    .notif-item.is-unread .notif-item-title,
    .notif-item.is-unread .notif-title-done,
    .notif-item.is-unread .notif-title-running,
    .notif-item.is-unread .notif-title-stopped,
    .notif-item.is-unread .notif-title-default {
      color: #1677ff !important;
    }
    .notif-item .notif-item-title,
    .notif-item .notif-title-done,
    .notif-item .notif-title-running,
    .notif-item .notif-title-stopped,
    .notif-item .notif-title-default {
      color: #94a3b8 !important;
    }

    /* Modal Dialog */
    body.light-mode #antdModalCard {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
      color: #0f172a !important;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
    }
    body.light-mode #antdModalTitle {
      color: #0f172a !important;
    }
    body.light-mode #antdModalContent {
      color: #475569 !important;
    }
    body.light-mode #antdModalRoot {
      background-color: rgba(15, 23, 42, 0.45) !important;
    }

    /* Dark Mode Defaults */
    body.dark-mode #mermaidDiagram {
      background-color: #0d1726 !important;
    }
    body.dark-mode .absolute.top-3.right-3 {
      background-color: rgba(16, 30, 56, 0.95) !important;
      border-color: #244170 !important;
    }
    body.dark-mode #gitActionAlert {
      background-color: rgba(36, 65, 112, 0.3) !important;
      border-color: #244170 !important;
      color: #38bdf8 !important;
    }
    body.dark-mode #btnPrevFe, 
    body.dark-mode #btnPrevBe {
      background-color: #182c4f !important;
      border-color: #2e528f !important;
      color: #38bdf8 !important;
    }
    body.dark-mode #btnPrevFe:hover, 
    body.dark-mode #btnPrevBe:hover {
      background-color: #244170 !important;
      color: #ffffff !important;
    }
    body.dark-mode #antdModalCard {
      background-color: #101e38 !important;
      border-color: #244170 !important;
      color: #f1f5f9 !important;
    }
    body.dark-mode #antdModalTitle {
      color: #ffffff !important;
    }
    body.dark-mode #antdModalContent {
      color: #94a3b8 !important;
    }

    /* Toast thông báo: Nền trắng, chữ đen cho toàn bộ chế độ */
    #studioToast,
    body.dark-mode #studioToast,
    body.light-mode #studioToast {
      background-color: #ffffff !important;
      color: #0f172a !important;
      border: 1px solid #cbd5e1 !important;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
    }
    #studioToast span,
    body.dark-mode #studioToast span,
    body.light-mode #studioToast span {
      color: #0f172a !important;
    }

    /* Nút xác nhận modal: Không xử lý hover / không đổi màu khi hover */
    #antdModalOkBtn,
    #antdModalOkBtn:hover,
    #antdModalOkBtn:focus,
    #antdModalOkBtn:active {
      background-color: rgb(25, 156, 255) !important;
      border-color: rgb(25, 156, 255) !important;
      color: #ffffff !important;
      outline: none !important;
      box-shadow: none !important;
      transform: none !important;
    }

    /* BẢO TOÀN HEADER - TUYỆT ĐỐI KHÔNG THAY ĐỔI THEO YÊU CẦU */
    header {
      background-color: #182c4f !important;
      border-bottom: 1px solid #244170 !important;
      color: #ffffff !important;
    }
    header .bg-\[\#101e38\] {
      background-color: #101e38 !important;
      border-color: #244170 !important;
      color: #cbd5e1 !important;
    }
    header .bg-\[\#0d1c33\] {
      background-color: #0d1c33 !important;
      border-color: #244170 !important;
    }
    header .text-slate-300 {
      color: #cbd5e1 !important;
    }
    header .text-slate-200 {
      color: #e2e8f0 !important;
    }
    header .text-white {
      color: #ffffff !important;
    }
    header .border-\[\#244170\] {
      border-color: #244170 !important;
    }

    /* Đảm bảo class hidden luôn có độ ưu tiên cao nhất, không bị grid/flex đè */
    .hidden {
      display: none !important;
    }

    /* Căn chỉnh chuẩn justify-between cho 3 cột Chi tiết Module: Frontend ↔ API Contract ↔ Backend */
    .diagram-flow-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 76px minmax(0, 1.35fr) 76px minmax(0, 1fr);
      align-items: center;
      gap: 0.375rem;
      width: 100%;
    }
    @media (max-width: 1023px) {
      .diagram-flow-grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }
    .diagram-col-box {
      display: flex !important;
      align-items: center !important;
      justify-content: space-between !important;
      width: 100% !important;
      gap: 0.5rem;
    }

    /* ====================================================================
       GIT DIFF VIEWER (CHUẨN MÀU ĐỎ / XANH LÁ NHƯ GITHUB / GITLAB)
       ==================================================================== */
    .git-diff-container {
      background-color: #0d1117 !important;
      border: 1px solid #30363d !important;
      border-radius: 6px !important;
      overflow-x: auto !important;
      font-family: 'JetBrains Mono', Consolas, monospace !important;
      font-size: 11.5px !important;
      line-height: 1.55 !important;
    }
    .git-diff-row {
      display: flex;
      align-items: stretch;
      min-width: 100%;
      width: max-content;
    }
    .git-diff-ln {
      width: 38px;
      min-width: 38px;
      padding: 0 6px;
      text-align: right;
      user-select: none;
      font-size: 10.5px;
      opacity: 0.65;
      border-right: 1px solid rgba(148, 163, 184, 0.16);
      flex-shrink: 0;
    }
    .git-diff-sign {
      width: 22px;
      min-width: 22px;
      text-align: center;
      user-select: none;
      font-weight: 700;
      flex-shrink: 0;
    }
    .git-diff-code {
      padding: 0 10px 0 4px;
      white-space: pre;
      flex: 1;
    }

    /* Dòng thêm mới (+): Xanh lá Git */
    .git-diff-add {
      background-color: rgba(46, 160, 67, 0.22) !important;
      border-left: 3px solid #2ea043 !important;
    }
    .git-diff-add .git-diff-ln {
      background-color: rgba(46, 160, 67, 0.32) !important;
      color: #7ee787 !important;
      opacity: 0.9;
    }
    .git-diff-add .git-diff-sign,
    .git-diff-add .git-diff-code {
      color: #7ee787 !important;
      font-weight: 500;
    }

    /* Dòng xóa đi (-): Đỏ Git */
    .git-diff-del {
      background-color: rgba(248, 81, 73, 0.22) !important;
      border-left: 3px solid #f85149 !important;
    }
    .git-diff-del .git-diff-ln {
      background-color: rgba(248, 81, 73, 0.32) !important;
      color: #ffa198 !important;
      opacity: 0.9;
    }
    .git-diff-del .git-diff-sign,
    .git-diff-del .git-diff-code {
      color: #ffa198 !important;
      font-weight: 500;
    }

    /* Dòng Hunk Header (@@ -a,b +c,d @@) */
    .git-diff-hunk {
      background-color: rgba(56, 139, 253, 0.15) !important;
      color: #79c0ff !important;
      padding: 2px 10px !important;
      font-weight: 600 !important;
      border-top: 1px solid rgba(56, 139, 253, 0.25);
      border-bottom: 1px solid rgba(56, 139, 253, 0.25);
    }

    /* Dòng ngữ cảnh (Context) */
    .git-diff-ctx {
      background-color: transparent !important;
      border-left: 3px solid transparent !important;
    }
    .git-diff-ctx .git-diff-ln {
      color: #6e7681 !important;
    }
    .git-diff-ctx .git-diff-sign,
    .git-diff-ctx .git-diff-code {
      color: #c9d1d9 !important;
    }

    /* Light Mode cho Git Diff Box & Các dòng Đỏ / Xanh */
    body.light-mode .changed-files-box {
      background-color: #ffffff !important;
      border-color: #d0d7de !important;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }
    body.light-mode .changed-files-box > .changed-files-header {
      background-color: #f6f8fa !important;
      border-bottom-color: #d0d7de !important;
      color: #1f2328 !important;
    }
    body.light-mode .changed-file-card {
      background-color: #ffffff !important;
      border-color: #d0d7de !important;
    }
    body.light-mode .changed-file-header {
      background-color: #f6f8fa !important;
      border-bottom-color: #d0d7de !important;
    }
    .file-tag-preexisting {
      color: #facc15 !important;
      background-color: rgba(234, 179, 8, 0.15) !important;
      border: 1px solid rgba(234, 179, 8, 0.35) !important;
    }
    body.light-mode .file-tag-preexisting {
      color: #b45309 !important;
      background-color: #fef3c7 !important;
      border: 1px solid #fcd34d !important;
    }
    .file-tag-ai {
      color: #60a5fa !important;
      background-color: rgba(59, 130, 246, 0.15) !important;
      border: 1px solid rgba(59, 130, 246, 0.35) !important;
    }
    body.light-mode .file-tag-ai {
      color: #1d4ed8 !important;
      background-color: #eff6ff !important;
      border: 1px solid #bfdbfe !important;
    }
    .file-edit-btn {
      color: #38bdf8 !important;
    }
    body.light-mode .file-edit-btn {
      color: #0284c7 !important;
    }
    body.light-mode .file-edit-btn:hover {
      background-color: #f0f9ff !important;
      color: #0369a1 !important;
    }
    body.light-mode .git-diff-container {
      background-color: #ffffff !important;
      border-color: #d0d7de !important;
    }
    body.light-mode .git-diff-add {
      background-color: #dafbe1 !important;
      border-left: 3px solid #1a7f37 !important;
    }
    body.light-mode .git-diff-add .git-diff-ln {
      background-color: #aceebb !important;
      color: #116329 !important;
    }
    body.light-mode .git-diff-add .git-diff-sign,
    body.light-mode .git-diff-add .git-diff-code {
      color: #116329 !important;
    }
    body.light-mode .git-diff-del {
      background-color: #ffebe9 !important;
      border-left: 3px solid #cf222e !important;
    }
    body.light-mode .git-diff-del .git-diff-ln {
      background-color: #ffcecb !important;
      color: #a40e26 !important;
    }
    body.light-mode .git-diff-del .git-diff-sign,
    body.light-mode .git-diff-del .git-diff-code {
      color: #a40e26 !important;
    }
    body.light-mode .git-diff-hunk {
      background-color: #ddf4ff !important;
      color: #0969da !important;
      border-top-color: #b6e3ff !important;
      border-bottom-color: #b6e3ff !important;
    }
    body.light-mode .git-diff-ctx .git-diff-ln {
      color: #6e7781 !important;
    }
    body.light-mode .git-diff-ctx .git-diff-sign,
    body.light-mode .git-diff-ctx .git-diff-code {
      color: #1f2328 !important;
    }
    /* Badge +N (Xanh) và -N (Đỏ) luôn giữ đúng màu trong cả Light & Dark mode */
    .git-stat-add,
    body.light-mode main .git-stat-add,
    body.dark-mode main .git-stat-add {
      background-color: rgba(34, 197, 94, 0.15) !important;
      color: #16a34a !important;
      border: 1px solid rgba(34, 197, 94, 0.4) !important;
    }
    body.dark-mode main .git-stat-add {
      color: #4ade80 !important;
    }
    .git-stat-del,
    body.light-mode main .git-stat-del,
    body.dark-mode main .git-stat-del {
      background-color: rgba(239, 68, 68, 0.15) !important;
      color: #dc2626 !important;
      border: 1px solid rgba(239, 68, 68, 0.4) !important;
    }
    body.dark-mode main .git-stat-del {
      color: #f87171 !important;
    }

    /* ======================================================== */
    /* VS Code Theme for Git Diffstat / Merge Log Output        */
    /* ======================================================== */
    .vscode-git-output,
    #feMergeSuccessLogText,
    #beMergeSuccessLogText,
    #feMergeConflictLogText,
    #beMergeConflictLogText {
      background-color: #1e1e1e !important;
      border: 1px solid #333333 !important;
      color: #d4d4d4 !important;
      font-family: "JetBrains Mono", Consolas, "Courier New", monospace !important;
      box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4) !important;
      border-radius: 6px !important;
      line-height: 1.6 !important;
      padding: 10px 12px !important;
    }
    .vscode-git-file { color: #9cdcfe !important; }
    .vscode-git-pipe { color: #64748b !important; font-weight: bold; }
    .vscode-git-num { color: #dcdcaa !important; font-weight: 600; }
    .vscode-git-add { color: #4ec9b0 !important; }
    .vscode-git-del { color: #f14c4c !important; }
    .vscode-git-files { color: #d4d4d4 !important; }
    .vscode-git-strategy { color: #c586c0 !important; }
    .vscode-git-info { color: #858585 !important; }
    .vscode-git-keyword { color: #569cd6 !important; }
    .vscode-git-hash { color: #b5cea8 !important; }
    .vscode-git-conflict { color: #f14c4c !important; }
    .vscode-git-muted { color: #858585 !important; }

    body.light-mode .vscode-git-output,
    body.light-mode #feMergeSuccessLogText,
    body.light-mode #beMergeSuccessLogText,
    body.light-mode #feMergeConflictLogText,
    body.light-mode #beMergeConflictLogText {
      background-color: #f6f8fa !important;
      border: 1px solid #d0d7de !important;
      color: #24292f !important;
      box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }
    body.light-mode .vscode-git-file { color: #0969da !important; }
    body.light-mode .vscode-git-pipe { color: #8c959f !important; font-weight: bold; }
    body.light-mode .vscode-git-num { color: #953800 !important; font-weight: 600; }
    body.light-mode .vscode-git-add { color: #1a7f37 !important; }
    body.light-mode .vscode-git-del { color: #cf222e !important; }
    body.light-mode .vscode-git-files { color: #24292f !important; }
    body.light-mode .vscode-git-strategy { color: #8250df !important; }
    body.light-mode .vscode-git-info { color: #57606a !important; }
    body.light-mode .vscode-git-keyword { color: #0550ae !important; }
    body.light-mode .vscode-git-hash { color: #116329 !important; }
    body.light-mode .vscode-git-conflict { color: #cf222e !important; }
    body.light-mode .vscode-git-muted { color: #6e7781 !important; }

  </style>
</head>
<body class="min-h-screen font-sans flex flex-col">
  <script>
    (function() {
      var t = localStorage.getItem('easysalon_theme') || 'light';
      document.body.classList.add(t === 'dark' ? 'dark-mode' : 'light-mode');
    })();
  </script>

  <!-- Header: Tông màu chủ đạo #182c4f và #ffffff -->
  <header class="border-b border-[#244170] bg-[#182c4f] text-white sticky top-0 z-30 px-6 py-2.5 flex items-center justify-between shadow-md">
    <div class="flex items-center gap-3">
      <img src="/logo-my.png" alt="EasySalon Logo" class="h-8 md:h-9 w-auto object-contain cursor-pointer select-none" onclick="switchTab('task')" />
    </div>

    <!-- Mode Navigation Tabs & Nút chuyển Sáng / Tối -->
    <div class="flex items-center gap-2.5">
      <div class="flex items-center bg-[#0d1c33] p-1 rounded-md border border-[#244170] text-xs font-medium space-x-1">
        <button id="tabBtn_task" type="button" onclick="switchTab('task')" class="px-3.5 py-1.5 rounded bg-white text-[#182c4f] font-semibold transition text-xs cursor-pointer select-none">
          Tác vụ
        </button>
        <button id="tabBtn_branch" type="button" onclick="switchTab('branch')" class="px-3.5 py-1.5 rounded text-slate-300 hover:text-white hover:bg-white/5 font-medium transition text-xs cursor-pointer select-none">
          Điều khiển Git
        </button>
        <button id="tabBtn_diagram" type="button" onclick="switchTab('diagram')" class="px-3.5 py-1.5 rounded text-slate-300 hover:text-white hover:bg-white/5 font-medium transition text-xs cursor-pointer select-none">
          Sơ đồ liên kết
        </button>
        <button id="tabBtn_log" type="button" onclick="switchTab('log')" class="px-3.5 py-1.5 rounded text-slate-300 hover:text-white hover:bg-white/5 font-medium transition text-xs cursor-pointer select-none">
          Lịch sử
        </button>
      </div>

      <!-- Nút Thông báo Git Updates kèm Badge đỏ -->
      <div class="relative" id="notifWrap">
        <button id="notifBellBtn" type="button" onclick="toggleNotifDropdown()" class="p-1.5 rounded-lg bg-transparent hover:bg-white/10 text-white transition flex items-center justify-center cursor-pointer select-none relative" title="Thông báo cập nhật commit Git">
          <svg class="w-5 h-5 fill-current text-white" viewBox="0 0 24 24">
            <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
          </svg>
          <span id="notifBadge" class="hidden absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-white text-[10px] font-bold font-mono flex items-center justify-center border-2 border-[#182c4f] shadow-md">0</span>
        </button>

        <!-- Dropdown Menu Thông báo (Giao diện sáng, viền tinh tế, chiều rộng rộng rãi) -->
        <div id="notifDropdownMenu" class="hidden absolute right-0 top-full mt-2 w-[540px] sm:w-[580px] max-w-[calc(100vw-24px)] z-50 bg-white border border-slate-200 rounded-xl shadow-2xl overflow-hidden flex flex-col text-slate-900">
          <div class="px-3.5 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[#199cff]"></span>
              <span class="font-bold text-xs text-black">Thông báo</span>
              <span id="notifDropdownBadge" class="text-xs text-slate-400 font-normal hidden">0 chưa đọc</span>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" id="btnMarkAllNotifsAsRead" onclick="markAllNotificationsAsRead()" class="text-[11px] font-semibold text-[#199cff] hover:text-blue-700 transition cursor-pointer" title="Đánh dấu tất cả thông báo là đã đọc">Đọc tất cả</button>
              <button type="button" onclick="checkSyncPullUpdates(true)" class="text-[11px] font-semibold text-slate-600 hover:text-black transition flex items-center gap-1 cursor-pointer" title="Kiểm tra remote ngay">
                <svg class="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
                <span>Quét</span>
              </button>
            </div>
          </div>

          <!-- Bộ lọc Tag: Tất cả / Git / Tác vụ Agent (Nền trắng, tab chọn màu xanh chữ trắng) -->
          <div id="notifFilterTabs" class="px-3 py-2 bg-white border-b border-slate-200 flex items-center gap-2 text-[11px] overflow-x-auto scrollbar-thin">
            <!-- Rendered by JS -->
          </div>

          <!-- Danh sách thông báo -->
          <div id="notifItemsList" class="max-h-80 overflow-y-auto divide-y divide-slate-100 text-xs bg-white">
            <div class="p-4 text-center text-slate-500 text-xs">
              Đang tải danh sách thông báo...
            </div>
          </div>
        </div>
      </div>

      <!-- Nút chuyển Dark / Light Mode -->
      <button id="themeToggleBtn" type="button" onclick="toggleTheme()" class="h-[31px] px-2.5 py-1 rounded-md bg-[#0d1c33] hover:bg-[#142647] border border-[#244170] text-slate-200 hover:text-white transition text-xs flex items-center gap-1.5 cursor-pointer select-none" title="Chuyển chế độ Giao diện Sáng / Tối">
        <span id="themeToggleIcon" class="flex items-center text-xs">☀️</span>
        <span id="themeToggleText" class="font-medium text-[11px]">Sáng</span>
      </button>
    </div>
  </header>

  <!-- TAB 1: TÁC VỤ (LÀM TASK / FIX BUG) -->
  <main id="view_task" class="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-5">
    <div class="lg:col-span-4 space-y-4">
      <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm">
        <div class="flex items-center justify-between mb-2.5">
          <h2 class="text-sm font-semibold text-white flex items-center gap-2">
            <span>Hàng đợi tác vụ (Task Queue)</span>
          </h2>
          <button type="button" onclick="addNewParallelTask()" title="Thêm tác vụ mới vào hàng đợi (Queue)"
            class="flex items-center gap-1 text-[11px] font-semibold bg-[#199cff]/20 hover:bg-[#199cff] text-[#199cff] hover:text-white px-2.5 py-1 rounded transition border border-[#199cff]/40 shadow-sm">
            <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            <span>Thêm tác vụ</span>
          </button>
        </div>

        <!-- Task queue tabs list -->
        <div id="parallelTaskTabs" class="flex items-center gap-1.5 overflow-x-auto pb-2 mb-3  scrollbar-thin">
          <!-- Rendered dynamically by JS -->
        </div>

        <!-- Option chọn Loại tác vụ: Làm task vs Fix bug vs Refactor code -->
        <div class="space-y-1 mb-3">
          <label class="text-xs font-medium text-slate-300">Loại tác vụ:</label>
          <select id="taskTypeSelect" onchange="setTaskActionType(this.value)" class="w-full bg-[#0e192c] border border-[#244170] rounded-md p-2 text-xs text-slate-100 focus:outline-none focus:border-[#38bdf8] font-medium">
            <option value="task" selected>Làm task</option>
            <option value="fixbug">Fix bug</option>
            <option value="refactor">Refactor code</option>
          </select>
        </div>

        <!-- Tùy chọn Nơi thực hiện / Phạm vi: FE, BE, hoặc Cả hai -->
        <div class="space-y-1 mb-3">
          <label id="taskTargetLabel" class="text-xs font-medium text-slate-300">Nơi thực hiện:</label>
          <select id="taskTargetSelect" onchange="onTaskTargetChange()" class="w-full bg-[#0e192c] border border-[#244170] rounded-md p-2 text-xs text-slate-100 focus:outline-none focus:border-[#38bdf8]">
            <option value="both" selected>Cả hai (Frontend ↔ Backend phối hợp)</option>
            <option value="fe">Chỉ Frontend (easysalon-webapp)</option>
            <option value="be">Chỉ Backend (easysalon-api)</option>
          </select>
        </div>

        <!-- Multi-Skill Selector cho Làm task & Fix bug -->
        <div class="mb-3 space-y-1 relative">
          <div class="flex items-center justify-between">
            <label class="text-xs font-medium text-slate-300">Skill trọng tâm:</label>
            <span id="taskSkillCount" class="text-[11px] font-mono text-cyan-400">0 đã chọn</span>
          </div>
          
          <div id="taskSkillPickerTrigger" onclick="toggleSkillDropdown('task')"
            class="w-full min-h-[38px] bg-[#0e192c] border border-[#244170] hover:border-[#38bdf8] rounded-md p-2 text-xs text-slate-100 cursor-pointer flex items-center justify-between gap-2 transition">
            <div id="taskSelectedTags" class="flex flex-wrap items-center gap-1.5 flex-1 min-w-0">
              <span class="text-slate-400 text-xs italic">-- Chọn một hoặc nhiều skill --</span>
            </div>
            <div class="text-slate-400 px-1 shrink-0">
              <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
            </div>
          </div>

          <!-- Dropdown danh sách skill -->
          <div id="taskSkillDropdown" class="hidden absolute top-full left-0 right-0 mt-1 bg-[#0e192c] border border-[#244170] rounded-md shadow-xl z-50 p-2.5 max-h-72 flex flex-col space-y-2">
            <div class="flex items-center gap-2 pb-2 border-b border-[#244170]">
              <input type="text" id="taskSkillSearch" oninput="filterSkillOptions('task')" placeholder="Tìm kiếm skill..."
                class="flex-1 bg-[#101e38] border border-[#244170] rounded px-2.5 py-1 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-[#38bdf8]" />
              <button onclick="selectAllSkills('task')" type="button" class="text-[11px] text-cyan-400 hover:text-white px-2 py-0.5 rounded hover:bg-white/5 font-medium">Chọn hết</button>
              <button onclick="clearAllSkills('task')" type="button" class="text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded hover:bg-white/5 font-medium">Bỏ chọn</button>
            </div>
            <div id="taskSkillOptionList" class="overflow-y-auto space-y-1 flex-1 pr-1 max-h-52">
              <!-- Rendered by JS -->
            </div>
          </div>
        </div>

        <!-- Nội dung task / Hiện tượng lỗi -->
        <div class="space-y-1">
          <div class="flex items-center justify-between">
            <label id="taskPromptLabel" class="text-xs font-medium text-slate-300">Yêu cầu / Mô tả chi tiết:</label>
            <button type="button" onclick="formatTaskPromptInput()"
              class="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 cursor-pointer select-none transition hover:underline"
              title="Định dạng lại nội dung theo chuẩn BDD / Gherkin và phân đoạn dễ nhìn">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h10M4 18h16" />
              </svg>
              <span>Định dạng lại</span>
            </button>
          </div>
          <textarea id="taskPromptInput" rows="4" oninput="onTaskPromptInput()"
            placeholder="Ví dụ: Thêm API và Component hiển thị trạng thái giường cho BedRoomPosition..."
            class="w-full bg-[#0e192c] border border-[#244170] focus:border-[#38bdf8] rounded-md p-2.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none transition resize-none leading-relaxed"></textarea>
        </div>

        <!-- Ô mã code lỗi console / Exception (chỉ hiển thị khi chọn fix bug) -->
        <div id="taskLogContainer" class="space-y-1 mt-3 hidden">
          <div class="flex items-center justify-between">
            <label class="text-xs font-medium text-slate-300">Mã lỗi / Console log / Exception:</label>
            <span class="text-[10px] text-slate-400 italic font-mono">Không bắt buộc</span>
          </div>
          <textarea id="taskLogInput" rows="3" oninput="onTaskLogInput()"
            placeholder="Dán mã lỗi HTTP (400, 500...), Exception, JSON response, hoặc console error tại đây (nếu có)..."
            class="w-full bg-[#0e192c] border border-[#244170] focus:border-[#38bdf8] rounded-md p-2.5 text-xs font-mono text-slate-200 placeholder-slate-400 focus:outline-none transition resize-none"></textarea>
        </div>

        <!-- Action Buttons -->
        <div class="mt-4 space-y-2">
          <div class="flex items-center gap-2">
            <button id="btnStartTask" onclick="startCurrentTask()" 
              class="ant-btn ant-btn-primary flex-1 h-[36px] text-white" style="color: #ffffff !important;">
              <svg class="w-3.5 h-3.5 fill-current mr-1 text-white" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              <span id="btnStartTaskText" class="text-white font-medium" style="color: #ffffff !important;">Bắt đầu tác vụ này</span>
            </button>
            <button id="btnStopTask" onclick="stopCurrentTask()" 
              class="hidden ant-btn ant-btn-danger flex-1 h-[36px]">
              <svg class="w-3.5 h-3.5 fill-current mr-1" viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg>
              <span>Dừng tác vụ này</span>
            </button>
          </div>
          <button id="btnStopAllParallel" onclick="stopAllTasks()" 
            class="hidden w-full h-[32px] rounded text-[11px] font-semibold bg-rose-600/20 hover:bg-rose-600 text-rose-400 hover:text-white border border-rose-500/40 transition flex items-center justify-center gap-1.5">
            <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg>
            <span>Dừng tất cả tác vụ</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Feed hiển thị diễn biến task -->
    <div class="lg:col-span-8 flex flex-col h-[78vh] bg-[#101e38] border border-[#244170] rounded-lg shadow-sm overflow-hidden">
      <div class="px-4 py-2.5 border-b border-[#244170] bg-[#182c4f] flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span id="taskFeedTitle" class="font-semibold text-xs text-white">Diễn biến thực thi</span>
        </div>
        <div class="flex items-center gap-2">
          <div id="feedTaskFilterTabs" class="flex items-center gap-1 bg-[#0e192c] p-0.5 rounded border border-[#244170] overflow-x-auto max-w-[520px] scrollbar-thin">
            <!-- Rendered dynamically by JS: [Tất cả] [Task 1] [Task 2] -->
          </div>
        </div>
      </div>
      <div id="taskFeed" class="flex-1 overflow-y-auto p-4 space-y-4">
        <div id="taskEmptyState" class="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
          <h3 id="taskEmptyTitle" class="text-xs font-semibold text-slate-300">Chưa có tác vụ nào đang chạy</h3>
          <p id="taskEmptySubtitle" class="text-xs text-slate-400 max-w-sm mt-1">Cấu hình thông tin bên trái và nhấn "Bắt đầu tác vụ".</p>
        </div>
      </div>
      <div id="taskTypingIndicator" class="hidden px-4 py-2.5 border-t border-[#244170] bg-[#0e192c] flex items-center justify-between text-xs">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          <span id="taskTypingText" class="text-cyan-400 font-mono text-[11px]">Đang thực thi tác vụ...</span>
        </div>
      </div>
    </div>
  </main>

  <!-- TAB 3: NHÁNH HIỆN TẠI (GIT BRANCH MANAGER) -->
  <main id="view_branch" class="hidden flex-1 w-full max-w-[90%] mx-auto p-4 md:p-6 space-y-5">
    <!-- Action Bar trên cùng -->
    <div class="flex flex-wrap items-center justify-between gap-4 bg-[#101e38] border border-[#244170] rounded-lg p-4 shadow-sm">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded bg-[#182c4f] border border-[#244170] flex items-center justify-center text-cyan-400">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M17 12c-1.1 0-2 .9-2 2 0 .74.4 1.38 1 1.72V17c0 1.1-.9 2-2 2H9c-1.1 0-2-.9-2-2v-4.28c.6-.34 1-.98 1-1.72 0-1.1-.9-2-2-2s-2 .9-2 2c0 .74.4 1.38 1 1.72V17c0 2.21 1.79 4 4 4h5c2.21 0 4-1.79 4-4v-1.28c.6-.34 1-.98 1-1.72 0-1.1-.9-2-2-2zm-11-1c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm11 4c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z"/></svg>
        </div>
        <div>
          <h2 class="text-sm font-semibold text-white">Điều khiển Git</h2>
          <p class="text-xs text-slate-400">Kiểm tra thông tin commit, đồng bộ pull, working tree và chuyển nhánh cho Frontend & Backend</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button id="btnRefreshGit" onclick="refreshCurrentGitView()" class="ant-btn ant-btn-primary text-xs h-[32px] inline-flex items-center gap-1.5 transition-colors">
          <span id="refreshGitSpinner" class="hidden">
            <svg class="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </span>
          <span id="refreshGitText">Làm mới</span>
        </button>
      </div>
    </div>

    <!-- Sub-Tabs bên trong Điều khiển Git -->
    <div class="flex items-center gap-2 border-b border-[#244170] pb-2">
      <button id="gitSubTabBtn_pull_sync" type="button" onclick="switchGitSubTab('pull_sync')" 
        class="active-git-subtab px-3.5 py-1.5 rounded-md bg-[rgb(25,156,255)] text-white font-bold text-xs shadow-sm transition cursor-pointer select-none">
        Pull Staging / Master / Beta
      </button>
      <button id="gitSubTabBtn_branch" type="button" onclick="switchGitSubTab('branch')" 
        class="px-3.5 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-white/10 font-medium text-xs transition cursor-pointer select-none">
        Chuyển & Tạo nhánh
      </button>
      <button id="gitSubTabBtn_cherry_pick" type="button" onclick="switchGitSubTab('cherry_pick')" 
        class="px-3.5 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-white/10 font-medium text-xs transition cursor-pointer select-none">
        Cherry-Pick
      </button>
      <button id="gitSubTabBtn_merge" type="button" onclick="switchGitSubTab('merge')" 
        class="px-3.5 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-white/10 font-medium text-xs transition cursor-pointer select-none">
        Merge nhánh
      </button>
    </div>

    <!-- SUB-VIEW 1: CHUYỂN & TẠO NHÁNH -->
    <div id="gitSubView_branch" class="hidden space-y-5">
      <!-- Card Tạo Nhánh (Frontend & Backend) -->
    <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 shadow-sm space-y-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          <span class="font-semibold text-xs text-white">Tạo nhánh (Frontend & Backend)</span>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
        <div class="md:col-span-5">
          <label class="text-[11px] text-slate-300 block mb-1">Tên nhánh mới (-b):</label>
          <input type="text" id="bothBranchInput" placeholder="Ví dụ: feat/nvt/EAS-12373/booking-bed-room-management"
            class="w-full bg-[#0e192c] border border-[#244170] rounded-md px-3 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-[#38bdf8]" />
        </div>
        <div class="md:col-span-4">
          <label class="text-[11px] text-slate-300 block mb-1">Từ nhánh gốc:</label>
          <select id="bothBaseBranchSelect" class="w-full bg-[#0e192c] border border-[#244170] rounded-md px-3 py-1.5 text-xs font-mono text-slate-100 focus:outline-none focus:border-[#38bdf8]">
            <option value="staging">staging (khuyên dùng)</option>
            <option value="master">master</option>
          </select>
        </div>
        <div class="md:col-span-3">
          <button id="btnSwitchBoth" onclick="doCreateNewBranchBoth()" class="ant-btn ant-btn-primary w-full h-[32px] text-xs font-medium whitespace-nowrap">
            <svg class="w-3.5 h-3.5 fill-none stroke-current mr-1" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            <span>Tạo nhánh</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 2 Cột Quản lý Nhánh: Frontend & Backend -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- CỘT 1: FRONTEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm flex flex-col justify-between">
        <div class="space-y-3.5">
          <div class="flex items-center justify-between pb-2.5 border-b border-[#244170]">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
              <span class="font-semibold text-xs text-cyan-400">Frontend (easysalon-webapp)</span>
            </div>
          </div>

          <!-- Thông tin nhánh hiện tại -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-md p-3.5 space-y-2.5">
            <div>
              <div class="text-[11px] text-slate-400 mb-1 flex items-center justify-between">
                <span>Nhánh hiện tại:</span>
                <span id="feWorkingStatus" class="text-[11px] font-medium text-emerald-400"></span>
              </div>
              <div class="flex items-center gap-2">
                <span id="feCurrentBranch" class="font-mono text-cyan-300 font-semibold text-xs bg-cyan-950/80 px-2.5 py-1 rounded border border-cyan-800/60 truncate">
                  Đang nạp...
                </span>
                <button onclick="copyToClipboard(document.getElementById('feCurrentBranch').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs" title="Sao chép tên nhánh">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-2 border-t border-[#244170]">
              <div>
                <span class="text-slate-400 text-[11px]">Commit gần nhất:</span>
                <div id="feCommitInfo" class="font-mono text-slate-200 text-[11px] mt-0.5 truncate" title="...">...</div>
              </div>
              <div>
                <span class="text-slate-400 text-[11px]">Trạng thái:</span>
                <div id="feStatusInfo" class="text-slate-200 text-[11px] mt-0.5">...</div>
              </div>
            </div>

            <div class="pt-2 border-t border-[#244170] flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <span class="text-slate-400 text-[11px]">Đồng bộ Remote:</span>
                <span id="feSyncBadge" class="text-[11px] font-mono text-slate-300">Đang kiểm tra...</span>
              </div>
              <button id="btnPullFe" onclick="doPullBranch('fe')" class="hidden ant-btn text-xs h-[28px] px-3 flex items-center gap-1.5 bg-[#182c4f] border-[#2e528f] text-cyan-300 hover:bg-[#244170]">
                <svg class="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                <span id="fePullBtnText">Pull nhánh này</span>
              </button>
            </div>

            <!-- Stash của nhánh Frontend -->
            <div id="feStashSection" style="display: none;"
              class="hidden pt-2 border-t border-[#244170] flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span class="text-slate-400 text-[11px] whitespace-nowrap">Code trong Stash:</span>
                <span id="feStashBadge"
                  class="text-[11px] font-mono text-cyan-300 bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800/80 truncate max-w-[220px] sm:max-w-[280px]"
                  title="">Đang kiểm tra...</span>
              </div>
              <button id="btnPopStashFe" type="button" onclick="doPopStash('fe')"
                class="ant-btn text-xs h-[28px] px-3 inline-flex items-center gap-1.5 bg-[#1677ff] hover:bg-[#4096ff] text-white font-sans font-medium rounded border border-[#1677ff] shadow-sm cursor-pointer select-none transition"
                title="Khôi phục mã nguồn đã cất từ git stash (git stash pop)">
                <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span id="fePopStashBtnText">Lấy code từ stash</span>
              </button>
            </div>
          </div>

          <!-- Khu vực chọn và chuyển nhánh -->
          <div class="space-y-1.5">
            <label class="text-xs font-medium text-slate-200 block">Tên nhánh muốn checkout:</label>
            <div class="flex items-center gap-2">
              <input type="text" id="feBranchInput" oninput="filterBranchList('fe')" onkeydown="handleBranchInputKeyDown(event, 'fe')" placeholder="Gõ tên nhánh hoặc chọn trong danh sách..."
                class="flex-1 bg-[#0e192c] border border-[#244170] rounded-md px-3 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500" />
              <button id="btnSwitchFe" onclick="doCheckout('fe')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <span>Chuyển nhánh</span>
              </button>
            </div>
            <select id="feBranchSelect" size="5" onchange="onSelectBranchOption('fe')" oninput="onSelectBranchOption('fe')" onkeyup="onSelectBranchOption('fe')" onkeydown="handleBranchSelectKeyDown(event, 'fe')" ondblclick="onSelectBranchOption('fe'); doCheckout('fe');" class="w-full bg-[#0e192c] border border-[#244170] rounded-md p-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500">
              <option disabled>Đang tải danh sách nhánh...</option>
            </select>
            <div class="flex items-center justify-between text-[11px] text-slate-400 px-0.5 min-h-[24px]">
              <button type="button" id="btnPrevFe" onclick="doCheckoutPrevious('fe')" class="hidden items-center gap-1.5 px-2 py-0.5 rounded bg-[#182c4f] hover:bg-[#244170] text-cyan-300 hover:text-white border border-[#2e528f] transition text-[11px] font-medium" title="Quay về nhánh trước đó (git checkout -)">
                <svg class="w-3 h-3 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>
                <span>Quay về: <b id="fePrevBranchLabel" class="font-mono text-cyan-200">--</b></span>
              </button>
              <span class="text-slate-500 text-[11px] ml-auto">Nhấn đúp để chọn</span>
            </div>
          </div>
        </div>
      </div>

      <!-- CỘT 2: BACKEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm flex flex-col justify-between">
        <div class="space-y-3.5">
          <div class="flex items-center justify-between pb-2.5 border-b border-[#244170]">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="font-semibold text-xs text-emerald-400">Backend (easysalon-api)</span>
            </div>
          </div>

          <!-- Thông tin nhánh hiện tại -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-md p-3.5 space-y-2.5">
            <div>
              <div class="text-[11px] text-slate-400 mb-1 flex items-center justify-between">
                <span>Nhánh hiện tại:</span>
                <span id="beWorkingStatus" class="text-[11px] font-medium text-emerald-400"></span>
              </div>
              <div class="flex items-center gap-2">
                <span id="beCurrentBranch" class="font-mono text-emerald-300 font-semibold text-xs bg-emerald-950/80 px-2.5 py-1 rounded border border-emerald-800/60 truncate">
                  Đang nạp...
                </span>
                <button onclick="copyToClipboard(document.getElementById('beCurrentBranch').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs" title="Sao chép tên nhánh">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-2 border-t border-[#244170]">
              <div>
                <span class="text-slate-400 text-[11px]">Commit gần nhất:</span>
                <div id="beCommitInfo" class="font-mono text-slate-200 text-[11px] mt-0.5 truncate" title="...">...</div>
              </div>
              <div>
                <span class="text-slate-400 text-[11px]">Trạng thái:</span>
                <div id="beStatusInfo" class="text-slate-200 text-[11px] mt-0.5">...</div>
              </div>
            </div>

            <div class="pt-2 border-t border-[#244170] flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <span class="text-slate-400 text-[11px]">Đồng bộ Remote:</span>
                <span id="beSyncBadge" class="text-[11px] font-mono text-slate-300">Đang kiểm tra...</span>
              </div>
              <button id="btnPullBe" onclick="doPullBranch('be')" class="hidden ant-btn text-xs h-[28px] px-3 flex items-center gap-1.5 bg-[#182c4f] border-[#2e528f] text-emerald-300 hover:bg-[#244170]">
                <svg class="w-3 h-3 fill-current" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                <span id="bePullBtnText">Pull nhánh này</span>
              </button>
            </div>

            <!-- Stash của nhánh Backend -->
            <div id="beStashSection" style="display: none;"
              class="hidden pt-2 border-t border-[#244170] flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span class="text-slate-400 text-[11px] whitespace-nowrap">Code trong Stash:</span>
                <span id="beStashBadge"
                  class="text-[11px] font-mono text-emerald-300 bg-emerald-950/70 px-2 py-0.5 rounded border border-emerald-800/80 truncate max-w-[220px] sm:max-w-[280px]"
                  title="">Đang kiểm tra...</span>
              </div>
              <button id="btnPopStashBe" type="button" onclick="doPopStash('be')"
                class="ant-btn text-xs h-[28px] px-3 inline-flex items-center gap-1.5 bg-[#1677ff] hover:bg-[#4096ff] text-white font-sans font-medium rounded border border-[#1677ff] shadow-sm cursor-pointer select-none transition"
                title="Khôi phục mã nguồn đã cất từ git stash (git stash pop)">
                <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span id="bePopStashBtnText">Lấy code từ stash</span>
              </button>
            </div>
          </div>

          <!-- Khu vực chọn và chuyển nhánh -->
          <div class="space-y-1.5">
            <label class="text-xs font-medium text-slate-200 block">Tên nhánh muốn checkout:</label>
            <div class="flex items-center gap-2">
              <input type="text" id="beBranchInput" oninput="filterBranchList('be')" onkeydown="handleBranchInputKeyDown(event, 'be')" placeholder="Gõ tên nhánh hoặc chọn trong danh sách..."
                class="flex-1 bg-[#0e192c] border border-[#244170] rounded-md px-3 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-500" />
              <button id="btnSwitchBe" onclick="doCheckout('be')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <span>Chuyển nhánh</span>
              </button>
            </div>
            <select id="beBranchSelect" size="5" onchange="onSelectBranchOption('be')" oninput="onSelectBranchOption('be')" onkeyup="onSelectBranchOption('be')" onkeydown="handleBranchSelectKeyDown(event, 'be')" ondblclick="onSelectBranchOption('be'); doCheckout('be');" class="w-full bg-[#0e192c] border border-[#244170] rounded-md p-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500">
              <option disabled>Đang tải danh sách nhánh...</option>
            </select>
            <div class="flex items-center justify-between text-[11px] text-slate-400 px-0.5 min-h-[24px]">
              <button type="button" id="btnPrevBe" onclick="doCheckoutPrevious('be')" class="hidden items-center gap-1.5 px-2 py-0.5 rounded bg-[#182c4f] hover:bg-[#244170] text-emerald-300 hover:text-white border border-[#2e528f] transition text-[11px] font-medium" title="Quay về nhánh trước đó (git checkout -)">
                <svg class="w-3 h-3 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>
                <span>Quay về: <b id="bePrevBranchLabel" class="font-mono text-emerald-200">--</b></span>
              </button>
              <span class="text-slate-500 text-[11px] ml-auto">Nhấn đúp để chọn</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- SUB-VIEW 2: CHERRY-PICK -->
  <div id="gitSubView_cherry_pick" class="hidden space-y-5">
    <!-- Info bar: Nhánh hiện tại cho Cherry-Pick -->
    <div class="bg-[#101e38] border border-[#244170] rounded-lg p-3.5 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
      <div class="flex items-center gap-2 text-slate-300">
        <svg class="w-4 h-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <span>Commit được cherry-pick sẽ được áp dụng trực tiếp vào <b>nhánh hiện tại</b> của từng repository:</span>
      </div>
      <div class="flex items-center gap-3 font-mono text-xs">
        <div class="flex items-center gap-1.5 bg-[#0e192c] border border-[#244170] px-2.5 py-1 rounded">
          <span class="w-2 h-2 rounded-full bg-cyan-400 shrink-0"></span>
          <span class="text-slate-400 text-[11px]">FE hiện tại:</span>
          <span id="feCherryTopBranch" class="text-cyan-300 font-bold">Đang nạp...</span>
        </div>
        <div class="flex items-center gap-1.5 bg-[#0e192c] border border-[#244170] px-2.5 py-1 rounded">
          <span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span>
          <span class="text-slate-400 text-[11px]">BE hiện tại:</span>
          <span id="beCherryTopBranch" class="text-emerald-300 font-bold">Đang nạp...</span>
        </div>
      </div>
    </div>

    <!-- 2 Cột Cherry-Pick: Frontend & Backend -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- CỘT 1: FRONTEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-[#244170]">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
              <span class="font-semibold text-xs text-cyan-400">Frontend (easysalon-webapp)</span>
            </div>
          </div>

          <!-- Thẻ hiển thị rõ nhánh hiện tại dạng Dropdown có Search -->
          <div class="bg-[#0e192c] border border-cyan-800/60 rounded-md p-3 space-y-1.5">
            <div class="text-[11px] text-slate-400 flex items-center justify-between">
              <span class="font-medium text-slate-300 flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
                <span>Đang ở nhánh:</span>
              </span>
              <span class="text-[10px] font-mono text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800">Nhánh nhận commit</span>
            </div>
            <div class="flex items-center gap-2 pt-0.5">
              <div class="relative flex-1" id="feCherryBranchDropdownWrap">
                <button type="button" id="feCherryBranchTrigger" onclick="toggleCherryBranchDropdown('fe')"
                  class="w-full flex items-center justify-between bg-[#101e38] border border-cyan-700/80 rounded px-2.5 py-1.5 text-xs font-mono text-cyan-300 font-bold focus:outline-none focus:border-cyan-400 cursor-pointer shadow-sm text-left">
                  <span id="feCherrySelectedBranchText" class="truncate">Đang nạp...</span>
                  <svg class="w-3.5 h-3.5 text-cyan-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="feCherryBranchDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-cyan-700/80 rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="feCherryBranchSearchInput" oninput="filterCherryBranches('fe')" placeholder="Tìm kiếm tên nhánh..."
                      class="w-full bg-[#0e192c] border border-cyan-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="feCherryBranchOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>
              <button type="button" onclick="copyToClipboard(document.getElementById('feCherrySelectedBranchText').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs shrink-0" title="Sao chép tên nhánh">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>
            </div>
          </div>

          <!-- Banner Xung đột nếu có -->
          <div id="feCherryConflictBox" class="hidden bg-amber-950/40 border border-amber-600/60 rounded-md p-3 space-y-2 text-xs">
            <div class="flex items-center justify-between text-amber-300 font-semibold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-amber-400" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                <span>Đang gặp xung đột (Conflict) trong cherry-pick!</span>
              </span>
            </div>
            <div id="feCherryConflictFiles" class="font-mono text-[11px] text-amber-200/90 bg-black/40 p-2 rounded max-h-24 overflow-y-auto"></div>
            <div class="flex items-center gap-2 pt-1">
              <button onclick="doCherryPickContinue('fe')" class="ant-btn ant-btn-primary h-[28px] px-3 text-[11px] font-medium bg-emerald-600 hover:bg-emerald-500 border-emerald-500">
                <span>Tiếp tục (--continue)</span>
              </button>
              <button onclick="doCherryPickAbort('fe')" class="ant-btn ant-btn-danger h-[28px] px-3 text-[11px] font-medium">
                <span>Hủy bỏ (--abort)</span>
              </button>
            </div>
          </div>

          <!-- Banner Thành công: Hiển thị Input commit message và Nút Push code -->
          <div id="feCherrySuccessBox" class="hidden bg-emerald-950/40 border border-emerald-600/60 rounded-md p-3.5 space-y-3 text-xs">
            <div class="flex items-center justify-between gap-2 text-emerald-300 font-semibold">
              <div class="flex items-center gap-2">
                <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span id="feCherrySuccessTitle">Cherry-pick commit thành công!</span>
              </div>
              <button type="button" onclick="clearCherrySuccessBox('fe')" class="p-1 rounded text-emerald-400/70 hover:text-emerald-200 hover:bg-emerald-900/50 transition cursor-pointer" title="Đóng thông báo">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div id="feCherryCommitMsgSection" class="space-y-1.5">
              <label class="text-[11px] text-slate-300 font-medium block">Nội dung commit message (nếu muốn chỉnh sửa):</label>
              <input type="text" id="feCherryCommitMsgInput" placeholder="Nội dung commit message..." class="w-full bg-[#101e38] border border-[#244170] rounded px-3 py-1.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-500 font-mono" />
            </div>
            <div class="flex items-center justify-between gap-2 pt-1">
              <span id="feCherryPushPromptText" class="text-[11px] text-slate-400">Đẩy commit này lên nhánh remote:</span>
              <div class="flex items-center gap-2">
                <button id="btnFeCherryPush" type="button" onclick="doCherryPush('fe')" class="ant-btn ant-btn-primary h-[30px] px-3.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500 whitespace-nowrap inline-flex items-center gap-1.5">
                  <span id="feCherryPushSpinner" class="hidden">
                    <svg class="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  </span>
                  <span id="btnFeCherryPushText">Push code lên nhánh</span>
                </button>
                <button id="btnFeCherryCloseSuccess" type="button" onclick="clearCherrySuccessBox('fe')" class="hidden ant-btn h-[30px] px-3 text-xs font-semibold bg-slate-700/60 hover:bg-slate-700 text-slate-200 border-slate-600 cursor-pointer">
                  Đóng
                </button>
              </div>
            </div>
            <!-- Nút quay về nhánh cũ sau khi push cherry-pick thành công -->
            <div id="feCherryReturnBranchWrap" class="hidden pt-2 border-t border-emerald-800/60 flex flex-wrap items-center justify-between gap-2">
              <span class="text-[11px] text-emerald-300 flex items-center gap-1.5 font-medium whitespace-nowrap shrink-0">
                <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã push code lên remote thành công.</span>
              </span>
              <button id="btnFeCherryReturnPrevBranch" type="button" onclick="doReturnToPrevCherryBranch('fe')" class="ant-btn h-[28px] px-3 text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white border-sky-500 flex items-center gap-1.5 shadow-sm max-w-full">
                <svg class="w-3.5 h-3.5 fill-none stroke-current shrink-0" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
                <span id="btnFeCherryReturnPrevBranchText" class="truncate max-w-[280px] sm:max-w-[340px]">Quay về lại nhánh lúc nãy</span>
              </button>
            </div>
          </div>

          <!-- Banner Lỗi Cherry-Pick (nếu có lỗi trong quá trình thực hiện) -->
          <div id="feCherryErrorBox" class="hidden bg-rose-950/40 border border-rose-600/60 rounded-md p-3 space-y-2 text-xs">
            <div class="flex items-center justify-between text-rose-300 font-semibold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-rose-400 shrink-0" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
                <span>Xảy ra lỗi trong quá trình cherry-pick:</span>
              </span>
              <button type="button" onclick="document.getElementById('feCherryErrorBox').classList.add('hidden')" class="text-rose-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <div id="feCherryErrorDetail" class="font-mono text-[11px] text-rose-200/90 bg-black/40 p-2 rounded whitespace-pre-wrap max-h-32 overflow-y-auto"></div>
          </div>


          <!-- Khu vực duyệt commit từ nhánh khác -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-xs font-medium text-slate-200">Hoặc duyệt commit từ nhánh khác:</label>
              <span id="feCherryCommitsCount" class="text-[11px] font-mono text-slate-400"></span>
            </div>
            <div class="flex items-center gap-2">
              <input type="hidden" id="feCherrySourceBranchSelect" value="staging" />
              <div class="relative flex-1" id="feCherrySourceBranchDropdownWrap">
                <button type="button" id="feCherrySourceBranchTrigger" onclick="toggleCherrySourceBranchDropdown('fe')"
                  class="w-full flex items-center justify-between bg-[#101e38] border border-cyan-700/80 rounded px-2.5 py-1.5 text-xs font-mono text-cyan-300 font-bold focus:outline-none focus:border-cyan-400 cursor-pointer shadow-sm text-left">
                  <span id="feCherrySelectedSourceBranchText" class="truncate">staging</span>
                  <svg class="w-3.5 h-3.5 text-cyan-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="feCherrySourceBranchDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-cyan-700/80 rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="feCherrySourceBranchSearchInput" oninput="filterCherrySourceBranches('fe')"
                      onkeydown="if(event.key==='Enter'){event.preventDefault();selectFirstFilteredCherrySourceBranch('fe')}"
                      placeholder="Tìm kiếm tên nhánh..."
                      class="w-full bg-[#0e192c] border border-cyan-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="feCherrySourceBranchOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>

              <button onclick="loadBranchCommits('fe')" class="ant-btn text-xs h-[31px] px-2.5 bg-[#0e192c] border-[#244170] text-slate-200 hover:text-white shrink-0" title="Tải lại danh sách commit của nhánh này">
                <span>Tải lại</span>
              </button>
            </div>

            <!-- Danh sách commit tải về -->
            <div id="feCherryCommitsList" class="bg-[#0e192c] border border-[#244170] rounded-md p-2 space-y-1.5 max-h-72 overflow-y-auto">
              <div class="text-center text-xs text-slate-400 py-6">Đang tải danh sách commit...</div>
            </div>
          </div>
        </div>
      </div>

      <!-- CỘT 2: BACKEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-[#244170]">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="font-semibold text-xs text-emerald-400">Backend (easysalon-api)</span>
            </div>
          </div>

          <!-- Thẻ hiển thị rõ nhánh hiện tại dạng Dropdown có Search -->
          <div class="bg-[#0e192c] border border-emerald-800/60 rounded-md p-3 space-y-1.5">
            <div class="text-[11px] text-slate-400 flex items-center justify-between">
              <span class="font-medium text-slate-300 flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>Đang ở nhánh:</span>
              </span>
              <span class="text-[10px] font-mono text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800">Nhánh nhận commit</span>
            </div>
            <div class="flex items-center gap-2 pt-0.5">
              <div class="relative flex-1" id="beCherryBranchDropdownWrap">
                <button type="button" id="beCherryBranchTrigger" onclick="toggleCherryBranchDropdown('be')"
                  class="w-full flex items-center justify-between bg-[#101e38] border border-emerald-700/80 rounded px-2.5 py-1.5 text-xs font-mono text-emerald-300 font-bold focus:outline-none focus:border-emerald-400 cursor-pointer shadow-sm text-left">
                  <span id="beCherrySelectedBranchText" class="truncate">Đang nạp...</span>
                  <svg class="w-3.5 h-3.5 text-emerald-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="beCherryBranchDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-emerald-700/80 rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="beCherryBranchSearchInput" oninput="filterCherryBranches('be')" placeholder="Tìm kiếm tên nhánh..."
                      class="w-full bg-[#0e192c] border border-emerald-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="beCherryBranchOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>
              <button type="button" onclick="copyToClipboard(document.getElementById('beCherrySelectedBranchText').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs shrink-0" title="Sao chép tên nhánh">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>
            </div>
          </div>

          <!-- Banner Xung đột nếu có -->
          <div id="beCherryConflictBox" class="hidden bg-amber-950/40 border border-amber-600/60 rounded-md p-3 space-y-2 text-xs">
            <div class="flex items-center justify-between text-amber-300 font-semibold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-amber-400" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                <span>Đang gặp xung đột (Conflict) trong cherry-pick!</span>
              </span>
            </div>
            <div id="beCherryConflictFiles" class="font-mono text-[11px] text-amber-200/90 bg-black/40 p-2 rounded max-h-24 overflow-y-auto"></div>
            <div class="flex items-center gap-2 pt-1">
              <button onclick="doCherryPickContinue('be')" class="ant-btn ant-btn-primary h-[28px] px-3 text-[11px] font-medium bg-emerald-600 hover:bg-emerald-500 border-emerald-500">
                <span>Tiếp tục (--continue)</span>
              </button>
              <button onclick="doCherryPickAbort('be')" class="ant-btn ant-btn-danger h-[28px] px-3 text-[11px] font-medium">
                <span>Hủy bỏ (--abort)</span>
              </button>
            </div>
          </div>

          <!-- Banner Thành công: Hiển thị Input commit message và Nút Push code -->
          <div id="beCherrySuccessBox" class="hidden bg-emerald-950/40 border border-emerald-600/60 rounded-md p-3.5 space-y-3 text-xs">
            <div class="flex items-center justify-between gap-2 text-emerald-300 font-semibold">
              <div class="flex items-center gap-2">
                <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span id="beCherrySuccessTitle">Cherry-pick commit thành công!</span>
              </div>
              <button type="button" onclick="clearCherrySuccessBox('be')" class="p-1 rounded text-emerald-400/70 hover:text-emerald-200 hover:bg-emerald-900/50 transition cursor-pointer" title="Đóng thông báo">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div id="beCherryCommitMsgSection" class="space-y-1.5">
              <label class="text-[11px] text-slate-300 font-medium block">Nội dung commit message (nếu muốn chỉnh sửa):</label>
              <input type="text" id="beCherryCommitMsgInput" placeholder="Nội dung commit message..." class="w-full bg-[#101e38] border border-[#244170] rounded px-3 py-1.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-500 font-mono" />
            </div>
            <div class="flex items-center justify-between gap-2 pt-1">
              <span id="beCherryPushPromptText" class="text-[11px] text-slate-400">Đẩy commit này lên nhánh remote:</span>
              <div class="flex items-center gap-2">
                <button id="btnBeCherryPush" type="button" onclick="doCherryPush('be')" class="ant-btn ant-btn-primary h-[30px] px-3.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500 whitespace-nowrap inline-flex items-center gap-1.5">
                  <span id="beCherryPushSpinner" class="hidden">
                    <svg class="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  </span>
                  <span id="btnBeCherryPushText">Push code lên nhánh</span>
                </button>
                <button id="btnBeCherryCloseSuccess" type="button" onclick="clearCherrySuccessBox('be')" class="hidden ant-btn h-[30px] px-3 text-xs font-semibold bg-slate-700/60 hover:bg-slate-700 text-slate-200 border-slate-600 cursor-pointer">
                  Đóng
                </button>
              </div>
            </div>
            <!-- Nút quay về nhánh cũ sau khi push cherry-pick thành công -->
            <div id="beCherryReturnBranchWrap" class="hidden pt-2 border-t border-emerald-800/60 flex flex-wrap items-center justify-between gap-2">
              <span class="text-[11px] text-emerald-300 flex items-center gap-1.5 font-medium whitespace-nowrap shrink-0">
                <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã push code lên remote thành công.</span>
              </span>
              <button id="btnBeCherryReturnPrevBranch" type="button" onclick="doReturnToPrevCherryBranch('be')" class="ant-btn h-[28px] px-3 text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white border-sky-500 flex items-center gap-1.5 shadow-sm max-w-full">
                <svg class="w-3.5 h-3.5 fill-none stroke-current shrink-0" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
                <span id="btnBeCherryReturnPrevBranchText" class="truncate max-w-[280px] sm:max-w-[340px]">Quay về lại nhánh lúc nãy</span>
              </button>
            </div>
          </div>

          <!-- Banner Lỗi Cherry-Pick (nếu có lỗi trong quá trình thực hiện) -->
          <div id="beCherryErrorBox" class="hidden bg-rose-950/40 border border-rose-600/60 rounded-md p-3 space-y-2 text-xs">
            <div class="flex items-center justify-between text-rose-300 font-semibold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-rose-400 shrink-0" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
                <span>Xảy ra lỗi trong quá trình cherry-pick:</span>
              </span>
              <button type="button" onclick="document.getElementById('beCherryErrorBox').classList.add('hidden')" class="text-rose-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <div id="beCherryErrorDetail" class="font-mono text-[11px] text-rose-200/90 bg-black/40 p-2 rounded whitespace-pre-wrap max-h-32 overflow-y-auto"></div>
          </div>


          <!-- Khu vực duyệt commit từ nhánh khác -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-xs font-medium text-slate-200">Hoặc duyệt commit từ nhánh khác:</label>
              <span id="beCherryCommitsCount" class="text-[11px] font-mono text-slate-400"></span>
            </div>
            <div class="flex items-center gap-2">
              <input type="hidden" id="beCherrySourceBranchSelect" value="staging" />
              <div class="relative flex-1" id="beCherrySourceBranchDropdownWrap">
                <button type="button" id="beCherrySourceBranchTrigger" onclick="toggleCherrySourceBranchDropdown('be')"
                  class="w-full flex items-center justify-between bg-[#101e38] border border-emerald-700/80 rounded px-2.5 py-1.5 text-xs font-mono text-emerald-300 font-bold focus:outline-none focus:border-emerald-400 cursor-pointer shadow-sm text-left">
                  <span id="beCherrySelectedSourceBranchText" class="truncate">staging</span>
                  <svg class="w-3.5 h-3.5 text-emerald-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="beCherrySourceBranchDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-emerald-700/80 rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="beCherrySourceBranchSearchInput" oninput="filterCherrySourceBranches('be')"
                      onkeydown="if(event.key==='Enter'){event.preventDefault();selectFirstFilteredCherrySourceBranch('be')}"
                      placeholder="Tìm kiếm tên nhánh..."
                      class="w-full bg-[#0e192c] border border-emerald-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="beCherrySourceBranchOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>

              <button onclick="loadBranchCommits('be')" class="ant-btn text-xs h-[31px] px-2.5 bg-[#0e192c] border-[#244170] text-slate-200 hover:text-white shrink-0" title="Tải lại danh sách commit của nhánh này">
                <span>Tải lại</span>
              </button>
            </div>

            <!-- Danh sách commit tải về -->
            <div id="beCherryCommitsList" class="bg-[#0e192c] border border-[#244170] rounded-md p-2 space-y-1.5 max-h-72 overflow-y-auto">
              <div class="text-center text-xs text-slate-400 py-6">Đang tải danh sách commit...</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- SUB-VIEW 3: PULL STAGING / MASTER / BETA -->
  <div id="gitSubView_pull_sync" class="space-y-5">
    <!-- 2 Cột: Frontend & Backend -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- CỘT 1: FRONTEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-xl p-4 md:p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <!-- Header & Thẻ Nhánh Hiện Tại Frontend -->
          <div class="space-y-2 pb-2 border-b border-[#244170]">
            <div class="flex items-center justify-between">
              <span class="font-bold text-sm text-cyan-400">Frontend (easysalon-webapp)</span>
            </div>
            <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-2 px-3 flex items-center gap-2 text-xs shadow-sm min-w-0">
              <span class="text-slate-400 font-sans text-xs shrink-0">Đang ở nhánh:</span>
              <span id="feSyncCurrBranch" class="font-mono text-cyan-300 font-bold truncate flex-1" title="Đang nạp...">Đang nạp...</span>
            </div>
          </div>

          <!-- Khối hành động Staging -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">staging</span>
                <span class="text-xs text-slate-200 font-medium">Nhánh kiểm thử Staging</span>
              </div>
              <div id="fe_staging_statusBadge" class="hidden"></div>
            </div>
            <div class="text-[11px] text-slate-400">Cập nhật mã nguồn mới nhất từ remote <code>origin/staging</code></div>
            <div id="fe_staging_commitsBox" class="hidden"></div>
            <div class="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-[#244170]/40">
              <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
                <input type="checkbox" id="feReturnStaging" class="w-3.5 h-3.5 rounded border-[#244170] accent-sky-500 cursor-pointer" />
                <span>Pull Và ở nhánh hiện tại</span>
              </label>
              <button id="btnFePullStaging" type="button" onclick="doSyncPull('fe', 'staging')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <svg id="fePullStagingSpinner" class="hidden animate-spin h-3.5 w-3.5 mr-1.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <span id="btnFePullStagingText">Pull Staging</span>
              </button>
            </div>
          </div>

          <!-- Khối hành động Master -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">master</span>
                <span class="text-xs text-slate-200 font-medium">Nhánh chính thức Master</span>
              </div>
              <div id="fe_master_statusBadge" class="hidden"></div>
            </div>
            <div class="text-[11px] text-slate-400">Cập nhật mã nguồn mới nhất từ remote <code>origin/master</code></div>
            <div id="fe_master_commitsBox" class="hidden"></div>
            <div class="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-[#244170]/40">
              <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
                <input type="checkbox" id="feReturnMaster" class="w-3.5 h-3.5 rounded border-[#244170] accent-amber-500 cursor-pointer" />
                <span>Pull Và ở nhánh hiện tại</span>
              </label>
              <button id="btnFePullMaster" type="button" onclick="doSyncPull('fe', 'master')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <svg id="fePullMasterSpinner" class="hidden animate-spin h-3.5 w-3.5 mr-1.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <span id="btnFePullMasterText">Pull Master</span>
              </button>
            </div>
          </div>

          <!-- Khối hành động Beta -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800">beta</span>
                <span class="text-xs text-slate-200 font-medium">Nhánh thử nghiệm Beta</span>
              </div>
              <div id="fe_beta_statusBadge" class="hidden"></div>
            </div>
            <div class="text-[11px] text-slate-400">Cập nhật mã nguồn mới nhất từ remote <code>origin/beta</code></div>
            <div id="fe_beta_commitsBox" class="hidden"></div>
            <div class="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-[#244170]/40">
              <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
                <input type="checkbox" id="feReturnBeta" class="w-3.5 h-3.5 rounded border-[#244170] accent-purple-500 cursor-pointer" />
                <span>Pull Và ở nhánh hiện tại</span>
              </label>
              <button id="btnFePullBeta" type="button" onclick="doSyncPull('fe', 'beta')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <svg id="fePullBetaSpinner" class="hidden animate-spin h-3.5 w-3.5 mr-1.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <span id="btnFePullBetaText">Pull Beta</span>
              </button>
            </div>
          </div>

          <!-- Banner Xung đột Frontend nếu có -->
          <div id="feSyncConflictBox" class="hidden bg-amber-950/40 border border-amber-600/60 rounded-md p-3.5 space-y-2 text-xs">
            <div class="flex items-center justify-between text-amber-300 font-semibold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-amber-400" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                <span id="feSyncConflictTitle">Phát hiện xung đột (Conflict) khi pull Frontend!</span>
              </span>
            </div>
            <p class="text-[11px] text-amber-200/80">Quá trình pull nhánh gặp xung đột mã nguồn. Danh sách các file bị conflict:</p>
            <div id="feSyncConflictFiles" class="font-mono text-[11px] text-rose-300 bg-black/40 p-2 rounded max-h-32 overflow-y-auto"></div>
            <div class="flex items-center gap-2 pt-1">
              <button onclick="doAbortMerge('fe')" class="ant-btn ant-btn-danger h-[28px] px-3 text-[11px] font-medium">
                <span>Hủy bỏ Merge (git merge --abort)</span>
              </button>
            </div>
          </div>

          <!-- Banner Kết quả thành công hoặc log Frontend -->
          <div id="feSyncResultBox" class="hidden bg-[#0e192c] border border-emerald-800/60 rounded-md p-3 space-y-1.5 text-xs">
            <div class="flex items-center justify-between text-emerald-300 font-semibold">
              <span id="feSyncResultTitle" class="flex items-center gap-1.5">
                <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã pull thành công</span>
              </span>
              <button type="button" onclick="document.getElementById('feSyncResultBox').classList.add('hidden')" class="text-slate-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <pre id="feSyncResultOutput" class="font-mono text-[11px] text-slate-200 bg-black/40 p-2 rounded max-h-32 overflow-y-auto whitespace-pre-wrap"></pre>
          </div>
        </div>
      </div>

      <!-- CỘT 2: BACKEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-xl p-4 md:p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <!-- Header & Thẻ Nhánh Hiện Tại Backend -->
          <div class="space-y-2 pb-2 border-b border-[#244170]">
            <div class="flex items-center justify-between">
              <span class="font-bold text-sm text-emerald-400">Backend (easysalon-api)</span>
            </div>
            <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-2 px-3 flex items-center gap-2 text-xs shadow-sm min-w-0">
              <span class="text-slate-400 font-sans text-xs shrink-0">Đang ở nhánh:</span>
              <span id="beSyncCurrBranch" class="font-mono text-emerald-300 font-bold truncate flex-1" title="Đang nạp...">Đang nạp...</span>
            </div>
          </div>

          <!-- Khối hành động Staging -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">staging</span>
                <span class="text-xs text-slate-200 font-medium">Nhánh kiểm thử Staging</span>
              </div>
              <div id="be_staging_statusBadge" class="hidden"></div>
            </div>
            <div class="text-[11px] text-slate-400">Cập nhật mã nguồn mới nhất từ remote <code>origin/staging</code></div>
            <div id="be_staging_commitsBox" class="hidden"></div>
            <div class="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-[#244170]/40">
              <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
                <input type="checkbox" id="beReturnStaging" class="w-3.5 h-3.5 rounded border-[#244170] accent-emerald-500 cursor-pointer" />
                <span>Pull Và ở nhánh hiện tại</span>
              </label>
              <button id="btnBePullStaging" type="button" onclick="doSyncPull('be', 'staging')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <svg id="bePullStagingSpinner" class="hidden animate-spin h-3.5 w-3.5 mr-1.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <span id="btnBePullStagingText">Pull Staging</span>
              </button>
            </div>
          </div>

          <!-- Khối hành động Master -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">master</span>
                <span class="text-xs text-slate-200 font-medium">Nhánh chính thức Master</span>
              </div>
              <div id="be_master_statusBadge" class="hidden"></div>
            </div>
            <div class="text-[11px] text-slate-400">Cập nhật mã nguồn mới nhất từ remote <code>origin/master</code></div>
            <div id="be_master_commitsBox" class="hidden"></div>
            <div class="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-[#244170]/40">
              <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
                <input type="checkbox" id="beReturnMaster" class="w-3.5 h-3.5 rounded border-[#244170] accent-amber-500 cursor-pointer" />
                <span>Pull Và ở nhánh hiện tại</span>
              </label>
              <button id="btnBePullMaster" type="button" onclick="doSyncPull('be', 'master')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <svg id="bePullMasterSpinner" class="hidden animate-spin h-3.5 w-3.5 mr-1.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <span id="btnBePullMasterText">Pull Master</span>
              </button>
            </div>
          </div>

          <!-- Khối hành động Beta -->
          <div class="bg-[#0e192c] border border-[#244170] rounded-lg p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800">beta</span>
                <span class="text-xs text-slate-200 font-medium">Nhánh thử nghiệm Beta</span>
              </div>
              <div id="be_beta_statusBadge" class="hidden"></div>
            </div>
            <div class="text-[11px] text-slate-400">Cập nhật mã nguồn mới nhất từ remote <code>origin/beta</code></div>
            <div id="be_beta_commitsBox" class="hidden"></div>
            <div class="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-[#244170]/40">
              <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
                <input type="checkbox" id="beReturnBeta" class="w-3.5 h-3.5 rounded border-[#244170] accent-purple-500 cursor-pointer" />
                <span>Pull Và ở nhánh hiện tại</span>
              </label>
              <button id="btnBePullBeta" type="button" onclick="doSyncPull('be', 'beta')" class="ant-btn ant-btn-primary h-[31px] px-3 text-xs font-medium whitespace-nowrap">
                <svg id="bePullBetaSpinner" class="hidden animate-spin h-3.5 w-3.5 mr-1.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <span id="btnBePullBetaText">Pull Beta</span>
              </button>
            </div>
          </div>

          <!-- Banner Xung đột Backend nếu có -->
          <div id="beSyncConflictBox" class="hidden bg-amber-950/40 border border-amber-600/60 rounded-md p-3.5 space-y-2 text-xs">
            <div class="flex items-center justify-between text-amber-300 font-semibold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-amber-400" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                <span id="beSyncConflictTitle">Phát hiện xung đột (Conflict) khi pull Backend!</span>
              </span>
            </div>
            <p class="text-[11px] text-amber-200/80">Quá trình pull nhánh gặp xung đột mã nguồn. Danh sách các file bị conflict:</p>
            <div id="beSyncConflictFiles" class="font-mono text-[11px] text-rose-300 bg-black/40 p-2 rounded max-h-32 overflow-y-auto"></div>
            <div class="flex items-center gap-2 pt-1">
              <button onclick="doAbortMerge('be')" class="ant-btn ant-btn-danger h-[28px] px-3 text-[11px] font-medium">
                <span>Hủy bỏ Merge (git merge --abort)</span>
              </button>
            </div>
          </div>

          <!-- Banner Kết quả thành công hoặc log Backend -->
          <div id="beSyncResultBox" class="hidden bg-[#0e192c] border border-emerald-800/60 rounded-md p-3 space-y-1.5 text-xs">
            <div class="flex items-center justify-between text-emerald-300 font-semibold">
              <span id="beSyncResultTitle" class="flex items-center gap-1.5">
                <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã pull thành công</span>
              </span>
              <button type="button" onclick="document.getElementById('beSyncResultBox').classList.add('hidden')" class="text-slate-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <pre id="beSyncResultOutput" class="font-mono text-[11px] text-slate-200 bg-black/40 p-2 rounded max-h-32 overflow-y-auto whitespace-pre-wrap"></pre>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- SUB-VIEW 4: MERGE NHÁNH (GIT MERGE) -->
  <div id="gitSubView_merge" class="hidden space-y-5">
    <!-- Action / Info Bar trên cùng -->
    <div class="bg-[#101e38] border border-[#244170] rounded-lg p-3.5 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
      <div class="flex items-center gap-2.5 text-slate-300">
        <div class="w-7 h-7 rounded bg-[#182c4f] border border-[#244170] flex items-center justify-center text-cyan-400 shrink-0">
          <svg class="w-4 h-4 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7v10M8 7a3 3 0 100-6 3 3 0 000 6zm0 10a3 3 0 100 6 3 3 0 000-6zm8-4a3 3 0 100-6 3 3 0 000 6zm0 0v2a4 4 0 01-4 4H8"/>
          </svg>
        </div>
        <div>
          <span class="font-semibold text-white">Hợp nhất nhánh (Git Merge):</span>
          <span class="text-slate-400 ml-1">Gộp code từ nhánh nguồn (A) sang nhánh đích (B). Tự động hiển thị chi tiết log và file xung đột bên dưới khi xảy ra conflict.</span>
        </div>
      </div>
      <div class="flex items-center gap-3 font-mono text-xs">
        <div class="flex items-center gap-1.5 bg-[#0e192c] border border-[#244170] px-2.5 py-1 rounded">
          <span class="w-2 h-2 rounded-full bg-cyan-400 shrink-0"></span>
          <span class="text-slate-400 text-[11px]">FE hiện tại:</span>
          <span id="feMergeTopBranch" class="text-cyan-300 font-bold">Đang nạp...</span>
        </div>
        <div class="flex items-center gap-1.5 bg-[#0e192c] border border-[#244170] px-2.5 py-1 rounded">
          <span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span>
          <span class="text-slate-400 text-[11px]">BE hiện tại:</span>
          <span id="beMergeTopBranch" class="text-emerald-300 font-bold">Đang nạp...</span>
        </div>
      </div>
    </div>

    <!-- 2 Cột: Frontend & Backend -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- CỘT 1: FRONTEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-[#244170]">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
              <span class="font-semibold text-xs text-cyan-400">Frontend (easysalon-webapp)</span>
            </div>
          </div>

          <!-- Thẻ chọn Nhánh merge A (Lấy code từ nhánh này) dạng Dropdown có Search -->
          <div class="merge-branch-box bg-[#0e192c] border border-amber-800/60 rounded-md p-3 space-y-1.5">
            <div class="text-[11px] text-slate-400 flex items-center justify-between">
              <span class="font-medium text-slate-300 flex items-center gap-1.5">
                <span class="px-1.5 py-0.2 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono text-[10px]">A</span>
                <span>Nhánh merge (Lấy code từ nhánh này):</span>
              </span>
              <div class="flex items-center gap-2">
                <span id="feMergeSourceCount" class="text-[10px] font-mono text-slate-400"></span>
                <button type="button" onclick="setMergeSourceToCurrent('fe')" class="text-[10px] text-cyan-400 hover:text-white underline cursor-pointer" title="Chọn ngay nhánh hiện tại làm nhánh merge">
                  Chọn nhánh đang đứng
                </button>
              </div>
            </div>
            <div class="flex items-center gap-2 pt-0.5">
              <input type="hidden" id="feMergeSourceSelect" value="" />
              <div class="relative flex-1" id="feMergeSourceDropdownWrap">
                <button type="button" id="feMergeSourceTrigger" onclick="toggleMergeDropdown('fe', 'source')"
                  class="merge-trigger-btn w-full flex items-center justify-between bg-[#101e38] border border-[#244170] rounded px-2.5 py-1.5 text-xs font-mono text-slate-200 font-bold focus:outline-none focus:border-cyan-400 cursor-pointer shadow-sm text-left">
                  <span id="feMergeSelectedSourceText" class="truncate">Đang nạp...</span>
                  <svg class="w-3.5 h-3.5 text-slate-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="feMergeSourceDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-[#244170] rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="feMergeSourceSearchInput" oninput="filterMergeDropdown('fe', 'source')" placeholder="Tìm kiếm tên nhánh merge..."
                      class="w-full bg-[#0e192c] border border-cyan-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="feMergeSourceOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>
              <button type="button" onclick="copyToClipboard(document.getElementById('feMergeSelectedSourceText').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs shrink-0" title="Sao chép tên nhánh">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>
            </div>
          </div>

          <!-- Mũi tên chỉ hướng merge -->
          <div class="flex items-center justify-center -my-1">
            <div class="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#0e192c] border border-[#244170] text-[11px] text-cyan-300 font-medium shadow-sm">
              <svg class="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
              </svg>
              <span>Hợp nhất từ nhánh merge (trên) ➔ vào nhánh cần merge (dưới)</span>
            </div>
          </div>

          <!-- Thẻ chọn Nhánh cần merge B (Nhận code) dạng Dropdown có Search -->
          <div class="merge-branch-box bg-[#0e192c] border border-cyan-800/60 rounded-md p-3 space-y-1.5">
            <div class="text-[11px] text-slate-400 flex items-center justify-between">
              <span class="font-medium text-slate-300 flex items-center gap-1.5">
                <span class="px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono text-[10px]">B</span>
                <span>Nhánh cần merge (Merge vào nhánh này):</span>
              </span>
              <button type="button" onclick="setMergeTargetToCurrent('fe')" class="text-[10px] text-cyan-400 hover:text-white underline cursor-pointer" title="Chọn ngay nhánh hiện tại làm nhánh đích">
                Chọn nhánh đang đứng
              </button>
            </div>
            <div class="flex items-center gap-2 pt-0.5">
              <input type="hidden" id="feMergeTargetSelect" value="" />
              <div class="relative flex-1" id="feMergeTargetDropdownWrap">
                <button type="button" id="feMergeTargetTrigger" onclick="toggleMergeDropdown('fe', 'target')"
                  class="merge-trigger-btn w-full flex items-center justify-between bg-[#101e38] border border-cyan-700/80 rounded px-2.5 py-1.5 text-xs font-mono text-cyan-300 font-bold focus:outline-none focus:border-cyan-400 cursor-pointer shadow-sm text-left">
                  <span id="feMergeSelectedTargetText" class="truncate">Đang nạp...</span>
                  <svg class="w-3.5 h-3.5 text-cyan-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="feMergeTargetDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-cyan-700/80 rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="feMergeTargetSearchInput" oninput="filterMergeDropdown('fe', 'target')" placeholder="Tìm kiếm tên nhánh đích..."
                      class="w-full bg-[#0e192c] border border-cyan-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="feMergeTargetOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>
              <button type="button" onclick="copyToClipboard(document.getElementById('feMergeSelectedTargetText').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs shrink-0" title="Sao chép tên nhánh">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>
            </div>
          </div>

          <!-- Tùy chọn Merge & Commit message -->
          <div class="space-y-2 text-xs pt-1">
            <div class="flex flex-wrap items-center justify-between gap-3 text-slate-200">
              <label class="flex items-center gap-2 cursor-pointer select-none text-slate-200 font-medium">
                <input type="checkbox" id="feMergeNoFF" class="w-3.5 h-3.5 rounded border-[#244170] accent-sky-500 cursor-pointer" />
                <span>Tạo commit riêng (--no-ff)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer select-none text-slate-200 font-medium">
                <input type="checkbox" id="feMergeReturnCurrent" class="w-3.5 h-3.5 rounded border-[#244170] accent-sky-500 cursor-pointer" />
                <span>Quay về nhánh cũ sau khi merge</span>
              </label>
            </div>
            <input type="text" id="feMergeCommitMsg" placeholder="Nội dung commit message (tùy chọn)..."
              class="w-full bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400" />
          </div>

          <!-- Nút bấm thực hiện Merge -->
          <div class="pt-1">
            <button id="btnFeDoMerge" type="button" onclick="doExecuteMerge('fe')"
              class="ant-btn ant-btn-primary w-full h-[34px] text-xs font-semibold flex items-center justify-center gap-2 shadow-sm">
              <span id="feMergeSpinner" class="hidden">
                <svg class="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              </span>
              <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 7v10M8 7a3 3 0 100-6 3 3 0 000 6zm0 10a3 3 0 100 6 3 3 0 000-6zm8-4a3 3 0 100-6 3 3 0 000 6zm0 0v2a4 4 0 01-4 4H8"/>
              </svg>
              <span id="feMergeBtnText">Thực hiện Merge Frontend</span>
            </button>
          </div>

          <!-- Banner Xung đột & Log UI nếu xảy ra conflict (Frontend) -->
          <div id="feMergeConflictBox" class="hidden bg-amber-950/40 border border-amber-600/70 rounded-lg p-3.5 space-y-3 text-xs shadow-lg">
            <div class="flex items-center justify-between text-amber-300 font-bold text-[13px] border-b border-amber-700/50 pb-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-amber-400 shrink-0 animate-pulse" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <span>Xảy ra xung đột mã nguồn (Merge Conflict)!</span>
              </span>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-900/60 border border-amber-600 text-amber-200">Cần xử lý</span>
            </div>

            <!-- Danh sách file bị conflict -->
            <div class="space-y-1">
              <span class="text-[11px] text-amber-200 font-semibold block">Các file bị xung đột:</span>
              <div id="feMergeConflictFiles" class="font-mono text-[11px] text-amber-200/90 bg-black/50 p-2.5 rounded border border-amber-800/60 max-h-32 overflow-y-auto space-y-1"></div>
            </div>

            <!-- LOG UI CHI TIẾT XUNG ĐỘT (CONSOLE OUTPUT) -->
            <div class="space-y-1">
              <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold">
                <span class="flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/></svg>
                  <span>Log UI chi tiết xung đột (Git Console Output):</span>
                </span>
                <button type="button" onclick="copyToClipboard(document.getElementById('feMergeConflictLogText').textContent)"
                  class="text-[10px] text-slate-300 hover:text-white px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 transition cursor-pointer" title="Sao chép toàn bộ log xung đột">
                  Sao chép log
                </button>
              </div>
              <pre id="feMergeConflictLogText" class="font-mono text-[11px] text-amber-200/95 bg-[#090d16] border border-amber-800/80 p-3 rounded-md max-h-56 overflow-y-auto whitespace-pre-wrap shadow-inner leading-relaxed select-text"></pre>
            </div>

            <!-- Nút hành động giải quyết xung đột -->
            <div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-amber-800/60">
              <button id="btnFeMergeAbort" type="button" onclick="doMergeAbort('fe')" class="ant-btn ant-btn-danger h-[30px] px-3.5 text-xs font-semibold flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                <span>Hủy bỏ Merge (--abort)</span>
              </button>
              <button id="btnFeMergeContinue" type="button" onclick="doMergeContinue('fe')" class="ant-btn ant-btn-primary h-[30px] px-3.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500 flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã sửa xong & Tiếp tục (--continue)</span>
              </button>
            </div>
          </div>

          <!-- Banner Thành công & Log Frontend -->
          <div id="feMergeSuccessBox" class="hidden bg-emerald-950/40 border border-emerald-600/70 rounded-lg p-3.5 space-y-3 text-xs shadow-md">
            <div class="flex items-center justify-between text-emerald-300 font-bold text-xs border-b border-emerald-700/50 pb-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span id="feMergeSuccessTitle">Merge Frontend thành công!</span>
              </span>
              <button type="button" onclick="document.getElementById('feMergeSuccessBox').classList.add('hidden')" class="text-slate-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <div id="feMergeSuccessText" class="text-slate-200 text-xs"></div>
            <!-- Log output thành công -->
            <div class="space-y-1">
              <span class="text-[10px] text-slate-400 block font-semibold">Log chi tiết:</span>
              <pre id="feMergeSuccessLogText" class="font-mono text-[11px] text-slate-200 bg-[#090d16] border border-[#244170] p-2.5 rounded max-h-36 overflow-y-auto whitespace-pre-wrap select-text"></pre>
            </div>
            <div class="flex items-center justify-between gap-2 pt-1 border-t border-emerald-800/60">
              <span class="text-[11px] text-slate-400">Đẩy nhánh đích vừa merge lên Remote:</span>
              <div class="flex items-center gap-2">
                <button id="btnFeMergeViewDiff" type="button" onclick="toggleMergeDiffView('fe')"
                  title="Xem chi tiết các thay đổi vừa được merge (Diff / Files)"
                  class="ant-btn h-[28px] px-2.5 text-xs font-semibold bg-[#10223d] hover:bg-[#1a3660] text-sky-300 hover:text-sky-200 border border-sky-500/50 flex items-center gap-1.5 transition cursor-pointer">
                  <svg class="w-3.5 h-3.5 shrink-0 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span>Xem thay đổi đã merge</span>
                </button>
                <button id="btnFeMergePush" type="button" onclick="doMergePush('fe')" class="ant-btn ant-btn-primary h-[28px] px-3 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500 flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                  <span>Push nhánh đích</span>
                </button>
              </div>
            </div>

            <!-- Khu vực hiển thị Diff & File đã merge khi bấm icon con mắt -->
            <div id="feMergeDiffContainer" class="hidden pt-2 border-t border-emerald-800/60 space-y-2">
              <div class="flex items-center justify-between text-[11px] text-slate-300">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-sky-400 flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 stroke-current fill-none" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <span>Nội dung thay đổi đã merge (Diff):</span>
                  </span>
                  <span id="feMergeDiffStat" class="text-[10px] text-slate-400 font-mono"></span>
                </div>
                <div class="flex items-center gap-2">
                  <button id="btnFeCopyMergeDiff" type="button" onclick="copyMergeDiff('fe')"
                    class="text-[10px] text-sky-400 hover:text-sky-300 font-sans px-2 py-0.5 rounded border border-sky-500/30 hover:bg-sky-500/10 transition cursor-pointer">
                    Sao chép diff
                  </button>
                  <button id="btnFeCollapseMergeDiff" type="button" onclick="toggleMergeDiffView('fe')"
                    class="text-[10px] text-slate-400 hover:text-white font-sans px-2 py-0.5 rounded hover:bg-white/5 transition cursor-pointer">
                    Thu gọn
                  </button>
                </div>
              </div>

              <!-- Danh sách file thay đổi -->
              <div id="feMergeDiffFiles" class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto"></div>

              <!-- Khung code diff cuộn được -->
              <div id="feMergeDiffBody" class="sync-diff-wrapper rounded-md bg-[#1e1e1e] border border-[#333333] max-h-[380px] min-h-[100px] overflow-auto text-[11.5px] font-mono leading-relaxed shadow-inner">
                <div class="text-slate-400 text-xs p-3 text-center">Chưa có dữ liệu diff.</div>
              </div>
            </div>
            <!-- Nút quay về nhánh cũ sau khi push thành công -->
            <div id="feMergeReturnBranchWrap" class="hidden pt-2 border-t border-emerald-800/60 flex flex-wrap items-center justify-between gap-2">
              <span class="text-[11px] text-emerald-300 flex items-center gap-1.5 font-medium whitespace-nowrap shrink-0">
                <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã push code lên remote thành công.</span>
              </span>
              <button id="btnFeReturnPrevBranch" type="button" onclick="doReturnToPrevBranch('fe')" class="ant-btn h-[28px] px-3 text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white border-sky-500 flex items-center gap-1.5 shadow-sm max-w-full">
                <svg class="w-3.5 h-3.5 fill-none stroke-current shrink-0" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
                <span id="btnFeReturnPrevBranchText" class="truncate max-w-[280px] sm:max-w-[340px]">Quay về lại nhánh lúc nãy</span>
              </button>
            </div>
          </div>

          <!-- Banner Lỗi chung (Frontend) -->
          <div id="feMergeErrorBox" class="hidden bg-rose-950/40 border border-rose-600/70 rounded-lg p-3 space-y-2 text-xs">
            <div class="flex items-center justify-between text-rose-300 font-bold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-rose-400 shrink-0" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
                <span>Không thể thực hiện Merge:</span>
              </span>
              <button type="button" onclick="document.getElementById('feMergeErrorBox').classList.add('hidden')" class="text-rose-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <pre id="feMergeErrorDetail" class="font-mono text-[11px] text-rose-200/90 bg-black/40 p-2.5 rounded whitespace-pre-wrap max-h-36 overflow-y-auto"></pre>
          </div>
        </div>
      </div>

      <!-- CỘT 2: BACKEND -->
      <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-[#244170]">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="font-semibold text-xs text-emerald-400">Backend (easysalon-api)</span>
            </div>
          </div>

          <!-- Thẻ chọn Nhánh merge A (Lấy code từ nhánh này) dạng Dropdown có Search -->
          <div class="merge-branch-box bg-[#0e192c] border border-amber-800/60 rounded-md p-3 space-y-1.5">
            <div class="text-[11px] text-slate-400 flex items-center justify-between">
              <span class="font-medium text-slate-300 flex items-center gap-1.5">
                <span class="px-1.5 py-0.2 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono text-[10px]">A</span>
                <span>Nhánh merge (Lấy code từ nhánh này):</span>
              </span>
              <div class="flex items-center gap-2">
                <span id="beMergeSourceCount" class="text-[10px] font-mono text-slate-400"></span>
                <button type="button" onclick="setMergeSourceToCurrent('be')" class="text-[10px] text-emerald-400 hover:text-white underline cursor-pointer" title="Chọn ngay nhánh hiện tại làm nhánh merge">
                  Chọn nhánh đang đứng
                </button>
              </div>
            </div>
            <div class="flex items-center gap-2 pt-0.5">
              <input type="hidden" id="beMergeSourceSelect" value="" />
              <div class="relative flex-1" id="beMergeSourceDropdownWrap">
                <button type="button" id="beMergeSourceTrigger" onclick="toggleMergeDropdown('be', 'source')"
                  class="merge-trigger-btn w-full flex items-center justify-between bg-[#101e38] border border-[#244170] rounded px-2.5 py-1.5 text-xs font-mono text-slate-200 font-bold focus:outline-none focus:border-emerald-400 cursor-pointer shadow-sm text-left">
                  <span id="beMergeSelectedSourceText" class="truncate">Đang nạp...</span>
                  <svg class="w-3.5 h-3.5 text-slate-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="beMergeSourceDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-[#244170] rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="beMergeSourceSearchInput" oninput="filterMergeDropdown('be', 'source')" placeholder="Tìm kiếm tên nhánh merge..."
                      class="w-full bg-[#0e192c] border border-emerald-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="beMergeSourceOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>
              <button type="button" onclick="copyToClipboard(document.getElementById('beMergeSelectedSourceText').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs shrink-0" title="Sao chép tên nhánh">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>
            </div>
          </div>

          <!-- Mũi tên chỉ hướng merge -->
          <div class="flex items-center justify-center -my-1">
            <div class="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#0e192c] border border-[#244170] text-[11px] text-emerald-300 font-medium shadow-sm">
              <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
              </svg>
              <span>Hợp nhất từ nhánh merge (trên) ➔ vào nhánh cần merge (dưới)</span>
            </div>
          </div>

          <!-- Thẻ chọn Nhánh cần merge B (Nhận code) dạng Dropdown có Search -->
          <div class="merge-branch-box bg-[#0e192c] border border-emerald-800/60 rounded-md p-3 space-y-1.5">
            <div class="text-[11px] text-slate-400 flex items-center justify-between">
              <span class="font-medium text-slate-300 flex items-center gap-1.5">
                <span class="px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono text-[10px]">B</span>
                <span>Nhánh cần merge (Merge vào nhánh này):</span>
              </span>
              <button type="button" onclick="setMergeTargetToCurrent('be')" class="text-[10px] text-emerald-400 hover:text-white underline cursor-pointer" title="Chọn ngay nhánh hiện tại làm nhánh đích">
                Chọn nhánh đang đứng
              </button>
            </div>
            <div class="flex items-center gap-2 pt-0.5">
              <input type="hidden" id="beMergeTargetSelect" value="" />
              <div class="relative flex-1" id="beMergeTargetDropdownWrap">
                <button type="button" id="beMergeTargetTrigger" onclick="toggleMergeDropdown('be', 'target')"
                  class="merge-trigger-btn w-full flex items-center justify-between bg-[#101e38] border border-emerald-700/80 rounded px-2.5 py-1.5 text-xs font-mono text-emerald-300 font-bold focus:outline-none focus:border-emerald-400 cursor-pointer shadow-sm text-left">
                  <span id="beMergeSelectedTargetText" class="truncate">Đang nạp...</span>
                  <svg class="w-3.5 h-3.5 text-emerald-400 ml-2 shrink-0 transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                  </svg>
                </button>

                <!-- Dropdown Menu with Search -->
                <div id="beMergeTargetDropdownMenu" class="hidden absolute left-0 right-0 top-full mt-1 z-40 bg-[#101e38] border border-emerald-700/80 rounded-md shadow-2xl p-2 space-y-2">
                  <div class="relative">
                    <input type="text" id="beMergeTargetSearchInput" oninput="filterMergeDropdown('be', 'target')" placeholder="Tìm kiếm tên nhánh đích..."
                      class="w-full bg-[#0e192c] border border-emerald-800 rounded px-2.5 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-400" />
                    <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                  </div>
                  <div id="beMergeTargetOptionsList" class="max-h-56 overflow-y-auto space-y-0.5 text-xs font-mono pr-0.5">
                    <!-- Rendered by JS -->
                  </div>
                </div>
              </div>
              <button type="button" onclick="copyToClipboard(document.getElementById('beMergeSelectedTargetText').textContent.trim())" class="p-1 hover:bg-[#182c4f] text-slate-400 hover:text-white rounded transition text-xs shrink-0" title="Sao chép tên nhánh">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>
            </div>
          </div>

          <!-- Tùy chọn Merge & Commit message -->
          <div class="space-y-2 text-xs pt-1">
            <div class="flex flex-wrap items-center justify-between gap-3 text-slate-200">
              <label class="flex items-center gap-2 cursor-pointer select-none text-slate-200 font-medium">
                <input type="checkbox" id="beMergeNoFF" class="w-3.5 h-3.5 rounded border-[#244170] accent-emerald-500 cursor-pointer" />
                <span>Tạo commit riêng (--no-ff)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer select-none text-slate-200 font-medium">
                <input type="checkbox" id="beMergeReturnCurrent" class="w-3.5 h-3.5 rounded border-[#244170] accent-emerald-500 cursor-pointer" />
                <span>Quay về nhánh cũ sau khi merge</span>
              </label>
            </div>
            <input type="text" id="beMergeCommitMsg" placeholder="Nội dung commit message (tùy chọn)..."
              class="w-full bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-400" />
          </div>

          <!-- Nút bấm thực hiện Merge -->
          <div class="pt-1">
            <button id="btnBeDoMerge" type="button" onclick="doExecuteMerge('be')"
              class="ant-btn ant-btn-primary w-full h-[34px] text-xs font-semibold flex items-center justify-center gap-2 shadow-sm bg-emerald-600 hover:bg-emerald-500 border-emerald-500">
              <span id="beMergeSpinner" class="hidden">
                <svg class="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              </span>
              <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 7v10M8 7a3 3 0 100-6 3 3 0 000 6zm0 10a3 3 0 100 6 3 3 0 000-6zm8-4a3 3 0 100-6 3 3 0 000 6zm0 0v2a4 4 0 01-4 4H8"/>
              </svg>
              <span id="beMergeBtnText">Thực hiện Merge Backend</span>
            </button>
          </div>

          <!-- Banner Xung đột & Log UI nếu xảy ra conflict (Backend) -->
          <div id="beMergeConflictBox" class="hidden bg-amber-950/40 border border-amber-600/70 rounded-lg p-3.5 space-y-3 text-xs shadow-lg">
            <div class="flex items-center justify-between text-amber-300 font-bold text-[13px] border-b border-amber-700/50 pb-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-amber-400 shrink-0 animate-pulse" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <span>Xảy ra xung đột mã nguồn (Merge Conflict)!</span>
              </span>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-900/60 border border-amber-600 text-amber-200">Cần xử lý</span>
            </div>

            <!-- Danh sách file bị conflict -->
            <div class="space-y-1">
              <span class="text-[11px] text-amber-200 font-semibold block">Các file bị xung đột:</span>
              <div id="beMergeConflictFiles" class="font-mono text-[11px] text-amber-200/90 bg-black/50 p-2.5 rounded border border-amber-800/60 max-h-32 overflow-y-auto space-y-1"></div>
            </div>

            <!-- LOG UI CHI TIẾT XUNG ĐỘT (CONSOLE OUTPUT) -->
            <div class="space-y-1">
              <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold">
                <span class="flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/></svg>
                  <span>Log UI chi tiết xung đột (Git Console Output):</span>
                </span>
                <button type="button" onclick="copyToClipboard(document.getElementById('beMergeConflictLogText').textContent)"
                  class="text-[10px] text-slate-300 hover:text-white px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 transition cursor-pointer" title="Sao chép toàn bộ log xung đột">
                  Sao chép log
                </button>
              </div>
              <pre id="beMergeConflictLogText" class="font-mono text-[11px] text-amber-200/95 bg-[#090d16] border border-amber-800/80 p-3 rounded-md max-h-56 overflow-y-auto whitespace-pre-wrap shadow-inner leading-relaxed select-text"></pre>
            </div>

            <!-- Nút hành động giải quyết xung đột -->
            <div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-amber-800/60">
              <button id="btnBeMergeAbort" type="button" onclick="doMergeAbort('be')" class="ant-btn ant-btn-danger h-[30px] px-3.5 text-xs font-semibold flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                <span>Hủy bỏ Merge (--abort)</span>
              </button>
              <button id="btnBeMergeContinue" type="button" onclick="doMergeContinue('be')" class="ant-btn ant-btn-primary h-[30px] px-3.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500 flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã sửa xong & Tiếp tục (--continue)</span>
              </button>
            </div>
          </div>

          <!-- Banner Thành công & Log Backend -->
          <div id="beMergeSuccessBox" class="hidden bg-emerald-950/40 border border-emerald-600/70 rounded-lg p-3.5 space-y-3 text-xs shadow-md">
            <div class="flex items-center justify-between text-emerald-300 font-bold text-xs border-b border-emerald-700/50 pb-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span id="beMergeSuccessTitle">Merge Backend thành công!</span>
              </span>
              <button type="button" onclick="document.getElementById('beMergeSuccessBox').classList.add('hidden')" class="text-slate-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <div id="beMergeSuccessText" class="text-slate-200 text-xs"></div>
            <!-- Log output thành công -->
            <div class="space-y-1">
              <span class="text-[10px] text-slate-400 block font-semibold">Log chi tiết:</span>
              <pre id="beMergeSuccessLogText" class="font-mono text-[11px] text-slate-200 bg-[#090d16] border border-[#244170] p-2.5 rounded max-h-36 overflow-y-auto whitespace-pre-wrap select-text"></pre>
            </div>
            <div class="flex items-center justify-between gap-2 pt-1 border-t border-emerald-800/60">
              <span class="text-[11px] text-slate-400">Đẩy nhánh đích vừa merge lên Remote:</span>
              <div class="flex items-center gap-2">
                <button id="btnBeMergeViewDiff" type="button" onclick="toggleMergeDiffView('be')"
                  title="Xem chi tiết các thay đổi vừa được merge (Diff / Files)"
                  class="ant-btn h-[28px] px-2.5 text-xs font-semibold bg-[#10223d] hover:bg-[#1a3660] text-emerald-300 hover:text-emerald-200 border border-emerald-500/50 flex items-center gap-1.5 transition cursor-pointer">
                  <svg class="w-3.5 h-3.5 shrink-0 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span>Xem thay đổi đã merge</span>
                </button>
                <button id="btnBeMergePush" type="button" onclick="doMergePush('be')" class="ant-btn ant-btn-primary h-[28px] px-3 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 border-emerald-500 flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                  <span>Push nhánh đích</span>
                </button>
              </div>
            </div>

            <!-- Khu vực hiển thị Diff & File đã merge khi bấm icon con mắt -->
            <div id="beMergeDiffContainer" class="hidden pt-2 border-t border-emerald-800/60 space-y-2">
              <div class="flex items-center justify-between text-[11px] text-slate-300">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-emerald-400 flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 stroke-current fill-none" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <span>Nội dung thay đổi đã merge (Diff):</span>
                  </span>
                  <span id="beMergeDiffStat" class="text-[10px] text-slate-400 font-mono"></span>
                </div>
                <div class="flex items-center gap-2">
                  <button id="btnBeCopyMergeDiff" type="button" onclick="copyMergeDiff('be')"
                    class="text-[10px] text-emerald-400 hover:text-emerald-300 font-sans px-2 py-0.5 rounded border border-emerald-500/30 hover:bg-emerald-500/10 transition cursor-pointer">
                    Sao chép diff
                  </button>
                  <button id="btnBeCollapseMergeDiff" type="button" onclick="toggleMergeDiffView('be')"
                    class="text-[10px] text-slate-400 hover:text-white font-sans px-2 py-0.5 rounded hover:bg-white/5 transition cursor-pointer">
                    Thu gọn
                  </button>
                </div>
              </div>

              <!-- Danh sách file thay đổi -->
              <div id="beMergeDiffFiles" class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto"></div>

              <!-- Khung code diff cuộn được -->
              <div id="beMergeDiffBody" class="sync-diff-wrapper rounded-md bg-[#1e1e1e] border border-[#333333] max-h-[380px] min-h-[100px] overflow-auto text-[11.5px] font-mono leading-relaxed shadow-inner">
                <div class="text-slate-400 text-xs p-3 text-center">Chưa có dữ liệu diff.</div>
              </div>
            </div>
            <!-- Nút quay về nhánh cũ sau khi push thành công -->
            <div id="beMergeReturnBranchWrap" class="hidden pt-2 border-t border-emerald-800/60 flex flex-wrap items-center justify-between gap-2">
              <span class="text-[11px] text-emerald-300 flex items-center gap-1.5 font-medium whitespace-nowrap shrink-0">
                <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Đã push code lên remote thành công.</span>
              </span>
              <button id="btnBeReturnPrevBranch" type="button" onclick="doReturnToPrevBranch('be')" class="ant-btn h-[28px] px-3 text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white border-sky-500 flex items-center gap-1.5 shadow-sm max-w-full">
                <svg class="w-3.5 h-3.5 fill-none stroke-current shrink-0" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
                <span id="btnBeReturnPrevBranchText" class="truncate max-w-[280px] sm:max-w-[340px]">Quay về lại nhánh lúc nãy</span>
              </button>
            </div>
          </div>

          <!-- Banner Lỗi chung (Backend) -->
          <div id="beMergeErrorBox" class="hidden bg-rose-950/40 border border-rose-600/70 rounded-lg p-3 space-y-2 text-xs">
            <div class="flex items-center justify-between text-rose-300 font-bold">
              <span class="flex items-center gap-1.5">
                <svg class="w-4 h-4 fill-current text-rose-400 shrink-0" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
                <span>Không thể thực hiện Merge:</span>
              </span>
              <button type="button" onclick="document.getElementById('beMergeErrorBox').classList.add('hidden')" class="text-rose-400 hover:text-white text-[11px]">Đóng</button>
            </div>
            <pre id="beMergeErrorDetail" class="font-mono text-[11px] text-rose-200/90 bg-black/40 p-2.5 rounded whitespace-pre-wrap max-h-36 overflow-y-auto"></pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</main>

  <!-- TAB 5: LOG LỊCH SỬ (WORK LOGS & AUDIT TRAIL) -->
  <main id="view_log" class="hidden flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-4 bg-[#101e38] border border-[#244170] rounded-lg p-4 shadow-sm">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded bg-[#182c4f] border border-[#244170] flex items-center justify-center text-amber-400">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
        </div>
        <div>
          <h2 class="text-sm font-semibold text-white">Lịch sử hoạt động</h2>
          <p class="text-xs text-slate-400">Ghi lại toàn bộ phiên thực thi task, chẩn đoán lỗi và thao tác Git</p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <div class="flex items-center bg-[#0e192c] border border-[#244170] rounded-md p-0.5 text-xs space-x-0.5">
          <button id="logFilter_all" onclick="setLogTypeFilter('all')" class="active-log-filter px-2.5 py-1 rounded bg-[rgb(25,156,255)] text-white font-bold text-xs shadow-sm cursor-pointer select-none">Tất cả</button>
          <button id="logFilter_TASK" onclick="setLogTypeFilter('TASK')" class="px-2.5 py-1 rounded text-slate-300 hover:text-white text-xs transition cursor-pointer select-none">Tác vụ</button>
          <button id="logFilter_GIT" onclick="setLogTypeFilter('GIT')" class="px-2.5 py-1 rounded text-slate-300 hover:text-white text-xs transition cursor-pointer select-none">Điều khiển Git</button>
        </div>

        <input type="text" id="logSearchInput" oninput="renderFilteredLogs()" placeholder="Tìm kiếm log..." 
          class="bg-[#0e192c] border border-[#244170] rounded-md px-3 py-1.5 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500" />

        <button onclick="loadWorkLogs()" class="ant-btn text-xs h-[30px]">
          <span>Làm mới</span>
        </button>
        <button onclick="clearLogs()" class="ant-btn ant-btn-danger text-xs h-[30px]" title="Xóa toàn bộ lịch sử hoạt động">
          <span>Xóa tất cả lịch sử</span>
        </button>
      </div>
    </div>

    <!-- Danh sách log -->
    <div id="logListContainer" class="space-y-2.5">
      <div class="text-center py-16 text-slate-500 text-xs">Đang tải lịch sử hoạt động...</div>
    </div>
  </main>

  <!-- TAB 6: SƠ ĐỒ LIÊN KẾT (ARCHITECTURE DIAGRAM & MODULE MAP) -->
  <main id="view_diagram" class="hidden flex-1 max-w-[96rem] w-full mx-auto p-4 md:p-6 space-y-5">
    <!-- Card Sơ đồ tổng thể -->
    <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm">
      <div class="border-b border-[#244170] pb-3 mb-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold text-white">
            Sơ đồ kiến trúc liên kết: Frontend (React) ↔ Backend (.NET Web API)
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">Mô hình hóa kết nối qua RESTful API Routes thực tế và quan hệ phụ thuộc Import/Export trong code.</p>
        </div>
      </div>

      <!-- Toolbar Sơ đồ liên kết -->
      <div class="flex flex-wrap items-center justify-between gap-3 mb-3 bg-[#0e192c] border border-[#244170] rounded-md p-2.5">
        <div class="flex items-center gap-2 text-xs text-slate-400">
          <span>Nhấp vào node trên sơ đồ để xem thông tin chi tiết module.</span>
          <span class="text-slate-600">|</span>
          <span>Đồng bộ: <span id="scanTimestamp" class="font-mono text-cyan-400">...</span></span>
        </div>
        <div class="flex items-center gap-2">
          <button id="btnRescanDiagram" onclick="doManualRescanDiagram()" 
            class="ant-btn ant-btn-primary text-xs h-[30px]">
            <svg id="rescanSpinner" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            <span>Quét lại Source Code</span>
          </button>
        </div>
      </div>

      <!-- Mermaid Diagram Container with Zoom & Pan Controls -->
      <div class="relative bg-[#0e192c] rounded-md border border-[#244170] overflow-hidden">
        <!-- Floating Zoom Toolbar -->
        <div class="absolute top-3 right-3 z-20 flex items-center gap-1 bg-[#101e38]/90 backdrop-blur border border-[#244170] rounded-md px-2 py-1 shadow-md">
          <button onclick="diagramZoomIn()" title="Phóng to" class="p-1 hover:bg-[#182c4f] text-slate-300 hover:text-white rounded transition text-xs font-bold">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          </button>
          <button onclick="diagramZoomOut()" title="Thu nhỏ" class="p-1 hover:bg-[#182c4f] text-slate-300 hover:text-white rounded transition text-xs font-bold">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/></svg>
          </button>
          <span id="diagramZoomLevel" class="text-[11px] font-mono text-cyan-400 px-1 min-w-[36px] text-center select-none">100%</span>
          <button onclick="diagramZoomReset()" title="Đặt lại 100%" class="px-1.5 py-0.5 hover:bg-[#182c4f] text-slate-300 hover:text-white rounded text-[11px] font-mono transition">
            100%
          </button>
          <button onclick="diagramFitView()" title="Vừa vặn khung nhìn" class="px-1.5 py-0.5 hover:bg-[#182c4f] text-cyan-300 hover:text-white rounded text-[11px] font-medium transition">
            Fit
          </button>
        </div>

        <!-- Hint drag instruction at bottom left -->
        <div class="absolute bottom-2 left-3 z-20 pointer-events-none text-[10px] text-slate-400 bg-[#0e192c]/90 px-2 py-0.5 rounded border border-[#244170]">
          Kéo để di chuyển • Cuộn chuột để thu phóng • Nhấp vào Node để xem chi tiết
        </div>

        <!-- Zoomable & Pannable Viewport -->
        <div id="diagramViewport" class="w-full h-[580px] overflow-hidden cursor-grab active:cursor-grabbing select-none flex items-center justify-center p-4">
          <div id="diagramCanvas" class="transition-transform duration-75 origin-center inline-block">
            <div id="mermaidDiagram" class="mermaid flex items-center justify-center p-12 text-slate-400 text-xs font-medium">
              <svg class="animate-spin w-4 h-4 mr-2 text-cyan-400 inline-block" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              <span>Đang phân tích mã nguồn và dựng sơ đồ liên kết...</span>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Mỗi module một hàng: Frontend | API | Backend -->
    <div class="bg-[#101e38] border border-[#244170] rounded-lg p-4 md:p-5 shadow-sm relative">
      <!-- Định nghĩa Gradient chạy dọc từ đầu mũi tên đến cuối mũi tên -->
      <svg class="w-0 h-0 absolute pointer-events-none overflow-hidden" aria-hidden="true">
        <defs>
          <linearGradient id="flowGradFeToApi" gradientUnits="userSpaceOnUse" x1="-70" y1="12" x2="10" y2="12">
            <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.1" />
            <stop offset="40%" stop-color="#06b6d4" stop-opacity="1" />
            <stop offset="75%" stop-color="#38bdf8" stop-opacity="1" />
            <stop offset="92%" stop-color="#a855f7" stop-opacity="1" />
            <stop offset="100%" stop-color="#a855f7" stop-opacity="0.1" />
            <animate attributeName="x1" from="-70" to="80" dur="1.2s" repeatCount="indefinite" />
            <animate attributeName="x2" from="10" to="160" dur="1.2s" repeatCount="indefinite" />
          </linearGradient>
          <linearGradient id="flowGradApiToBe" gradientUnits="userSpaceOnUse" x1="-70" y1="12" x2="10" y2="12">
            <stop offset="0%" stop-color="#a855f7" stop-opacity="0.1" />
            <stop offset="40%" stop-color="#a855f7" stop-opacity="1" />
            <stop offset="75%" stop-color="#199cff" stop-opacity="1" />
            <stop offset="92%" stop-color="#10b981" stop-opacity="1" />
            <stop offset="100%" stop-color="#10b981" stop-opacity="0.1" />
            <animate attributeName="x1" from="-70" to="80" dur="1.2s" repeatCount="indefinite" />
            <animate attributeName="x2" from="10" to="160" dur="1.2s" repeatCount="indefinite" />
          </linearGradient>
        </defs>
      </svg>

      <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-3 mb-3.5">
        <div>
          <h3 class="text-sm font-semibold text-white">
            Chi tiết Module: Frontend ↔ API Contract ↔ Backend (.NET)
          </h3>
          <p class="text-xs text-slate-400 mt-0.5 max-w-3xl">Liên kết trực tiếp các hàm tương tác API ở Frontend qua từng phương thức GET, POST, PUT, DELETE tới hàm xử lý ở Backend.</p>
        </div>
        <div class="flex items-center gap-2 w-full lg:w-auto">
          <span id="diagramMatchCount" class="shrink-0 text-[11px] font-mono text-slate-200 bg-[#0e192c] border border-[#244170] rounded px-2.5 py-1">—</span>
          <input type="text" id="diagramSearchInput" oninput="filterDiagramModules()"
            placeholder="Tìm module, hàm FE, API, hàm BE..."
            class="w-full lg:w-72 bg-[#0e192c] border border-[#244170] rounded-md px-3 py-1 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-500" />
        </div>
      </div>

      <div class="hidden lg:grid grid-cols-[minmax(0,1fr)_76px_minmax(0,1.35fr)_76px_minmax(0,1fr)] items-center gap-2 mb-2 px-3">
        <div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-cyan-300">
          <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
          Frontend · Hàm tương tác API
        </div>
        <div></div>
        <div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-purple-300">
          <span class="w-2 h-2 rounded-full bg-purple-400"></span>
          API Contract · GET / POST / PUT / DELETE
        </div>
        <div></div>
        <div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          Backend · Hàm xử lý (.NET Actions)
        </div>
      </div>

      <div id="diagramModuleEmpty" class="hidden text-center text-sm text-slate-400 py-12 border border-dashed border-slate-700 rounded-md">
        Không có module nào khớp từ khóa.
      </div>
      <div id="moduleLookupList" class="space-y-3">
        <!-- Rendered by JS -->
      </div>
    </div>
  </main>

  <!-- Ant Design Modal Root (Confirm / Alert Dialog) -->
  <div id="antdModalRoot" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm transition-opacity duration-150">
    <div id="antdModalCard" class="bg-[#101e38] border border-[#244170] rounded-lg shadow-2xl max-w-md w-full p-5 text-white transform transition-all duration-150 scale-95 opacity-0">
      <div class="flex items-start gap-3">
        <div id="antdModalIcon" class="shrink-0 mt-0.5"></div>
        <div class="flex-1 min-w-0">
          <h3 id="antdModalTitle" class="text-sm font-semibold text-white leading-snug"></h3>
          <div id="antdModalContent" class="text-xs text-slate-300 mt-2 leading-relaxed whitespace-pre-wrap"></div>
        </div>
      </div>
      <div class="flex items-center justify-end gap-2 mt-5 pt-1">
        <button id="antdModalCancelBtn" type="button" class="ant-btn text-xs h-[32px] px-3.5 text-slate-300 hover:text-white">
          Hủy
        </button>
        <button id="antdModalOkBtn" type="button" class="ant-btn ant-btn-primary text-xs h-[32px] px-3.5">
          Xác nhận
        </button>
      </div>
    </div>
  </div>

  <script id="studioMainScript">
const TABS = ['task', 'branch', 'log', 'diagram'];
let activeTab = 'task';
let renderedTurnCount = 0;
let mermaidRendered = false;

// ---------------- ANTD MODAL CONFIRM & ALERT ----------------
function antdConfirm({ title = 'Xác nhận', content = '', okText = 'Xác nhận', cancelText = 'Hủy', danger = false }) {
  return new Promise((resolve) => {
    const root = document.getElementById('antdModalRoot');
    const card = document.getElementById('antdModalCard');
    const titleEl = document.getElementById('antdModalTitle');
    const contentEl = document.getElementById('antdModalContent');
    const iconEl = document.getElementById('antdModalIcon');
    const cancelBtn = document.getElementById('antdModalCancelBtn');
    const okBtn = document.getElementById('antdModalOkBtn');

    if (!root || !card) {
      const plainContent = String(content || '').replace(/<[^>]+>/g, '');
      resolve(window.confirm(plainContent ? `${title}\n\n${plainContent}` : title));
      return;
    }

    titleEl.textContent = title;
    if (typeof content === 'string' && /<[a-z][\s\S]*>/i.test(content)) {
      contentEl.innerHTML = content;
    } else {
      contentEl.textContent = content;
    }
    okBtn.textContent = okText;
    cancelBtn.textContent = cancelText;
    cancelBtn.style.display = 'inline-flex';

    if (danger) {
      okBtn.className = 'ant-btn text-xs h-[32px] px-3.5 bg-rose-600 hover:bg-rose-500 border border-rose-500 text-white font-medium';
    } else {
      okBtn.className = 'ant-btn ant-btn-primary text-xs h-[32px] px-3.5 font-medium';
    }

    iconEl.innerHTML = `
          <svg class="w-5 h-5 ${danger ? 'text-rose-400' : 'text-blue-400'}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        `;

    function cleanup(result) {
      card.classList.remove('scale-100', 'opacity-100');
      card.classList.add('scale-95', 'opacity-0');
      setTimeout(() => {
        root.classList.add('hidden');
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        root.onclick = null;
        document.removeEventListener('keydown', keyHandler);
        resolve(result);
      }, 120);
    }

    function keyHandler(e) {
      if (e.key === 'Escape') cleanup(false);
      if (e.key === 'Enter') cleanup(true);
    }

    okBtn.onclick = () => cleanup(true);
    cancelBtn.onclick = () => cleanup(false);
    root.onclick = (e) => {
      if (e.target === root) cleanup(false);
    };
    document.addEventListener('keydown', keyHandler);

    root.classList.remove('hidden');
    requestAnimationFrame(() => {
      card.classList.remove('scale-95', 'opacity-0');
      card.classList.add('scale-100', 'opacity-100');
    });
  });
}

function antdAlert({ title = 'Thông báo', content = '', okText = 'Đã hiểu', type = 'info' }) {
  return new Promise((resolve) => {
    const root = document.getElementById('antdModalRoot');
    const card = document.getElementById('antdModalCard');
    const titleEl = document.getElementById('antdModalTitle');
    const contentEl = document.getElementById('antdModalContent');
    const iconEl = document.getElementById('antdModalIcon');
    const cancelBtn = document.getElementById('antdModalCancelBtn');
    const okBtn = document.getElementById('antdModalOkBtn');

    if (!root || !card) {
      window.alert(content ? `${title}\n\n${content}` : title);
      resolve(true);
      return;
    }

    titleEl.textContent = title;
    contentEl.textContent = content;
    okBtn.textContent = okText;
    cancelBtn.style.display = 'none';

    const isError = type === 'error';
    const isSuccess = type === 'success';

    okBtn.className = 'ant-btn ant-btn-primary text-xs h-[32px] px-3.5 font-medium';

    if (isError) {
      iconEl.innerHTML = `
            <svg class="w-5 h-5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          `;
    } else if (isSuccess) {
      iconEl.innerHTML = `
            <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          `;
    } else {
      iconEl.innerHTML = `
            <svg class="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          `;
    }

    function cleanup() {
      card.classList.remove('scale-100', 'opacity-100');
      card.classList.add('scale-95', 'opacity-0');
      setTimeout(() => {
        root.classList.add('hidden');
        okBtn.onclick = null;
        root.onclick = null;
        document.removeEventListener('keydown', keyHandler);
        resolve(true);
      }, 120);
    }

    function keyHandler(e) {
      if (e.key === 'Escape' || e.key === 'Enter') cleanup();
    }

    okBtn.onclick = () => cleanup();
    root.onclick = (e) => {
      if (e.target === root) cleanup();
    };
    document.addEventListener('keydown', keyHandler);

    root.classList.remove('hidden');
    requestAnimationFrame(() => {
      card.classList.remove('scale-95', 'opacity-0');
      card.classList.add('scale-100', 'opacity-100');
    });
  });
}

function antdPromptStash({ title = 'Lỗi Pull nhánh', content = '', okText = 'Git stash nó', cancelText = 'Đã hiểu' }) {
  return new Promise((resolve) => {
    const root = document.getElementById('antdModalRoot');
    const card = document.getElementById('antdModalCard');
    const titleEl = document.getElementById('antdModalTitle');
    const contentEl = document.getElementById('antdModalContent');
    const iconEl = document.getElementById('antdModalIcon');
    const cancelBtn = document.getElementById('antdModalCancelBtn');
    const okBtn = document.getElementById('antdModalOkBtn');

    if (!root || !card) {
      if (window.confirm(`${title}\n\n${content}\n\nBạn có muốn Git Stash các thay đổi dở dang để tiếp tục pull không?`)) {
        resolve('stash');
      } else {
        resolve('close');
      }
      return;
    }

    titleEl.textContent = title;
    contentEl.textContent = content;
    cancelBtn.textContent = cancelText;
    cancelBtn.style.display = 'inline-flex';
    cancelBtn.className = 'ant-btn text-xs h-[32px] px-3.5 text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-600';

    okBtn.textContent = okText;
    okBtn.className = 'ant-btn text-xs h-[32px] px-3.5 bg-amber-600 hover:bg-amber-500 border border-amber-500 text-white font-semibold shadow-md';

    iconEl.innerHTML = `
      <svg class="w-5 h-5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    `;

    function cleanup(action) {
      card.classList.remove('scale-100', 'opacity-100');
      card.classList.add('scale-95', 'opacity-0');
      setTimeout(() => {
        root.classList.add('hidden');
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        root.onclick = null;
        document.removeEventListener('keydown', keyHandler);
        resolve(action);
      }, 120);
    }

    function keyHandler(e) {
      if (e.key === 'Escape') cleanup('close');
    }

    okBtn.onclick = () => cleanup('stash');
    cancelBtn.onclick = () => cleanup('close');
    root.onclick = (e) => {
      if (e.target === root) cleanup('close');
    };
    document.addEventListener('keydown', keyHandler);

    root.classList.remove('hidden');
    requestAnimationFrame(() => {
      card.classList.remove('scale-95', 'opacity-0');
      card.classList.add('scale-100', 'opacity-100');
    });
  });
}
window.antdPromptStash = antdPromptStash;

function isAuthorMe(author, isMe) {
  if (isMe === true) return true;
  if (!author || typeof author !== 'string') return false;
  const s = author.trim().toLowerCase();
  if (!s) return false;
  if (s.includes('thiết') || s.includes('thiet') || s.includes('thietnv')) {
    return true;
  }
  if (window._currentGitUser && typeof window._currentGitUser === 'string') {
    const cur = window._currentGitUser.trim().toLowerCase();
    if (cur && (s.includes(cur) || cur.includes(s))) {
      return true;
    }
  }
  return false;
}
window.isAuthorMe = isAuthorMe;

function formatCommitAuthor(author, isMe) {
  if (!author) return '';
  const isMine = isAuthorMe(author, isMe);
  if (isMine) {
    return `${escapeHtml(author)} <span class="text-blue-400 font-medium font-sans">(Tôi)</span>`;
  }
  return escapeHtml(author);
}
window.formatCommitAuthor = formatCommitAuthor;

/**
 * Chuẩn hóa thời gian tương đối sang định dạng tiếng Việt.
 * Nếu số phút >= 60 phút thì chuyển thành XhYY (ví dụ: 80 phút -> 1h20, 80p -> 1h20).
 */
function formatRelativeDate(raw) {
  if (!raw) return '';
  const s = String(raw).trim();
  if (!s) return '';

  const isAgo = /\bago\b/i.test(s) || /trước/i.test(s);
  let clean = s.replace(/\bago\b/gi, '').replace(/\btrước\b/gi, '').trim();

  // Pattern 1: X hours, Y mins (e.g. 1 hour, 20 minutes / 1h20)
  const mHm = clean.match(/(\d+)\s*(?:hours?|giờ|hrs?|h)\s*(?:,?\s*and\s*)?,?\s*(\d+)\s*(?:minutes?|phút|mins?|min|m|p)?(?:$|\s|[.,!])/i);
  if (mHm) {
    let h = parseInt(mHm[1], 10);
    let m = parseInt(mHm[2], 10);
    h += Math.floor(m / 60);
    m = m % 60;
    const res = m > 0 ? `${h}h${m < 10 ? '0' + m : m}` : `${h}h`;
    return isAgo ? `${res} trước` : res;
  }

  // Pattern 2: Only hours (e.g. 1 hour, 2 hours, 1h)
  const mH = clean.match(/(\d+)\s*(?:hours?|giờ|hrs?|h)(?:$|\s|[.,!])/i);
  if (mH) {
    const h = parseInt(mH[1], 10);
    return isAgo ? `${h}h trước` : `${h}h`;
  }

  // Pattern 3: Only minutes (e.g. 80 minutes, 80 min, 80p, 80 phút, 80m)
  const mM = clean.match(/(\d+)\s*(?:minutes?|phút|mins?|min|m|p)(?:$|\s|[.,!])/i);
  if (mM) {
    const m = parseInt(mM[1], 10);
    let res = '';
    if (m >= 60) {
      const h = Math.floor(m / 60);
      const remM = m % 60;
      res = remM > 0 ? `${h}h${remM < 10 ? '0' + remM : remM}p` : `${h}h`;
    } else {
      res = `${m}p`;
    }
    return isAgo ? `${res} trước` : res;
  }

  // Pattern 4: Seconds
  const mS = clean.match(/(\d+)\s*(?:seconds?|giây|secs?|s)(?:$|\s|[.,!])/i);
  if (mS) {
    const sec = parseInt(mS[1], 10);
    let res = '';
    if (sec >= 60) {
      const m = Math.floor(sec / 60);
      const remS = sec % 60;
      res = remS > 0 ? `${m}p${remS}s` : `${m}p`;
    } else {
      res = `${sec}s`;
    }
    return isAgo ? `${res} trước` : res;
  }
  }

  // Pattern 5: Days
  const mD = clean.match(/(\d+)\s*(?:days?|ngày)(?:$|\s|[.,!])/i);
  if (mD) {
    const d = parseInt(mD[1], 10);
    return isAgo ? `${d} ngày trước` : `${d} ngày`;
  }

  // Pattern 6: Weeks
  const mW = clean.match(/(\d+)\s*(?:weeks?|tuần)(?:$|\s|[.,!])/i);
  if (mW) {
    const w = parseInt(mW[1], 10);
    return isAgo ? `${w} tuần trước` : `${w} tuần`;
  }

  // Pattern 7: Months
  const mMo = clean.match(/(\d+)\s*(?:months?|tháng)(?:$|\s|[.,!])/i);
  if (mMo) {
    const mo = parseInt(mMo[1], 10);
    return isAgo ? `${mo} tháng trước` : `${mo} tháng`;
  }

  // Pattern 8: Years
  const mY = clean.match(/(\d+)\s*(?:years?|năm)(?:$|\s|[.,!])/i);
  if (mY) {
    const y = parseInt(mY[1], 10);
    return isAgo ? `${y} năm trước` : `${y} năm`;
  }

  const lower = clean.toLowerCase();
  if (lower.includes('just now') || lower.includes('moment ago')) return 'vừa xong';
  if (lower.includes('yesterday')) return 'hôm qua';

  return s;
}

/**
 * Định dạng thời lượng (giây) sang dạng thân thiện.
 * Nếu thời gian >= 60 phút (3600s), hiển thị dạng XhYY (ví dụ: 80 phút -> 1h20).
 */
function formatDuration(sec) {
  if (sec === null || sec === undefined || isNaN(sec)) return '';
  const totalSec = Number(sec);
  if (totalSec < 60) {
    return `${Math.round(totalSec * 10) / 10}s`;
  }
  const totalMin = Math.floor(totalSec / 60);
  const remSec = Math.round(totalSec % 60);

  if (totalMin >= 60) {
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    return m > 0 ? `${h}h${m < 10 ? '0' + m : m}` : `${h}h`;
  }

  return remSec > 0 ? `${totalMin}p${remSec < 10 ? '0' + remSec : remSec}s` : `${totalMin}p`;
}

function switchTab(tab, updateHistory = true) {
  if (tab === 'live' || tab === 'fixbug') {
    const actionType = tab === 'fixbug' ? 'fixbug' : 'task';
    tab = 'task';
    if (typeof setTaskActionType === 'function') setTaskActionType(actionType);
  }
  if (!TABS.includes(tab)) tab = 'task';

  // Nếu bấm vào đúng tab đang active (và không có subtab mới cần chuyển)
  if (activeTab === tab &&
      (!window.initGitSubTab || window.initGitSubTab === activeGitSubTab) &&
      (!window.initSettingsSubTab || window.initSettingsSubTab === activeSettingsSubTab)) {
    return;
  }

  activeTab = tab;
  window.activeTab = tab;
  try { localStorage.setItem('activeAgentStudioTab', tab); } catch (e) { }

  // Xóa style tạm thời ở <head> nếu có
  const initStyle = document.getElementById('initialTabStyle');
  if (initStyle) initStyle.remove();
  const initGitSubStyle = document.getElementById('initialGitSubTabStyle');
  if (initGitSubStyle) initGitSubStyle.remove();

  // Cập nhật URL trên thanh địa chỉ trình duyệt không reload trang
  let targetPath = (window.TAB_ROUTES && window.TAB_ROUTES[tab]) || ('/' + tab);
  if (tab === 'branch') {
    const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    const urlSub = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
    const sub = window.initGitSubTab || urlSub || activeGitSubTab || 'pull_sync';
    const subRoutes = window.GIT_SUBTAB_ROUTES || {
      'pull_sync': '/git-control',
      'branch': '/git-control/checkout-branch',
      'switch': '/git-control/switch-branch',
      'cherry_pick': '/git-control/cherry-pick',
      'merge': '/git-control/merge'
    };
    targetPath = subRoutes[sub] || '/git-control';
  }
  if (updateHistory && window.location.pathname !== targetPath) {
    try {
      const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
      const urlSub = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
      const sub = window.initGitSubTab || urlSub || activeGitSubTab || 'pull_sync';
      window.history.pushState({ tab: tab, subTab: tab === 'branch' ? sub : null }, '', targetPath);
    } catch (e) { }
  }

  TABS.forEach(t => {
    const viewEl = document.getElementById('view_' + t);
    const btnEl = document.getElementById('tabBtn_' + t);
    if (t === tab) {
      if (viewEl) {
        viewEl.classList.remove('hidden');
        if (tab === 'task') {
          viewEl.style.setProperty('display', 'grid', 'important');
        } else if (tab === 'jira') {
          viewEl.style.setProperty('display', 'flex', 'important');
          viewEl.style.setProperty('flex-direction', 'column', 'important');
        } else {
          viewEl.style.setProperty('display', 'block', 'important');
        }
      }
      if (btnEl) {
        btnEl.className = 'px-3.5 py-1.5 rounded-md bg-[#ffffff] text-[#182c4f] font-bold shadow-sm transition text-xs cursor-pointer select-none';
      }
    } else {
      if (viewEl && (!viewEl.classList.contains('hidden') || viewEl.style.display !== 'none')) {
        viewEl.classList.add('hidden');
        viewEl.style.setProperty('display', 'none', 'important');
      }
      if (btnEl) {
        btnEl.className = 'px-3.5 py-1.5 rounded-md text-slate-200 hover:text-white hover:bg-white/10 font-medium transition text-xs cursor-pointer select-none';
      }
    }
  });

  if (window.scrollY > 0) {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  if (tab === 'branch') {
    const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    const urlSub = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
    const sub = window.initGitSubTab || urlSub || activeGitSubTab || 'pull_sync';
    activeGitSubTab = sub;
    window.initGitSubTab = sub;
    if (typeof switchGitSubTab === 'function') {
      switchGitSubTab(sub, false);
    }
  }

  if (tab !== 'jira' && typeof stopJiraAutoSync === 'function') {
    stopJiraAutoSync();
  }

  if (!updateHistory) {
    executeTabCallback(tab);
  } else {
    clearTimeout(window._tabCallbackTimer);
    window._tabCallbackTimer = setTimeout(() => {
      if (activeTab !== tab) return;
      executeTabCallback(tab);
    }, 40);
  }
}

function executeTabCallback(tab) {
  try {
    if (tab === 'task') {
      if (typeof pollStatus === 'function') pollStatus();
    } else if (tab === 'branch') {
      const sub = activeGitSubTab || 'pull_sync';
      if (sub === 'pull_sync') {
        if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
      } else if (sub === 'switch') {
        if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      } else if (sub === 'cherry_pick') {
        if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
      } else if (sub === 'merge') {
        if (typeof loadMergeInfo === 'function') loadMergeInfo();
      }
    } else if (tab === 'log') {
      if (typeof loadWorkLogs === 'function') loadWorkLogs();
    } else if (tab === 'diagram') {
      if (typeof renderDiagram === 'function') renderDiagram();
    }
  } catch (err) {
    console.error('Lỗi khi kích hoạt callback của tab:', tab, err);
  }
}
window.switchTab = switchTab;

let activeGitSubTab = 'pull_sync';

function switchGitSubTab(subTab, updateHistory = true) {
  if (!['branch', 'switch', 'cherry_pick', 'pull_sync', 'merge'].includes(subTab)) subTab = 'pull_sync';
  activeGitSubTab = subTab;
  window.initGitSubTab = subTab;

  const initGitSubStyle = document.getElementById('initialGitSubTabStyle');
  if (initGitSubStyle) initGitSubStyle.remove();

  // Cập nhật URL đồng bộ với git subtab trên thanh địa chỉ trình duyệt
  const subRoutes = window.GIT_SUBTAB_ROUTES || {
    'pull_sync': '/git-control',
    'branch': '/git-control/checkout-branch',
    'switch': '/git-control/switch-branch',
    'cherry_pick': '/git-control/cherry-pick',
    'merge': '/git-control/merge'
  };
  const targetPath = subRoutes[subTab] || '/git-control';
  if (updateHistory && activeTab === 'branch' && window.location.pathname !== targetPath) {
    try {
      window.history.pushState({ tab: 'branch', subTab: subTab }, '', targetPath);
    } catch (e) { }
  }
  try { localStorage.setItem('activeGitSubTab', subTab); } catch(e) {}

  const btnBranch = document.getElementById('gitSubTabBtn_branch');
  const btnSwitch = document.getElementById('gitSubTabBtn_switch');
  const btnCherry = document.getElementById('gitSubTabBtn_cherry_pick');
  const btnSync = document.getElementById('gitSubTabBtn_pull_sync');
  const btnMerge = document.getElementById('gitSubTabBtn_merge');

  const viewBranch = document.getElementById('gitSubView_branch');
  const viewSwitch = document.getElementById('gitSubView_switch');
  const viewCherry = document.getElementById('gitSubView_cherry_pick');
  const viewSync = document.getElementById('gitSubView_pull_sync');
  const viewMerge = document.getElementById('gitSubView_merge');

  const isLight = document.body.classList.contains('light-mode');
  const activeCls = 'active-git-subtab px-3.5 py-1.5 rounded-md bg-[rgb(25,156,255)] text-white font-bold text-xs shadow-sm transition cursor-pointer select-none';
  const inactiveCls = isLight
    ? 'px-3.5 py-1.5 rounded-md text-[#334155] hover:text-[#0f172a] hover:bg-slate-200/60 font-medium text-xs transition cursor-pointer select-none'
    : 'px-3.5 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-white/10 font-medium text-xs transition cursor-pointer select-none';

  if (viewBranch) viewBranch.classList.add('hidden');
  if (viewSwitch) viewSwitch.classList.add('hidden');
  if (viewCherry) viewCherry.classList.add('hidden');
  if (viewSync) viewSync.classList.add('hidden');
  if (viewMerge) viewMerge.classList.add('hidden');

  if (btnBranch) btnBranch.className = inactiveCls;
  if (btnSwitch) btnSwitch.className = inactiveCls;
  if (btnCherry) btnCherry.className = inactiveCls;
  if (btnSync) btnSync.className = inactiveCls;
  if (btnMerge) btnMerge.className = inactiveCls;

  if (subTab === 'branch') {
    if (viewBranch) viewBranch.classList.remove('hidden');
    if (btnBranch) btnBranch.className = activeCls;
  } else if (subTab === 'switch') {
    if (viewSwitch) viewSwitch.classList.remove('hidden');
    if (btnSwitch) btnSwitch.className = activeCls;
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
  } else if (subTab === 'cherry_pick') {
    if (viewCherry) viewCherry.classList.remove('hidden');
    if (btnCherry) btnCherry.className = activeCls;
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
  } else if (subTab === 'merge') {
    if (viewMerge) viewMerge.classList.remove('hidden');
    if (btnMerge) btnMerge.className = activeCls;
    if (typeof loadMergeInfo === 'function') loadMergeInfo();
  } else {
    if (viewSync) viewSync.classList.remove('hidden');
    if (btnSync) btnSync.className = activeCls;
    if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
  }
}
window.switchGitSubTab = switchGitSubTab;

async function refreshCurrentGitView() {
  const btn = document.getElementById('btnRefreshGit');
  const spinner = document.getElementById('refreshGitSpinner');
  const text = document.getElementById('refreshGitText');
  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  if (text) text.textContent = 'Đang tải...';

  try {
    if (activeGitSubTab === 'cherry_pick') {
      if (typeof loadCherryPickInfo === 'function') await loadCherryPickInfo();
    } else if (activeGitSubTab === 'pull_sync') {
      if (typeof loadPullSyncInfo === 'function') await loadPullSyncInfo();
    } else if (activeGitSubTab === 'merge') {
      if (typeof loadMergeInfo === 'function') await loadMergeInfo();
    } else {
      if (typeof loadGitBranchInfo === 'function') await loadGitBranchInfo();
    }
    showToast('Đã làm mới dữ liệu Git.');
  } catch (err) {
    showToast('Lỗi khi làm mới: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
    if (text) text.textContent = 'Làm mới';
  }
}
window.refreshCurrentGitView = refreshCurrentGitView;

// Lắng nghe nút Back / Forward trên trình duyệt
window.addEventListener('popstate', (e) => {
  const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
  let targetTab = (e.state && e.state.tab) || (typeof window.getTabFromUrl === 'function' ? window.getTabFromUrl() : null) || 'task';
  let targetSubTab = (e.state && e.state.subTab) || (window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath]) || window.initGitSubTab;
  switchTab(targetTab, false);
  if (targetTab === 'branch') {
    if (!targetSubTab) targetSubTab = 'pull_sync';
    if (typeof switchGitSubTab === 'function') {
      window.initGitSubTab = null;
      switchGitSubTab(targetSubTab, false);
    }
  }
});

const DIAGRAM_MODULES = [
  {
    id: 'booking-bedroom',
    title: 'Phòng & Sơ đồ giường (BedRoom)',
    skill: 'skill-booking-bedroom',
    api: {
      route: '/bed-room-position',
      endpoints: [
        { method: 'GET', path: '/bed-room-position', note: 'Lấy sơ đồ danh sách phòng & giường' },
        { method: 'POST', path: '/bed-room-position/change-bed', note: 'Chuyển đổi giường / di dời dịch vụ' },
        { method: 'PUT', path: '/bed-room-position/{id}/status', note: 'Đổi trạng thái giường (trống/bận)' }
      ]
    },
    fe: {
      path: 'src/scripts/business/bed-room',
      resource: 'src/scripts/restful/resources/bedRoomPosition.ts',
      desc: 'Quản lý bản đồ sơ đồ giường, trạng thái ghế bận/trống realtime, modal chuyển đổi giường khách đang làm dịch vụ.',
      imports: [
        '@/business/booking',
        '@/business/customer',
        '@/scripts/restful/resources/bedRoomPosition',
        '@/scripts/helpers/formatHelper'
      ],
      exports: [
        'BedRoomMapContainer',
        'BedItemCard',
        'ChangeBedModal',
        'useBedRoomState'
      ]
    },
    be: {
      path: 'Controllers/BedRoomPositionController.cs',
      controller: 'BedRoomPositionController : BaseApiController',
      desc: 'Xử lý truy vấn trạng thái phòng/giường đa chi nhánh, giao dịch atomic đổi giường an toàn cho KTV.',
      injections: [
        'IBedRoomPositionService',
        'IBookingService',
        'IUnitOfWork',
        'ISalonBranchContext'
      ],
      exports: [
        'GetBedRoomPositions() -> ApiResponse<List<BedRoomPositionDto>>',
        'ChangeBed(ChangeBedRequestDto) -> ApiResponse<bool>',
        'UpdateStatus(int id, UpdateStatusDto) -> ApiResponse'
      ],
      links: ['Booking (Ràng buộc lịch hẹn)', 'SalonBranchId (Filter phòng)']
    }
  },
  {
    id: 'pos-cashier',
    title: 'Thu ngân & Bán hàng (POS / Invoice)',
    skill: 'skill-pos-cashier',
    api: {
      route: '/api/v1/invoices',
      endpoints: [
        { method: 'POST', path: '/api/v1/invoices', note: 'Tạo hóa đơn bán lẻ / dịch vụ' },
        { method: 'GET', path: '/api/v1/invoices/{id}', note: 'Lấy chi tiết đơn hàng & thanh toán' },
        { method: 'POST', path: '/api/v1/invoices/{id}/pay', note: 'Xác nhận thanh toán đa phương thức' }
      ]
    },
    fe: {
      path: 'src/scripts/business/invoice',
      resource: 'src/scripts/restful/resources/invoice.ts',
      desc: 'Màn hình thu ngân POS, chọn dịch vụ/sản phẩm/combo, áp khuyến mãi, chia bill, in phiếu hóa đơn.',
      imports: [
        '@/business/customer',
        '@/business/invoice-detail',
        '@/business/commission',
        '@/business/cashbook-transaction',
        '@/scripts/restful/resources/invoice'
      ],
      exports: [
        'InvoiceContainer',
        'InvoiceItemTable',
        'PaymentModal',
        'useInvoiceStore'
      ]
    },
    be: {
      path: 'Controllers/InvoiceController.cs',
      controller: 'InvoiceController : BaseApiController',
      desc: 'Trọng tâm đơn hàng POS: Điều phối thanh toán, tự động trừ kho nguyên phụ liệu, tính hoa hồng KTV và ghi nhận sổ quỹ.',
      injections: [
        'IInvoiceLocalService',
        'ProductInventoryService',
        'CommissionService',
        'PaymentReceiptService',
        'IUnitOfWork'
      ],
      exports: [
        'CreateInvoiceAsync(InvoiceRequestDto) -> ApiResponse<InvoiceDto>',
        'PayInvoiceAsync(int id, PaymentRequestDto) -> ApiResponse',
        'CancelInvoiceAsync(int id, CancelReasonDto) -> ApiResponse'
      ],
      links: ['Kho hàng (Trừ tồn kho)', 'Hoa hồng (Ghi nhận KTV)', 'Sổ quỹ (Phiếu thu)', 'HĐĐT (Phát hành)']
    }
  },
  {
    id: 'calendar-schedule',
    title: 'Lịch hẹn & Ca làm việc (Booking / Calendar)',
    skill: 'skill-calendar-schedule',
    api: {
      route: '/api/v1/bookings',
      endpoints: [
        { method: 'GET', path: '/api/v1/bookings', note: 'Lấy lịch đặt hẹn theo ngày/chi nhánh' },
        { method: 'POST', path: '/api/v1/bookings', note: 'Đặt lịch hẹn mới cho khách' },
        { method: 'PUT', path: '/api/v1/bookings/{id}/checkin', note: 'Check-in khách vào giường' }
      ]
    },
    fe: {
      path: 'src/scripts/business/booking',
      resource: 'src/scripts/restful/resources/booking.ts',
      desc: 'Lịch biểu đặt hẹn theo nhân viên, khung giờ, check-in khách đến salon và đẩy vào danh sách chờ.',
      imports: [
        '@/business/customer',
        '@/business/bed-room',
        '@/scripts/restful/resources/booking',
        '@/scripts/helpers/dateHelper'
      ],
      exports: [
        'BookingCalendarContainer',
        'BookingCreateModal',
        'BookingCardItem',
        'useBookingCalendar'
      ]
    },
    be: {
      path: 'Controllers/BookingController.cs',
      controller: 'BookingController : BaseApiController',
      desc: 'Quản lý lịch hẹn, kiểm tra trùng khung giờ KTV, thông báo nhắc hẹn Zalo/SMS và luồng check-in.',
      injections: [
        'IBookingService',
        'ICustomerService',
        'IStaffScheduleService',
        'IUnitOfWork'
      ],
      exports: [
        'GetBookingsAsync(BookingFilterDto) -> ApiResponse<List<BookingDto>>',
        'CreateBookingAsync(BookingCreateDto) -> ApiResponse<BookingDto>',
        'CheckinBookingAsync(int id) -> ApiResponse<bool>'
      ],
      links: ['Customer (Hồ sơ khách)', 'BedRoomPosition (Gán giường)', 'Staff (Ca làm việc)']
    }
  },
  {
    id: 'customer-crm',
    title: 'Khách hàng & Hạng thẻ VIP (Customer CRM)',
    skill: 'skill-customer-crm',
    api: {
      route: '/api/v1/customers',
      endpoints: [
        { method: 'GET', path: '/api/v1/customers', note: 'Tra cứu danh sách & phân hạng thẻ khách' },
        { method: 'POST', path: '/api/v1/customers', note: 'Thêm mới hồ sơ khách hàng' },
        { method: 'GET', path: '/api/v1/customers/{id}/debts', note: 'Tra cứu sổ công nợ khách hàng' }
      ]
    },
    fe: {
      path: 'src/scripts/business/customer',
      resource: 'src/scripts/restful/resources/customer.ts',
      desc: 'Quản lý thông tin khách, lịch sử trị liệu, điểm tích lũy thành viên, hạn mức công nợ và sinh nhật.',
      imports: [
        '@/scripts/restful/resources/customer',
        '@/business/customer-group',
        '@/business/customer-debt',
        '@/components/common/AvatarUploader'
      ],
      exports: [
        'CustomerListTable',
        'CustomerDetailDrawer',
        'CustomerDebtHistory',
        'useCustomerStore'
      ]
    },
    be: {
      path: 'Controllers/CustomerController.cs',
      controller: 'CustomerController : BaseApiController',
      desc: 'Hồ sơ 360 độ khách hàng, xếp hạng thẻ tự động theo doanh số, kiểm soát hạn mức công nợ tối đa.',
      injections: [
        'ICustomerService',
        'ICustomerDebtService',
        'ICustomerRankService',
        'IUnitOfWork'
      ],
      exports: [
        'GetCustomersAsync(CustomerFilterDto) -> ApiResponse<PagedList<CustomerDto>>',
        'CreateCustomerAsync(CustomerCreateDto) -> ApiResponse<CustomerDto>',
        'GetCustomerDebtsAsync(int id) -> ApiResponse<DebtSummaryDto>'
      ],
      links: ['Invoice (Lịch sử chi tiêu)', 'Booking (Lịch hẹn)', 'Package (Liệu trình đã mua)']
    }
  },
  {
    id: 'warehouse-inventory',
    title: 'Kho hàng & Nhập xuất tồn (Warehouse)',
    skill: 'skill-warehouse-inventory',
    api: {
      route: '/api/v1/warehouse-transactions',
      endpoints: [
        { method: 'GET', path: '/api/v1/warehouse-transactions', note: 'Danh sách phiếu nhập / xuất kho' },
        { method: 'POST', path: '/api/v1/warehouse-transactions/import', note: 'Tạo phiếu nhập hàng nhà cung cấp' },
        { method: 'POST', path: '/api/v1/warehouse-transactions/deduct', note: 'Trừ kho hao phí nguyên vật liệu làm dịch vụ' }
      ]
    },
    fe: {
      path: 'src/scripts/business/warehouse-transaction',
      resource: 'src/scripts/restful/resources/warehouseTransaction.ts',
      desc: 'Phiếu nhập xuất kho, kiểm kê định kỳ, cấu hình định mức tiêu hao nguyên vật liệu trên từng gói dịch vụ.',
      imports: [
        '@/scripts/restful/resources/warehouseTransaction',
        '@/business/product',
        '@/business/supplier',
        '@/components/common/BarcodeScanner'
      ],
      exports: [
        'WarehouseTransactionTable',
        'CreateImportNoteModal',
        'InventoryCheckForm',
        'useWarehouseStore'
      ]
    },
    be: {
      path: 'Controllers/WarehouseTransactionController.cs',
      controller: 'WarehouseTransactionController : BaseApiController',
      desc: 'Tính giá vốn bình quân gia quyền, quản lý tồn kho theo lô/hạn dùng, tự động trừ kho khi POS chốt bill.',
      injections: [
        'IProductInventoryService',
        'IWarehouseTransactionService',
        'ISupplierService',
        'IUnitOfWork'
      ],
      exports: [
        'GetTransactionsAsync(FilterDto) -> ApiResponse<PagedList<WarehouseDto>>',
        'CreateImportNoteAsync(ImportNoteDto) -> ApiResponse<int>',
        'DeductConsumptionAsync(DeductDto) -> ApiResponse<bool>'
      ],
      links: ['Invoice (Trừ kho bán lẻ & tiêu hao)', 'Cashbook (Phiếu chi trả NCC)']
    }
  },
  {
    id: 'commission-setup',
    title: 'Hoa hồng & Chiết khấu KTV (Commission)',
    skill: 'skill-commission-setup',
    api: {
      route: '/api/v1/commissions',
      endpoints: [
        { method: 'GET', path: '/api/v1/commissions/policies', note: 'Lấy chính sách hoa hồng KTV' },
        { method: 'POST', path: '/api/v1/commissions/calculate', note: 'Tính toán hoa hồng theo hóa đơn' },
        { method: 'GET', path: '/api/v1/commissions/report-staff', note: 'Báo cáo tổng hợp hoa hồng theo nhân viên' }
      ]
    },
    fe: {
      path: 'src/scripts/business/commission-setup',
      resource: 'src/scripts/restful/resources/commission.ts',
      desc: 'Cấu hình công thức hoa hồng theo % hoặc tiền cố định, chia hoa hồng nhiều KTV làm chung 1 bill.',
      imports: [
        '@/scripts/restful/resources/commission',
        '@/business/staff',
        '@/business/service-category'
      ],
      exports: [
        'CommissionPolicySetting',
        'StaffCommissionTable',
        'useCommissionStore'
      ]
    },
    be: {
      path: 'Controllers/CommissionController.cs',
      controller: 'CommissionController : BaseApiController',
      desc: 'Engine tính toán hoa hồng: phân bổ tỷ lệ KTV chính, phụ, tư vấn viên; bảo lưu doanh số tính lương.',
      injections: [
        'ICommissionService',
        'IStaffService',
        'ISalaryService',
        'IUnitOfWork'
      ],
      exports: [
        'GetPoliciesAsync() -> ApiResponse<List<CommissionPolicyDto>>',
        'CalculateBillCommissionAsync(int invoiceId) -> ApiResponse<CommissionResultDto>',
        'GetStaffCommissionSummaryAsync(DateRangeDto) -> ApiResponse<SummaryDto>'
      ],
      links: ['Invoice (Hóa đơn phát sinh)', 'TimeSheet/Salary (Đẩy vào bảng lương)']
    }
  },
  {
    id: 'revenue-expenditure',
    title: 'Thu chi & Sổ quỹ tiền mặt (Cashbook)',
    skill: 'skill-revenue-expenditure',
    api: {
      route: '/api/v1/cashbook-transactions',
      endpoints: [
        { method: 'GET', path: '/api/v1/cashbook-transactions', note: 'Tra cứu danh sách phiếu thu/chi' },
        { method: 'POST', path: '/api/v1/cashbook-transactions/receipt', note: 'Tạo phiếu thu tiền mặt / chuyển khoản' },
        { method: 'POST', path: '/api/v1/cashbook-transactions/payment', note: 'Tạo phiếu chi tiền' }
      ]
    },
    fe: {
      path: 'src/scripts/business/cashbook-transaction',
      resource: 'src/scripts/restful/resources/cashbookTransaction.ts',
      desc: 'Sổ thu chi salon, quản lý dòng tiền mặt, chuyển khoản, ví điện tử, đối soát đầu ca & kết ca.',
      imports: [
        '@/scripts/restful/resources/cashbookTransaction',
        '@/business/invoice',
        '@/components/common/PaymentMethodSelector'
      ],
      exports: [
        'CashbookTransactionTable',
        'ReceiptPaymentModal',
        'ShiftEndReport',
        'useCashbookStore'
      ]
    },
    be: {
      path: 'Controllers/CashbookTransactionController.cs',
      controller: 'CashbookTransactionController : BaseApiController',
      desc: 'Quản lý sổ quỹ tiền, hạch toán phiếu thu khi thanh toán đơn hàng, hạch toán phiếu chi mua hàng và chi lương.',
      injections: [
        'IPaymentReceiptService',
        'ICashbookBalanceService',
        'IUnitOfWork'
      ],
      exports: [
        'GetTransactionsAsync(CashbookFilterDto) -> ApiResponse<PagedList<CashbookDto>>',
        'CreateReceiptAsync(CreateReceiptDto) -> ApiResponse<int>',
        'CreatePaymentAsync(CreatePaymentDto) -> ApiResponse<int>'
      ],
      links: ['Invoice (Phiếu thu bán hàng)', 'Warehouse (Phiếu chi nhập hàng)', 'Salary (Phiếu chi lương)']
    }
  },
  {
    id: 'service-package-combo',
    title: 'Gói liệu trình & Thẻ combo (Package)',
    skill: 'skill-service-package-combo',
    api: {
      route: '/api/v1/packages',
      endpoints: [
        { method: 'GET', path: '/api/v1/packages', note: 'Lấy danh mục gói liệu trình & combo' },
        { method: 'POST', path: '/api/v1/packages/treatment-history', note: 'Trừ buổi liệu trình khi khách làm dịch vụ' },
        { method: 'GET', path: '/api/v1/packages/customer/{customerId}', note: 'Gói liệu trình đang sở hữu của khách' }
      ]
    },
    fe: {
      path: 'src/scripts/business/package',
      resource: 'src/scripts/restful/resources/package.ts',
      desc: 'Cấu hình combo nhiều buổi, quản lý thẻ làm đẹp của khách, check-in trừ số buổi còn lại và hạn dùng thẻ.',
      imports: [
        '@/scripts/restful/resources/package',
        '@/business/customer',
        '@/business/treatment'
      ],
      exports: [
        'PackageManagementTable',
        'CustomerTreatmentCard',
        'DeductTreatmentSessionModal',
        'usePackageStore'
      ]
    },
    be: {
      path: 'Controllers/PackageController.cs',
      controller: 'PackageController : BaseApiController',
      desc: 'Kiểm soát hạn mức số buổi liệu trình, ghi nhật ký hình ảnh trước/sau điều trị, bảo lưu thẻ khách.',
      injections: [
        'IPackageService',
        'ITreatmentHistoryService',
        'ICustomerService',
        'IUnitOfWork'
      ],
      exports: [
        'GetPackagesAsync() -> ApiResponse<List<PackageDto>>',
        'DeductTreatmentAsync(DeductSessionDto) -> ApiResponse<bool>',
        'GetCustomerTreatmentsAsync(int customerId) -> ApiResponse<List<CustomerPackageDto>>'
      ],
      links: ['Customer (Thẻ sở hữu)', 'BedRoom (Trừ buổi tại giường)', 'Invoice (Bán gói combo)']
    }
  },
  {
    id: 'tax-einvoice',
    title: 'Hóa đơn điện tử (E-Invoice)',
    skill: 'skill-tax-einvoice',
    api: {
      route: '/api/v1/e-invoices',
      endpoints: [
        { method: 'POST', path: '/api/v1/e-invoices/issue', note: 'Phát hành HĐĐT kết nối Tổng cục Thuế' },
        { method: 'GET', path: '/api/v1/e-invoices/{invoiceId}/status', note: 'Tra cứu trạng thái cấp mã CQT' },
        { method: 'POST', path: '/api/v1/e-invoices/cancel', note: 'Hủy hoặc lập hóa đơn điều chỉnh' }
      ]
    },
    fe: {
      path: 'src/scripts/business/electronic-invoice',
      resource: 'src/scripts/restful/resources/electronicInvoice.ts',
      desc: 'Quản lý phát hành hóa đơn điện tử máy tính tiền (VNPT / Viettel / MISA), ký số và gửi email hóa đơn khách.',
      imports: [
        '@/scripts/restful/resources/electronicInvoice',
        '@/business/invoice'
      ],
      exports: [
        'ElectronicInvoiceTable',
        'IssueInvoiceModal',
        'InvoiceStatusBadge',
        'useEInvoiceStore'
      ]
    },
    be: {
      path: 'Controllers/ElectronicInvoiceController.cs',
      controller: 'ElectronicInvoiceController : BaseApiController',
      desc: 'Tích hợp API đối tác Thuế, xử lý XML/JSON ký số điện tử, đồng bộ mã xác thực của Cơ quan Thuế.',
      injections: [
        'IElectronicInvoiceProviderService',
        'IInvoiceService',
        'IUnitOfWork'
      ],
      exports: [
        'IssueInvoiceAsync(IssueEInvoiceDto) -> ApiResponse<EInvoiceResultDto>',
        'CheckCqtStatusAsync(int id) -> ApiResponse<EInvoiceStatusDto>',
        'CancelEInvoiceAsync(CancelEInvoiceDto) -> ApiResponse<bool>'
      ],
      links: ['Invoice (Dữ liệu đơn hàng gốc POS)']
    }
  },
  {
    id: 'payroll-timesheet',
    title: 'Chấm công & Bảng lương (Payroll)',
    skill: 'skill-payroll-timesheet',
    api: {
      route: '/api/v1/time-sheets',
      endpoints: [
        { method: 'GET', path: '/api/v1/time-sheets', note: 'Dữ liệu chấm công ca kíp nhân viên' },
        { method: 'POST', path: '/api/v1/time-sheets/checkin', note: 'Check-in vân tay / wifi chi nhánh' },
        { method: 'POST', path: '/api/v1/salaries/calculate', note: 'Chốt bảng lương & hoa hồng tháng' }
      ]
    },
    fe: {
      path: 'src/scripts/business/time-sheet',
      resource: 'src/scripts/restful/resources/timeSheet.ts',
      desc: 'Bảng theo dõi công chuẩn, đi muộn về sớm, phê duyệt nghỉ phép và tổng hợp phiếu lương từng KTV.',
      imports: [
        '@/scripts/restful/resources/timeSheet',
        '@/business/staff',
        '@/business/commission'
      ],
      exports: [
        'TimeSheetCalendar',
        'SalarySummaryTable',
        'StaffPayslipModal',
        'useTimeSheetStore'
      ]
    },
    be: {
      path: 'Controllers/TimeSheetController.cs',
      controller: 'TimeSheetController : BaseApiController',
      desc: 'Tổng hợp công từ máy chấm công, tính lương cứng + phụ cấp + hoa hồng dịch vụ - các khoản phạt.',
      injections: [
        'ITimeSheetService',
        'ISalaryCalculationService',
        'ICommissionService',
        'IUnitOfWork'
      ],
      exports: [
        'GetTimeSheetsAsync(TimeSheetFilterDto) -> ApiResponse<List<TimeSheetDto>>',
        'CalculateMonthlySalaryAsync(int month, int year) -> ApiResponse<SalaryReportDto>'
      ],
      links: ['Commission (Hoa hồng tháng)', 'Cashbook (Sinh phiếu chi lương)']
    }
  },
  {
    id: 'report-analytics',
    title: 'Báo cáo & Thống kê (Analytics)',
    skill: 'skill-report-analytics',
    api: {
      route: '/api/v1/reports',
      endpoints: [
        { method: 'GET', path: '/api/v1/reports/revenue-overview', note: 'Tổng quan doanh thu, lợi nhuận gộp' },
        { method: 'GET', path: '/api/v1/reports/staff-performance', note: 'Hiệu suất làm việc & phục vụ của KTV' },
        { method: 'GET', path: '/api/v1/reports/inventory-depletion', note: 'Báo cáo tiêu hao nguyên vật liệu' }
      ]
    },
    fe: {
      path: 'src/scripts/business/report',
      resource: 'src/scripts/restful/resources/report.ts',
      desc: 'Biểu đồ trực quan doanh thu theo giờ, tỷ lệ lấp đầy ghế/giường salon, top dịch vụ bán chạy nhất.',
      imports: [
        '@/scripts/restful/resources/report',
        '@/business/invoice',
        '@/business/warehouse-transaction',
        '@/components/common/Charts'
      ],
      exports: [
        'RevenueOverviewChart',
        'StaffPerformanceRanking',
        'InventoryDepletionReport',
        'useReportStore'
      ]
    },
    be: {
      path: 'Controllers/ReportController.cs',
      controller: 'ReportController : BaseApiController',
      desc: 'Tối ưu hóa các query tổng hợp lớn (Aggregation queries), cache kết quả phân tích theo chi nhánh.',
      injections: [
        'IReportService',
        'IAnalyticsEngine',
        'ISalonBranchContext'
      ],
      exports: [
        'GetRevenueOverviewAsync(ReportDateRangeDto) -> ApiResponse<RevenueOverviewDto>',
        'GetStaffPerformanceAsync(ReportDateRangeDto) -> ApiResponse<List<StaffPerformanceDto>>'
      ],
      links: ['Invoice', 'Cashbook', 'WarehouseTransaction', 'BedRoomPosition']
    }
  }
];

function scrollToBottom(role) {
  const container = document.getElementById(role === 'fe' ? 'feTerminalStream' : 'beTerminalStream');
  const btn = document.getElementById(role === 'fe' ? 'feScrollBottomBtn' : 'beScrollBottomBtn');
  if (container) {
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  }
  if (btn) btn.classList.add('hidden');
}

function setupScrollListeners() {
  ['fe', 'be'].forEach(role => {
    const container = document.getElementById(role === 'fe' ? 'feTerminalStream' : 'beTerminalStream');
    const btn = document.getElementById(role === 'fe' ? 'feScrollBottomBtn' : 'beScrollBottomBtn');
    if (!container) return;

    container.addEventListener('scroll', () => {
      const isAtBottom = (container.scrollHeight - container.scrollTop - container.clientHeight) <= 80;
      if (btn) {
        if (isAtBottom) {
          btn.classList.add('hidden');
        } else {
          btn.classList.remove('hidden');
        }
      }
    });
  });
}

async function fetchTerminals() {
  try {
    const res = await fetch('/api/terminals');
    const data = await res.json();
    renderTerminalFeed('fe', data.fe);
    renderTerminalFeed('be', data.be);
  } catch (err) { }
}

/* ========================================================
   VS CODE DARK+ THEME SYNTAX HIGHLIGHTER & MARKDOWN EXTENSIONS
   ======================================================== */

const LANG_MAP = {
  json: { label: 'JSON', file: 'payload.json', icon: '{}', color: '#cbcb41' },
  javascript: { label: 'JavaScript', file: 'script.js', icon: 'JS', color: '#f7df1e' },
  js: { label: 'JavaScript', file: 'script.js', icon: 'JS', color: '#f7df1e' },
  typescript: { label: 'TypeScript', file: 'snippet.ts', icon: 'TS', color: '#3178c6' },
  ts: { label: 'TypeScript', file: 'snippet.ts', icon: 'TS', color: '#3178c6' },
  tsx: { label: 'React TSX', file: 'Component.tsx', icon: 'TSX', color: '#3178c6' },
  jsx: { label: 'React JSX', file: 'Component.jsx', icon: 'JSX', color: '#61dafb' },
  csharp: { label: 'C# .NET', file: 'snippet.cs', icon: 'C#', color: '#239120' },
  cs: { label: 'C# .NET', file: 'snippet.cs', icon: 'C#', color: '#239120' },
  dotnet: { label: 'C# .NET', file: 'Program.cs', icon: 'C#', color: '#512bd4' },
  sql: { label: 'SQL', file: 'query.sql', icon: 'SQL', color: '#e38c00' },
  mysql: { label: 'MySQL', file: 'query.sql', icon: 'SQL', color: '#00758f' },
  bash: { label: 'Bash', file: 'terminal.sh', icon: '$', color: '#4eaa25' },
  sh: { label: 'Shell', file: 'script.sh', icon: '$', color: '#4eaa25' },
  shell: { label: 'Shell', file: 'script.sh', icon: '$', color: '#4eaa25' },
  zsh: { label: 'Zsh', file: 'script.zsh', icon: '$', color: '#4eaa25' },
  python: { label: 'Python', file: 'main.py', icon: 'PY', color: '#3572a5' },
  py: { label: 'Python', file: 'main.py', icon: 'PY', color: '#3572a5' },
  html: { label: 'HTML', file: 'index.html', icon: '<>', color: '#e34c26' },
  xml: { label: 'XML', file: 'config.xml', icon: '<>', color: '#e34c26' },
  css: { label: 'CSS', file: 'styles.css', icon: '#', color: '#563d7c' },
  scss: { label: 'SCSS', file: 'styles.scss', icon: '#', color: '#c6538c' },
  diff: { label: 'Git Diff', file: 'changes.diff', icon: '±', color: '#40c463' },
  patch: { label: 'Patch', file: 'patch.diff', icon: '±', color: '#40c463' },
  yaml: { label: 'YAML', file: 'config.yaml', icon: 'YML', color: '#cb171e' },
  yml: { label: 'YAML', file: 'config.yml', icon: 'YML', color: '#cb171e' }
};

function escapeBasic(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function highlightVsCode(code, lang) {
  if (!code) return '';
  lang = (lang || '').toLowerCase().trim();
  const trimmed = code.trim();

  // Tự động nhận diện JSON hoặc Javascript Object notation
  if (!lang || lang === 'json' || lang === 'js' || lang === 'ts') {
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      lang = 'json';
    }
  }

  if (lang === 'json') {
    const jsonRegex = /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?|(\.\.\.)|([{}[\],:])/g;
    return code.replace(jsonRegex, (match, strVal, colon, boolVal, ellipsis, bracket) => {
      if (strVal) {
        if (colon) {
          return `<span class="vsc-key">${escapeBasic(strVal)}</span><span class="vsc-punct">:</span>`;
        } else {
          return `<span class="vsc-string">${escapeBasic(strVal)}</span>`;
        }
      } else if (boolVal) {
        return `<span class="vsc-keyword">${boolVal}</span>`;
      } else if (ellipsis) {
        return `<span class="vsc-comment">${ellipsis}</span>`;
      } else if (bracket) {
        if (bracket === '{' || bracket === '}') return `<span class="vsc-bracket-1">${bracket}</span>`;
        if (bracket === '[' || bracket === ']') return `<span class="vsc-bracket-2">${bracket}</span>`;
        return `<span class="vsc-punct">${bracket}</span>`;
      } else {
        return `<span class="vsc-number">${match}</span>`;
      }
    });
  }

  const tokenRegex = /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(\/\/.*$|\/\*[\s\S]*?\*\/|#.*$)|(\b(?:const|let|var|function|return|if|else|for|while|switch|case|break|continue|try|catch|finally|throw|class|interface|type|extends|implements|import|export|from|default|async|await|new|this|super|public|private|protected|static|readonly|get|set|void|string|number|boolean|any|true|false|null|undefined|namespace|using|in|is|of|typeof|instanceof|select|from|where|insert|into|update|delete|join|inner|left|right|on|group|by|order|asc|desc|limit)\b)|(\b-?\d+(?:\.\d+)?\b)|(\b[a-zA-Z_$][a-zA-Z0-9_$]*(?=\s*\())|([{}()[\];,])/gm;

  let lastIdx = 0;
  let out = '';
  let match;
  while ((match = tokenRegex.exec(code)) !== null) {
    if (match.index > lastIdx) {
      out += escapeBasic(code.substring(lastIdx, match.index));
    }
    const [full, str, comment, keyword, num, fn, punct] = match;
    if (str) {
      out += `<span class="vsc-string">${escapeBasic(str)}</span>`;
    } else if (comment) {
      out += `<span class="vsc-comment">${escapeBasic(comment)}</span>`;
    } else if (keyword) {
      if (/^(if|else|for|while|switch|case|return|break|continue|try|catch|finally|throw|import|export|from)$/.test(keyword)) {
        out += `<span class="vsc-control">${escapeBasic(keyword)}</span>`;
      } else {
        out += `<span class="vsc-keyword">${escapeBasic(keyword)}</span>`;
      }
    } else if (num) {
      out += `<span class="vsc-number">${escapeBasic(num)}</span>`;
    } else if (fn) {
      out += `<span class="vsc-func">${escapeBasic(fn)}</span>`;
    } else if (punct) {
      if (punct === '{' || punct === '}') out += `<span class="vsc-bracket-1">${punct}</span>`;
      else if (punct === '[' || punct === ']') out += `<span class="vsc-bracket-2">${punct}</span>`;
      else if (punct === '(' || punct === ')') out += `<span class="vsc-bracket-3">${punct}</span>`;
      else out += `<span class="vsc-punct">${punct}</span>`;
    } else {
      out += escapeBasic(full);
    }
    lastIdx = tokenRegex.lastIndex;
  }
  if (lastIdx < code.length) {
    out += escapeBasic(code.substring(lastIdx));
  }
  return out;
}

let _currentMarkdownContextFiles = [];
let _currentMarkdownRawText = '';

function resolveVsCodeFilename(code, normLang, customFilename) {
  if (customFilename) return customFilename;

  // 1. Kiểm tra danh sách file thay đổi từ context của lượt/session hiện tại
  let contextFiles = _currentMarkdownContextFiles || [];
  if (!contextFiles || contextFiles.length === 0) {
    if (typeof parallelTasks !== 'undefined' && Array.isArray(parallelTasks)) {
      const curTask = parallelTasks.find(t => t.id === activeTaskId);
      if (curTask && curTask.changed_files && curTask.changed_files.length > 0) {
        contextFiles = curTask.changed_files;
      }
    }
  }

  if (Array.isArray(contextFiles) && contextFiles.length > 0) {
    const fileObjs = contextFiles.map(f => {
      const p = (typeof f === 'string' ? f : (f.path || f.name || f.file || '')).trim();
      const base = p.split('/').pop() || p;
      const ext = base.includes('.') ? base.split('.').pop().toLowerCase() : '';
      return { path: p, base, ext };
    }).filter(o => o.base);

    // Ưu tiên 1: Tên file xuất hiện trực tiếp trong nội dung đoạn code
    for (const f of fileObjs) {
      const stem = f.base.replace(/\.[^.]+$/, '');
      if (stem.length > 2 && code.includes(stem)) {
        return f.base;
      }
    }

    // Ưu tiên 2: File có đuôi mở rộng phù hợp với ngôn ngữ của code block
    const langExtMap = {
      typescript: ['ts', 'tsx'],
      ts: ['ts', 'tsx'],
      tsx: ['tsx'],
      javascript: ['js', 'jsx', 'mjs', 'cjs'],
      js: ['js', 'jsx'],
      jsx: ['jsx'],
      csharp: ['cs'],
      cs: ['cs'],
      dotnet: ['cs'],
      python: ['py'],
      py: ['py'],
      json: ['json'],
      html: ['html', 'htm'],
      css: ['css'],
      scss: ['scss'],
      sql: ['sql'],
      mysql: ['sql'],
      bash: ['sh', 'bash'],
      sh: ['sh'],
      shell: ['sh'],
      yaml: ['yaml', 'yml'],
      yml: ['yaml', 'yml']
    };
    const validExts = langExtMap[normLang] || [normLang];
    const matchExt = fileObjs.find(f => validExts.includes(f.ext));
    if (matchExt) {
      return matchExt.base;
    }

    // Ưu tiên 3: Nếu chỉ có 1 file thay đổi thì hiển thị chính file đó
    if (fileObjs.length === 1) {
      return fileObjs[0].base;
    }
  }

  // 2. Tìm tên file được đề cập trong toàn bộ ngữ cảnh văn bản Markdown (ví dụ: BookingDetailServiceItem.tsx)
  if (_currentMarkdownRawText) {
    const matches = _currentMarkdownRawText.match(/[\w\-./\\]+\.(?:tsx|ts|jsx|js|cs|json|sql|py|html|css|scss|sh|ya?ml)\b/gi);
    if (matches && matches.length > 0) {
      for (const m of matches) {
        const base = m.split('/').pop();
        if (base && !base.startsWith('http')) {
          const ext = base.split('.').pop().toLowerCase();
          const langExtMap = {
            typescript: ['ts', 'tsx'],
            ts: ['ts', 'tsx'],
            tsx: ['tsx'],
            javascript: ['js', 'jsx'],
            js: ['js'],
            csharp: ['cs'],
            cs: ['cs'],
            dotnet: ['cs']
          };
          const validExts = langExtMap[normLang] || [normLang];
          if (validExts.includes(ext) || code.includes(base.replace(/\.[^.]+$/, ''))) {
            return base;
          }
        }
      }
    }
  }

  // 3. Fallback theo tên ngôn ngữ (dạng snippet.<ext>, không cố định 'service.ts')
  const defaultExt = (normLang === 'typescript' ? 'ts' : (normLang === 'csharp' ? 'cs' : (normLang || 'txt')));
  return `snippet.${defaultExt}`;
}

function renderVsCodeBlock(code, lang) {
  const cleanCode = (code || '').trimEnd();
  const lines = cleanCode.split('\n');
  let normLang = (lang || '').toLowerCase().trim();
  let customFilename = '';

  if (normLang && (normLang.includes(':') || normLang.includes(' '))) {
    const parts = normLang.split(/[:\s]+/);
    normLang = (parts[0] || '').toLowerCase().trim();
    customFilename = parts[1] || '';
  }

  // Tự động nhận diện JSON nếu không chỉ định ngôn ngữ
  if (!normLang) {
    const trimmed = cleanCode.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      normLang = 'json';
    }
  }

  const activeFilename = customFilename || resolveVsCodeFilename(cleanCode, normLang, customFilename);
  const fileExt = activeFilename.includes('.') ? activeFilename.split('.').pop().toLowerCase() : normLang;
  const meta = Object.assign({}, LANG_MAP[fileExt] || LANG_MAP[normLang] || {
    label: (fileExt || normLang || 'CODE').toUpperCase(),
    file: activeFilename,
    icon: '</>',
    color: '#007acc'
  });
  meta.file = activeFilename;

  const highlightedHtml = highlightVsCode(cleanCode, normLang);

  return `
<div class="vscode-editor-card my-3 rounded-lg overflow-hidden border border-[#2d2d2d] bg-[#1e1e1e] shadow-xl font-mono text-[12px] text-[#d4d4d4]" data-code="${encodeURIComponent(cleanCode)}">
  <div class="vscode-editor-header flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#2d2d2d] select-none text-[11px]">
    <div class="flex items-center gap-2">
      <div class="vscode-mac-dots flex items-center gap-1.5 mr-2">
        <span class="vscode-dot vscode-dot-red"></span>
        <span class="vscode-dot vscode-dot-yellow"></span>
        <span class="vscode-dot vscode-dot-green"></span>
      </div>
      <div class="vscode-tab flex items-center gap-1.5 px-2.5 py-0.5 rounded-t bg-[#1e1e1e] border-t-2 border-t-[#007acc] text-[#cccccc] font-mono text-[11px] shadow-sm">
        <span style="color: ${meta.color}; font-weight: bold; font-size: 11px;">${meta.icon}</span>
        <span class="text-[#cccccc] font-medium truncate max-w-[220px]">${meta.file}</span>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-[10px] uppercase font-semibold text-slate-400 font-mono tracking-wider">${meta.label}</span>
      <button type="button" onclick="copyVsCodeSnippet(this)"
        class="vscode-copy-btn flex items-center gap-1 px-2.5 py-0.5 rounded bg-[#2d2d2d] hover:bg-[#3e3e42] text-slate-300 hover:text-white transition text-[11px] cursor-pointer border border-[#3c3c3c] shadow-sm select-none"
        title="Sao chép toàn bộ code">
        <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
        <span>Copy</span>
      </button>
    </div>
  </div>
  <div class="vscode-editor-body p-3 overflow-x-auto text-[12px] leading-[1.65] bg-[#1e1e1e] text-[#d4d4d4]">
    <div class="vscode-code-wrap flex font-mono text-[12px] leading-[1.65]">
      <div class="vscode-line-numbers select-none text-right pr-3.5 pl-1 text-[#858585] border-r border-[#333333] shrink-0 font-mono text-[12px] leading-[1.65]">
        ${lines.map((_, idx) => `<div>${idx + 1}</div>`).join('')}
      </div>
      <div class="vscode-code-content pl-3.5 flex-1 overflow-x-auto font-mono text-[12px] leading-[1.65] whitespace-pre">
        <pre class="m-0 p-0 bg-transparent border-0 font-mono text-[12px] leading-[1.65] whitespace-pre"><code class="p-0 bg-transparent border-0 font-mono text-[12px] leading-[1.65] whitespace-pre text-[#d4d4d4]">${highlightedHtml}</code></pre>
      </div>
    </div>
  </div>
</div>
  `.trim();
}

function copyVsCodeSnippet(btn) {
  if (!btn) return;
  const card = btn.closest('.vscode-editor-card');
  if (!card) return;
  const rawCode = decodeURIComponent(card.getAttribute('data-code') || '');
  if (!rawCode) return;

  const originalHtml = btn.innerHTML;
  const doFeedback = () => {
    btn.innerHTML = `
      <svg class="w-3.5 h-3.5 fill-none stroke-emerald-400" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
      </svg>
      <span class="text-emerald-400 font-semibold">Đã chép!</span>
    `;
    setTimeout(() => {
      btn.innerHTML = originalHtml;
    }, 2000);
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(rawCode).then(doFeedback).catch(() => {
      fallbackCopySnippet(rawCode);
      doFeedback();
    });
  } else {
    fallbackCopySnippet(rawCode);
    doFeedback();
  }
}

function fallbackCopySnippet(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  textarea.style.top = '0';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    document.execCommand('copy');
  } catch (err) {}
  document.body.removeChild(textarea);
}

function isJsonLike(str) {
  const t = (str || '').trim();
  if (!((t.startsWith('{') && t.endsWith('}')) || (t.startsWith('[') && t.endsWith(']')))) {
    return false;
  }
  try {
    JSON.parse(t);
    return true;
  } catch (e) {}
  const hasKeys = /"[^"]+"\s*:|([a-zA-Z_$][a-zA-Z0-9_$]*\s*:)/.test(t);
  const hasPunct = /[,{}[\]]/.test(t);
  return hasKeys && hasPunct;
}

function wrapRawJsonBlocks(text) {
  if (!text) return '';
  const codeBlockRegex = /```[\s\S]*?```/g;
  const blocks = [];
  let masked = text.replace(codeBlockRegex, (m) => {
    blocks.push(m);
    return `__CODE_BLOCK_${blocks.length - 1}__`;
  });

  masked = masked.replace(/(^|\n)([ \t]*\{[\s\S]*?\n[ \t]*\}|[ \t]*\[[\s\S]*?\n[ \t]*\])(?=\n|$)/g, (match, prefix, candidate) => {
    if (isJsonLike(candidate)) {
      return prefix + '```json\n' + candidate.trim() + '\n```';
    }
    return match;
  });

  return masked.replace(/__CODE_BLOCK_(\d+)__/g, (m, idx) => blocks[Number(idx)]);
}

let _markedVsCodeInitialized = false;
function initMarkedVsCodeRenderer() {
  if (_markedVsCodeInitialized || typeof marked === 'undefined') return;
  try {
    const renderer = new marked.Renderer();
    renderer.code = function(code, lang) {
      if (typeof code === 'object' && code !== null) {
        lang = code.lang;
        code = code.text;
      }
      return renderVsCodeBlock(code, lang);
    };
    if (marked.use) {
      marked.use({ renderer });
    } else if (marked.setOptions) {
      marked.setOptions({ renderer });
    }
    _markedVsCodeInitialized = true;
  } catch (err) {
    console.error('Failed to init marked VS Code renderer', err);
  }
}

window.copyVsCodeSnippet = copyVsCodeSnippet;

function safeMarkdown(text, contextFiles) {
  if (!text) return '';
  _currentMarkdownContextFiles = Array.isArray(contextFiles) ? contextFiles : [];
  _currentMarkdownRawText = typeof text === 'string' ? text : '';
  initMarkedVsCodeRenderer();
  try {
    const preprocessed = wrapRawJsonBlocks(text);
    if (typeof marked !== 'undefined' && marked.parse) {
      return marked.parse(preprocessed);
    }
  } catch (e) { }
  return escapeHtml(text).split('\n').join('<br/>');
}

function renderTerminalFeed(role, feed) {
  const isFe = role === 'fe';
  const container = document.getElementById(isFe ? 'feTerminalStream' : 'beTerminalStream');
  const conclusionCard = document.getElementById(isFe ? 'feCompletedCard' : 'beCompletedCard');
  const conclusionText = document.getElementById(isFe ? 'feCompletedText' : 'beCompletedText');
  const conclusionTime = document.getElementById(isFe ? 'feCompletedTime' : 'beCompletedTime');

  if (!container) return;

  // Hiển thị phần Kết quả rút ra đã làm hoàn thành
  if (feed && feed.completed_result && feed.completed_result.content) {
    if (conclusionCard && conclusionText) {
      conclusionCard.classList.remove('hidden');
      if (conclusionTime) {
        const rawTime = feed.completed_result.timestamp || '';
        conclusionTime.textContent = rawTime.length > 8 ? rawTime.slice(11, 19) : rawTime;
      }
      conclusionText.innerHTML = safeMarkdown(feed.completed_result.content, (feed && feed.changed_files) || []);
    }
  }

  if (!feed || !feed.cid) {
    if (container.dataset.hasSession !== 'false') {
      container.innerHTML = '<div class="text-slate-500 text-center py-12">Chưa phát hiện phiên làm việc nào của Terminal này.</div>';
      container.dataset.hasSession = 'false';
    }
    return;
  }
  container.dataset.hasSession = 'true';

  const messages = feed.messages || [];
  if (messages.length === 0) {
    if (container.dataset.hasMessages !== 'false') {
      container.innerHTML = '<div class="text-slate-500 text-center py-12">Terminal đang mở, chưa có dữ liệu mới.</div>';
      container.dataset.hasMessages = 'false';
    }
    return;
  }
  container.dataset.hasMessages = 'true';

  // Kiểm tra dữ liệu có thay đổi không
  const lastSignature = container.dataset.lastSignature || '';
  const currentSignature = (feed.cid || '') + '_' + messages.length + '_' + (messages[messages.length - 1]?.timestamp || '');
  if (lastSignature === currentSignature) {
    return;
  }

  const isAtBottom = (container.scrollHeight - container.scrollTop - container.clientHeight) <= 80;

  container.innerHTML = messages.map(m => {
    if (m.role === 'user') {
      return `
            <div class="bg-[#0b0f19] border border-[#1e293b] rounded-md p-3 font-mono">
              <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span class="text-amber-400 font-semibold font-mono">Input:</span>
                <span class="text-slate-500">${m.timestamp ? m.timestamp.slice(11, 19) : ''}</span>
              </div>
              <div class="text-slate-200 text-xs font-mono leading-relaxed whitespace-pre-wrap pl-2.5 border-l-2 border-amber-500/60">${escapeHtml(m.content)}</div>
            </div>
          `;
    } else {
      const toolsHtml = m.tools && m.tools.length > 0 ? `
            <div class="flex flex-wrap gap-1.5 mb-2">
              ${m.tools.map(t => `<span class="px-2 py-0.5 rounded bg-slate-800 text-[11px] text-slate-300 border border-slate-700/60 font-mono font-medium">${escapeHtml(t)}</span>`).join('')}
            </div>
          ` : '';

      return `
            <div class="rounded-md border border-[#1e293b] p-3.5 bg-[#050811]">
              <div class="flex items-center justify-between text-[11px] text-slate-400 mb-2">
                <span class="${isFe ? 'text-cyan-400' : 'text-emerald-400'} font-semibold font-mono">
                  Output (${isFe ? 'webapp' : 'api'}):
                </span>
                <span class="text-slate-500 font-mono">${m.timestamp ? m.timestamp.slice(11, 19) : ''}</span>
              </div>
              ${toolsHtml}
              <div class="markdown-body text-[13px] text-slate-200 leading-[1.8] tracking-wide overflow-x-auto">
                ${safeMarkdown(m.content || '', (feed && feed.changed_files) || [])}
              </div>
            </div>
          `;
    }
  }).join('');

  container.dataset.lastSignature = currentSignature;

  if (isAtBottom) {
    container.scrollTop = container.scrollHeight;
  }
}

const FRIENDLY_SKILL_DESCRIPTIONS = {
  // Backend (19 skills)
  'skill-auth': 'Phân quyền 8 Host, JWT & lọc CurrentSalonId',
  'skill-base': 'Cây kế thừa Base (Controller, Service, UnitOfWork)',
  'skill-bridge-frontend': 'Cầu nối liên agent Backend <-> Frontend qua bridge.py',
  'skill-business-flow': 'Luồng nghiệp vụ cốt lõi: PayInvoice, CheckIn, Hủy/Xóa đơn',
  'skill-catalog': 'Tra cứu CATALOG.md, chống tạo symbol ảo',
  'skill-commission': 'Tính hoa hồng nhân viên (Thế hệ Cũ vs Mới)',
  'skill-controller': 'Chuẩn Controller, OkList, ActionBaseValue, DTO vs Entity',
  'skill-debug': 'Quy trình 5 bước điều tra lỗi EF ChangeTracker & HTTP',
  'skill-entity': 'EF Core Model, Mapping snake/Pascal, Migration MySQL',
  'skill-export-excel': 'Xuất file Excel ClosedXML & OpenXML streaming',
  'skill-import-excel': 'Import Excel: Preview & Submit',
  'skill-integration': 'Tích hợp HDĐT (MISA, Viettel, VNPT), SMS Vihat, QR MB',
  'skill-kafka': 'Kafka Producer, Consumer topic, Background worker QUEUE',
  'skill-mimic': 'Mô phỏng file lân cận, nghiêm cấm viết comment',
  'skill-report': 'Báo cáo Dapper raw SQL nhiều bảng, ValidDateRange',
  'skill-schedule': 'Quartz Job định kỳ (IJob) trong SALON_HAIR_SCHEDULE',
  'skill-service': 'Chuẩn tầng Service, DomainService (Manager), UnitOfWork',
  'skill-shared': 'Tiện ích chung: sinh mã tự tăng, SettingAdvance',
  'skill-warehouse': 'Quản lý kho hàng NK/XK/CK, tồn kho, giá vốn',

  // Frontend (26 skills)
  'skill-api': 'Cấu hình RESTful API Client & RequestParameter',
  'skill-booking-bedroom': 'Phòng & Vị trí giường / Đổi giường',
  'skill-calendar-schedule': 'Lịch hẹn & Ca làm việc',
  'skill-call-backend': 'Cầu nối gọi Backend API & tra cứu DTO',
  'skill-commission-setup': 'Hoa hồng & Chiết khấu KTV',
  'skill-crud': 'Quy chuẩn hoàn thiện luồng CRUD',
  'skill-customer-crm': 'Khách hàng & Hạng thẻ VIP / Tích điểm',
  'skill-debug-fixbug': 'Quy trình 5 bước điều tra & vá lỗi Frontend',
  'skill-excel-import': 'Đọc và xuất file Excel dữ liệu lớn',
  'skill-form': 'Quy chuẩn Formik & Yup validation schema',
  'skill-layer-flow': 'Event Bus, Redux, Context, subGlobalModal tầng 1 & 2',
  'skill-lint-verify': 'Kiểm tra TypeScript & ESLint',
  'skill-online-booking-portal': 'Cổng đặt hẹn trực tuyến Online',
  'skill-payroll-timesheet': 'Chấm công & Bảng lương',
  'skill-pos-cashier': 'Thu ngân & Bán hàng / Hóa đơn',
  'skill-print-template': 'Mẫu in bill, hóa đơn, barcode',
  'skill-realtime-hardware': 'Máy in bill, két tiền, máy quét mã',
  'skill-refactor-mimic': 'Mô phỏng component lân cận & cấm comment',
  'skill-report-analytics': 'Báo cáo & Thống kê kinh doanh',
  'skill-revenue-expenditure': 'Thu chi & Sổ quỹ tiền mặt',
  'skill-routing-permission': 'Định tuyến RoutePage & phân quyền chi nhánh',
  'skill-service-package-combo': 'Gói liệu trình & Thẻ combo',
  'skill-table': 'Bảng dữ liệu Antd Table, phân trang, sort, filter',
  'skill-tax-einvoice': 'Thuế & Hóa đơn điện tử',
  'skill-warehouse-inventory': 'Kho hàng & Nhập xuất tồn'
};

const SKILLS_DICTIONARY = {
  // Backend skills (19)
  'skill-auth': 'Phân quyền 8 Host (API, STAFF, PORTAL...), Claims JWT, xác thực và cô lập dữ liệu theo CurrentSalonId.',
  'skill-base': 'Cây kế thừa Base chuẩn: SharedApiControllerBase, SalonControllerBase, ApplicationService, DomainService, UnitOfWork.',
  'skill-bridge-frontend': 'Cầu nối liên agent Backend <-> Frontend qua công cụ bridge.py để đối chiếu model, DTO và Formik.',
  'skill-business-flow': 'Luồng nghiệp vụ chuyển đổi trạng thái cốt lõi: PayInvoice, EditAsPay, CheckIn, hủy/xóa hóa đơn, dùng gói.',
  'skill-catalog': 'Tra cứu ai-boundary/CATALOG.md trước khi viết code, nghiêm cấm tự bịa class, hàm hay hằng status ngoài catalog.',
  'skill-commission': 'Tính toán hoa hồng nhân viên: Rẽ nhánh hệ thống cũ vs mới (CheckUseNewCommission), hook khi Pay/Debt.',
  'skill-controller': 'Chuẩn Web API Controller: Action result Ok, OkList, BadRequest, NotFound, ActionBaseValue, tách DTO vs Entity.',
  'skill-debug': 'Quy trình 5 bước điều tra bug, bẫy lỗi EF Core ChangeTracker, AsNoTracking, transaction commit, lệch múi giờ.',
  'skill-entity': 'Cấu hình EF Core Model, Fluent API mapping snake/Pascal case, Query Filter, Migration MySQL.',
  'skill-export-excel': 'Xuất file Excel ClosedXML và OpenXML streaming, trả trực tiếp FileStreamResult không bọc Ok().',
  'skill-import-excel': 'Import Excel qua ImportHttpHelper: 2 giai đoạn preview (kiểm tra dòng lỗi) và submit (lưu dữ liệu).',
  'skill-integration': 'Tích hợp dịch vụ bên thứ 3: Hóa đơn điện tử (MISA, Viettel, VNPT), SMS Vihat, QR MB Bank, loa TingTing.',
  'skill-kafka': 'Event streaming Kafka Producer (KafkaProducerService), Consumer topic, Background worker trong SALON_HAIR_QUEUE.',
  'skill-mimic': 'Nguyên tắc viết code mô phỏng file lân cận trong cùng thư mục, nghiêm cấm viết comment thừa (//, /* */).',
  'skill-report': 'Báo cáo tổng hợp Dapper raw SQL nhiều bảng hiệu năng cao, validate khoảng ngày GetValidDateRangeQuery.',
  'skill-schedule': 'Quartz Job định kỳ (IJob) trong SALON_HAIR_SCHEDULE, BackgroundWorker và các task chờ.',
  'skill-service': 'Chuẩn tầng ApplicationService (tự saveChange) và DomainService/Manager (dùng lại query, validation).',
  'skill-shared': 'Tiện ích chung: sinh mã tự tăng SysObjectAutoIncrement, SettingAdvance, DefinedException, ngày tháng.',
  'skill-warehouse': 'Quản lý kho hàng: Nhập/xuất/chuyển kho (mã NK, XK, CK), tính giá vốn bình quân và tồn kho.',

  // Frontend skills (26)
  'skill-api': 'Cấu hình RESTful API Client, xử lý mảng RequestParameter, headers và lỗi mạng.',
  'skill-booking-bedroom': 'Bản đồ phòng & giường realtime, cập nhật trạng thái bận/trống, đổi giường, gán KTV làm dịch vụ.',
  'skill-calendar-schedule': 'Đặt lịch hẹn khách hàng, điều phối KTV, xếp ca làm việc và liên kết gán phòng/giường.',
  'skill-call-backend': 'Cầu nối gọi trực tiếp Backend API, tra cứu DTO và đối chiếu payload hợp đồng.',
  'skill-commission-setup': 'Cấu hình hoa hồng KTV theo bậc, dịch vụ, bán sản phẩm, làm tour; tính thưởng tức thì theo bill.',
  'skill-crud': 'Quy chuẩn hoàn thiện luồng CRUD gồm Form + Table + Modal + Event Bus reload.',
  'skill-customer-crm': 'Hồ sơ khách hàng, phân hạng thẻ VIP, tích lũy điểm thưởng, quản lý công nợ và lịch sử dịch vụ.',
  'skill-debug-fixbug': 'Quy trình 5 bước: Phân loại tầng lỗi → Truy vết log/payload → Nạp schema/rule → Vá lỗi vi phẫu → Kiểm chứng.',
  'skill-excel-import': 'Đọc và xuất file Excel dữ liệu lớn, kiểm tra validation dòng lỗi trước khi import.',
  'skill-form': 'Quy chuẩn Formik & Yup validation schema, xử lý submit form, tránh lỗi undefined initialValues.',
  'skill-layer-flow': 'Luồng dữ liệu Event Bus, Redux, Context, quản lý modal tầng 1 và popup tầng 2 (subGlobalModal).',
  'skill-lint-verify': 'Kiểm tra cú pháp TypeScript, quy tắc ESLint và build bundle dự án.',
  'skill-online-booking-portal': 'Cổng đặt hẹn trực tuyến cho khách hàng tự book lịch qua Web / App.',
  'skill-payroll-timesheet': 'Tổng hợp ngày công, ca kíp, phạt đi muộn và tiền hoa hồng trong tháng để chốt bảng lương.',
  'skill-pos-cashier': 'Order dịch vụ, combo, áp mã giảm giá, thanh toán đa phương thức và in phiếu thu hóa đơn.',
  'skill-print-template': 'Thiết kế mẫu in bill nhiệt (K80, K57), phiếu thanh toán và tem nhãn barcode.',
  'skill-realtime-hardware': 'Kết nối phần cứng bán hàng: Máy in bill LAN/USB, két đựng tiền, máy quét mã vạch.',
  'skill-refactor-mimic': 'Mô phỏng component lân cận, tuân thủ kiến trúc hiện hành và không viết comment thừa.',
  'skill-report-analytics': 'Dashboard doanh thu bán lẻ, tỷ lệ lấp đầy giường, hiệu suất KTV và báo cáo lãi lỗ.',
  'skill-revenue-expenditure': 'Tổng hợp phiếu thu bán lẻ, phiếu chi mua kho, chi lương; theo dõi sổ quỹ tiền mặt & ngân hàng.',
  'skill-routing-permission': 'Định tuyến RoutePage, phân quyền chi nhánh (withContext) và bảo vệ route.',
  'skill-service-package-combo': 'Bán thẻ liệu trình nhiều buổi, trừ buổi tự động khi khách làm tại giường, gia hạn thẻ.',
  'skill-table': 'Bảng dữ liệu Antd Table, phân trang, sort, filter, tối ưu render danh sách lớn.',
  'skill-tax-einvoice': 'Kết nối VNPT, Viettel, MISA phát hành hóa đơn điện tử hợp lệ theo quy định Tổng cục Thuế.',
  'skill-warehouse-inventory': 'Quản lý kho xuất nhập tồn, trừ kho hàng bán & định mức tiêu hao nguyên vật liệu làm dịch vụ.'
};

let ALL_CUSTOM_SKILLS = { fe: [], be: [] };

function getSkillShortDesc(name, rawDesc) {
  if (FRIENDLY_SKILL_DESCRIPTIONS[name]) {
    return FRIENDLY_SKILL_DESCRIPTIONS[name];
  }
  if (rawDesc) {
    const clean = rawDesc.replace(/^Use this skill when /i, '').replace(/^Use this skill to /i, '');
    return clean.slice(0, 50) + (clean.length > 50 ? '...' : '');
  }
  return 'Skill nội bộ';
}

function getSkillDesc(skillName) {
  if (SKILLS_DICTIONARY[skillName]) return SKILLS_DICTIONARY[skillName];
  const all = [...(ALL_CUSTOM_SKILLS.fe || []), ...(ALL_CUSTOM_SKILLS.be || [])];
  const item = all.find(s => s.name === skillName);
  return item?.desc || FRIENDLY_SKILL_DESCRIPTIONS[skillName] || '';
}

async function loadCustomSkills() {
  try {
    const res = await fetch('/api/skills');
    ALL_CUSTOM_SKILLS = await res.json();
  } catch (err) { }
  updateSkillDropdowns();
}

let selectedTaskSkills = (() => {
  try {
    const raw = localStorage.getItem('easysalon_selected_skills');
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length > 0) return arr;
    }
    const draftRaw = localStorage.getItem('easySalon_studio_drafts');
    if (draftRaw) {
      const draft = JSON.parse(draftRaw);
      if (draft && Array.isArray(draft.taskSkills) && draft.taskSkills.length > 0) {
        return draft.taskSkills;
      }
    }
  } catch (e) { }
  return [];
})();
let selectedFixBugSkills = [];

function getAvailableSkills(mode) {
  const scope = mode === 'task'
    ? (document.getElementById('taskTargetSelect')?.value || 'both')
    : (document.getElementById('fixbugScopeSelect')?.value || 'both');

  const feList = ALL_CUSTOM_SKILLS.fe || [];
  const beList = ALL_CUSTOM_SKILLS.be || [];

  if (scope === 'fe') return feList.map(s => ({ ...s, group: 'Frontend' }));
  if (scope === 'be') return beList.map(s => ({ ...s, group: 'Backend' }));
  return [
    ...feList.map(s => ({ ...s, group: 'Frontend' })),
    ...beList.map(s => ({ ...s, group: 'Backend' }))
  ];
}

function toggleSkillDropdown(mode) {
  const dropdown = document.getElementById(mode + 'SkillDropdown');
  const otherMode = mode === 'task' ? 'fixbug' : 'task';
  const otherDropdown = document.getElementById(otherMode + 'SkillDropdown');
  if (otherDropdown) otherDropdown.classList.add('hidden');

  if (!dropdown) return;
  const isHidden = dropdown.classList.contains('hidden');
  if (isHidden) {
    dropdown.classList.remove('hidden');
    renderSkillOptions(mode);
    const searchInput = document.getElementById(mode + 'SkillSearch');
    if (searchInput) {
      searchInput.value = '';
      searchInput.focus();
    }
  } else {
    dropdown.classList.add('hidden');
  }
}

function renderSkillPicker(mode) {
  renderSkillTags(mode);
  renderSkillOptions(mode);
  updateFixBugPromptPreview();
  if (typeof syncFormToCurrentTask === 'function') syncFormToCurrentTask();
  if (mode === 'task') {
    try {
      localStorage.setItem('easysalon_selected_skills', JSON.stringify(selectedTaskSkills));
    } catch (e) { }
    if (typeof saveDraft === 'function') saveDraft(false);
    if (typeof scheduleQueueSync === 'function') scheduleQueueSync();
  }
}

function renderSkillTags(mode) {
  const container = document.getElementById(mode + 'SelectedTags');
  const countEl = document.getElementById(mode + 'SkillCount');
  const selected = mode === 'task' ? selectedTaskSkills : selectedFixBugSkills;

  if (countEl) {
    countEl.textContent = `${selected.length} đã chọn`;
  }

  if (!container) return;

  if (selected.length === 0) {
    container.innerHTML = `<span class="text-slate-400 text-xs px-1 italic">${mode === 'task' ? '-- Tự động quét theo chủ đề --' : '-- Chọn một hoặc nhiều skill kiểm tra --'}</span>`;
    return;
  }

  container.innerHTML = selected.map(s => `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#199cff] border border-[#199cff] text-white font-mono text-[11px] font-medium shadow-sm transition">
          <span>${escapeHtml(s)}</span>
          <button type="button" onclick="removeSkill('${mode}', '${escapeHtml(s)}', event)" class="text-white/80 hover:text-white font-bold text-xs ml-0.5 leading-none transition-colors">×</button>
        </span>
      `).join('');
}

function renderSkillOptions(mode) {
  const listEl = document.getElementById(mode + 'SkillOptionList');
  if (!listEl) return;

  const searchInput = document.getElementById(mode + 'SkillSearch');
  const q = (searchInput?.value || '').toLowerCase().trim();
  const skills = getAvailableSkills(mode);
  const selected = mode === 'task' ? selectedTaskSkills : selectedFixBugSkills;

  const filtered = skills.filter(s => {
    if (!q) return true;
    return s.name.toLowerCase().includes(q) || (s.desc && s.desc.toLowerCase().includes(q));
  });

  if (filtered.length === 0) {
    listEl.innerHTML = `<div class="text-center py-6 text-slate-400 text-xs">Không có skill nào khớp "${escapeHtml(q)}"</div>`;
    return;
  }

  listEl.innerHTML = filtered.map(s => {
    const isChecked = selected.includes(s.name);
    const shortDesc = getSkillShortDesc(s.name, s.desc);
    return `
          <div onclick="toggleSkillSelection('${mode}', '${escapeHtml(s.name)}')"
            class="skill-option-item ${isChecked ? 'is-selected bg-[#199cff] border border-[#199cff] text-white' : 'border border-transparent'} flex items-start gap-2.5 p-2 rounded-lg cursor-pointer transition">
            <input type="checkbox" ${isChecked ? 'checked' : ''} class="mt-0.5 rounded text-white pointer-events-none accent-[#199cff]" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="skill-name font-mono text-xs font-semibold ${isChecked ? 'text-white' : 'text-slate-200'}">${escapeHtml(s.name)}</span>
                <span class="skill-group text-[10px] font-mono px-1.5 py-0.2 rounded ${isChecked ? 'bg-white/20 text-white border border-white/40' : (s.group === 'Frontend' ? 'bg-cyan-950 text-cyan-400 border border-cyan-800' : 'bg-emerald-950 text-emerald-400 border border-emerald-800')}">${s.group}</span>
              </div>
              <div class="skill-desc text-[11px] ${isChecked ? 'text-white/85' : 'text-slate-400'} truncate mt-0.5">${escapeHtml(shortDesc)}</div>
            </div>
          </div>
        `;
  }).join('');
}

function filterSkillOptions(mode) {
  renderSkillOptions(mode);
}

function toggleSkillSelection(mode, skillName) {
  if (mode === 'task') {
    const idx = selectedTaskSkills.indexOf(skillName);
    if (idx >= 0) selectedTaskSkills.splice(idx, 1);
    else selectedTaskSkills.push(skillName);
  } else {
    const idx = selectedFixBugSkills.indexOf(skillName);
    if (idx >= 0) selectedFixBugSkills.splice(idx, 1);
    else selectedFixBugSkills.push(skillName);
  }
  renderSkillPicker(mode);
}

function removeSkill(mode, skillName, event) {
  if (event) event.stopPropagation();
  if (mode === 'task') {
    selectedTaskSkills = selectedTaskSkills.filter(s => s !== skillName);
  } else {
    selectedFixBugSkills = selectedFixBugSkills.filter(s => s !== skillName);
  }
  renderSkillPicker(mode);
}

function selectAllSkills(mode) {
  const skills = getAvailableSkills(mode);
  const names = skills.map(s => s.name);
  if (mode === 'task') {
    selectedTaskSkills = Array.from(new Set([...selectedTaskSkills, ...names]));
  } else {
    selectedFixBugSkills = Array.from(new Set([...selectedFixBugSkills, ...names]));
  }
  renderSkillPicker(mode);
}

function clearAllSkills(mode) {
  if (mode === 'task') {
    selectedTaskSkills = [];
  } else {
    selectedFixBugSkills = [];
  }
  renderSkillPicker(mode);
}

function getActionOpeningPhrase(actionType) {
  if (actionType === 'fixbug') return 'Fix bug:';
  if (actionType === 'refactor') return 'Refactor code:';
  return 'Làm task:';
}
window.getActionOpeningPhrase = getActionOpeningPhrase;

function formatFullPromptWithAction(actionType, slashSkills, desc, log) {
  const opening = getActionOpeningPhrase(actionType);
  const cleanDesc = (desc || '').trim();

  // Kiểm tra nếu người dùng đã tự gõ câu mở đầu (tránh lặp prefix)
  const prefixRegex = /^(?:làm\s*task|thực\s*hiện\s*task|fix\s*bug|sửa\s*lỗi|refactor\s*code|tái\s*cấu\s*trúc(?:\s*mã\s*nguồn)?)(?:\s*[:\-]\s*|\s+)/i;
  let textWithOpening = cleanDesc;
  if (cleanDesc) {
    if (!prefixRegex.test(cleanDesc)) {
      textWithOpening = `${opening} ${cleanDesc}`;
    }
  } else {
    textWithOpening = opening;
  }

  const parts = [];
  const head = [slashSkills, textWithOpening].filter(Boolean).join(' ').trim();
  if (head) parts.push(head);
  if (actionType === 'fixbug' && log && log.trim()) {
    parts.push('Log lỗi:\n' + log.trim());
  }
  return parts.join('\n\n');
}
window.formatFullPromptWithAction = formatFullPromptWithAction;

function updateFixBugPromptPreview() {
  const previewEl = document.getElementById('fixbugPromptPreview');
  const scopeBadge = document.getElementById('fixbugScopeBadge');
  const scope = document.getElementById('taskTargetSelect')?.value || 'both';
  const desc = document.getElementById('taskPromptInput')?.value?.trim() || '';
  const log = document.getElementById('taskLogInput')?.value?.trim() || '';

  if (scopeBadge) {
    if (scope === 'fe') {
      scopeBadge.className = 'font-mono text-[10px] text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/80';
      scopeBadge.textContent = 'Frontend (webapp)';
    } else if (scope === 'be') {
      scopeBadge.className = 'font-mono text-[10px] text-emerald-300 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/80';
      scopeBadge.textContent = 'Backend (api)';
    } else {
      scopeBadge.className = 'font-mono text-[10px] text-indigo-300 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/80';
      scopeBadge.textContent = 'FE & BE';
    }
  }

  const slashSkills = selectedTaskSkills.map(s => s.startsWith('/') ? s : '/' + s).join(' ');
  const fullPrompt = formatFullPromptWithAction(currentTaskActionType, slashSkills, desc, log);

  if (previewEl) {
    if (desc || slashSkills) {
      previewEl.textContent = fullPrompt;
      previewEl.classList.remove('text-slate-500', 'italic');
      previewEl.classList.add('text-cyan-300');
    } else {
      const openText = getActionOpeningPhrase(currentTaskActionType);
      previewEl.textContent = `-- Chọn skill và nhập nội dung để xem lệnh ${slashSkills ? slashSkills + ' ' : ''}${openText} [mô tả yêu cầu] --`;
      previewEl.classList.add('text-slate-500', 'italic');
      previewEl.classList.remove('text-cyan-300');
    }
  }
}

function onFixBugScopeChange() {
  onTaskTargetChange();
}

function onTaskTargetChange() {
  const val = document.getElementById('taskTargetSelect')?.value || 'both';
  const available = getAvailableSkills('task').map(s => s.name);
  if (available.length > 0) {
    selectedTaskSkills = selectedTaskSkills.filter(s => available.includes(s));
  }
  renderSkillPicker('task');
  updateFixBugPromptPreview();
}

function updateSkillDropdowns() {
  renderSkillPicker('task');
}

document.addEventListener('click', (e) => {
  const taskTrigger = document.getElementById('taskSkillPickerTrigger');
  const taskDropdown = document.getElementById('taskSkillDropdown');
  if (taskDropdown && !taskDropdown.classList.contains('hidden')) {
    if (taskTrigger && !taskTrigger.contains(e.target) && !taskDropdown.contains(e.target)) {
      taskDropdown.classList.add('hidden');
    }
  }
});

// ---------------- TASK & FIX BUG UNIFIED LOGIC ----------------
let currentTaskActionType = 'task'; // 'task' | 'fixbug' | 'refactor'

function setTaskActionType(type) {
  currentTaskActionType = type;
  const select = document.getElementById('taskTypeSelect');
  if (select && select.value !== type) {
    select.value = type;
  }
  const logContainer = document.getElementById('taskLogContainer');
  const promptLabel = document.getElementById('taskPromptLabel');
  const promptInput = document.getElementById('taskPromptInput');
  const btnStartText = document.getElementById('btnStartTaskText');
  const targetLabel = document.getElementById('taskTargetLabel');

  if (type === 'fixbug') {
    if (logContainer) logContainer.classList.remove('hidden');
    if (targetLabel) targetLabel.textContent = 'Phạm vi sửa lỗi:';
    if (promptLabel) promptLabel.textContent = 'Mô tả lỗi / Hiện tượng:';
    if (promptInput && !promptInput.value.trim()) {
      promptInput.placeholder = 'Ví dụ: Bấm nút lưu đổi giường nhưng báo lỗi 400 Bad Request...';
    }
    if (btnStartText) btnStartText.textContent = 'Bắt đầu sửa lỗi';
  } else if (type === 'refactor') {
    if (logContainer) logContainer.classList.add('hidden');
    if (targetLabel) targetLabel.textContent = 'Phạm vi Refactor:';
    if (promptLabel) promptLabel.textContent = 'Yêu cầu / Mô tả Refactor:';
    if (promptInput && !promptInput.value.trim()) {
      promptInput.placeholder = 'Ví dụ: Tối ưu lại luồng state quản lý giỏ hàng, tách component con và clean code...';
    }
    if (btnStartText) btnStartText.textContent = 'Bắt đầu Refactor';
  } else {
    if (logContainer) logContainer.classList.add('hidden');
    if (targetLabel) targetLabel.textContent = 'Nơi thực hiện:';
    if (promptLabel) promptLabel.textContent = 'Yêu cầu / Mô tả chi tiết:';
    if (promptInput && !promptInput.value.trim()) {
      promptInput.placeholder = 'Ví dụ: Thêm API và Component hiển thị trạng thái giường cho BedRoomPosition...';
    }
    if (btnStartText) btnStartText.textContent = 'Bắt đầu thực thi';
  }

  // Cập nhật tên tab phù hợp với loại tác vụ được chọn (nếu chưa đặt tên tùy chỉnh)
  if (typeof parallelTasks !== 'undefined' && Array.isArray(parallelTasks)) {
    const cur = parallelTasks.find(t => t.id === activeTaskId);
    if (cur) {
      cur.type = type;
      if (!cur.isCustomName) {
        const idx = parallelTasks.findIndex(t => t.id === cur.id) + 1;
        const typeLabel = type === 'fixbug' ? 'Fix bug' : (type === 'refactor' ? 'Refactor code' : 'Tính năng mới');
        cur.name = `Task ${idx}: ${typeLabel}`;
      }
      if (typeof renderParallelTaskTabs === 'function') renderParallelTaskTabs();
      if (typeof renderFeedFilterTabs === 'function') renderFeedFilterTabs();
      if (typeof updateTaskActionButtons === 'function') updateTaskActionButtons();
    }
  }

  updateFixBugPromptPreview();
  saveDraft(false);
  scheduleQueueSync();
}

// Icon đổi tên tác vụ (icon cây bút / edit)
const EDIT_ICON_SVG = `<svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`;

// Helper bóc tách prefix (Task X:) và tên con (Tính năng mới / Fix bug / Tên tùy chỉnh)
function parseTaskName(rawName, fallbackIdx) {
  const str = (rawName || '').trim();
  const match = str.match(/^Task\s*(\d+)[:\s\-]\s*(.*)$/i);
  if (match) {
    return {
      prefix: `Task ${match[1]}:`,
      subName: match[2].trim() || 'Tính năng mới'
    };
  }
  return {
    prefix: `Task ${fallbackIdx}:`,
    subName: str || 'Tính năng mới'
  };
}

let editingTaskId = null;
let isStartingEdit = false;

function startInlineEditTask(taskId, e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  editingTaskId = taskId;
  isStartingEdit = true;
  renderParallelTaskTabs();
  setTimeout(() => {
    const input = document.getElementById(`inlineTaskInput_${taskId}`);
    if (input) {
      input.focus();
      input.select();
    }
    setTimeout(() => {
      isStartingEdit = false;
    }, 200);
  }, 50);
}

function handleInlineTaskKey(e, taskId, inputEl) {
  if (e.key === 'Enter') {
    e.preventDefault();
    saveInlineTaskName(taskId, inputEl.value);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    editingTaskId = null;
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
  }
}

function saveInlineTaskName(taskId, newSubName) {
  if (isStartingEdit) return;
  if (editingTaskId !== taskId && editingTaskId !== null) return;
  const task = parallelTasks.find(t => t.id === taskId);
  if (!task) {
    editingTaskId = null;
    return;
  }
  const idx = parallelTasks.findIndex(t => t.id === taskId) + 1;
  const { prefix, subName: oldSubName } = parseTaskName(task.name, idx);
  let cleaned = (newSubName || '').trim();
  cleaned = cleaned.replace(/^Task\s*\d+[:\s\-]\s*/i, '').trim();
  const fallback = task.type === 'fixbug' ? 'Fix bug' : 'Tính năng mới';
  const finalSub = cleaned || fallback;

  editingTaskId = null;

  // Nếu tên không thay đổi so với cũ, thoát chế độ sửa trong im lặng, không báo toast
  if (finalSub === oldSubName) {
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    return;
  }

  task.name = `${prefix} ${finalSub}`;
  task.isCustomName = true;

  renderParallelTaskTabs();
  renderFeedFilterTabs();
  saveDraft(false);
  scheduleQueueSync();
  pollStatus();
  showToast(`Đã đổi tên tác vụ thành: ${task.name}`, 'success');
}

function promptRenameTask(taskId) {
  startInlineEditTask(taskId);
}

function formatJiraText(text) {
  if (!text) return '';
  let s = String(text).trim();
  s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  s = s.replace(/(?:^|\n|\s+)(Acceptance Criteria[^\n]*?|Tiêu chí chấp nhận[^\n]*?)(?=(?:\s+(?:AC\s*\d+|Kịch bản|Scenario)|$|\n))/gi, '\n\n### $1\n');
  s = s.replace(/(?:^|\n|\s+)((?:AC\s*\d+|Kịch bản\s*\d+|Scenario\s*\d+)[\s:\-]+[^\n]*?)(?=(?:\s+(?:Given|When|Then|And|But)\b|$|\n))/g, '\n\n#### $1\n');
  s = s.replace(/(?:^|\n|\s+)\b(Given)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:When|Then|And|But|AC\s*\d+|Kịch bản|Scenario)\b|$|\n))/g, '\n- **Given**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(When)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:Then|And|But|AC\s*\d+|Given|Kịch bản|Scenario)\b|$|\n))/g, '\n- **When**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(Then)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Kịch bản|Scenario)\b|$|\n))/g, '\n- **Then**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(And)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Then|Kịch bản|Scenario)\b|$|\n))/g, '\n  - **And**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(But)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Then|Kịch bản|Scenario)\b|$|\n))/g, '\n  - **But**: $2');
  const headings = [
    'Hiện tượng lỗi', 'Mô tả lỗi', 'Bug description',
    'Các bước tái hiện', 'Steps to reproduce',
    'Kết quả thực tế', 'Actual result',
    'Kết quả mong muốn', 'Expected result',
    'Môi trường', 'Environment',
    'Mục tiêu', 'Objective',
    'Yêu cầu chức năng', 'Functional requirements'
  ];
  headings.forEach(h => {
    const re = new RegExp(`(?:^|\\n|(?:(?<=[.!?])\\s+))(${h})\\s*:\\s*`, 'gi');
    s = s.replace(re, '\n\n### $1:\n');
  });
  const lines = s.split('\n').map(line => line.replace(/[ \t]+/g, ' ').trimEnd());
  s = lines.join('\n');
  s = s.replace(/\n{3,}/g, '\n\n');
  return s.trim();
}
window.formatJiraText = formatJiraText;

function formatTaskPromptInput() {
  const promptInput = document.getElementById('taskPromptInput');
  if (!promptInput) return;
  const val = promptInput.value;
  if (!val || !val.trim()) {
    showToast('Khung yêu cầu đang trống!', 'info');
    return;
  }
  const formatted = formatJiraText(val);
  if (formatted === val) {
    showToast('Nội dung đã ở định dạng chuẩn tối ưu!', 'info');
    return;
  }
  promptInput.value = formatted;
  if (typeof onTaskPromptInput === 'function') {
    onTaskPromptInput();
  }
  showToast('Đã định dạng lại nội dung theo chuẩn BDD & đề mục!', 'success');
}
window.formatTaskPromptInput = formatTaskPromptInput;

function onTaskPromptInput() {
  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  saveDraft(false);
  scheduleQueueSync();
}

function onTaskLogInput() {
  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  saveDraft(false);
  scheduleQueueSync();
}

// ---------------- PERSISTENT TASK QUEUE (FIFO QUEUE) STATE ----------------
let parallelTasks = [
  {
    id: 'task_1',
    name: 'Task 1: Tính năng mới',
    type: 'task', // 'task' | 'fixbug'
    target: 'both',
    skills: [],
    prompt: '',
    error_log: '',
    status: 'idle', // 'idle' | 'queued' | 'running' | 'completed' | 'stopped'
    sessionId: null
  }
];
let activeTaskId = 'task_1';
let activeFeedFilter = 'all'; // 'all' | taskId
let _queueSyncTimer = null;
let _initialQueueRestored = false;

function scheduleQueueSync() {
  clearTimeout(_queueSyncTimer);
  _queueSyncTimer = setTimeout(() => {
    syncQueueToServer();
  }, 400);
}

async function syncQueueToServer() {
  try {
    syncFormToCurrentTask();
    const payload = parallelTasks.map(t => ({
      id: t.id,
      title: t.name,
      name: t.name,
      mode: t.type,
      type: t.type,
      target: t.target || 'both',
      scope: t.target || 'both',
      skills: t.skills || [],
      prompt: t.prompt || '',
      error_log: t.error_log || '',
      fix_desc: t.prompt || '',
      fix_err: t.error_log || '',
      status: t.status || 'idle'
    }));
    await fetch('/api/queue/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ queue: payload })
    });
  } catch (e) { }
}

function syncFormToCurrentTask() {
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  if (!cur) return;
  cur.type = currentTaskActionType;
  cur.target = document.getElementById('taskTargetSelect')?.value || 'both';
  cur.skills = [...selectedTaskSkills];
  cur.prompt = (document.getElementById('taskPromptInput')?.value || '').trim();
  cur.error_log = (document.getElementById('taskLogInput')?.value || '').trim();
}

function loadTaskToForm(taskId) {
  const task = parallelTasks.find(t => t.id === taskId);
  if (!task) return;
  setTaskActionType(task.type);
  const targetSelect = document.getElementById('taskTargetSelect');
  if (targetSelect) {
    targetSelect.value = task.target || 'both';
  }
  if (Array.isArray(task.skills) && task.skills.length > 0) {
    selectedTaskSkills = [...task.skills];
  } else if (selectedTaskSkills && selectedTaskSkills.length > 0) {
    task.skills = [...selectedTaskSkills];
  }
  renderSkillPicker('task');

  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) promptInput.value = task.prompt || '';
  const logInput = document.getElementById('taskLogInput');
  if (logInput) logInput.value = task.error_log || '';
  updateFixBugPromptPreview();
}

function selectParallelTask(taskId) {
  syncFormToCurrentTask();
  activeTaskId = taskId;
  activeFeedFilter = taskId;
  loadTaskToForm(taskId);
  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  pollStatus();
}

function addNewParallelTask() {
  syncFormToCurrentTask();
  const nextNum = parallelTasks.length + 1;
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  const newType = (cur && cur.type === 'task') ? 'fixbug' : 'task';
  const newId = 'task_' + Date.now();
  const defaultName = `Task ${nextNum}: ${newType === 'fixbug' ? 'Fix bug' : 'Tính năng mới'}`;
  const newTask = {
    id: newId,
    name: defaultName,
    isCustomName: false,
    type: newType,
    target: 'both',
    skills: [],
    prompt: '',
    error_log: '',
    status: 'idle',
    sessionId: null
  };
  parallelTasks.push(newTask);
  activeTaskId = newId;
  activeFeedFilter = newId;
  loadTaskToForm(newId);
  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  syncQueueToServer();
  pollStatus();

  setTimeout(() => {
    const container = document.getElementById('parallelTaskTabs');
    if (container) {
      container.scrollTo({ left: container.scrollWidth, behavior: 'smooth' });
    }
  }, 60);

  showToast(`Đã thêm ${newTask.name}`, 'info');
}

async function removeParallelTask(taskId, e) {
  if (e) e.stopPropagation();

  let cleanId = taskId;
  let idx = parallelTasks.findIndex(t => t.id === cleanId);
  if (idx === -1 && String(cleanId).startsWith('queued_')) {
    cleanId = String(cleanId).replace('queued_', '');
    idx = parallelTasks.findIndex(t => t.id === cleanId);
  }

  const t = idx !== -1 ? parallelTasks[idx] : null;
  const taskName = t ? t.name : (cleanId || 'Tác vụ');
  const isRunningOrQueued = t ? (t.status === 'running' || t.status === 'queued') : false;

  const conf = await antdConfirm({
    title: 'Xác nhận xóa tác vụ?',
    content: isRunningOrQueued
      ? `Tác vụ [${taskName}] đang chạy hoặc đang chờ. Bạn có chắc chắn muốn dừng và xóa tác vụ này? Tiến trình đang chạy sẽ bị dừng lại ngay lập tức.`
      : `Bạn có chắc chắn muốn xóa [${taskName}] khỏi danh sách và diễn biến thực thi?`,
    danger: true,
    okText: 'Xác nhận xóa',
    cancelText: 'Hủy'
  });
  if (!conf) return;

  // 1. Dừng tiến trình ngay lập tức nếu đang chạy hoặc đang chờ
  try {
    await fetch('/api/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: cleanId })
    });
  } catch (err) { }

  // 2. Xóa khỏi hàng đợi trên server
  try {
    await fetch('/api/queue/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: cleanId })
    });
  } catch (err) { }

  // 3. Dọn dẹp DOM ngay lập tức trên Diễn biến thực thi
  const wrapEl = document.getElementById('sessWrap_' + taskId) || document.getElementById('sessWrap_' + cleanId);
  if (wrapEl) wrapEl.remove();

  if (idx !== -1) {
    if (parallelTasks.length <= 1) {
      parallelTasks = [{
        id: 'task_' + Date.now(),
        name: 'Task 1: Tính năng mới',
        type: 'task',
        target: 'both',
        skills: [],
        prompt: '',
        error_log: '',
        status: 'idle',
        sessionId: null
      }];
      activeTaskId = parallelTasks[0].id;
      loadTaskToForm(activeTaskId);
    } else {
      parallelTasks.splice(idx, 1);
      if (activeTaskId === cleanId) {
        activeTaskId = parallelTasks[Math.max(0, idx - 1)].id;
        loadTaskToForm(activeTaskId);
      }
    }
  }

  if (activeFeedFilter === cleanId || activeFeedFilter === taskId) {
    activeFeedFilter = 'all';
  }

  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  await syncQueueToServer();
  pollStatus();
  showToast(`Đã xóa ${taskName}`);
}

async function clearCompletedTasks() {
  const completedTasks = parallelTasks.filter(t => t.status === 'completed' || t.status === 'done' || t.status === 'stopped');
  if (completedTasks.length === 0) {
    showToast('Không có tác vụ đã xử lý nào để xóa.', 'info');
    return;
  }

  const conf = await antdConfirm({
    title: 'Xóa các tác vụ đã xử lý?',
    content: `Bạn có chắc muốn xóa ${completedTasks.length} tác vụ đã hoàn tất / đã dừng khỏi danh sách?`,
    danger: true,
    okText: 'Xóa tác vụ'
  });
  if (!conf) return;

  try {
    await fetch('/api/queue/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: 'completed' })
    });
  } catch (e) { }

  completedTasks.forEach(t => {
    const wrapEl = document.getElementById('sessWrap_' + t.id);
    if (wrapEl) wrapEl.remove();
  });

  parallelTasks = parallelTasks.filter(t => t.status !== 'completed' && t.status !== 'done' && t.status !== 'stopped');

  if (parallelTasks.length === 0) {
    parallelTasks = [{
      id: 'task_' + Date.now(),
      name: 'Task 1: Tính năng mới',
      type: 'task',
      target: 'both',
      skills: [],
      prompt: '',
      error_log: '',
      status: 'idle',
      sessionId: null
    }];
  }

  if (!parallelTasks.some(t => t.id === activeTaskId)) {
    activeTaskId = parallelTasks[0].id;
    loadTaskToForm(activeTaskId);
  }

  if (activeFeedFilter !== 'all' && !parallelTasks.some(t => t.id === activeFeedFilter)) {
    activeFeedFilter = 'all';
  }

  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  await syncQueueToServer();
  pollStatus();
  showToast(`Đã xóa ${completedTasks.length} tác vụ đã xử lý xong.`);
}

function renderParallelTaskTabs() {
  const container = document.getElementById('parallelTaskTabs');
  if (!container) return;

  container.innerHTML = parallelTasks.map((t, idx) => {
    const isActive = t.id === activeTaskId;
    const isEditing = editingTaskId === t.id;
    const { prefix, subName } = parseTaskName(t.name, idx + 1);

    let statusDot = '';
    if (t.status === 'running') {
      statusDot = '<span class="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-ping shrink-0" title="Đang chạy"></span>';
    } else if (t.status === 'queued') {
      statusDot = '<span class="px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[9px] font-mono shrink-0" title="Đang chờ trong hàng đợi">Chờ</span>';
    } else if (t.status === 'completed' || t.status === 'done') {
      statusDot = '<span class="text-emerald-400 text-[10px] font-bold shrink-0" title="Đã hoàn tất">✓</span>';
    }

    if (isEditing) {
      return `
        <div class="task-tab-editing shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium select-none bg-[#101e38] border-[#38bdf8] shadow-sm">
          ${statusDot}
          <span class="text-cyan-300 font-bold shrink-0">${escapeHtml(prefix)}</span>
          <input id="inlineTaskInput_${t.id}" type="text" value="${escapeHtml(subName)}"
            class="bg-[#08101e] text-white text-xs px-1.5 py-0.5 rounded border border-[#199cff] focus:outline-none focus:ring-1 focus:ring-cyan-300 w-28 md:w-36 font-normal shadow-inner"
            onclick="event.stopPropagation()"
            onkeydown="handleInlineTaskKey(event, '${t.id}', this)"
            onblur="if (!isStartingEdit) saveInlineTaskName('${t.id}', this.value)" />
          <button type="button" onclick="saveInlineTaskName('${t.id}', document.getElementById('inlineTaskInput_${t.id}').value)"
            class="text-emerald-400 hover:text-emerald-300 p-0.5 text-xs font-bold transition cursor-pointer" title="Lưu tên">✓</button>
        </div>
      `;
    }

    return `
      <div onclick="selectParallelTask('${t.id}')" ondblclick="startInlineEditTask('${t.id}', event)"
        title="Bấm để chọn, nhấp icon cây bút để đổi tên"
        class="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-md cursor-pointer border text-xs font-medium transition select-none ${isActive
        ? 'active-task-tab bg-[rgb(25,156,255)] border-[rgb(25,156,255)] text-white shadow-sm font-bold'
        : 'bg-[#0e192c] border-[#244170] text-slate-300 hover:text-white hover:border-[#199cff]/60'
      }">
        ${statusDot}
        <span class="max-w-[130px] truncate"><span class="opacity-80">${escapeHtml(prefix)}</span> ${escapeHtml(subName)}</span>
        <button type="button" onclick="startInlineEditTask('${t.id}', event)" title="Đổi tên tác vụ"
          class="shrink-0 p-1 opacity-80 hover:opacity-100 hover:bg-white/20 rounded transition cursor-pointer flex items-center justify-center">
          ${EDIT_ICON_SVG}
        </button>
        <button type="button" onclick="removeParallelTask('${t.id}', event)" title="Xóa tác vụ này"
          class="ml-0.5 opacity-80 hover:opacity-100 hover:text-rose-400 p-0.5 rounded leading-none text-xs font-bold transition hover:bg-rose-500/20">×</button>
      </div>
    `;
  }).join('');
}

function updateTaskActionButtons() {
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  const btnStart = document.getElementById('btnStartTask');
  const btnStop = document.getElementById('btnStopTask');
  const btnStopAll = document.getElementById('btnStopAllParallel');
  const startText = document.getElementById('btnStartTaskText');

  const isCurrentActive = cur && (cur.status === 'running' || cur.status === 'queued');
  const activeCount = parallelTasks.filter(t => t.status === 'running' || t.status === 'queued').length;
  const anyRunning = parallelTasks.some(t => t.status === 'running');

  if (btnStart && btnStop) {
    if (isCurrentActive) {
      btnStart.classList.add('hidden');
      btnStop.classList.remove('hidden');
    } else {
      btnStart.classList.remove('hidden');
      btnStop.classList.add('hidden');
      if (startText) {
        if (anyRunning) {
          startText.textContent = 'Đưa vào hàng đợi (Queue)';
        } else if (cur && (cur.status === 'completed' || cur.status === 'done' || cur.status === 'stopped')) {
          startText.textContent = 'Tiếp tục task này trên AI Terminal';
        } else if (cur && cur.type === 'fixbug') {
          startText.textContent = 'Bắt đầu sửa lỗi này';
        } else if (cur && cur.type === 'refactor') {
          startText.textContent = 'Bắt đầu Refactor code';
        } else {
          startText.textContent = 'Bắt đầu tác vụ này';
        }
      }
    }
  }

  if (btnStopAll) {
    if (activeCount > 1) {
      btnStopAll.classList.remove('hidden');
    } else {
      btnStopAll.classList.add('hidden');
    }
  }
}

async function startSingleTaskById(taskId) {
  const task = parallelTasks.find(t => t.id === taskId);
  if (!task) return;
  if (taskId === activeTaskId) syncFormToCurrentTask();

  if (!task.prompt && !task.error_log) {
    await antdAlert({ title: 'Thiếu thông tin', content: `Tác vụ [${task.name}] chưa có nội dung yêu cầu hoặc mô tả lỗi!`, type: 'error' });
    return;
  }

  const anyRunning = parallelTasks.some(t => t.status === 'running' && t.id !== task.id);
  task.status = anyRunning ? 'queued' : 'running';
  renderParallelTaskTabs();
  updateTaskActionButtons();
  await syncQueueToServer();

  const mode = task.type || 'task';
  const slashSkills = (task.skills || []).map(s => s.startsWith('/') ? s : '/' + s).join(' ');
  const formattedPrompt = formatFullPromptWithAction(mode, slashSkills, task.prompt, task.error_log);

  try {
    if (task.type === 'fixbug') {
      const res = await fetch('/api/fixbug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task.id,
          title: task.name,
          mode: 'fixbug',
          skills: task.skills,
          skill: task.skills.join(', '),
          scope: task.target || 'both',
          description: formattedPrompt,
          original_prompt: task.original_prompt || task.prompt || '',
          error_log: task.error_log
        })
      });
      const d = await res.json();
      if (!d.success) {
        task.status = 'idle';
        await antdAlert({ title: 'Lỗi', content: d.message, type: 'error' });
      } else {
        task.status = d.queue_status === 'queued' ? 'queued' : 'running';
        showToast(d.message || `Đã đưa ${task.name} vào hàng đợi`, 'success');
      }
    } else {
      const res = await fetch('/api/task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task.id,
          title: task.name,
          mode: mode,
          prompt: formattedPrompt,
          original_prompt: task.original_prompt || task.prompt || '',
          error_log: task.error_log,
          target: task.target || 'both',
          starter: 'fe',
          rounds: 4,
          skills: task.skills,
          skill: task.skills.join(', ')
        })
      });
      const d = await res.json();
      if (!d.success) {
        task.status = 'idle';
        await antdAlert({ title: 'Lỗi', content: d.message, type: 'error' });
      } else {
        task.status = d.queue_status === 'queued' ? 'queued' : 'running';
        showToast(d.message || `Đã đưa ${task.name} vào hàng đợi`, 'success');
      }
    }
  } catch (e) {
    task.status = 'idle';
    await antdAlert({ title: 'Lỗi kết nối', content: e.message, type: 'error' });
  }
  if (task.status === 'idle') {
    await syncQueueToServer();
  }
  renderParallelTaskTabs();
  updateTaskActionButtons();
  pollStatus();
}

function startCurrentTask() {
  return startSingleTaskById(activeTaskId);
}

function startUnifiedTask() {
  return startCurrentTask();
}

function startTask() {
  return startCurrentTask();
}

function startFixBug() {
  return startCurrentTask();
}

async function startAllParallelTasks() {
  syncFormToCurrentTask();
  const idleTasks = parallelTasks.filter(t => t.status !== 'running' && t.status !== 'queued');
  if (idleTasks.length === 0) {
    showToast('Tất cả tác vụ đều đã nằm trong hàng đợi hoặc đang chạy!', 'info');
    return;
  }
  for (const t of idleTasks) {
    if (!t.prompt && !t.error_log) {
      await antdAlert({ title: 'Thiếu thông tin', content: `[${t.name}] chưa có nội dung yêu cầu hoặc mô tả lỗi. Vui lòng nhập trước khi chạy!`, type: 'error' });
      return;
    }
  }
  showToast(`Đang xếp ${idleTasks.length} tác vụ vào hàng đợi thực thi tuần tự...`, 'info');
  for (const t of idleTasks) {
    await startSingleTaskById(t.id);
  }
}

async function stopCurrentTask() {
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  const taskName = cur ? cur.name : 'tác vụ này';
  const confirmed = await antdConfirm({
    title: 'Dừng tác vụ',
    content: `Bạn có chắc muốn dừng <strong>${escapeHtml(taskName)}</strong>?`,
    danger: true,
    okText: 'Dừng ngay'
  });
  if (confirmed) {
    await fetch('/api/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: activeTaskId })
    });
    if (cur) cur.status = 'stopped';
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    updateTaskActionButtons();
    pollStatus();
  }
}

async function stopAllTasks() {
  const confirmed = await antdConfirm({
    title: 'Dừng toàn bộ hàng đợi',
    content: 'Bạn có chắc chắn muốn dừng toàn bộ các tác vụ đang chạy và đang chờ trong hàng đợi?',
    danger: true,
    okText: 'Dừng tất cả'
  });
  if (confirmed) {
    await fetch('/api/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: 'all' })
    });
    parallelTasks.forEach(t => { if (t.status === 'running' || t.status === 'queued') t.status = 'stopped'; });
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    updateTaskActionButtons();
    pollStatus();
  }
}

function stopProcess() {
  return stopCurrentTask();
}

function setTaskPrompt(text, skill, target) {
  setTaskActionType('task');
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) promptInput.value = text;
  if (target) {
    const targetSelect = document.getElementById('taskTargetSelect');
    if (targetSelect) {
      targetSelect.value = target;
      onTaskTargetChange();
    }
  }
  if (skill) {
    const sClean = skill.startsWith('skill-') ? skill : 'skill-' + skill;
    selectedTaskSkills = [sClean];
    renderSkillPicker('task');
  }
  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  scheduleQueueSync();
}

function setFixBugSample(desc, log, skill, scope) {
  setTaskActionType('fixbug');
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) promptInput.value = desc;
  const logInput = document.getElementById('taskLogInput');
  if (logInput) logInput.value = log || '';
  if (scope) {
    const targetSelect = document.getElementById('taskTargetSelect');
    if (targetSelect) {
      targetSelect.value = scope;
      onTaskTargetChange();
    }
  }
  if (skill) {
    const sClean = skill.startsWith('skill-') ? skill : 'skill-' + skill;
    selectedTaskSkills = [sClean];
    renderSkillPicker('task');
  }
  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  scheduleQueueSync();
}

function setFixBug(desc, log, skill, scope) {
  setFixBugSample(desc, log, skill, scope);
}

// ---------------- TOOL BADGE, LIVE STREAMING & CODE CHANGES ----------------
function getToolBadgeClass(toolName) {
  if (toolName === 'run_command') return 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
  if (toolName === 'read_file' || toolName === 'view_file') return 'bg-sky-500/20 text-sky-300 border border-sky-500/30';
  if (toolName === 'edit_file' || toolName === 'replace_file_content' || toolName === 'write_to_file' || toolName === 'write_file') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (toolName === 'grep_search' || toolName === 'find_by_name') return 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
  return 'bg-slate-500/20 text-slate-300 border border-slate-500/30';
}

function toggleStepOutput(outId) {
  const el = document.getElementById(outId);
  if (el) {
    el.classList.toggle('hidden');
    const isHidden = el.classList.contains('hidden');
    const arrowEl = document.getElementById('arrow_' + outId);
    if (arrowEl) {
      arrowEl.classList.toggle('rotate-180', !isHidden);
    }
  }
}

function formatDiffColoredHtml(diffText) {
  if (!diffText) return '<div class="text-slate-500 italic p-2">Không có nội dung diff chi tiết.</div>';
  const lines = diffText.replace(/\r\n/g, '\n').split('\n');
  let oldLn = null;
  let newLn = null;
  const rows = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Bỏ qua các dòng metadata đầu của git diff để hiển thị sạch như GitHub PR diff
    if (
      line.startsWith('diff --git ') ||
      line.startsWith('index ') ||
      line.startsWith('--- ') ||
      line.startsWith('+++ ') ||
      line.startsWith('new file mode ') ||
      line.startsWith('deleted file mode ')
    ) {
      continue;
    }

    if (line.startsWith('@@')) {
      const m = line.match(/@@\s*-(\d+)(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@/);
      if (m) {
        oldLn = parseInt(m[1], 10);
        newLn = parseInt(m[2], 10);
      }
      rows.push(`<div class="git-diff-hunk">${escapeHtml(line)}</div>`);
      continue;
    }

    if (line.startsWith('+')) {
      const code = escapeHtml(line.slice(1));
      const lnStr = newLn !== null ? newLn++ : '';
      rows.push(
        `<div class="git-diff-row git-diff-add">` +
        `<span class="git-diff-ln"></span>` +
        `<span class="git-diff-ln">${lnStr}</span>` +
        `<span class="git-diff-sign">+</span>` +
        `<span class="git-diff-code">${code || ' '}</span>` +
        `</div>`
      );
    } else if (line.startsWith('-')) {
      const code = escapeHtml(line.slice(1));
      const lnStr = oldLn !== null ? oldLn++ : '';
      rows.push(
        `<div class="git-diff-row git-diff-del">` +
        `<span class="git-diff-ln">${lnStr}</span>` +
        `<span class="git-diff-ln"></span>` +
        `<span class="git-diff-sign">-</span>` +
        `<span class="git-diff-code">${code || ' '}</span>` +
        `</div>`
      );
    } else if (line.startsWith('\\ No newline')) {
      continue;
    } else {
      const rawCode = line.startsWith(' ') ? line.slice(1) : line;
      const oStr = oldLn !== null ? oldLn++ : '';
      const nStr = newLn !== null ? newLn++ : '';
      rows.push(
        `<div class="git-diff-row git-diff-ctx">` +
        `<span class="git-diff-ln">${oStr}</span>` +
        `<span class="git-diff-ln">${nStr}</span>` +
        `<span class="git-diff-sign"> </span>` +
        `<span class="git-diff-code">${escapeHtml(rawCode) || ' '}</span>` +
        `</div>`
      );
    }
  }

  return `<div class="git-diff-container">${rows.join('')}</div>`;
}

function extractExitStatusAndClean(text) {
  let statusHtml = '';
  let remaining = (text || '').trim();

  const exitMatch = remaining.match(/^Command exited with code (\d+)\.?\s*/i);
  if (exitMatch) {
    const code = parseInt(exitMatch[1], 10);
    const isSuccess = (code === 0);
    statusHtml = `
      <div class="step-out-header flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-100 dark:border-slate-800 text-[11px] font-sans select-none">
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold ${
            isSuccess
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-rose-50 text-rose-700 border border-rose-200'
          }">
            ${isSuccess ? '✓ Hoàn thành (code 0)' : `✕ Thoát mã lỗi (code ${code})`}
          </span>
          <span class="text-slate-400 text-[10.5px]">Kết quả thực thi lệnh</span>
        </div>
      </div>
    `.trim();
    remaining = remaining.slice(exitMatch[0].length).trim();
  }

  if (remaining.startsWith('Command output:\n')) {
    remaining = remaining.slice('Command output:\n'.length).trim();
  } else if (remaining.startsWith('Command output:')) {
    remaining = remaining.slice('Command output:'.length).trim();
  }

  return { statusHtml, remaining };
}

function formatCommandOutputLines(lines) {
  const grepWithLineRegex = /^([^\s:]+\.[a-zA-Z0-9_-]+):(\d+):(.*)$/;
  const grepNoLineRegex = /^([^\s:]+\.[a-zA-Z0-9_-]+):(.*)$/;
  const gitStatusModRegex = /^(\s*)(modified|new file|deleted|renamed):\s+(.*)$/;
  const gitBranchRegex = /^On branch (.+)$/;

  const rows = [];
  let grepCount = 0;
  for (const l of lines) {
    const cleanL = l.replace(/\r/g, '').trim();
    if (grepWithLineRegex.test(cleanL) || (grepNoLineRegex.test(cleanL) && cleanL.includes('/'))) {
      grepCount++;
    }
  }

  if (grepCount > 0) {
    rows.push(`<div class="text-[10.5px] font-sans font-medium text-slate-400 dark:text-slate-500 mb-1 flex items-center justify-between select-none"><span>Kết quả tìm kiếm (${grepCount} vị trí):</span></div>`);
  }

  for (const rawLine of lines) {
    const line = rawLine.replace(/\r/g, '');
    if (!line.trim()) {
      rows.push('<div class="h-1"></div>');
      continue;
    }

    const grepM = line.trim().match(grepWithLineRegex);
    if (grepM) {
      const file = grepM[1];
      const lineNum = grepM[2];
      const code = grepM[3].replace(/^ {6,}/, '  ').replace(/^\t+/, '  ');
      rows.push(`
        <div class="step-grep-row flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2.5 py-1 px-1.5 rounded hover:bg-[#f0f7ff] dark:hover:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800/40 last:border-0 font-mono text-[11px] leading-relaxed transition">
          <div class="shrink-0 flex items-center gap-1.5 select-all">
            <span class="step-grep-file font-semibold text-[#1677ff] dark:text-sky-400 hover:underline cursor-pointer" title="${escapeHtml(file)}">${escapeHtml(file)}</span>
            <span class="step-grep-line font-bold text-[10px] px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 shrink-0" title="Dòng ${lineNum}">:${lineNum}:</span>
          </div>
          <div class="step-grep-code text-slate-800 dark:text-slate-200 overflow-x-auto whitespace-pre min-w-0 flex-1 pl-3 sm:pl-0 border-l-2 sm:border-l-0 border-blue-200 dark:border-blue-800">
            ${escapeHtml(code)}
          </div>
        </div>
      `.trim());
      continue;
    }

    const grepNoLineM = line.trim().match(grepNoLineRegex);
    if (grepNoLineM && (grepNoLineM[1].includes('/') || grepCount > 0)) {
      const file = grepNoLineM[1];
      const code = grepNoLineM[2].replace(/^ {6,}/, '  ').replace(/^\t+/, '  ');
      rows.push(`
        <div class="step-grep-row flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2.5 py-1 px-1.5 rounded hover:bg-[#f0f7ff] dark:hover:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800/40 last:border-0 font-mono text-[11px] leading-relaxed transition">
          <div class="shrink-0 flex items-center gap-1.5 select-all">
            <span class="step-grep-file font-semibold text-[#1677ff] dark:text-sky-400 hover:underline cursor-pointer" title="${escapeHtml(file)}">${escapeHtml(file)}</span>
          </div>
          <div class="step-grep-code text-slate-800 dark:text-slate-200 overflow-x-auto whitespace-pre min-w-0 flex-1 pl-3 sm:pl-0 border-l-2 sm:border-l-0 border-blue-200 dark:border-blue-800">
            ${escapeHtml(code)}
          </div>
        </div>
      `.trim());
      continue;
    }

    const modM = line.match(gitStatusModRegex);
    if (modM) {
      const type = modM[2];
      const path = modM[3];
      const colorClass = type === 'modified' ? 'text-amber-600' : (type === 'new file' ? 'text-emerald-600' : 'text-rose-600');
      rows.push(`
        <div class="px-1.5 py-1 font-mono text-[11px] whitespace-pre overflow-x-auto flex items-center gap-2 hover:bg-slate-50 dark:hover:bg-slate-800/40 rounded transition">
          <span class="${colorClass} font-semibold font-mono w-20 shrink-0 select-none">${escapeHtml(type)}:</span>
          <span class="text-blue-600 dark:text-sky-400 font-medium select-all">${escapeHtml(path)}</span>
        </div>
      `.trim());
      continue;
    }

    const branchM = line.match(gitBranchRegex);
    if (branchM) {
      rows.push(`
        <div class="px-1.5 py-0.5 font-mono text-[11px] whitespace-pre overflow-x-auto text-slate-500">
          Nhánh: <span class="text-[#1677ff] font-bold select-all">${escapeHtml(branchM[1])}</span>
        </div>
      `.trim());
      continue;
    }

    if (/^(WARNING|Warning):/.test(line.trim())) {
      rows.push(`<div class="px-1.5 py-0.5 font-mono text-[11px] text-amber-600 whitespace-pre overflow-x-auto leading-relaxed">${escapeHtml(line)}</div>`);
      continue;
    }
    if (/^(ERROR|Error):/.test(line.trim())) {
      rows.push(`<div class="px-1.5 py-0.5 font-mono text-[11px] text-rose-600 whitespace-pre overflow-x-auto leading-relaxed">${escapeHtml(line)}</div>`);
      continue;
    }

    rows.push(`<div class="px-1.5 py-0.5 font-mono text-[11px] text-slate-700 dark:text-slate-300 whitespace-pre overflow-x-auto leading-relaxed select-text">${escapeHtml(line)}</div>`);
  }

  return rows.join('\n');
}

function formatStepOutputWithDiff(outputText) {
  if (!outputText) return '';
  const normalized = String(outputText).replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  const diffIdx = normalized.indexOf('diff --git ');
  if (diffIdx !== -1) {
    const beforeDiff = normalized.slice(0, diffIdx).trim();
    const diffPart = normalized.slice(diffIdx);
    const { statusHtml, remaining } = extractExitStatusAndClean(beforeDiff);
    const remainingLines = remaining ? remaining.split('\n') : [];
    return `
      ${statusHtml}
      ${remainingLines.length > 0 ? `<div class="mb-2">${formatCommandOutputLines(remainingLines)}</div>` : ''}
      ${formatDiffColoredHtml(diffPart)}
    `.trim();
  }

  if (normalized.includes('\n@@ -') || normalized.startsWith('@@ -')) {
    return formatDiffColoredHtml(normalized);
  }

  const { statusHtml, remaining } = extractExitStatusAndClean(normalized);
  if (!remaining.trim() || remaining.trim() === 'No output from the command.') {
    return `
      ${statusHtml}
      <div class="text-slate-400 italic text-[11px] py-1 font-sans">Không có dữ liệu đầu ra từ câu lệnh.</div>
    `.trim();
  }

  const lines = remaining.trim().split('\n');
  return `
    ${statusHtml}
    <div class="step-out-lines flex flex-col gap-0.5 mt-1">
      ${formatCommandOutputLines(lines)}
    </div>
  `.trim();
}

let _collapsedTurnCards = new Set();
let _userInteractedTurnCards = new Map(); // cardId -> boolean (true: user explicitly collapsed, false: user explicitly expanded)
let _collapsedStepBoxes = new Set();
let _collapsedDiffBoxes = new Set();

function toggleTurnCollapse(cardId, event) {
  if (event) {
    event.stopPropagation();
  }
  const card = document.getElementById(cardId);
  const bodyEl = document.getElementById('turnBody_' + cardId);
  const chevronEl = document.getElementById('turnChevron_' + cardId);
  const badgeEl = document.getElementById('turnCollapsedBadge_' + cardId);

  if (!bodyEl) return;
  const isHidden = bodyEl.classList.contains('hidden');
  if (isHidden) {
    bodyEl.classList.remove('hidden');
    _collapsedTurnCards.delete(cardId);
    _userInteractedTurnCards.set(cardId, false);
    if (chevronEl) chevronEl.classList.remove('-rotate-90');
    if (badgeEl) badgeEl.classList.add('hidden');
  } else {
    bodyEl.classList.add('hidden');
    _collapsedTurnCards.add(cardId);
    _userInteractedTurnCards.set(cardId, true);
    if (chevronEl) chevronEl.classList.add('-rotate-90');
    if (badgeEl) badgeEl.classList.remove('hidden');
  }

  // Cập nhật sig để pollStatus không bị lệch
  if (card && card.dataset.sig) {
    const parts = card.dataset.sig.split('_');
    if (parts.length >= 3) {
      parts[parts.length - 3] = String(_collapsedTurnCards.has(cardId));
      card.dataset.sig = parts.join('_');
    }
  }
}
window.toggleTurnCollapse = toggleTurnCollapse;

function toggleStepLogsCollapse(boxId, event) {
  if (event) {
    event.stopPropagation();
  }
  const bodyEl = document.getElementById('stepLogsBody_' + boxId);
  const arrowEl = document.getElementById('stepArrow_' + boxId);
  const headerEl = document.getElementById('stepHeader_' + boxId);

  if (!bodyEl) return;
  const isHidden = bodyEl.classList.contains('hidden');
  if (isHidden) {
    bodyEl.classList.remove('hidden');
    _collapsedStepBoxes.delete(boxId);
    if (arrowEl) arrowEl.classList.add('rotate-180');
    if (headerEl) {
      headerEl.classList.add('border-b');
    }
  } else {
    bodyEl.classList.add('hidden');
    _collapsedStepBoxes.add(boxId);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
    if (headerEl) {
      headerEl.classList.remove('border-b');
    }
  }

  // Cập nhật sig của card tương ứng để không bị reload đè mất trạng thái
  const cardId = 'turnCard_' + boxId.replace(/^stepBox_/, '');
  const card = document.getElementById(cardId);
  if (card && card.dataset.sig) {
    const parts = card.dataset.sig.split('_');
    if (parts.length >= 3) {
      parts[parts.length - 2] = String(_collapsedStepBoxes.has(boxId));
      card.dataset.sig = parts.join('_');
    }
  }
}
window.toggleStepLogsCollapse = toggleStepLogsCollapse;

function toggleDiffBoxCollapse(boxId, event) {
  if (event) {
    event.stopPropagation();
  }
  const bodyEl = document.getElementById('diffBoxBody_' + boxId);
  const arrowEl = document.getElementById('diffArrow_' + boxId);
  const headerEl = document.getElementById('diffHeader_' + boxId);

  if (!bodyEl) return;
  const isHidden = bodyEl.classList.contains('hidden');
  if (isHidden) {
    bodyEl.classList.remove('hidden');
    _collapsedDiffBoxes.delete(boxId);
    if (arrowEl) arrowEl.classList.add('rotate-180');
    if (headerEl) {
      headerEl.classList.add('border-b');
    }
  } else {
    bodyEl.classList.add('hidden');
    _collapsedDiffBoxes.add(boxId);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
    if (headerEl) {
      headerEl.classList.remove('border-b');
    }
  }

  // Cập nhật sig của card tương ứng để không bị reload đè mất trạng thái
  const cardId = 'turnCard_' + boxId.replace(/^diffBox_/, '');
  const card = document.getElementById(cardId);
  if (card && card.dataset.sig) {
    const parts = card.dataset.sig.split('_');
    if (parts.length >= 3) {
      parts[parts.length - 1] = String(_collapsedDiffBoxes.has(boxId));
      card.dataset.sig = parts.join('_');
    }
  }
}
window.toggleDiffBoxCollapse = toggleDiffBoxCollapse;

function renderChangedFilesHtml(changedFiles, sessId, turnIdx) {
  if (!changedFiles || changedFiles.length === 0) return '';

  // Sắp xếp: file do AI trực tiếp chỉnh sửa lên đầu, các file đã thay đổi trước đó ở sau
  const displayFiles = [...changedFiles].sort((a, b) => (b.touched_by_ai ? 1 : 0) - (a.touched_by_ai ? 1 : 0));
  if (displayFiles.length === 0) return '';

  const totalAdds = displayFiles.reduce((acc, f) => acc + (Number(f.additions) || 0), 0);
  const totalDels = displayFiles.reduce((acc, f) => acc + (Number(f.deletions) || 0), 0);
  const diffBoxId = `diffBox_${sessId}_${turnIdx}`;
  const isDiffCollapsed = _collapsedDiffBoxes.has(diffBoxId);

  return `
        <div class="changed-files-box mb-3 rounded-lg border border-[#333333] bg-[#181818] overflow-hidden shadow-sm">
          <div id="diffHeader_${diffBoxId}"
               onclick="toggleDiffBoxCollapse('${diffBoxId}', event)"
               class="changed-files-header px-3 py-2 bg-[#252526] ${isDiffCollapsed ? '' : 'border-b border-[#333333]'} flex items-center justify-between text-[11px] font-semibold text-slate-200 cursor-pointer select-none hover:bg-[#2d2d30] transition"
               title="${isDiffCollapsed ? 'Nhấp để hiển thị thay đổi mã nguồn' : 'Nhấp để thu gọn thay đổi mã nguồn'}">
            <div class="flex items-center gap-2">
              <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <span class="font-sans font-semibold">Thay đổi mã nguồn (${displayFiles.length} file)</span>
              <span class="git-stat-add px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#73c991] bg-[#73c991]/15">+${totalAdds}</span>
              <span class="git-stat-del px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#f14c4c] bg-[#f14c4c]/15">-${totalDels}</span>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" onclick="toggleDiffBoxCollapse('${diffBoxId}', event)"
                class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                title="${isDiffCollapsed ? 'Nhấp để hiển thị thay đổi mã nguồn' : 'Nhấp để thu gọn thay đổi mã nguồn'}">
                <svg id="diffArrow_${diffBoxId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isDiffCollapsed ? '' : 'rotate-180'}" viewBox="0 0 24 24" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>
          <div id="diffBoxBody_${diffBoxId}" class="${isDiffCollapsed ? 'hidden' : ''} p-2.5 space-y-3 max-h-[500px] overflow-y-auto font-mono text-[11px]">
            ${displayFiles.map((f, fIdx) => {
    const diffId = `file_diff_${sessId}_${turnIdx}_${fIdx}`;
    const st = (f.status || 'M').toUpperCase();
    const isAdded = st.includes('A');
    const isDeleted = st.includes('D');
    const stBadgeClass = isAdded
      ? 'bg-emerald-500/15 text-[#73c991] border-emerald-500/40'
      : (isDeleted ? 'bg-rose-500/15 text-[#f14c4c] border-rose-500/40' : 'bg-amber-500/15 text-[#cca700] border-amber-500/40');
    const isPre = Boolean(f.is_preexisting || (!f.touched_by_ai && f.touched_by_ai !== undefined));
    const autoExpand = Boolean(f.touched_by_ai || (!isPre && fIdx < 3));

    const filePath = f.path || '';
    const lastSlash = filePath.lastIndexOf('/');
    const dirPart = lastSlash !== -1 ? filePath.slice(0, lastSlash + 1) : '';
    const filePart = lastSlash !== -1 ? filePath.slice(lastSlash + 1) : filePath;

    return `
                <div class="changed-file-card rounded-md border border-[#333333] bg-[#1e1e1e] overflow-hidden shadow-sm">
                  <div class="changed-file-header px-3 py-1.5 bg-[#252526] border-b border-[#333333] flex items-center justify-between gap-2 cursor-pointer select-none hover:bg-[#2d2d30] transition" onclick="toggleStepOutput('${diffId}')">
                    <div class="flex items-center gap-2 min-w-0 flex-1">
                      <span class="px-1.5 py-0.5 rounded text-[9.5px] font-bold border font-mono ${stBadgeClass}">${escapeHtml(st)}</span>
                      <span class="truncate font-mono text-[11.5px]" title="${escapeHtml(filePath)}">
                        <span class="text-slate-400">${escapeHtml(dirPart)}</span><span class="text-slate-100 font-bold">${escapeHtml(filePart)}</span>
                      </span>
                      ${isPre ? `
                        <span class="file-tag-preexisting px-1.5 py-0.5 rounded text-[10px] font-sans font-medium text-amber-300 bg-amber-500/15 border border-amber-500/35 shrink-0" title="Tập tin này đã có thay đổi từ trước khi chạy tác vụ, không phải do AI chỉnh sửa trong phiên này">
                          Thay đổi trước đó
                        </span>
                      ` : `
                        <span class="file-tag-ai px-1.5 py-0.5 rounded text-[10px] font-sans font-medium text-blue-300 bg-blue-500/20 border border-blue-400/35 shrink-0" title="Tập tin do AI trực tiếp chỉnh sửa">
                          Do AI chỉnh sửa
                        </span>
                      `}
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#73c991] bg-[#73c991]/15">+${f.additions || 0}</span>
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#f14c4c] bg-[#f14c4c]/15">-${f.deletions || 0}</span>
                      <button type="button" onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(f.repo || 'fe')}')"
                        class="file-edit-btn p-1 rounded hover:bg-sky-500/15 text-sky-400 hover:text-sky-300 transition flex items-center justify-center cursor-pointer"
                        title="Chỉnh sửa file (${escapeHtml(filePart)}) (Ctrl+S để lưu)">
                        <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      ${f.diff ? `
                        <button type="button" onclick="event.stopPropagation(); toggleStepOutput('${diffId}')"
                          class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                          title="${autoExpand ? 'Thu gọn Diff' : 'Mở rộng Diff'}">
                          <svg id="arrow_${diffId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${autoExpand ? 'rotate-180' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      ` : ''}
                    </div>
                  </div>
                  ${f.diff ? `
                    <div id="${diffId}" class="${autoExpand ? '' : 'hidden'} max-h-96 overflow-y-auto">
                      ${formatDiffColoredHtml(f.diff)}
                    </div>
                  ` : ''}
                </div>
              `;
  }).join('')}
          </div>
        </div>
      `;
}

function renderStepLogsHtml(stepLogs, sessId, turnIdx) {
  if (!stepLogs || stepLogs.length === 0) return '';

  const stepBoxId = `stepBox_${sessId}_${turnIdx}`;
  const isStepCollapsed = _collapsedStepBoxes.has(stepBoxId);

  return `
        <div class="tool-step-box mb-3 rounded-lg border border-[#244170] bg-[#0b1322] overflow-hidden shadow-inner">
          <div id="stepHeader_${stepBoxId}"
               onclick="toggleStepLogsCollapse('${stepBoxId}', event)"
               class="tool-step-header px-3 py-2 bg-[#101e38] ${isStepCollapsed ? '' : 'border-b border-[#244170]'} flex items-center justify-between text-[11px] font-semibold text-slate-300 cursor-pointer select-none hover:bg-[#152747] transition"
               title="${isStepCollapsed ? 'Nhấp để hiển thị tiến trình AI Terminal ngầm' : 'Nhấp để thu gọn tiến trình AI Terminal ngầm'}">
            <div class="flex items-center gap-2">
              <svg class="w-3.5 h-3.5 text-[#199cff]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              <span>Tiến trình AI Terminal ngầm (${stepLogs.length} thao tác)</span>
            </div>
            <div class="flex items-center gap-1.5 text-slate-400">
              <button type="button" onclick="toggleStepLogsCollapse('${stepBoxId}', event)"
                class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                title="${isStepCollapsed ? 'Nhấp để hiển thị tiến trình AI Terminal ngầm' : 'Nhấp để thu gọn tiến trình AI Terminal ngầm'}">
                <svg id="stepArrow_${stepBoxId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isStepCollapsed ? '' : 'rotate-180'}" viewBox="0 0 24 24" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>
          <div id="stepLogsBody_${stepBoxId}" class="${isStepCollapsed ? 'hidden' : ''} p-2 space-y-1.5 max-h-64 overflow-y-auto font-mono text-[11px]">
            ${stepLogs.map((step, sIdx) => {
    const outId = `step_out_${sessId}_${turnIdx}_${sIdx}`;
    const isDone = step.state === 'DONE';
    const durationStr = step.duration ? formatDuration(step.duration) : 'Xong';
    const cmdText = step.param_summary || (step.params && (step.params.CommandLine || step.params.command || step.params.Path || step.params.query)) || '';
    const autoShowOutput = Boolean(!isDone || (sIdx === stepLogs.length - 1 && step.output));
    return `
                <div class="tool-step-item rounded border border-slate-700/40 bg-[#0e192c] p-2 space-y-1.5">
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2 min-w-0 flex-1">
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${getToolBadgeClass(step.tool_name)}">${escapeHtml(step.tool_name)}</span>
                      <span class="text-slate-200 truncate font-mono text-[11px]" title="${escapeHtml(step.param_summary || '')}">${escapeHtml(step.param_summary || '')}</span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      ${!isDone
        ? '<span class="inline-flex items-center gap-1 text-cyan-400 text-[10px] font-mono"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>Đang chạy...</span>'
        : `<span class="text-emerald-400 text-[10px] flex items-center gap-1">
                             <svg class="w-3 h-3 fill-current" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                             ${durationStr}
                           </span>`
      }
                      <span class="text-slate-500 text-[10px]">${step.timestamp || ''}</span>
                      ${step.output ? `
                        <button type="button" onclick="toggleStepOutput('${outId}')" class="text-[10px] text-cyan-400 hover:text-white px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/60 hover:bg-cyan-800 transition flex items-center gap-1">
                          <span>Log output</span>
                          <svg id="arrow_${outId}" class="w-3 h-3 fill-none stroke-current transition-transform duration-200 ${autoShowOutput ? 'rotate-180' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      ` : ''}
                    </div>
                  </div>
                  ${cmdText ? `
                    <div class="px-2.5 py-1.5 rounded bg-[#060a12] border border-[#1e3458] font-mono text-[11px] text-slate-200 flex items-start gap-1.5 select-all overflow-x-auto shadow-inner">
                      <span class="text-cyan-400 font-bold select-none shrink-0">$</span>
                      <span class="break-all whitespace-pre-wrap text-emerald-300 font-mono">${escapeHtml(cmdText)}</span>
                    </div>
                  ` : ''}
                  ${!isDone ? `
                    <div class="px-2.5 py-1 rounded bg-cyan-950/40 border border-cyan-800/50 flex items-center justify-between text-[10.5px] text-cyan-300 font-mono">
                      <span class="flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
                        <span>Đang thực thi lệnh trên AI Terminal ngầm...</span>
                      </span>
                      <span class="text-cyan-400/80 animate-pulse text-[10px]">Realtime Streaming</span>
                    </div>
                  ` : ''}
                  ${step.output ? `
                    <div id="${outId}" class="${autoShowOutput ? '' : 'hidden'} mt-1.5 p-2 rounded-lg bg-white dark:bg-[#060a12] border border-slate-200 dark:border-[#1e3458] text-[11px] font-mono max-h-64 overflow-y-auto shadow-sm">
                      ${formatStepOutputWithDiff(step.output)}
                    </div>
                  ` : ''}
                </div>
              `;
  }).join('')}
          </div>
        </div>
      `;
}

// ---------------- FEED FILTER TABS & RENDERING ----------------
function renderFeedFilterTabs() {
  const container = document.getElementById('feedTaskFilterTabs');
  if (!container) return;

  const tabs = [
    { id: 'all', label: `Tất cả (${parallelTasks.length})` },
    ...parallelTasks.map((t, idx) => ({ id: t.id, name: t.name, status: t.status, type: t.type, idx: idx + 1 }))
  ];

  container.innerHTML = tabs.map(tab => {
    if (tab.id === 'all') {
      const isActive = activeFeedFilter === 'all';
      return `
        <button type="button" onclick="setFeedFilter('all')" title="Hiển thị tất cả"
          class="px-2.5 py-1 text-[11px] rounded font-medium transition flex items-center gap-1 shrink-0 select-none ${isActive
          ? 'active-feed-filter bg-[#199cff] text-white shadow-sm font-bold'
          : 'text-slate-300 hover:text-white hover:bg-white/5'
        }">
          <span>${escapeHtml(tab.label)}</span>
        </button>
      `;
    }

    const isActive = activeFeedFilter === tab.id;
    const isEditing = editingTaskId === tab.id;
    const { prefix, subName } = parseTaskName(tab.name, tab.idx);
    const isRunning = tab.status === 'running';
    const isQueued = tab.status === 'queued';
    const isDone = tab.status === 'completed' || tab.status === 'done';
    const isStopped = tab.status === 'stopped';

    let badge = '';
    if (isRunning) {
      badge = '<span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping ml-0.5" title="Đang chạy"></span>';
    } else if (isQueued) {
      badge = '<span class="w-1.5 h-1.5 rounded-full bg-amber-400 ml-0.5" title="Đang chờ trong hàng đợi"></span>';
    } else if (isDone) {
      badge = '<span class="text-emerald-400 text-[10px] font-bold ml-0.5" title="Đã hoàn tất">✓</span>';
    } else if (isStopped) {
      badge = '<span class="text-rose-400 text-[9px] font-bold ml-0.5" title="Đã dừng">■</span>';
    }

    return `
      <button type="button" onclick="setFeedFilter('${tab.id}')"
        title="Bấm để lọc theo tác vụ này"
        class="px-2.5 py-1 text-[11px] rounded font-medium transition flex items-center gap-1 shrink-0 select-none ${isActive
        ? 'active-feed-filter bg-[#199cff] text-white shadow-sm font-bold'
        : 'text-slate-300 hover:text-white hover:bg-white/5'
      }">
        <span class="max-w-[150px] truncate"><span class="opacity-80">${escapeHtml(prefix)}</span> ${escapeHtml(subName)}</span>
        ${badge}
      </button>
    `;
  }).join('');
}

function setFeedFilter(filterId) {
  activeFeedFilter = filterId;
  if (filterId !== 'all') {
    activeTaskId = filterId;
    loadTaskToForm(filterId);
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    updateTaskActionButtons();
  }
  renderFeedFilterTabs();
  pollStatus();
}

function renderFeedView(data) {
  const feed = document.getElementById('taskFeed');
  if (!feed) return;

  const serverTasks = data.tasks || {};
  const taskEntries = Object.entries(serverTasks);

  let sessionsToRender = [];

  if (activeFeedFilter === 'all') {
    if (taskEntries.length > 0) {
      sessionsToRender = taskEntries.filter(([tid, t]) => t.session).map(([tid, t]) => ({
        ...t.session,
        _taskTitle: t.title,
        _taskId: tid,
        _mode: t.mode,
        _statusText: t.status_text
      }));
    } else if (data.current_session) {
      const curTid = data.current_session.task_id || data.current_session.id || 'task_1';
      sessionsToRender = [{
        ...data.current_session,
        _taskTitle: data.current_session.title || (data.mode === 'fixbug' ? 'Fix bug' : 'Làm task'),
        _taskId: curTid,
        _mode: data.mode,
        _statusText: data.status_text
      }];
    }
  } else {
    const found = serverTasks[activeFeedFilter];
    if (found && found.session) {
      sessionsToRender = [{
        ...found.session,
        _taskTitle: found.title,
        _taskId: activeFeedFilter,
        _mode: found.mode,
        _statusText: found.status_text
      }];
    }
  }

  // Luôn dọn dẹp các wrapper session của task khác đang không thuộc phạm vi hiển thị
  const allowedWrapIds = new Set();
  sessionsToRender.forEach(s => allowedWrapIds.add('sessWrap_' + (s._taskId || s.id)));

  Array.from(feed.querySelectorAll('[id^="sessWrap_"]')).forEach(el => {
    if (!allowedWrapIds.has(el.id)) {
      el.remove();
    }
  });

  if (sessionsToRender.length === 0) {
    if (!document.getElementById('taskEmptyState')) {
      feed.innerHTML = `
        <div id="taskEmptyState" class="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
          <h3 id="taskEmptyTitle" class="text-xs font-semibold text-slate-300">Chưa có tác vụ nào đang chạy</h3>
          <p id="taskEmptySubtitle" class="text-xs text-slate-400 max-w-sm mt-1">Cấu hình thông tin bên trái và nhấn "Bắt đầu tác vụ".</p>
        </div>
      `;
    }
    return;
  }

  const empty = document.getElementById('taskEmptyState');
  if (empty) empty.remove();

  sessionsToRender.forEach(sess => {
    const sessWrapId = 'sessWrap_' + (sess._taskId || sess.id);
    let sessWrap = document.getElementById(sessWrapId);
    if (!sessWrap) {
      sessWrap = document.createElement('div');
      sessWrap.id = sessWrapId;
      sessWrap.className = 'space-y-3 mb-6 p-3.5 rounded-lg border border-[#244170] bg-[#0c1527]';
      feed.appendChild(sessWrap);
    }

    const sessHeaderId = 'sessHeader_' + (sess._taskId || sess.id);
    let sessHeader = document.getElementById(sessHeaderId);
    if (!sessHeader) {
      sessHeader = document.createElement('div');
      sessHeader.id = sessHeaderId;
      sessHeader.className = 'bg-[#101e38] border border-[#244170] rounded-md p-3 shadow-sm';
      sessWrap.appendChild(sessHeader);
    }

    const isFix = (sess.type === 'FIX_BUG' || sess._mode === 'fixbug');
    const isRefactor = (sess.type === 'REFACTOR' || sess._mode === 'refactor' || (sess._taskTitle && sess._taskTitle.toLowerCase().includes('refactor')));
    let badgeClass = 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30';
    let badgeLabel = 'TASK';
    if (isFix) {
      badgeClass = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
      badgeLabel = 'FIX BUG';
    } else if (isRefactor) {
      badgeClass = 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
      badgeLabel = 'REFACTOR';
    }
    const titleBadge = sess._taskTitle || (isFix ? 'Fix Bug' : (isRefactor ? 'Refactor Code' : 'Làm Task'));
    const rawScope = String(sess.scope || sess.target || 'both').toLowerCase();
    let scopeBadge = 'Cả hai (FE & BE)';
    if (rawScope === 'fe') scopeBadge = 'FE (Frontend)';
    else if (rawScope === 'be') scopeBadge = 'BE (Backend)';
    const skillBadge = sess.skill || 'Tự động';
    const isCompleted = sess.status === 'COMPLETED';
    const isQueued = sess.status === 'QUEUED';
    const isStopped = sess.status === 'STOPPED';
    const convertedCmd = sess.converted_prompt || '';

    let statusHtml = '<span class="text-cyan-400 flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>Đang chạy</span>';
    if (isCompleted) {
      statusHtml = '<span class="text-emerald-400 font-bold">✓ Hoàn tất</span>';
    } else if (isQueued) {
      statusHtml = `<span class="text-amber-300 font-bold flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>${escapeHtml(sess._statusText || 'Đang chờ trong hàng đợi')}</span>`;
    } else if (isStopped) {
      statusHtml = '<span class="text-rose-400 font-bold">■ Đã dừng</span>';
    }

    sessHeader.innerHTML = `
          <div class="flex items-center justify-between gap-2 mb-1.5">
            <div class="flex items-center gap-2 min-w-0">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${badgeClass}">${badgeLabel}</span>
              <span class="text-xs font-bold text-white truncate">${escapeHtml(titleBadge)}</span>
            </div>
            <div class="flex items-center gap-2 text-[10px] font-sans text-white/90 shrink-0">
              ${statusHtml}
              <button type="button" onclick="removeParallelTask('${sess._taskId || sess.task_id || sess.id}', event)" class="p-1 rounded bg-white/15 hover:bg-white/25 text-white border border-white/25 text-[10px] flex items-center justify-center transition cursor-pointer" title="Xóa tác vụ này khỏi Diễn biến thực thi">
                <svg class="w-3.5 h-3.5 fill-current text-white" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
              </button>
            </div>
          </div>
          ${(sess.prompt || sess.description) ? `
            <div class="text-xs text-slate-100 font-medium mt-1 leading-relaxed">${escapeHtml(sess.prompt || sess.description)}</div>
          ` : ''}
          ${sess.error_log ? `<pre class="mt-2 bg-black/60 p-2 rounded text-[11px] text-slate-300 font-mono overflow-x-auto border border-[#244170] max-h-32">${escapeHtml(sess.error_log)}</pre>` : ''}
        `;

    const turns = sess.turns || [];
    const isSessRunning = Boolean(sess._isRunning) && sess.status !== 'COMPLETED' && sess.status !== 'STOPPED';
    turns.forEach((t, i) => {
      const cardId = 'turnCard_' + (sess._taskId || sess.id) + '_' + i;
      let card = document.getElementById(cardId);
      const isFe = t.speaker === 'fe';
      const isLatestTurn = (i === turns.length - 1);
      const isStreaming = Boolean(t.is_streaming) && isSessRunning && isLatestTurn;
      const streamingIndicator = isStreaming ? '<span class="inline-flex items-center gap-1.5 text-[11px] text-cyan-400 font-mono"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>Đang xử lý trên AI Terminal...</span>' : '';
      const turnFiles = (t.changed_files && t.changed_files.length > 0) ? t.changed_files : (sess.changed_files || []);
      const bodyContent = t.content ? safeMarkdown(t.content, turnFiles) : '<div class="text-slate-400 italic text-xs">Đang thực thi lệnh trên AI Terminal ngầm và chuẩn bị phản hồi...</div>';
      const stepLogsHtml = renderStepLogsHtml(t.step_logs, sess._taskId || sess.id, i);
      const changedFilesHtml = renderChangedFilesHtml(t.changed_files, sess._taskId || sess.id, i);

      if (!card) {
        card = document.createElement('div');
        card.id = cardId;
        card.className = `rounded-lg border p-3.5 shadow-sm transition ${isFe ? 'bg-[#0f172a] border-cyan-800/60' : 'bg-[#091518] border-emerald-800/60'}`;
        sessWrap.appendChild(card);
      }

      // Xác định lượt mới nhất: các lượt đã xong tự động đóng lại, chỉ lượt mới nhất mở ra
      const isLatestTurn = (i === turns.length - 1);
      let isCollapsed;
      if (_userInteractedTurnCards.has(cardId)) {
        isCollapsed = _userInteractedTurnCards.get(cardId);
      } else {
        isCollapsed = !isLatestTurn;
      }

      if (isCollapsed) {
        _collapsedTurnCards.add(cardId);
      } else {
        _collapsedTurnCards.delete(cardId);
      }

      const stepBoxId = `stepBox_${sess._taskId || sess.id}_${i}`;
      const diffBoxId = `diffBox_${sess._taskId || sess.id}_${i}`;
      const isStepCollapsed = _collapsedStepBoxes.has(stepBoxId);
      const isDiffCollapsed = _collapsedDiffBoxes.has(diffBoxId);

      const changesSig = (t.changed_files || []).map(cf => `${cf.path}:${cf.status}:${cf.additions}:${cf.deletions}`).join('|');
      const currentSig = `${(t.content || '').length}_${(t.step_logs || []).length}_${t.elapsed_sec}_${isStreaming}_${(t.step_logs || []).map(s => s.state + (s.output ? s.output.length : 0)).join(',')}_${changesSig}_${isCollapsed}_${isStepCollapsed}_${isDiffCollapsed}`;
      if (card.dataset.sig !== currentSig) {
        card.dataset.sig = currentSig;
        card.innerHTML = `
              <div onclick="toggleTurnCollapse('${cardId}', event)"
                class="flex items-center justify-between text-xs font-semibold cursor-pointer select-none py-1 px-1.5 -mx-1.5 rounded hover:bg-white/5 transition ${isFe ? 'text-cyan-400' : 'text-emerald-400'}">
                <span class="flex items-center gap-2 min-w-0">
                  <button type="button" onclick="toggleTurnCollapse('${cardId}', event)"
                    class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer shrink-0"
                    title="${isCollapsed ? 'Nhấp để mở rộng lượt này' : 'Nhấp để thu gọn lượt này'}">
                    <svg id="turnChevron_${cardId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isCollapsed ? '-rotate-90' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  <span class="font-bold truncate">${escapeHtml(t.label || (isFe ? 'Frontend Agent' : 'Backend Agent'))} • Lượt ${t.round}/${sess.total_rounds || 1}</span>
                  ${streamingIndicator}
                </span>
                <span class="text-slate-400 text-[10px] font-mono shrink-0 ml-2">${t.timestamp || ''} (${formatDuration(t.elapsed_sec || 0)})</span>
              </div>
              <div id="turnBody_${cardId}" class="turn-body-content mt-2.5 ${isCollapsed ? 'hidden' : ''}">
                ${stepLogsHtml}
                ${changedFilesHtml}
                <div class="markdown-body text-[13px] text-slate-200 leading-[1.82] tracking-wide overflow-x-auto">${bodyContent}</div>
              </div>
            `;
      }
    });

    const taskIdKey = sess._taskId || sess.task_id || sess.id;
    const contBoxId = 'sessContinueBox_' + taskIdKey;
    let contBox = document.getElementById(contBoxId);
    if (isCompleted || isStopped) {
      if (!contBox) {
        contBox = document.createElement('div');
        contBox.id = contBoxId;
        contBox.className = 'mt-3 pt-3 border-t border-[#244170] flex flex-col gap-2';
        contBox.innerHTML = `
              <div class="flex items-center justify-between text-[11px] font-semibold text-cyan-300">
                <span>Tiếp tục task trên AI Terminal ngầm đang chạy</span>
                <span class="text-[10px] font-mono text-slate-400">Giữ nguyên ngữ cảnh & lịch sử phiên</span>
              </div>
              <div class="flex items-center gap-2">
                <input id="continueInput_${taskIdKey}" type="text"
                  placeholder="Nhập yêu cầu tiếp theo (hoặc để trống để AI tiếp tục hoàn thiện task)..."
                  onkeydown="if(event.key==='Enter'){event.preventDefault();continueTaskFromFeed('${taskIdKey}');}"
                  class="flex-1 bg-[#0b1322] border border-[#244170] rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-[#199cff]" />
                <button type="button" onclick="continueTaskFromFeed('${taskIdKey}')"
                  class="px-3.5 py-1.5 rounded bg-[#199cff] hover:bg-[#1585d8] text-white text-xs font-bold shrink-0 flex items-center gap-1.5 shadow-sm transition" style="color: #ffffff !important;">
                  <span class="text-white font-bold" style="color: #ffffff !important;">▶ Tiếp tục task</span>
                </button>
              </div>
            `;
        sessWrap.appendChild(contBox);
      } else if (contBox.parentElement === sessWrap && sessWrap.lastElementChild !== contBox) {
        sessWrap.appendChild(contBox);
      }
    } else if (contBox) {
      contBox.remove();
    }
  });
}

async function continueTaskFromFeed(taskId) {
  let task = parallelTasks.find(t => t.id === taskId);
  if (!task) {
    activeTaskId = taskId;
    task = parallelTasks[0];
  }
  if (!task) return;
  const inputEl = document.getElementById('continueInput_' + taskId);
  const followUp = inputEl ? inputEl.value.trim() : '';
  if (followUp) {
    if (!task.original_prompt && task.prompt) {
      task.original_prompt = task.prompt;
    }
    task.prompt = followUp;
    if (inputEl) inputEl.value = '';
  } else if (!task.prompt) {
    task.prompt = 'Tiếp tục kiểm tra và sửa hoàn thiện code cho task này.';
  }
  activeTaskId = task.id;
  loadTaskToForm(task.id);
  await startSingleTaskById(task.id);
}

// ---------------- STATUS POLLING & QUEUE RECOVERY ----------------
async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    // Khôi phục hàng đợi (Queue) từ server khi mới tải lại trang (F5)
    if (!_initialQueueRestored && Array.isArray(data.queue) && data.queue.length > 0) {
      _initialQueueRestored = true;
      parallelTasks = data.queue.map((q, idx) => ({
        id: q.id || ('task_' + (idx + 1)),
        name: q.title || q.name || `Task ${idx + 1}: ${(q.mode || q.type) === 'fixbug' ? 'Fix bug' : 'Tính năng mới'}`,
        type: q.mode || q.type || 'task',
        target: q.target || q.scope || 'both',
        skills: Array.isArray(q.skills) ? q.skills : (q.skills ? String(q.skills).split(',').map(s => s.trim()).filter(Boolean) : []),
        prompt: q.prompt || q.fix_desc || '',
        error_log: q.error_log || q.fix_err || '',
        status: q.status === 'done' ? 'completed' : (q.status || 'idle'),
        sessionId: null
      }));
      const runningOrQueued = parallelTasks.find(t => t.status === 'running' || t.status === 'queued');
      activeTaskId = runningOrQueued ? runningOrQueued.id : parallelTasks[0].id;
      loadTaskToForm(activeTaskId);
    } else {
      _initialQueueRestored = true;
    }

    if (data.tasks) {
      const serverTaskIds = new Set(Object.keys(data.tasks));
      const serverQueueIds = new Set((data.queue || []).map(q => q.id));

      // Dọn dẹp các task đã xóa trên server khỏi parallelTasks
      parallelTasks = parallelTasks.filter(t => {
        if (!t.sessionId && t.status === 'idle') return true;
        return serverTaskIds.has(t.id) || serverQueueIds.has(t.id);
      });

      if (parallelTasks.length === 0) {
        parallelTasks = [{
          id: 'task_' + Date.now(),
          name: 'Task 1: Tính năng mới',
          type: 'task',
          target: 'both',
          skills: [],
          prompt: '',
          error_log: '',
          status: 'idle',
          sessionId: null
        }];
        activeTaskId = parallelTasks[0].id;
        loadTaskToForm(activeTaskId);
      }

      Object.entries(data.tasks).forEach(([tid, tinfo]) => {
        let task = parallelTasks.find(t => t.id === tid);
        const qStat = tinfo.queue_status || (tinfo.is_running ? 'running' : 'done');
        const mappedStatus = tinfo.is_running
          ? 'running'
          : (qStat === 'queued'
            ? 'queued'
            : (tinfo.session && tinfo.session.status === 'COMPLETED'
              ? 'completed'
              : (tinfo.session && tinfo.session.status === 'STOPPED' ? 'stopped' : 'idle')));

        if (!task) {
          const rawSkill = (tinfo.session && tinfo.session.skill) || '';
          task = {
            id: tid,
            name: tinfo.title || `Task (${tinfo.mode})`,
            type: tinfo.mode || 'task',
            target: (tinfo.session && (tinfo.session.target || tinfo.session.scope)) || 'both',
            skills: rawSkill ? rawSkill.split(',').map(s => s.trim()).filter(Boolean) : [],
            prompt: (tinfo.session && (tinfo.session.prompt || tinfo.session.description)) || '',
            error_log: (tinfo.session && tinfo.session.error_log) || '',
            status: mappedStatus,
            sessionId: tinfo.session ? tinfo.session.id : null
          };
          parallelTasks.push(task);
        } else {
          task.status = mappedStatus;
          if (tinfo.session) task.sessionId = tinfo.session.id;
        }
      });
    }

    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    renderFeedFilterTabs();
    updateTaskActionButtons();

    const taskTyping = document.getElementById('taskTypingIndicator');
    if (data.is_running) {
      if (taskTyping) {
        taskTyping.classList.remove('hidden');
        const typingText = document.getElementById('taskTypingText');
        if (typingText) typingText.innerText = data.status_text || 'Đang thực thi tác vụ trên AI Terminal...';
      }
    } else {
      if (taskTyping) taskTyping.classList.add('hidden');
    }

    renderFeedView(data);
    if (typeof updateNotifBadgeUI === 'function') updateNotifBadgeUI();

  } catch (e) {
    console.warn('pollStatus error:', e);
  }
}

// ---------------- DIAGRAM & MODULE ACTIONS ----------------
let currentModules = DIAGRAM_MODULES;
let diagramScale = 1.0;
let diagramPanX = 0;
let diagramPanY = 0;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;
let panZoomInitialized = false;

function renderDiagram() {
  initDiagramPanZoom();
  fetchDiagramData(false);
}

function updateDiagramTransform() {
  const canvas = document.getElementById('diagramCanvas');
  const zoomText = document.getElementById('diagramZoomLevel');
  if (canvas) {
    canvas.style.transform = `translate(${diagramPanX}px, ${diagramPanY}px) scale(${diagramScale})`;
  }
  if (zoomText) {
    zoomText.innerText = Math.round(diagramScale * 100) + '%';
  }
}

function diagramZoomIn() {
  diagramScale = Math.min(2.5, +(diagramScale + 0.15).toFixed(2));
  updateDiagramTransform();
}

function diagramZoomOut() {
  diagramScale = Math.max(0.35, +(diagramScale - 0.15).toFixed(2));
  updateDiagramTransform();
}

function diagramZoomReset() {
  diagramScale = 1.0;
  diagramPanX = 0;
  diagramPanY = 0;
  updateDiagramTransform();
}

function diagramFitView() {
  const viewport = document.getElementById('diagramViewport');
  const canvas = document.getElementById('diagramCanvas');
  const svg = canvas ? canvas.querySelector('svg') : null;
  if (!viewport || !canvas || !svg) return;

  const vRect = viewport.getBoundingClientRect();
  const sRect = svg.getBoundingClientRect();
  const rawWidth = sRect.width / diagramScale;
  const rawHeight = sRect.height / diagramScale;

  if (rawWidth > 0 && rawHeight > 0) {
    const fitScale = Math.min(1.1, Math.max(0.4, Math.min((vRect.width - 60) / rawWidth, (vRect.height - 60) / rawHeight)));
    diagramScale = +fitScale.toFixed(2);
    diagramPanX = 0;
    diagramPanY = 0;
    updateDiagramTransform();
  }
}

function initDiagramPanZoom() {
  if (panZoomInitialized) return;
  const viewport = document.getElementById('diagramViewport');
  if (!viewport) return;
  panZoomInitialized = true;

  viewport.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('.node')) return; // Cho phép click node
    isPanning = true;
    panStartX = e.clientX - diagramPanX;
    panStartY = e.clientY - diagramPanY;
    viewport.classList.add('cursor-grabbing');
    viewport.classList.remove('cursor-grab');
  });

  window.addEventListener('mousemove', (e) => {
    if (!isPanning) return;
    diagramPanX = e.clientX - panStartX;
    diagramPanY = e.clientY - panStartY;
    updateDiagramTransform();
  });

  window.addEventListener('mouseup', () => {
    if (isPanning) {
      isPanning = false;
      const vp = document.getElementById('diagramViewport');
      if (vp) {
        vp.classList.remove('cursor-grabbing');
        vp.classList.add('cursor-grab');
      }
    }
  });

  viewport.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.12 : -0.12;
    diagramScale = Math.min(2.5, Math.max(0.35, +(diagramScale + delta).toFixed(2)));
    updateDiagramTransform();
  }, { passive: false });
}

function bindMermaidNodeClicks() {
  const nodeMap = {
    'BOOKING_BEDROOM': { id: 'booking-bedroom', name: 'Phòng & Giường (BedRoom)' },
    'BED': { id: 'booking-bedroom', name: 'Phòng & Giường (BedRoom)' },
    'POS_CASHIER': { id: 'pos-cashier', name: 'Thu ngân & Hóa đơn (POS Invoice)' },
    'INV': { id: 'pos-cashier', name: 'Thu ngân & Hóa đơn (POS Invoice)' },
    'CALENDAR_SCHEDULE': { id: 'calendar-schedule', name: 'Lịch hẹn (Booking)' },
    'CUSTOMER_CRM': { id: 'customer-crm', name: 'Khách hàng (Customer CRM)' },
    'CUST': { id: 'customer-crm', name: 'Khách hàng (Customer CRM)' },
    'WAREHOUSE_INVENTORY': { id: 'warehouse-inventory', name: 'Kho hàng (Warehouse)' },
    'WH': { id: 'warehouse-inventory', name: 'Kho hàng (Warehouse)' },
    'COMMISSION_SETUP': { id: 'commission-setup', name: 'Hoa hồng (Commission)' },
    'COMM': { id: 'commission-setup', name: 'Hoa hồng (Commission)' },
    'REVENUE_EXPENDITURE': { id: 'revenue-expenditure', name: 'Thu chi & Sổ quỹ (Cashbook)' },
    'CASH': { id: 'revenue-expenditure', name: 'Thu chi & Sổ quỹ (Cashbook)' },
    'SERVICE_PACKAGE_COMBO': { id: 'service-package-combo', name: 'Gói liệu trình (Package)' },
    'PKG': { id: 'service-package-combo', name: 'Gói liệu trình (Package)' },
    'TAX_EINVOICE': { id: 'tax-einvoice', name: 'Hóa đơn điện tử (E-Invoice)' },
    'EINV': { id: 'tax-einvoice', name: 'Hóa đơn điện tử (E-Invoice)' },
    'PAYROLL_TIMESHEET': { id: 'payroll-timesheet', name: 'Chấm công & Lương (Payroll)' },
    'TIME': { id: 'payroll-timesheet', name: 'Chấm công & Lương (Payroll)' },
    'REPORT_ANALYTICS': { id: 'report-analytics', name: 'Báo cáo & Thống kê (Analytics)' },
    'REP': { id: 'report-analytics', name: 'Báo cáo & Thống kê (Analytics)' }
  };

  const svg = document.querySelector('#mermaidDiagram svg');
  if (!svg || typeof svg.querySelectorAll !== 'function') return;

  const nodes = svg.querySelectorAll('.node');
  nodes.forEach(node => {
    node.style.cursor = 'pointer';
    node.setAttribute('title', 'Nhấn để cuộn nhanh đến chi tiết module bên dưới');

    node.onclick = (e) => {
      e.stopPropagation();
      const nodeText = (node.id + ' ' + (node.textContent || '')).toUpperCase();
      let matched = null;
      let side = 'both';

      if (nodeText.includes('FE_') || nodeText.includes('FRONTEND') || nodeText.includes('BUSINESS/')) side = 'fe';
      else if (nodeText.includes('BE_') || nodeText.includes('BACKEND') || nodeText.includes('CONTROLLER')) side = 'be';

      for (const [key, val] of Object.entries(nodeMap)) {
        if (nodeText.includes(key)) {
          matched = val;
          break;
        }
      }

      if (matched) {
        highlightAndScrollToModule(matched.id, side, matched.name);
      }
    };
  });
}

function showToast(msg) {
  if (!msg) return;
  msg = String(msg).replace(/⚡/g, '').trim();
  let toast = document.getElementById('studioToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'studioToast';
    document.body.appendChild(toast);
  }
  toast.className = 'fixed top-5 left-1/2 -translate-x-1/2 z-50 bg-white text-[#0f172a] border border-slate-300 shadow-2xl px-4 py-2.5 rounded-lg text-xs font-medium flex items-start gap-2.5 transition-all duration-200 transform -translate-y-6 opacity-0 pointer-events-none max-w-lg';
  toast.style.backgroundColor = '#ffffff';
  toast.style.color = '#0f172a';
  toast.innerHTML = `
        <svg class="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span class="whitespace-pre-line leading-relaxed text-[#0f172a] font-medium">${escapeHtml(msg)}</span>
      `;
  toast.classList.remove('-translate-y-6', 'opacity-0');
  toast.classList.add('translate-y-0', 'opacity-100');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.classList.remove('translate-y-0', 'opacity-100');
    toast.classList.add('-translate-y-6', 'opacity-0');
  }, 3500);
}

async function renderDynamicMermaid(code) {
  const container = document.getElementById('mermaidDiagram');
  if (!container || !code) return;
  try {
    const renderId = 'mermaid_svg_' + Date.now();
    const { svg } = await mermaid.render(renderId, code);
    container.innerHTML = svg;
    mermaidRendered = true;
    setTimeout(bindMermaidNodeClicks, 200);
    setTimeout(diagramFitView, 250);
  } catch (err) {
    console.warn('Lỗi vẽ lại Mermaid diagram:', err);
  }
}

async function doManualRescanDiagram() {
  await fetchDiagramData(true);
  showToast('Đã quét lại Source Code và cập nhật sơ đồ.');
}

async function fetchDiagramData(force = false) {
  const spinner = document.getElementById('rescanSpinner');
  const btn = document.getElementById('btnRescanDiagram');
  if (force && spinner) spinner.classList.add('animate-spin');
  if (force && btn) btn.disabled = true;

  try {
    const res = await fetch('/api/diagram-data' + (force ? '?force=1' : ''));
    if (res.ok) {
      const data = await res.json();
      if (data && data.modules) {
        currentModules = data.modules;
        window.diagramData = data;
        renderDiagramColumns(currentModules);

        const feBadge = document.getElementById('gitFeBranchBadge');
        const beBadge = document.getElementById('gitBeBranchBadge');
        const scanTime = document.getElementById('scanTimestamp');
        if (feBadge) feBadge.innerText = `${data.fe_branch} (${data.fe_commit})`;
        if (beBadge) beBadge.innerText = `${data.be_branch} (${data.be_commit})`;
        if (scanTime) scanTime.innerText = data.scanned_at || '';

        // Tự động vẽ lại sơ đồ Mermaid với code thực tế của nhánh mới
        if (data.mermaid_code) {
          await renderDynamicMermaid(data.mermaid_code);
        }
      }
    }
  } catch (err) {
    console.error('Lỗi khi nạp dữ liệu diagram:', err);
  } finally {
    if (spinner) spinner.classList.remove('animate-spin');
    if (btn) btn.disabled = false;
    setTimeout(bindMermaidNodeClicks, 300);
  }
}

function getMethodBadgeClass(m) {
  const method = String(m || '').toUpperCase().replace('HTTP', '');
  if (method === 'GET') return 'bg-blue-950/90 text-blue-400 border-blue-700/80';
  if (method === 'POST') return 'bg-emerald-950/90 text-emerald-400 border-emerald-700/80';
  if (method === 'PUT') return 'bg-amber-950/90 text-amber-400 border-amber-700/80';
  if (method === 'DELETE') return 'bg-rose-950/90 text-rose-400 border-rose-700/80';
  return 'bg-purple-950/90 text-purple-300 border-purple-700/80';
}

function renderDiagramColumns(modules = currentModules) {
  const container = document.getElementById('moduleLookupList');
  if (!container) return;

  container.innerHTML = modules.map(m => `
        <div id="module-row-${m.id}" class="bg-[#101e38] border border-[#244170] hover:border-[#38bdf8] rounded-lg p-4 shadow-sm transition duration-150">
          <!-- Header: Module title and quick actions (Đã bỏ tag skill thừa) -->
          <div class="flex flex-wrap items-center justify-between gap-3 pb-2.5 mb-3 border-b border-[#244170]">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
              <h4 class="text-xs font-semibold text-white">${escapeHtml(m.title)}</h4>
            </div>
            <div class="flex items-center gap-1.5">
              <button onclick="quickActionTask('both', '${m.skill}', '${escapeHtml(m.title)}')" class="ant-btn text-xs h-[28px] px-2.5">
                <span>Làm task</span>
              </button>
              <button onclick="quickActionFixBug('both', '${m.skill}', '${escapeHtml(m.title)}')" class="ant-btn text-xs h-[28px] px-2.5">
                <span>Fix bug</span>
              </button>
            </div>
          </div>

          <!-- Sub-header 3 cột chuẩn justify-between: File Resource FE | Base Route API | Controller BE -->
          <div class="diagram-flow-grid mb-2.5 text-xs">
            <div id="fe-card-${m.id}" class="diagram-col-box bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5">
              <span class="text-[11px] font-semibold text-cyan-400 shrink-0">Frontend</span>
              <span class="text-[10.5px] font-mono text-cyan-300 truncate text-right" title="${escapeHtml(m.fe.resource)}">${escapeHtml(m.fe.resource)}</span>
            </div>
            <div class="hidden lg:block"></div>
            <div class="diagram-col-box bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5">
              <span class="text-[11px] font-semibold text-purple-300 shrink-0">API Contract</span>
              <span class="text-[10.5px] font-mono text-purple-300 bg-purple-950/80 px-2 py-0.5 rounded border border-purple-800/60 truncate text-right">${escapeHtml(m.api.route)}</span>
            </div>
            <div class="hidden lg:block"></div>
            <div id="be-card-${m.id}" class="diagram-col-box bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5">
              <span class="text-[11px] font-semibold text-emerald-400 shrink-0">Backend (.NET)</span>
              <span class="text-[10.5px] font-mono text-emerald-300 truncate text-right" title="${escapeHtml(m.be.controller)}">${escapeHtml(m.be.controller)}</span>
            </div>
          </div>

          <!-- Danh sách các hàng liên kết: Hàm call API ở Frontend ──► API (GET/POST/PUT/DELETE) ──► Hàm Backend -->
          <div class="space-y-2">
            ${(m.api.endpoints || []).map(ep => {
    const methodClass = getMethodBadgeClass(ep.method);
    const feFnName = ep.fe_func || 'fetchData';
    const beFnName = ep.be_action || 'ExecuteAction';
    return `
                <div class="diagram-flow-grid text-xs">
                  <!-- Cột 1: Hàm call API thực tế ở Frontend -->
                  <div class="diagram-col-box bg-[#0b1424] border border-[#1e365d] hover:border-cyan-400/70 rounded px-3 py-2 transition shadow-sm">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0"></span>
                      <span class="font-mono text-xs font-bold text-cyan-300 truncate" title="Hàm call API ở Frontend: ${escapeHtml(feFnName)}()">${escapeHtml(feFnName)}()</span>
                    </div>
                    <span class="px-1.5 py-0.2 rounded text-[8.5px] font-mono font-bold border ${methodClass} shrink-0">${escapeHtml(ep.method)}</span>
                  </div>

                  <!-- Mũi tên 1: Frontend ──► API (Màu chạy từ đầu mũi tên đến cuối mũi tên) -->
                  <div class="hidden lg:flex items-center justify-center px-0.5 select-none" aria-hidden="true">
                    <svg class="w-full h-6 overflow-visible" viewBox="0 0 76 24" fill="none">
                      <path d="M2 12 H66" stroke="rgba(56, 189, 248, 0.2)" stroke-width="2" stroke-linecap="round" />
                      <path d="M58 6 L68 12 L58 18" stroke="rgba(56, 189, 248, 0.25)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                      <path d="M2 12 H66" stroke="url(#flowGradFeToApi)" stroke-width="2.6" stroke-linecap="round" class="arrow-stream-line" />
                      <path d="M58 6 L68 12 L58 18" stroke="url(#flowGradFeToApi)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" class="arrow-head-fe-api" />
                      <circle r="2.6" cy="12" fill="#38bdf8">
                        <animate attributeName="cx" from="2" to="68" dur="1.2s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.88;1" dur="1.2s" repeatCount="indefinite" />
                      </circle>
                    </svg>
                  </div>

                  <!-- Cột 2: API Contract (GET / POST / PUT / DELETE) -->
                  <div class="diagram-col-box bg-[#121c33] border border-purple-800/60 hover:border-purple-400/80 rounded px-3 py-2 transition shadow-sm min-w-0">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold border ${methodClass} shrink-0">${escapeHtml(ep.method)}</span>
                      <span class="font-mono text-xs font-semibold text-slate-100 truncate" title="${escapeHtml(ep.path)}">${escapeHtml(ep.path)}</span>
                    </div>
                    <span class="text-[10px] text-slate-400 truncate hidden sm:inline shrink-0 text-right" title="${escapeHtml(ep.note)}">${escapeHtml(ep.note)}</span>
                  </div>

                  <!-- Mũi tên 2: API ──► Backend (Màu chạy từ đầu mũi tên đến cuối mũi tên) -->
                  <div class="hidden lg:flex items-center justify-center px-0.5 select-none" aria-hidden="true">
                    <svg class="w-full h-6 overflow-visible" viewBox="0 0 76 24" fill="none">
                      <path d="M2 12 H66" stroke="rgba(16, 185, 129, 0.2)" stroke-width="2" stroke-linecap="round" />
                      <path d="M58 6 L68 12 L58 18" stroke="rgba(16, 185, 129, 0.25)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                      <path d="M2 12 H66" stroke="url(#flowGradApiToBe)" stroke-width="2.6" stroke-linecap="round" class="arrow-stream-line" />
                      <path d="M58 6 L68 12 L58 18" stroke="url(#flowGradApiToBe)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" class="arrow-head-api-be" />
                      <circle r="2.6" cy="12" fill="#10b981">
                        <animate attributeName="cx" from="2" to="68" dur="1.2s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.88;1" dur="1.2s" repeatCount="indefinite" />
                      </circle>
                    </svg>
                  </div>

                  <!-- Cột 3: Hàm xử lý API ở Backend (.NET) -->
                  <div class="diagram-col-box bg-[#0b1424] border border-[#1e365d] hover:border-emerald-400/70 rounded px-3 py-2 transition shadow-sm">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
                      <span class="font-mono text-xs font-bold text-emerald-300 truncate" title="Hàm Backend: ${escapeHtml(beFnName)}()">${escapeHtml(beFnName)}()</span>
                    </div>
                    <span class="text-[10px] font-mono text-emerald-400/80 shrink-0">Action</span>
                  </div>
                </div>
              `;
  }).join('')}
          </div>
        </div>
      `).join('');

  filterDiagramModules();
}

function filterDiagramModules() {
  const query = (document.getElementById('diagramSearchInput')?.value || '').toLowerCase().trim();
  const emptyEl = document.getElementById('diagramModuleEmpty');
  const countEl = document.getElementById('diagramMatchCount');
  let matchedCount = 0;

  currentModules.forEach(m => {
    const row = document.getElementById('module-row-' + m.id);
    if (!row) return;

    if (!query) {
      row.classList.remove('hidden');
      matchedCount++;
      return;
    }

    const text = [
      m.title,
      m.skill,
      m.fe?.path,
      m.fe?.resource,
      m.fe?.desc,
      ...(m.fe?.imports || []),
      ...(m.fe?.exports || []),
      m.api?.route,
      ...(m.api?.endpoints || []).map(ep => `${ep.method} ${ep.path} ${ep.fe_func} ${ep.be_action} ${ep.note}`),
      m.be?.path,
      m.be?.controller,
      m.be?.desc,
      ...(m.be?.injections || []),
      ...(m.be?.links || []),
      ...(m.be?.exports || [])
    ].filter(Boolean).join(' ').toLowerCase();

    if (text.includes(query)) {
      row.classList.remove('hidden');
      matchedCount++;
    } else {
      row.classList.add('hidden');
    }
  });

  if (countEl) {
    countEl.textContent = `Hiển thị ${matchedCount}/${currentModules.length} modules`;
  }
  if (emptyEl) {
    if (matchedCount === 0) emptyEl.classList.remove('hidden');
    else emptyEl.classList.add('hidden');
  }
}

function highlightAndScrollToModule(moduleId, side, moduleTitle) {
  const row = document.getElementById('module-row-' + moduleId);
  const feCard = document.getElementById('fe-card-' + moduleId);
  const beCard = document.getElementById('be-card-' + moduleId);

  if (row) {
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    row.classList.add('ring-2', 'ring-cyan-400', 'border-cyan-400', 'shadow-2xl', 'shadow-cyan-500/20');
    setTimeout(() => {
      row.classList.remove('ring-2', 'ring-cyan-400', 'border-cyan-400', 'shadow-2xl', 'shadow-cyan-500/20');
    }, 2500);

    const targetCard = side === 'fe' ? feCard : side === 'be' ? beCard : null;
    if (targetCard) {
      targetCard.classList.add('ring-2', 'ring-cyan-400', 'bg-cyan-950/30');
      setTimeout(() => {
        targetCard.classList.remove('ring-2', 'ring-cyan-400', 'bg-cyan-950/30');
      }, 2500);
    }

    showToast(`Đã định vị module: ${moduleTitle || moduleId}`);
  }
}

function quickActionTask(role, skillKey, targetName) {
  switchTab('task');
  setTaskActionType('task');
  const targetSelect = document.getElementById('taskTargetSelect');
  if (targetSelect) {
    targetSelect.value = role;
    onTaskTargetChange();
  }
  if (skillKey) {
    selectedTaskSkills = [skillKey];
    renderSkillPicker('task');
  }
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) {
    promptInput.value = `Thực hiện nghiệp vụ cho [${targetName}] ở phía ${role.toUpperCase()}: `;
    promptInput.focus();
  }
}

function quickActionFixBug(role, skillKey, targetName) {
  switchTab('task');
  setTaskActionType('fixbug');
  const targetSelect = document.getElementById('taskTargetSelect');
  if (targetSelect) {
    targetSelect.value = role;
    onTaskTargetChange();
  }
  if (skillKey) {
    selectedTaskSkills = [skillKey];
    renderSkillPicker('task');
  }
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) {
    promptInput.value = `Chẩn đoán và khắc phục lỗi cho [${targetName}] ở phía ${role.toUpperCase()}: `;
    promptInput.focus();
  }
  updateFixBugPromptPreview();
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ==========================================
// GIT BRANCH MANAGEMENT
// ==========================================
let gitInfoData = { fe: null, be: null };

function selectBranchChip(role, branchName) {
  const select = document.getElementById(role + 'BranchSelect');
  const filterInput = document.getElementById(role + 'BranchFilter');
  if (filterInput) filterInput.value = branchName;
  filterBranchList(role);
  if (select) select.value = branchName;
}

function copyToClipboard(text) {
  if (!text) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Đã sao chép: ' + text);
    }).catch(() => {
      showToast(text);
    });
  } else {
    showToast(text);
  }
}

function populateBaseBranchSelect(feBranches = [], beBranches = []) {
  const sel = document.getElementById('bothBaseBranchSelect');
  if (!sel) return;
  const currentVal = sel.value;

  const allBranches = new Set();
  feBranches.forEach(b => { if (b.name) allBranches.add(b.name); });
  beBranches.forEach(b => { if (b.name) allBranches.add(b.name); });

  const standardBases = ['staging', 'master', 'beta', 'main'];
  const orderedList = [];
  standardBases.forEach(b => {
    if (allBranches.has(b)) {
      orderedList.push(b);
      allBranches.delete(b);
    }
  });

  const otherBranches = Array.from(allBranches).sort();
  orderedList.push(...otherBranches);

  sel.innerHTML = '';
  orderedList.forEach(b => {
    const opt = document.createElement('option');
    opt.value = b;
    const tag = (b === 'staging' || b === 'master') ? ' (khuyên dùng)' : '';
    opt.textContent = `${b}${tag}`;
    sel.appendChild(opt);
  });

  if (currentVal && orderedList.includes(currentVal)) {
    sel.value = currentVal;
  } else if (orderedList.includes('staging')) {
    sel.value = 'staging';
  }
}

async function doCreateNewBranchBoth() {
  const branchInp = document.getElementById('bothBranchInput');
  const baseSel = document.getElementById('bothBaseBranchSelect');
  const newBranch = (branchInp?.value || '').trim();
  const baseBranch = (baseSel?.value || 'staging').trim();

  if (!newBranch) {
    await antdAlert({
      title: 'Thiếu tên nhánh mới',
      content: 'Vui lòng nhập tên nhánh mới muốn tạo (ví dụ: feat/nvt/EAS-12373/booking-bed-room-management).',
      type: 'error'
    });
    return;
  }

  const confirmed = await antdConfirm({
    title: 'Xác nhận tạo nhánh',
    content: `Bạn có chắc muốn tạo nhánh mới ${newBranch} từ nhánh ${baseBranch}`
  });
  if (!confirmed) return;

  const btn = document.getElementById('btnSwitchBoth');
  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang tạo nhánh...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: 'both',
        branch: newBranch,
        create_new: true,
        base_branch: baseBranch
      })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Tạo nhánh thành công.' : 'Lỗi khi tạo nhánh.'));

    await loadGitBranchInfo();
    await fetchDiagramData(true);
    if (activeTab === 'log') loadWorkLogs();

    if (data.success && branchInp) {
      branchInp.value = '';
    }
  } catch (err) {
    showToast('Lỗi kết nối khi tạo nhánh: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

async function loadGitBranchInfo() {
  try {
    const res = await fetch('/api/git/info');
    const data = await res.json();
    gitInfoData = data;
    renderGitBranchCard('fe', data.fe);
    renderGitBranchCard('be', data.be);
    populateBaseBranchSelect(data.fe?.branches || [], data.be?.branches || []);
  } catch (err) {
    showGitAlert('Lỗi tải thông tin Git: ' + err.message, false);
  }
}

function renderGitBranchCard(role, info) {
  if (!info) return;
  const isFe = role === 'fe';
  const branchBadge = document.getElementById(isFe ? 'feCurrentBranch' : 'beCurrentBranch');
  const commitInfo = document.getElementById(isFe ? 'feCommitInfo' : 'beCommitInfo');
  const statusInfo = document.getElementById(isFe ? 'feStatusInfo' : 'beStatusInfo');
  const workingStatus = document.getElementById(isFe ? 'feWorkingStatus' : 'beWorkingStatus');
  const syncBadge = document.getElementById(isFe ? 'feSyncBadge' : 'beSyncBadge');
  const btnPull = document.getElementById(isFe ? 'btnPullFe' : 'btnPullBe');
  const pullBtnText = document.getElementById(isFe ? 'fePullBtnText' : 'bePullBtnText');

  if (branchBadge) {
    branchBadge.textContent = info.current_branch || 'unknown';
  }
  if (commitInfo) {
    if (info.commit_hash) {
      commitInfo.textContent = `${info.commit_hash} - ${info.commit_message} (${formatRelativeDate(info.commit_date)})`;
      commitInfo.title = `${info.commit_hash} - ${info.commit_message}`;
    } else {
      commitInfo.textContent = 'Không có thông tin commit';
    }
  }
  if (statusInfo) {
    if (info.dirty_count > 0) {
      statusInfo.innerHTML = `<span class="text-amber-400 font-medium">Có ${info.dirty_count} thay đổi chưa commit</span>`;
      if (workingStatus) workingStatus.innerHTML = `<span class="text-amber-400">Có thay đổi</span>`;
    } else {
      statusInfo.innerHTML = `<span class="text-emerald-400 font-medium">Working tree sạch (clean)</span>`;
      if (workingStatus) workingStatus.innerHTML = `<span class="text-emerald-400">Sạch</span>`;
    }
  }

  if (syncBadge) {
    if (info.needs_pull || (info.behind_count && info.behind_count > 0)) {
      syncBadge.innerHTML = `<span class="text-amber-400 font-semibold bg-amber-950/70 px-2 py-0.5 rounded border border-amber-800">Chậm hơn remote ${info.behind_count} commit (Cần Pull)</span>`;
      if (btnPull) {
        btnPull.classList.remove('hidden');
        btnPull.className = 'ant-btn text-xs h-[28px] px-3 flex items-center gap-1.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold border-amber-500 shadow-sm';
      }
      if (pullBtnText) {
        pullBtnText.textContent = `Pull ngay (${info.behind_count} commit)`;
      }
    } else if (info.ahead_count && info.ahead_count > 0) {
      syncBadge.innerHTML = `<span class="text-cyan-400 font-mono bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800">Nhanh hơn remote ${info.ahead_count} commit</span>`;
      if (btnPull) btnPull.classList.add('hidden');
    } else if (info.upstream) {
      syncBadge.innerHTML = `<span class="text-emerald-400 font-mono bg-emerald-950/70 px-2 py-0.5 rounded border border-emerald-800">Đã đồng bộ mới nhất</span>`;
      if (btnPull) btnPull.classList.add('hidden');
    } else {
      syncBadge.innerHTML = `<span class="text-slate-400 font-mono text-[11px]">Chưa gắn remote upstream</span>`;
      if (btnPull) btnPull.classList.add('hidden');
    }
  }

  const prevBtn = document.getElementById(isFe ? 'btnPrevFe' : 'btnPrevBe');
  if (prevBtn) {
    if (info.prev_branch && info.prev_branch !== info.current_branch) {
      prevBtn.classList.remove('hidden');
      prevBtn.classList.add('inline-flex');
      prevBtn.innerHTML = `
            <svg class="w-3 h-3 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>
            <span>Quay về: <b id="${isFe ? 'fePrevBranchLabel' : 'bePrevBranchLabel'}" class="font-mono ${isFe ? 'text-cyan-200' : 'text-emerald-200'}">${escapeHtml(info.prev_branch)}</b></span>
          `;
      prevBtn.title = `Quay về nhánh trước đó: "${info.prev_branch}" (git checkout -)`;
    } else {
      prevBtn.classList.add('hidden');
      prevBtn.classList.remove('inline-flex');
    }
  }

  // Hiển thị khu vực Stash và nút Lấy code từ stash nếu nhánh hiện tại có stash
  const stashSection = document.getElementById(isFe ? 'feStashSection' : 'beStashSection');
  const stashBadge = document.getElementById(isFe ? 'feStashBadge' : 'beStashBadge');
  const popStashBtnText = document.getElementById(isFe ? 'fePopStashBtnText' : 'bePopStashBtnText');

  const branchStashes = info.branch_stashes || [];
  const hasBranchStash = Boolean(info.has_branch_stash && branchStashes.length > 0);

  if (stashSection) {
    if (hasBranchStash) {
      const topStash = branchStashes[0];
      const count = branchStashes.length;
      stashSection.classList.remove('hidden');
      stashSection.style.display = 'flex';
      stashSection.dataset.stashRef = topStash.index;

      if (stashBadge) {
        const timeAgo = topStash.date ? ` (${formatRelativeDate(topStash.date)})` : '';
        const desc = topStash.message || topStash.raw_subject || 'Bản cất code';
        if (count > 1) {
          stashBadge.textContent = `${topStash.index}: ${desc}${timeAgo} (+${count - 1} bản khác)`;
          stashBadge.title = `Nhánh này có ${count} bản stash:\n` + branchStashes.map(s => `${s.index}: ${s.message || s.raw_subject} (${s.date})`).join('\n');
        } else {
          stashBadge.textContent = `${topStash.index}: ${desc}${timeAgo}`;
          stashBadge.title = `${topStash.index}: ${desc} (${topStash.date})`;
        }
      }

      if (popStashBtnText) {
        popStashBtnText.textContent = count > 1 ? `Lấy code từ stash (${topStash.index})` : 'Lấy code từ stash';
      }
    } else {
      stashSection.classList.add('hidden');
      stashSection.style.display = 'none';
      if (stashBadge) {
        stashBadge.textContent = '';
        stashBadge.title = '';
      }
    }
  }

  filterBranchList(role);
}

function filterBranchList(role) {
  const isFe = role === 'fe';
  const select = document.getElementById(isFe ? 'feBranchSelect' : 'beBranchSelect');
  const input = document.getElementById(isFe ? 'feBranchInput' : 'beBranchInput');
  if (!select || !gitInfoData || !gitInfoData[role]) return;

  const filterText = (input?.value || '').toLowerCase().trim();
  const branches = gitInfoData[role].branches || [];
  const currentBranch = gitInfoData[role].current_branch;
  const stashList = gitInfoData[role].stash_list || [];
  const branchesWithStash = new Set(stashList.map(s => s.branch).filter(Boolean));

  select.innerHTML = '';
  const filtered = branches.filter(b => b.name.toLowerCase().includes(filterText));

  if (filtered.length === 0) {
    const opt = document.createElement('option');
    opt.disabled = true;
    opt.textContent = filterText ? `Nhánh mới: "${filterText}" (tích chọn tạo mới nếu cần)` : 'Không có nhánh nào';
    select.appendChild(opt);
    return;
  }

  filtered.forEach(b => {
    const opt = document.createElement('option');
    opt.value = b.name;
    const prefix = b.name === currentBranch ? '[Hiện tại] ' : '';
    const dateStr = b.date ? ` [${formatRelativeDate(b.date)}]` : '';
    const stashStr = branchesWithStash.has(b.name) ? ' [Có stash]' : '';
    opt.textContent = `${prefix}${b.name}${dateStr}${stashStr}`;
    if (b.name === currentBranch) {
      opt.className = 'font-bold text-cyan-300 bg-cyan-950/40';
    }
    select.appendChild(opt);
  });
}

function selectBranchChip(role, branchName) {
  if (role === 'fe' || role === 'both') {
    const inp = document.getElementById('feBranchInput');
    if (inp) inp.value = branchName;
    filterBranchList('fe');
  }
  if (role === 'be' || role === 'both') {
    const inp = document.getElementById('beBranchInput');
    if (inp) inp.value = branchName;
    filterBranchList('be');
  }
  const bothInp = document.getElementById('bothBranchInput');
  if (bothInp) bothInp.value = branchName;
}

function handleBranchInputKeyDown(e, role) {
  const isFe = role === 'fe';
  const select = document.getElementById(isFe ? 'feBranchSelect' : 'beBranchSelect');
  if (!select) return;

  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    const validOptions = Array.from(select.options).filter(opt => !opt.disabled);
    if (validOptions.length === 0) return;

    select.focus();
    if (select.selectedIndex < 0 || select.options[select.selectedIndex]?.disabled) {
      select.value = validOptions[0].value;
    } else {
      let curIdx = validOptions.findIndex(o => o.value === select.value);
      if (e.key === 'ArrowDown') {
        curIdx = Math.min(validOptions.length - 1, curIdx + 1);
      } else {
        curIdx = Math.max(0, curIdx - 1);
      }
      select.value = validOptions[curIdx].value;
    }
    onSelectBranchOption(role);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    doCheckout(role);
  }
}

function handleBranchSelectKeyDown(e, role) {
  if (e.key === 'Enter') {
    e.preventDefault();
    doCheckout(role);
  } else if (e.key === 'Escape') {
    const isFe = role === 'fe';
    const input = document.getElementById(isFe ? 'feBranchInput' : 'beBranchInput');
    if (input) input.focus();
  }
}

function onSelectBranchOption(role) {
  const isFe = role === 'fe';
  const select = document.getElementById(isFe ? 'feBranchSelect' : 'beBranchSelect');
  const input = document.getElementById(isFe ? 'feBranchInput' : 'beBranchInput');
  if (select && input && select.value) {
    input.value = select.value;
  }
}

async function doCheckout(target) {
  let selectedBranch = '';
  let isCreateNew = false;
  let btn = null;

  if (target === 'both') {
    const inp = document.getElementById('bothBranchInput');
    const chk = document.getElementById('bothCreateNewBranch');
    selectedBranch = (inp?.value || '').trim();
    isCreateNew = Boolean(chk?.checked);
    btn = document.getElementById('btnSwitchBoth');
  } else if (target === 'fe') {
    const inp = document.getElementById('feBranchInput');
    const sel = document.getElementById('feBranchSelect');
    selectedBranch = (inp?.value || sel?.value || '').trim();
    isCreateNew = false;
    btn = document.getElementById('btnSwitchFe');
  } else if (target === 'be') {
    const inp = document.getElementById('beBranchInput');
    const sel = document.getElementById('beBranchSelect');
    selectedBranch = (inp?.value || sel?.value || '').trim();
    isCreateNew = false;
    btn = document.getElementById('btnSwitchBe');
  }

  if (!selectedBranch) {
    await antdAlert({
      title: 'Thiếu thông tin',
      content: 'Vui lòng nhập tên nhánh (ví dụ: feat/abc) hoặc chọn trong danh sách bên dưới.',
      type: 'error'
    });
    return;
  }

  const confirmMsg = isCreateNew
    ? `Bạn có chắc muốn tạo và chuyển sang nhánh ${selectedBranch}`
    : `Bạn có chắc muốn thực hiện chuyển sang nhánh ${selectedBranch}`;

  const confirmed = await antdConfirm({
    title: isCreateNew ? 'Xác nhận tạo nhánh' : 'Xác nhận chuyển nhánh',
    content: confirmMsg
  });
  if (!confirmed) return;

  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang checkout...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: target,
        branch: selectedBranch,
        create_new: isCreateNew
      })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Chuyển nhánh thành công.' : 'Lỗi chuyển nhánh.'));

    // 1. Cập nhật lại thông tin thẻ git
    await loadGitBranchInfo();

    const roleInfo = gitInfoData?.[target];
    if (roleInfo && roleInfo.has_branch_stash && roleInfo.branch_stashes?.length > 0) {
      const topStash = roleInfo.branch_stashes[0];
      showToast(`Nhánh "${selectedBranch}" có code đã cất trong ${topStash.index}. Bấm "Lấy code từ stash" để khôi phục.`);
    }

    // 2. TỰ ĐỘNG CẬP NHẬT LẠI TOÀN BỘ SƠ ĐỒ LIÊN KẾT FE ↔ BE THEO NHÁNH VỪA CHECKOUT
    await fetchDiagramData(true);

    // 3. Cập nhật log lịch sử nếu đang mở
    if (activeTab === 'log') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi chuyển nhánh: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

async function doCheckoutPrevious(target) {
  let prevBranch = '';
  let label = '';
  let btn = null;

  if (target === 'fe') {
    prevBranch = gitInfoData?.fe?.prev_branch || '';
    label = `Frontend (nhánh "${prevBranch || 'trước đó'}")`;
    btn = document.getElementById('btnPrevFe');
  } else if (target === 'be') {
    prevBranch = gitInfoData?.be?.prev_branch || '';
    label = `Backend (nhánh "${prevBranch || 'trước đó'}")`;
    btn = document.getElementById('btnPrevBe');
  } else {
    return;
  }

  if (target === 'fe' && !prevBranch) {
    await antdAlert({ title: 'Không thể quay lại', content: 'Frontend chưa có nhánh trước đó trong lịch sử reflog.', type: 'error' });
    return;
  }
  if (target === 'be' && !prevBranch) {
    await antdAlert({ title: 'Không thể quay lại', content: 'Backend chưa có nhánh trước đó trong lịch sử reflog.', type: 'error' });
    return;
  }

  const confirmed = await antdConfirm({
    title: 'Quay về nhánh trước',
    content: `Bạn có chắc muốn thực hiện chuyển sang nhánh ${prevBranch || 'trước đó'}`
  });
  if (!confirmed) return;

  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin h-3.5 w-3.5 text-white inline-block mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang quay lại...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: target,
        branch: prevBranch || '-',
        create_new: false
      })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã quay về nhánh trước đó.' : 'Lỗi khi quay lại nhánh trước.'));

    await loadGitBranchInfo();

    const roleInfo = gitInfoData?.[target];
    if (roleInfo && roleInfo.has_branch_stash && roleInfo.branch_stashes?.length > 0) {
      const topStash = roleInfo.branch_stashes[0];
      showToast(`Nhánh "${roleInfo.current_branch || prevBranch}" có code đã cất trong ${topStash.index}. Bấm "Lấy code từ stash" để khôi phục.`);
    }

    await fetchDiagramData(true);
    if (activeTab === 'log') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi quay về nhánh trước đó: ' + err.message);
    if (btn && origText) {
      btn.innerHTML = origText;
    }
  } finally {
    if (btn) {
      btn.disabled = false;
    }
  }
}

async function doPopStash(role) {
  const isFe = role === 'fe';
  const repoName = isFe ? 'Frontend' : 'Backend';
  const roleInfo = gitInfoData?.[role];
  const branchStashes = roleInfo?.branch_stashes || [];
  const stash = branchStashes[0] || roleInfo?.stash_list?.[0];
  const stashRef = stash?.index || 'stash@{0}';
  const stashMsg = stash?.message || stash?.raw_subject || '';
  const currentBranch = roleInfo?.current_branch || 'nhánh hiện tại';

  const confirmed = await antdConfirm({
    title: 'Xác nhận lấy code từ Git Stash',
    content: `Bạn có muốn lấy và áp dụng mã nguồn từ ${stashRef}${stashMsg ? ` ("${stashMsg}")` : ''} vào nhánh "${currentBranch}" (${repoName}) không?`
  });
  if (!confirmed) return;

  const btn = document.getElementById(isFe ? 'btnPopStashFe' : 'btnPopStashBe');
  const origHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-1.5 h-3.5 w-3.5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span>Đang lấy code...</span>
    `;
  }

  try {
    const res = await fetch('/api/git/stash/pop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        stash_index: stashRef
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || `Đã lấy code từ ${stashRef} thành công.`);
    } else {
      if (data.conflict) {
        await antdAlert({
          title: 'Xảy ra xung đột khi lấy code từ Stash',
          content: `${data.message}\n\nCác file xung đột đã được giữ lại trên working tree. Bạn có thể mở tab Xung đột Git để xử lý.`,
          type: 'warning'
        });
      } else {
        await antdAlert({
          title: 'Không thể lấy code từ Stash',
          content: data.message || 'Lỗi không xác định khi thực hiện git stash pop.',
          type: 'error'
        });
      }
    }
    await loadGitBranchInfo();
    if (typeof activeTab !== 'undefined' && activeTab === 'log' && typeof loadWorkLogs === 'function') {
      loadWorkLogs();
    }
  } catch (err) {
    showToast('Lỗi kết nối khi lấy code từ stash: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

async function doPullBranch(target) {
  let label = 'cả hai phía (Frontend & Backend)';
  let branchName = '';
  let btn = null;

  if (target === 'fe') {
    branchName = gitInfoData?.fe?.current_branch || 'hiện tại';
    label = `Frontend (nhánh "${branchName}")`;
    btn = document.getElementById('btnPullFe');
  } else if (target === 'be') {
    branchName = gitInfoData?.be?.current_branch || 'hiện tại';
    label = `Backend (nhánh "${branchName}")`;
    btn = document.getElementById('btnPullBe');
  } else {
    btn = document.getElementById('btnPullBoth');
  }

  const confirmed = await antdConfirm({
    title: 'Xác nhận Git Pull',
    content: `Bạn có chắc muốn thực hiện 'git pull' để kéo mã nguồn mới nhất từ remote cho ${label}?`
  });
  if (!confirmed) return;

  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin h-3.5 w-3.5 text-white inline-block mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang pull...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã pull cập nhật thành công.' : 'Lỗi git pull.'));
    await loadGitBranchInfo();
    await fetchDiagramData(true);
    if (activeTab === 'log') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi git pull: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

function showGitAlert(message, isSuccess) {
  if (message) showToast(message);
}

// ==========================================
// GIT CHERRY-PICK MANAGEMENT
// ==========================================
let cherryPickState = {
  fe: { in_progress: false, current_branch: '', source_branch: 'staging', branches: [], commits: [] },
  be: { in_progress: false, current_branch: '', source_branch: 'staging', branches: [], commits: [] }
};

function toggleCherryBranchDropdown(role) {
  const menu = document.getElementById(role === 'fe' ? 'feCherryBranchDropdownMenu' : 'beCherryBranchDropdownMenu');
  const otherMenu = document.getElementById(role === 'fe' ? 'beCherryBranchDropdownMenu' : 'feCherryBranchDropdownMenu');
  const sourceFe = document.getElementById('feCherrySourceBranchDropdownMenu');
  const sourceBe = document.getElementById('beCherrySourceBranchDropdownMenu');
  if (otherMenu) otherMenu.classList.add('hidden');
  if (sourceFe) sourceFe.classList.add('hidden');
  if (sourceBe) sourceBe.classList.add('hidden');
  if (!menu) return;

  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    const searchInput = document.getElementById(role === 'fe' ? 'feCherryBranchSearchInput' : 'beCherryBranchSearchInput');
    if (searchInput) {
      searchInput.value = '';
      setTimeout(() => searchInput.focus(), 60);
    }
    filterCherryBranches(role);
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleCherryBranchDropdown = toggleCherryBranchDropdown;

function filterCherryBranches(role) {
  const listEl = document.getElementById(role === 'fe' ? 'feCherryBranchOptionsList' : 'beCherryBranchOptionsList');
  const searchInput = document.getElementById(role === 'fe' ? 'feCherryBranchSearchInput' : 'beCherryBranchSearchInput');
  if (!listEl) return;

  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const currentBranch = cherryPickState[role]?.current_branch || '';

  const filtered = branches.filter(b => b.name.toLowerCase().includes(keyword));

  if (filtered.length === 0) {
    listEl.innerHTML = `<div class="p-3 text-center text-slate-400 text-xs">Không tìm thấy nhánh phù hợp</div>`;
    return;
  }

  listEl.innerHTML = filtered.map(b => {
    const isCurrent = b.name === currentBranch;
    const activeClass = isCurrent ? 'active-branch' : '';
    const currentBadge = isCurrent
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Hiện tại</span>`
      : '';

    return `
          <div onclick="selectCherryBranch('${role}', '${escapeHtml(b.name).replace(/'/g, "\\'")}')" 
            class="cherry-branch-opt ${activeClass} px-2.5 py-1.5 rounded transition cursor-pointer flex items-center justify-between gap-2 text-xs">
            <span class="truncate font-mono">${escapeHtml(b.name)}</span>
            ${currentBadge}
          </div>
        `;
  }).join('');
}
window.filterCherryBranches = filterCherryBranches;

function selectCherryBranch(role, branchName) {
  const menu = document.getElementById(role === 'fe' ? 'feCherryBranchDropdownMenu' : 'beCherryBranchDropdownMenu');
  if (menu) menu.classList.add('hidden');
  onCherryBranchSwitch(role, branchName);
}
window.selectCherryBranch = selectCherryBranch;

function selectFirstFilteredCherryBranch(role) {
  const searchInput = document.getElementById(role === 'fe' ? 'feCherryBranchSearchInput' : 'beCherryBranchSearchInput');
  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const match = branches.find(b => b.name.toLowerCase().includes(keyword));
  if (match) {
    selectCherryBranch(role, match.name);
  }
}
window.selectFirstFilteredCherryBranch = selectFirstFilteredCherryBranch;

function toggleCherrySourceBranchDropdown(role) {
  const menu = document.getElementById(role === 'fe' ? 'feCherrySourceBranchDropdownMenu' : 'beCherrySourceBranchDropdownMenu');
  const otherMenu = document.getElementById(role === 'fe' ? 'beCherrySourceBranchDropdownMenu' : 'feCherrySourceBranchDropdownMenu');
  const topFe = document.getElementById('feCherryBranchDropdownMenu');
  const topBe = document.getElementById('beCherryBranchDropdownMenu');
  if (otherMenu) otherMenu.classList.add('hidden');
  if (topFe) topFe.classList.add('hidden');
  if (topBe) topBe.classList.add('hidden');
  if (!menu) return;

  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    const searchInput = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSearchInput' : 'beCherrySourceBranchSearchInput');
    if (searchInput) {
      searchInput.value = '';
      setTimeout(() => searchInput.focus(), 60);
    }
    filterCherrySourceBranches(role);
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleCherrySourceBranchDropdown = toggleCherrySourceBranchDropdown;

function filterCherrySourceBranches(role) {
  const listEl = document.getElementById(role === 'fe' ? 'feCherrySourceBranchOptionsList' : 'beCherrySourceBranchOptionsList');
  const searchInput = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSearchInput' : 'beCherrySourceBranchSearchInput');
  if (!listEl) return;

  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const currentBranch = cherryPickState[role]?.current_branch || '';
  const selectedSource = cherryPickState[role]?.source_branch || document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect')?.value || 'staging';

  const filtered = branches.filter(b => b.name.toLowerCase().includes(keyword));

  if (filtered.length === 0) {
    listEl.innerHTML = `<div class="p-3 text-center text-slate-400 text-xs">Không tìm thấy nhánh phù hợp</div>`;
    return;
  }

  listEl.innerHTML = filtered.map(b => {
    const isSelected = b.name === selectedSource;
    const isCurrent = b.name === currentBranch;
    const activeClass = isSelected ? 'active-branch' : '';
    const currentBadge = isCurrent
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Đang đứng</span>`
      : (isSelected ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-sky-950 text-sky-300 border border-sky-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Đang chọn</span>` : '');

    return `
          <div onclick="selectCherrySourceBranch('${role}', '${escapeHtml(b.name).replace(/'/g, "\\'")}')" 
            class="cherry-branch-opt ${activeClass} px-2.5 py-1.5 rounded transition cursor-pointer flex items-center justify-between gap-2 text-xs">
            <span class="truncate font-mono">${escapeHtml(b.name)}</span>
            ${currentBadge}
          </div>
        `;
  }).join('');
}
window.filterCherrySourceBranches = filterCherrySourceBranches;

function selectCherrySourceBranch(role, branchName) {
  const menu = document.getElementById(role === 'fe' ? 'feCherrySourceBranchDropdownMenu' : 'beCherrySourceBranchDropdownMenu');
  if (menu) menu.classList.add('hidden');

  cherryPickState[role].source_branch = branchName;

  const select = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect');
  if (select) select.value = branchName;

  const textEl = document.getElementById(role === 'fe' ? 'feCherrySelectedSourceBranchText' : 'beCherrySelectedSourceBranchText');
  if (textEl) {
    textEl.textContent = branchName;
    textEl.title = `Nhánh nguồn: ${branchName}`;
  }

  loadBranchCommits(role);
}
window.selectCherrySourceBranch = selectCherrySourceBranch;

function selectFirstFilteredCherrySourceBranch(role) {
  const searchInput = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSearchInput' : 'beCherrySourceBranchSearchInput');
  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const match = branches.find(b => b.name.toLowerCase().includes(keyword));
  if (match) {
    selectCherrySourceBranch(role, match.name);
  }
}
window.selectFirstFilteredCherrySourceBranch = selectFirstFilteredCherrySourceBranch;

// ==========================================
// UNIFIED NOTIFICATIONS MANAGEMENT (HEADER BELL)
// ==========================================
let _gitNotifications = [];
let _notifActiveTag = 'all'; // 'all' | 'git' | 'agent'
let _readNotifIds = new Set(JSON.parse(localStorage.getItem('easysalon_read_notifs') || '[]'));

function getAllCombinedNotifications() {
  const list = [];

  // 1. Git notifications
  (_gitNotifications || []).forEach(item => {
    list.push({
      id: `git_${item.role}_${item.branch}`,
      tag: 'git',
      tagLabel: 'Git',
      title: `${item.role.toUpperCase()} ${item.branch}: Có ${item.behind_count} commit mới`,
      desc: item.latest ? (item.latest.subject || '') : 'Có bản cập nhật remote cần pull về local.',
      author: item.latest ? item.latest.author : '',
      date: item.latest ? item.latest.date : '',
      hash: item.latest ? item.latest.hash : '',
      role: item.role,
      branch: item.branch,
      behind_count: item.behind_count
    });
  });

  // 2. Agent Task notifications - Chỉ thông báo khi Tác vụ Agent ĐÃ HOÀN TẤT
  (parallelTasks || []).forEach(t => {
    const isDone = (t.status === 'completed' || t.status === 'done');
    if (isDone) {
      list.push({
        id: `agent_${t.id}_completed`,
        tag: 'agent',
        tagLabel: 'Tác vụ Agent',
        title: 'Tác vụ đã hoàn tất',
        desc: `[${t.name}] đã thực thi xong thành công trên AI Terminal.`,
        taskId: t.id,
        taskStatus: 'completed'
      });
    }
  });

  return list;
}

function updateNotifBadgeUI() {
  const all = getAllCombinedNotifications();
  const unreadCount = all.filter(n => !_readNotifIds.has(n.id)).length;

  const badge = document.getElementById('notifBadge');
  const dropdownBadge = document.getElementById('notifDropdownBadge');
  const btnMarkAll = document.getElementById('btnMarkAllNotifsAsRead');

  if (badge) {
    if (unreadCount > 0) {
      badge.classList.remove('hidden');
      badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
    } else {
      badge.classList.add('hidden');
    }
  }

  if (dropdownBadge) {
    dropdownBadge.classList.remove('hidden');
    if (unreadCount > 0) {
      dropdownBadge.textContent = `${unreadCount} chưa đọc`;
      dropdownBadge.className = 'text-xs text-blue-600 font-semibold';
    } else {
      dropdownBadge.textContent = '0 chưa đọc';
      dropdownBadge.className = 'text-xs text-slate-400 font-normal';
    }
  }

  if (btnMarkAll) {
    if (unreadCount > 0) {
      btnMarkAll.className = 'text-[11px] font-semibold text-[#199cff] hover:text-blue-700 transition cursor-pointer';
      btnMarkAll.style.color = '#199cff';
      btnMarkAll.disabled = false;
      btnMarkAll.title = 'Đánh dấu tất cả thông báo là đã đọc';
    } else {
      btnMarkAll.className = 'text-[11px] font-semibold text-slate-400 cursor-default select-none transition';
      btnMarkAll.style.color = '#94a3b8';
      btnMarkAll.disabled = true;
      btnMarkAll.title = 'Đã đọc tất cả thông báo';
    }
  }
}
window.updateNotifBadgeUI = updateNotifBadgeUI;

function renderNotifFilterTabs() {
  const container = document.getElementById('notifFilterTabs');
  if (!container) return;

  const all = getAllCombinedNotifications();
  const allUnread = all.filter(n => !_readNotifIds.has(n.id)).length;

  const gitItems = all.filter(n => n.tag === 'git');
  const gitUnread = gitItems.filter(n => !_readNotifIds.has(n.id)).length;

  const agentItems = all.filter(n => n.tag === 'agent');
  const agentUnread = agentItems.filter(n => !_readNotifIds.has(n.id)).length;

  const tags = [
    { id: 'all', label: 'Tất cả', count: all.length, unread: allUnread },
    { id: 'git', label: 'Git', count: gitItems.length, unread: gitUnread },
    { id: 'agent', label: 'Tác vụ Agent', count: agentItems.length, unread: agentUnread }
  ];

  container.innerHTML = tags.map(t => {
    const isActive = _notifActiveTag === t.id;
    return `
      <button type="button" onclick="setNotifTagFilter('${t.id}', event)"
        class="px-3 py-1 rounded text-[11px] font-medium transition flex items-center gap-1.5 shrink-0 select-none cursor-pointer ${isActive
        ? 'bg-[#199cff] text-white font-bold shadow-sm'
        : 'text-slate-700 hover:text-black hover:bg-slate-100'
      }">
        <span>${escapeHtml(t.label)}</span>
        <span class="text-[10px] font-mono opacity-80">(${t.count})</span>
        ${t.unread > 0 ? `<span class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-white' : 'bg-blue-600'} animate-pulse"></span>` : ''}
      </button>
    `;
  }).join('');
}
window.renderNotifFilterTabs = renderNotifFilterTabs;

function setNotifTagFilter(tag, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  _notifActiveTag = tag;
  renderNotificationList();
}
window.setNotifTagFilter = setNotifTagFilter;

function renderNotificationList() {
  renderNotifFilterTabs();
  updateNotifBadgeUI();

  const listEl = document.getElementById('notifItemsList');
  if (!listEl) return;

  const all = getAllCombinedNotifications();
  const filtered = _notifActiveTag === 'all'
    ? all
    : all.filter(n => n.tag === _notifActiveTag);

  if (filtered.length === 0) {
    const emptyMsg = _notifActiveTag === 'git'
      ? 'Không có thông báo Git nào.'
      : (_notifActiveTag === 'agent' ? 'Không có thông báo Tác vụ Agent nào.' : 'Không có thông báo nào.');
    listEl.innerHTML = `
      <div class="p-6 text-center text-slate-500 space-y-2 bg-white">
        <svg class="w-8 h-8 text-emerald-500 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="text-xs font-semibold text-slate-800">${emptyMsg}</p>
      </div>
    `;
    return;
  }

  listEl.innerHTML = filtered.map(item => {
    const isUnread = !_readNotifIds.has(item.id);

    const st = (item.taskStatus || item.status || '').toLowerCase();
    const titleLower = (item.title || '').toLowerCase();
    const isDone = st === 'completed' || st === 'done' || st === 'success' || titleLower.includes('hoàn tất') || titleLower.includes('thành công');
    const isRunning = st === 'running' || titleLower.includes('đang thực thi') || titleLower.includes('đang chạy');
    const isStopped = st === 'stopped' || titleLower.includes('đã dừng') || titleLower.includes('dừng');

    let tagBadge = '';
    let titleClass = 'notif-title-default';
    let titleStyle = 'color: #0f172a;';

    if (item.tag === 'git') {
      if (item.status === 'completed' || item.status === 'success') {
        tagBadge = '<span class="notif-tag-badge notif-tag-git-done">Git · Đã pull</span>';
        titleClass = 'notif-title-done';
        titleStyle = 'color: #389e0d;';
      } else {
        tagBadge = '<span onclick="setNotifTagFilter(\'git\', event)" class="notif-tag-badge notif-tag-git-pull" title="Nhấp để lọc theo Git">Git cần pull</span>';
        titleClass = 'notif-title-running';
        titleStyle = 'color: #d48806;';
      }
    } else {
      if (isDone) {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-done" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-done';
        titleStyle = 'color: #389e0d;';
      } else if (isRunning) {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-running" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-running';
        titleStyle = 'color: #d48806;';
      } else if (isStopped) {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-stopped" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-stopped';
        titleStyle = 'color: #1677ff;';
      } else {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-default" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-default';
        titleStyle = 'color: #475569;';
      }
    }

    return `
      <div onclick="onNotifItemClick('${escapeHtml(item.id)}', event)"
        class="notif-item p-3 transition duration-150 cursor-pointer flex flex-col gap-1 select-none border-b border-slate-100 ${isUnread
        ? 'is-unread bg-blue-50/60 hover:bg-blue-100/70 border-l-4 border-l-[#199cff]'
        : 'bg-white hover:bg-blue-50/80 border-l-4 border-l-transparent'
      }">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 flex-wrap min-w-0 flex-1">
            ${tagBadge}
            <span class="font-bold text-xs ${titleClass} notif-item-title transition truncate" style="${isUnread ? 'color: #1677ff !important;' : 'color: #94a3b8 !important;'}">
              ${escapeHtml(item.title)}
            </span>
          </div>
          ${isUnread ? '<span class="w-2 h-2 rounded-full bg-[#199cff] shrink-0" title="Chưa đọc"></span>' : ''}
        </div>
        <p class="text-[11.5px] ${isUnread ? 'text-slate-700' : 'text-slate-400'} leading-relaxed truncate" title="${escapeHtml(item.desc)}">
          ${item.hash ? `<span class="font-mono text-blue-600 font-bold">${escapeHtml(item.hash)}: </span>` : ''}${escapeHtml(item.desc)}
        </p>
        ${(item.author || item.date) ? `
          <div class="text-[10px] text-slate-500 font-medium">
            ${item.author ? `Bởi ${escapeHtml(item.author)}${isAuthorMe(item.author, item.is_me) ? ' <span class="font-semibold text-[#1677ff] font-sans">(Tôi)</span>' : ''}` : ''} ${item.date ? `• ${escapeHtml(formatRelativeDate(item.date))}` : ''}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}
window.renderNotificationList = renderNotificationList;

function onNotifItemClick(notifId, event) {
  if (event) {
    event.stopPropagation();
  }
  _readNotifIds.add(notifId);
  try {
    localStorage.setItem('easysalon_read_notifs', JSON.stringify([..._readNotifIds]));
  } catch (e) { }

  updateNotifBadgeUI();
  renderNotificationList();

  const all = getAllCombinedNotifications();
  const notif = all.find(n => n.id === notifId);
  if (!notif) return;

  if (notif.tag === 'git') {
    goToPullScreen(notif.role, notif.branch);
  } else if (notif.tag === 'agent') {
    const menu = document.getElementById('notifDropdownMenu');
    if (menu) menu.classList.add('hidden');
    if (typeof switchTab === 'function') switchTab('task');
    if (notif.taskId) {
      selectParallelTask(notif.taskId);
      setFeedFilter(notif.taskId);
    }
  }
}
window.onNotifItemClick = onNotifItemClick;

function markAllNotificationsAsRead() {
  const all = getAllCombinedNotifications();
  all.forEach(n => _readNotifIds.add(n.id));
  try {
    localStorage.setItem('easysalon_read_notifs', JSON.stringify([..._readNotifIds]));
  } catch (e) { }
  updateNotifBadgeUI();
  renderNotificationList();
  showToast('Đã đánh dấu tất cả thông báo là đã đọc.');
}
window.markAllNotificationsAsRead = markAllNotificationsAsRead;

function updateGitNotifications(notifs) {
  _gitNotifications = notifs || [];
  updateNotifBadgeUI();
  renderNotificationList();
}
window.updateGitNotifications = updateGitNotifications;

function markPullSuccess(role, branch) {
  if (typeof renderBranchSyncStatus === 'function') {
    renderBranchSyncStatus(role, branch, { needs_pull: false, behind_count: 0 });
  }
  _gitNotifications = (_gitNotifications || []).filter(item => !(item.role === role && item.branch === branch));
  updateNotifBadgeUI();
  renderNotificationList();
}
window.markPullSuccess = markPullSuccess;

function toggleNotifDropdown() {
  const menu = document.getElementById('notifDropdownMenu');
  if (!menu) return;
  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    renderNotificationList();
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleNotifDropdown = toggleNotifDropdown;

function goToPullScreen(role, branch) {
  const menu = document.getElementById('notifDropdownMenu');
  if (menu) menu.classList.add('hidden');

  if (typeof switchTab === 'function') switchTab('branch');
  if (typeof switchGitSubTab === 'function') switchGitSubTab('pull_sync');

  setTimeout(() => {
    const upperRole = role === 'fe' ? 'Fe' : 'Be';
    const upperBranch = branch.charAt(0).toUpperCase() + branch.slice(1);
    const btnId = `btn${upperRole}Pull${upperBranch}`;
    const btn = document.getElementById(btnId);
    const card = btn?.closest('.bg-\\[\\#0e192c\\]') || btn;

    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      card.classList.add('ring-2', role === 'fe' ? 'ring-cyan-400/80' : 'ring-emerald-400/80', 'transition-all', 'duration-300');
      setTimeout(() => {
        card.classList.remove('ring-2', 'ring-cyan-400/80', 'ring-emerald-400/80');
      }, 2000);
    }
  }, 150);

  showToast(`Đã chuyển tới phần Pull nhánh ${branch.toUpperCase()} của ${role === 'fe' ? 'Frontend' : 'Backend'}.`);
}
window.goToPullScreen = goToPullScreen;

document.addEventListener('click', (e) => {
  const feWrap = document.getElementById('feCherryBranchDropdownWrap');
  const beWrap = document.getElementById('beCherryBranchDropdownWrap');
  const feSourceWrap = document.getElementById('feCherrySourceBranchDropdownWrap');
  const beSourceWrap = document.getElementById('beCherrySourceBranchDropdownWrap');
  const feMergeTargetWrap = document.getElementById('feMergeTargetDropdownWrap');
  const feMergeSourceWrap = document.getElementById('feMergeSourceDropdownWrap');
  const beMergeTargetWrap = document.getElementById('beMergeTargetDropdownWrap');
  const beMergeSourceWrap = document.getElementById('beMergeSourceDropdownWrap');
  const notifWrap = document.getElementById('notifWrap');

  const path = (typeof e.composedPath === 'function') ? e.composedPath() : [];
  const isInside = (el) => el && (el.contains(e.target) || path.includes(el));

  if (feWrap && !isInside(feWrap)) {
    const feMenu = document.getElementById('feCherryBranchDropdownMenu');
    if (feMenu) feMenu.classList.add('hidden');
  }
  if (beWrap && !isInside(beWrap)) {
    const beMenu = document.getElementById('beCherryBranchDropdownMenu');
    if (beMenu) beMenu.classList.add('hidden');
  }
  if (feSourceWrap && !isInside(feSourceWrap)) {
    const feSourceMenu = document.getElementById('feCherrySourceBranchDropdownMenu');
    if (feSourceMenu) feSourceMenu.classList.add('hidden');
  }
  if (beSourceWrap && !isInside(beSourceWrap)) {
    const beSourceMenu = document.getElementById('beCherrySourceBranchDropdownMenu');
    if (beSourceMenu) beSourceMenu.classList.add('hidden');
  }
  if (feMergeTargetWrap && !isInside(feMergeTargetWrap)) {
    const m = document.getElementById('feMergeTargetDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (feMergeSourceWrap && !isInside(feMergeSourceWrap)) {
    const m = document.getElementById('feMergeSourceDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (beMergeTargetWrap && !isInside(beMergeTargetWrap)) {
    const m = document.getElementById('beMergeTargetDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (beMergeSourceWrap && !isInside(beMergeSourceWrap)) {
    const m = document.getElementById('beMergeSourceDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (notifWrap && !isInside(notifWrap)) {
    const notifMenu = document.getElementById('notifDropdownMenu');
    if (notifMenu) notifMenu.classList.add('hidden');
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const menus = [
      'feCherryBranchDropdownMenu',
      'beCherryBranchDropdownMenu',
      'feCherrySourceBranchDropdownMenu',
      'beCherrySourceBranchDropdownMenu',
      'feMergeTargetDropdownMenu',
      'feMergeSourceDropdownMenu',
      'beMergeTargetDropdownMenu',
      'beMergeSourceDropdownMenu',
      'notifDropdownMenu'
    ];
    menus.forEach(id => {
      const el = document.getElementById(id);
      if (el && !el.classList.contains('hidden')) el.classList.add('hidden');
    });
  }
});

async function loadCherryPickInfo() {
  try {
    const [infoRes, statusRes] = await Promise.all([
      fetch('/api/git/info').then(r => r.json()).catch(() => null),
      fetch('/api/git/cherry-pick/status').then(r => r.json()).catch(() => null)
    ]);

    if (infoRes) {
      gitInfoData = infoRes;
      ['fe', 'be'].forEach(role => {
        const roleInfo = infoRes[role];
        if (!roleInfo) return;
        cherryPickState[role].current_branch = roleInfo.current_branch || '';
        cherryPickState[role].branches = roleInfo.branches || [];

        // Cập nhật text hiển thị của Dropdown "Đang ở nhánh"
        const branchTextEl = document.getElementById(role === 'fe' ? 'feCherrySelectedBranchText' : 'beCherrySelectedBranchText');
        if (branchTextEl) {
          branchTextEl.textContent = roleInfo.current_branch || 'unknown';
          branchTextEl.title = `Đang ở nhánh: ${roleInfo.current_branch || 'unknown'}`;
        }
        filterCherryBranches(role);

        const topBranchEl = document.getElementById(role === 'fe' ? 'feCherryTopBranch' : 'beCherryTopBranch');
        if (topBranchEl) {
          topBranchEl.textContent = roleInfo.current_branch || 'unknown';
        }

        const select = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect');
        if (select && roleInfo.branches) {
          const currentVal = select.value || cherryPickState[role]?.source_branch;
          if (select.tagName === 'SELECT') {
            select.innerHTML = '';
            roleInfo.branches.forEach(b => {
              const opt = document.createElement('option');
              opt.value = b.name;
              opt.textContent = b.name + (b.name === roleInfo.current_branch ? ' [Đang đứng]' : '');
              select.appendChild(opt);
            });
          }

          // Ưu tiên giữ giá trị cũ, nếu không có thì tìm staging, sau đó master, hoặc nhánh đầu tiên
          const branchNames = roleInfo.branches.map(b => b.name);
          let chosen = 'staging';
          if (currentVal && branchNames.includes(currentVal)) {
            chosen = currentVal;
          } else if (branchNames.includes('staging')) {
            chosen = 'staging';
          } else if (branchNames.includes('master')) {
            chosen = 'master';
          } else if (branchNames.length > 0) {
            chosen = branchNames[0];
          }

          select.value = chosen;
          cherryPickState[role].source_branch = chosen;

          const sourceTextEl = document.getElementById(role === 'fe' ? 'feCherrySelectedSourceBranchText' : 'beCherrySelectedSourceBranchText');
          if (sourceTextEl) {
            sourceTextEl.textContent = chosen;
            sourceTextEl.title = `Nhánh nguồn: ${chosen}`;
          }
          filterCherrySourceBranches(role);
        }
      });
    }

    if (statusRes) {
      ['fe', 'be'].forEach(role => {
        const st = statusRes[role];
        const box = document.getElementById(role === 'fe' ? 'feCherryConflictBox' : 'beCherryConflictBox');
        const filesBox = document.getElementById(role === 'fe' ? 'feCherryConflictFiles' : 'beCherryConflictFiles');
        if (!box) return;

        if (st && st.in_progress) {
          box.classList.remove('hidden');
          if (filesBox) {
            if (st.conflicted_files && st.conflicted_files.length > 0) {
              filesBox.innerHTML = '<div class="text-amber-300 font-bold mb-1">Các file đang xung đột:</div>' +
                st.conflicted_files.map(f => `<div class="text-rose-300 font-mono text-[11px]">• ${escapeHtml(f)}</div>`).join('');
            } else if (st.status_raw) {
              filesBox.innerHTML = `<pre class="text-[11px] whitespace-pre-wrap">${escapeHtml(st.status_raw)}</pre>`;
            } else {
              filesBox.innerHTML = '<div>Đang trong trạng thái cherry-pick chưa hoàn tất.</div>';
            }
          }
        } else {
          box.classList.add('hidden');
        }
      });
    }

    // Tải danh sách commit ban đầu cho cả 2 nhánh nguồn được chọn
    loadBranchCommits('fe');
    loadBranchCommits('be');
  } catch (err) {
    console.error('Lỗi khi tải thông tin Cherry-Pick:', err);
  }
}

let cherryPickCommitsData = { fe: [], be: [] };
let cherryPickCurrentPage = { fe: 1, be: 1 };
const CHERRY_PAGE_SIZE = 10;

function changeCherryPage(role, targetPage) {
  const commits = cherryPickCommitsData[role] || [];
  const totalPages = Math.max(1, Math.ceil(commits.length / CHERRY_PAGE_SIZE));
  const newPage = Math.max(1, Math.min(totalPages, targetPage));
  cherryPickCurrentPage[role] = newPage;
  renderCommitsList(role);
}
window.changeCherryPage = changeCherryPage;

async function loadBranchCommits(role) {
  const select = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect');
  const listEl = document.getElementById(role === 'fe' ? 'feCherryCommitsList' : 'beCherryCommitsList');
  const countEl = document.getElementById(role === 'fe' ? 'feCherryCommitsCount' : 'beCherryCommitsCount');
  if (!select || !listEl) return;

  const branch = select.value || cherryPickState[role]?.source_branch || 'staging';
  listEl.innerHTML = `
        <div class="text-center text-xs text-slate-400 py-6 flex items-center justify-center gap-2">
          <svg class="animate-spin h-4 w-4 text-cyan-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang tải danh sách commit của nhánh <b>${escapeHtml(branch)}</b>...</span>
        </div>
      `;

  try {
    const res = await fetch(`/api/git/commits?target=${role}&branch=${encodeURIComponent(branch)}&limit=300`);
    const data = await res.json();
    if (data && data.commits) {
      cherryPickCommitsData[role] = data.commits;
      cherryPickCurrentPage[role] = 1;
      renderCommitsList(role);
    } else {
      cherryPickCommitsData[role] = [];
      listEl.innerHTML = `<div class="text-center text-xs text-slate-400 py-6">Không tìm thấy commit nào hoặc nhánh không tồn tại.</div>`;
      if (countEl) countEl.textContent = '';
    }
  } catch (err) {
    cherryPickCommitsData[role] = [];
    listEl.innerHTML = `<div class="text-center text-xs text-rose-400 py-6">Lỗi tải commit: ${escapeHtml(err.message)}</div>`;
    if (countEl) countEl.textContent = '';
  }
}

function renderCommitsList(role, commitsArg) {
  const listEl = document.getElementById(role === 'fe' ? 'feCherryCommitsList' : 'beCherryCommitsList');
  const countEl = document.getElementById(role === 'fe' ? 'feCherryCommitsCount' : 'beCherryCommitsCount');
  if (!listEl) return;

  if (Array.isArray(commitsArg)) {
    cherryPickCommitsData[role] = commitsArg;
  }
  const allCommits = cherryPickCommitsData[role] || [];

  if (allCommits.length === 0) {
    listEl.innerHTML = `<div class="text-center text-xs text-slate-400 py-6">Không có commit nào trong nhánh này.</div>`;
    if (countEl) countEl.textContent = '';
    return;
  }

  const page = cherryPickCurrentPage[role] || 1;
  const totalPages = Math.max(1, Math.ceil(allCommits.length / CHERRY_PAGE_SIZE));
  const safePage = Math.max(1, Math.min(totalPages, page));
  const startIdx = (safePage - 1) * CHERRY_PAGE_SIZE;
  const pageCommits = allCommits.slice(startIdx, startIdx + CHERRY_PAGE_SIZE);

  if (countEl) {
    countEl.textContent = `(${allCommits.length} commit - Trang ${safePage}/${totalPages})`;
  }

  const isFe = role === 'fe';
  const accentBg = isFe ? 'bg-cyan-950/70 border-cyan-800/60 text-cyan-300' : 'bg-emerald-950/70 border-emerald-800/60 text-emerald-300';
  const hoverBorder = isFe ? 'hover:border-cyan-500' : 'hover:border-emerald-500';

  const commitsHtml = pageCommits.map(c => {
    const shortHash = c.short_hash || (c.hash ? c.hash.substring(0, 8) : 'unknown');
    const safeSubject = escapeHtml(c.subject || '');
    const authorHtml = formatCommitAuthor(c.author, c.is_me);
    const safeDate = escapeHtml(formatRelativeDate(c.date || ''));
    const fullHash = c.hash || '';

    return `
          <div class="group bg-[#101e38] border border-[#244170] ${hoverBorder} rounded p-2 transition flex items-center justify-between gap-2.5 text-xs">
            <div class="flex-1 min-w-0 space-y-1">
              <div class="flex items-center gap-2">
                <span class="font-mono text-[11px] font-semibold px-1.5 py-0.5 rounded border ${accentBg} select-all" title="${fullHash}">
                  ${shortHash}
                </span>
                <span class="font-medium text-slate-100 truncate" title="${safeSubject}">${safeSubject}</span>
              </div>
              <div class="flex items-center gap-2 text-[10px] text-slate-400">
                <span class="truncate max-w-[170px]">${authorHtml}</span>
                <span>•</span>
                <span>${safeDate}</span>
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <button type="button" onclick="executeCherryPickDirect('${role}', '${fullHash}', '${safeSubject.replace(/'/g, "\\'")}')" class="ant-btn ant-btn-primary text-[11px] h-[26px] px-2.5 flex items-center gap-1 font-medium whitespace-nowrap shadow-sm rounded-[4px]">
                <span>Cherry-pick</span>
              </button>
            </div>
          </div>
        `;
  }).join('');

  const paginationHtml = totalPages > 1 ? `
    <div class="flex items-center justify-between pt-2 px-1 border-t border-[#244170] text-xs mt-1">
      <div class="text-[11px] text-slate-400 font-mono">
        Trang <b class="text-cyan-300">${safePage}</b> / <b>${totalPages}</b> <span class="text-slate-500">(${allCommits.length} commit)</span>
      </div>
      <div class="flex items-center gap-1">
        <button type="button" onclick="changeCherryPage('${role}', 1)" ${safePage <= 1 ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] font-mono transition cursor-pointer" title="Trang đầu">«</button>
        <button type="button" onclick="changeCherryPage('${role}', ${safePage - 1})" ${safePage <= 1 ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] transition cursor-pointer">‹ Trước</button>
        <span class="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-300 font-mono text-[11px] font-bold">${safePage}</span>
        <button type="button" onclick="changeCherryPage('${role}', ${safePage + 1})" ${safePage >= totalPages ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] transition cursor-pointer">Sau ›</button>
        <button type="button" onclick="changeCherryPage('${role}', ${totalPages})" ${safePage >= totalPages ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] font-mono transition cursor-pointer" title="Trang cuối">»</button>
      </div>
    </div>
  ` : '';

  listEl.innerHTML = commitsHtml + paginationHtml;
}

async function onCherryBranchSwitch(role, targetBranch) {
  if (!targetBranch) return;
  const current = cherryPickState[role]?.current_branch;
  if (targetBranch === current) return;

  if (!cherryPickState[role]) cherryPickState[role] = {};
  if (current) {
    cherryPickState[role].previous_branch = current;
  }

  const roleName = role === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)';

  const confirmed = await antdConfirm({
    title: 'Xác nhận chuyển nhánh',
    content: `Bạn có chắc muốn thực hiện chuyển sang nhánh "${targetBranch}" cho ${roleName}?`,
    okText: 'Chuyển nhánh'
  });

  if (!confirmed) return;

  showToast(`Đang chuyển ${role === 'fe' ? 'Frontend' : 'Backend'} sang nhánh '${targetBranch}'...`);

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        branch: targetBranch,
        create_new: false
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`${role === 'fe' ? 'Frontend' : 'Backend'}: Đã chuyển sang nhánh '${targetBranch}' thành công.`);
      clearCherrySuccessBox(role);
    } else {
      showToast(data.message || 'Lỗi khi chuyển nhánh.');
      await antdAlert({
        title: 'Lỗi chuyển nhánh',
        content: data.message || 'Không thể chuyển nhánh.',
        type: 'error'
      });
    }
  } catch (err) {
    showToast('Lỗi kết nối khi chuyển nhánh: ' + err.message);
  } finally {
    await loadGitBranchInfo();
    await loadCherryPickInfo();
  }
}
window.onCherryBranchSwitch = onCherryBranchSwitch;

async function executeCherryPickDirect(role, hash, subject) {
  if (!hash) return;
  const currentBranch = cherryPickState[role]?.current_branch || (document.getElementById(role === 'fe' ? 'feCherrySelectedBranchText' : 'beCherrySelectedBranchText')?.textContent.trim() || 'nhánh hiện tại');
  const shortHash = hash.length > 8 ? hash.substring(0, 8) : hash;

  const confirmed = await antdConfirm({
    title: 'Xác nhận Cherry-Pick',
    content: `Bạn có chắc muốn cherry-pick commit ${shortHash} vào nhánh "${currentBranch}"?`,
    okText: 'Cherry-Pick'
  });
  if (!confirmed) return;

  showToast(`Đang cherry-pick commit ${shortHash} vào nhánh ${currentBranch}...`);

  try {
    const res = await fetch('/api/git/cherry-pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        commits: hash,
        record_origin: true,
        no_commit: false
      })
    });
    const data = await res.json();

    const successBox = document.getElementById(role === 'fe' ? 'feCherrySuccessBox' : 'beCherrySuccessBox');
    const errorBox = document.getElementById(role === 'fe' ? 'feCherryErrorBox' : 'beCherryErrorBox');
    const commitMsgInput = document.getElementById(role === 'fe' ? 'feCherryCommitMsgInput' : 'beCherryCommitMsgInput');
    const successTitle = document.getElementById(role === 'fe' ? 'feCherrySuccessTitle' : 'beCherrySuccessTitle');

    if (data.success) {
      const msg = data.message || `Đã cherry-pick commit ${shortHash} vào nhánh '${currentBranch}' thành công!`;
      showToast(msg);
      if (errorBox) errorBox.classList.add('hidden');
      if (successBox) {
        successBox.classList.remove('hidden');
        if (successTitle) successTitle.textContent = `Đã cherry-pick commit ${shortHash} vào nhánh '${currentBranch}' thành công!`;
        if (commitMsgInput) {
          commitMsgInput.value = data.commit_message || subject || '';
          commitMsgInput.disabled = false;
        }
        const commitMsgSection = document.getElementById(role === 'fe' ? 'feCherryCommitMsgSection' : 'beCherryCommitMsgSection');
        if (commitMsgSection) commitMsgSection.classList.remove('hidden');
        const promptText = document.getElementById(role === 'fe' ? 'feCherryPushPromptText' : 'beCherryPushPromptText');
        if (promptText) promptText.textContent = 'Đẩy commit này lên nhánh remote:';
        const pushBtn = document.getElementById(role === 'fe' ? 'btnFeCherryPush' : 'btnBeCherryPush');
        const pushBtnText = document.getElementById(role === 'fe' ? 'btnFeCherryPushText' : 'btnBeCherryPushText');
        const closeBtn = document.getElementById(role === 'fe' ? 'btnFeCherryCloseSuccess' : 'btnBeCherryCloseSuccess');
        if (pushBtn) {
          pushBtn.dataset.pushed = 'false';
          pushBtn.disabled = false;
          pushBtn.classList.remove('opacity-60', 'cursor-not-allowed', 'pointer-events-none');
          if (pushBtnText) pushBtnText.textContent = 'Push code lên nhánh';
        }
        if (closeBtn) closeBtn.classList.add('hidden');
        const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
        if (returnWrap) returnWrap.classList.add('hidden');
      }
    } else if (data.conflict) {
      showToast('Xung đột (conflict) khi cherry-pick commit!');
      if (successBox) successBox.classList.add('hidden');
      if (errorBox) errorBox.classList.add('hidden');
      await antdAlert({
        title: 'Xảy ra xung đột (Conflict)',
        content: `Quá trình cherry-pick commit ${shortHash} gặp xung đột mã nguồn.\n\nVui lòng kiểm tra các file xung đột hiển thị trên giao diện, giải quyết và bấm "Tiếp tục (--continue)", hoặc bấm "Hủy bỏ (--abort)" để quay lại trạng thái ban đầu.`,
        type: 'error'
      });
    } else {
      showToast(data.message || 'Thao tác cherry-pick thất bại.');
      if (successBox) successBox.classList.add('hidden');
      if (errorBox) {
        errorBox.classList.remove('hidden');
        const errorDetail = document.getElementById(role === 'fe' ? 'feCherryErrorDetail' : 'beCherryErrorDetail');
        if (errorDetail) errorDetail.textContent = data.message || data.output || 'Không thể thực hiện cherry-pick.';
      }
      await antdAlert({
        title: 'Lỗi Cherry-Pick',
        content: data.message || 'Không thể thực hiện cherry-pick.',
        type: 'error'
      });
    }

    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi cherry-pick: ' + err.message);
  }
}
window.executeCherryPickDirect = executeCherryPickDirect;
window.quickCherryPick = executeCherryPickDirect;

function clearCherrySuccessBox(role) {
  const successBox = document.getElementById(role === 'fe' ? 'feCherrySuccessBox' : 'beCherrySuccessBox');
  const commitMsgInput = document.getElementById(role === 'fe' ? 'feCherryCommitMsgInput' : 'beCherryCommitMsgInput');
  const commitMsgSection = document.getElementById(role === 'fe' ? 'feCherryCommitMsgSection' : 'beCherryCommitMsgSection');
  const promptText = document.getElementById(role === 'fe' ? 'feCherryPushPromptText' : 'beCherryPushPromptText');
  const btn = document.getElementById(role === 'fe' ? 'btnFeCherryPush' : 'btnBeCherryPush');
  const btnText = document.getElementById(role === 'fe' ? 'btnFeCherryPushText' : 'btnBeCherryPushText');
  const closeBtn = document.getElementById(role === 'fe' ? 'btnFeCherryCloseSuccess' : 'btnBeCherryCloseSuccess');
  const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
  const successTitle = document.getElementById(role === 'fe' ? 'feCherrySuccessTitle' : 'beCherrySuccessTitle');

  if (successBox) successBox.classList.add('hidden');
  if (commitMsgInput) {
    commitMsgInput.value = '';
    commitMsgInput.disabled = false;
  }
  if (commitMsgSection) commitMsgSection.classList.remove('hidden');
  if (promptText) promptText.textContent = 'Đẩy commit này lên nhánh remote:';
  if (successTitle) successTitle.textContent = 'Cherry-pick commit thành công!';
  if (closeBtn) closeBtn.classList.add('hidden');

  if (btn) {
    btn.dataset.pushed = 'false';
    btn.disabled = false;
    btn.classList.remove('opacity-60', 'cursor-not-allowed', 'pointer-events-none');
    if (btnText) btnText.textContent = 'Push code lên nhánh';
  }
  if (returnWrap) returnWrap.classList.add('hidden');
}
window.clearCherrySuccessBox = clearCherrySuccessBox;

async function doCherryPush(role) {
  const roleName = role === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)';
  const currentBranch = cherryPickState[role]?.current_branch || (document.getElementById(role === 'fe' ? 'feCherrySelectedBranchText' : 'beCherrySelectedBranchText')?.textContent.trim() || '');
  const msgInput = document.getElementById(role === 'fe' ? 'feCherryCommitMsgInput' : 'beCherryCommitMsgInput');
  const btn = document.getElementById(role === 'fe' ? 'btnFeCherryPush' : 'btnBeCherryPush');
  const btnText = document.getElementById(role === 'fe' ? 'btnFeCherryPushText' : 'btnBeCherryPushText');
  const spinner = document.getElementById(role === 'fe' ? 'feCherryPushSpinner' : 'beCherryPushSpinner');
  const closeBtn = document.getElementById(role === 'fe' ? 'btnFeCherryCloseSuccess' : 'btnBeCherryCloseSuccess');

  // Validate: nếu đã push trước đó rồi thì cảnh báo và chặn lại, không push lần 2
  if (btn && btn.dataset.pushed === 'true') {
    await antdAlert({
      title: 'Đã hoàn tất Push',
      content: `Commit trên nhánh "${currentBranch}" (${roleName}) đã được đẩy lên remote hoàn tất rồi. Không cần push lần nữa!`,
      type: 'info'
    });
    return;
  }

  const commitMsg = msgInput ? msgInput.value.trim() : '';

  const confirmed = await antdConfirm({
    title: 'Xác nhận Push code',
    content: `Bạn có chắc muốn đẩy (git push) commit lên nhánh "${currentBranch}" của ${roleName}?`,
    okText: 'Push code'
  });
  if (!confirmed) return;

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  showToast(`Đang push code lên nhánh '${currentBranch}'...`);

  let pushSuccess = false;
  try {
    const res = await fetch('/api/git/push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        branch: currentBranch,
        commit_message: commitMsg
      })
    });
    const data = await res.json();
    if (data.success) {
      pushSuccess = true;
      if (data.already_pushed) {
        showToast(data.message || `Nhánh '${currentBranch}' đã đồng bộ với remote.`);
        await antdAlert({
          title: 'Đã đồng bộ remote',
          content: data.message || `Nhánh "${currentBranch}" đã ở trạng thái mới nhất trên remote (Everything up-to-date). Không có commit mới nào cần push lại!`,
          type: 'info'
        });
      } else {
        showToast(`Đã push code lên nhánh '${currentBranch}' thành công!`);
      }

      // Xóa nội dung input và khóa thao tác để tránh bấm push nhầm lần 2
      if (msgInput) {
        msgInput.value = '';
        msgInput.disabled = true;
      }
      const commitMsgSection = document.getElementById(role === 'fe' ? 'feCherryCommitMsgSection' : 'beCherryCommitMsgSection');
      if (commitMsgSection) commitMsgSection.classList.add('hidden');

      const promptText = document.getElementById(role === 'fe' ? 'feCherryPushPromptText' : 'beCherryPushPromptText');
      if (promptText) promptText.textContent = 'Trạng thái trên remote:';

      const successTitle = document.getElementById(role === 'fe' ? 'feCherrySuccessTitle' : 'beCherrySuccessTitle');
      if (successTitle) {
        successTitle.textContent = `Đã đẩy commit lên nhánh '${currentBranch}' thành công!`;
      }

      if (btn) {
        btn.dataset.pushed = 'true';
        btn.disabled = true;
        btn.classList.add('opacity-60', 'cursor-not-allowed', 'pointer-events-none');
        if (btnText) btnText.textContent = 'Đã push lên remote';
      }
      if (closeBtn) closeBtn.classList.remove('hidden');

      const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
      const prevBranch = (cherryPickState[role]?.previous_branch || cherryPickState[role]?.source_branch || '').trim();
      if (returnWrap && prevBranch && prevBranch !== currentBranch) {
        returnWrap.classList.remove('hidden');
        const returnText = document.getElementById(role === 'fe' ? 'btnFeCherryReturnPrevBranchText' : 'btnBeCherryReturnPrevBranchText');
        if (returnText) {
          returnText.textContent = `Quay về lại nhánh lúc nãy (${prevBranch})`;
          returnText.title = `Quay về lại nhánh ${prevBranch}`;
        }
      }
    } else {
      showToast(`Push thất bại: ${data.message || 'Lỗi khi push code.'}`);
      await antdAlert({
        title: 'Lỗi Push code',
        content: data.message || 'Không thể push code lên remote.',
        type: 'error'
      });
    }
  } catch (err) {
    showToast('Lỗi kết nối khi push: ' + err.message);
  } finally {
    if (spinner) spinner.classList.add('hidden');
    // Nếu push không thành công, mở lại nút để có thể thử lại
    if (!pushSuccess && btn) {
      btn.disabled = false;
    }
    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
  }
}
window.doCherryPush = doCherryPush;

async function doReturnToPrevCherryBranch(role) {
  const prevBranch = (cherryPickState[role]?.previous_branch || cherryPickState[role]?.source_branch || '').trim();
  if (!prevBranch) {
    showToast('Không tìm thấy thông tin nhánh lúc nãy để quay về.');
    return;
  }
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: `Quay về lại nhánh lúc nãy (${prevBranch})`,
    content: `Bạn có muốn checkout quay lại nhánh cũ "${prevBranch}" trên ${roleName}?`,
    okText: 'Quay về nhánh'
  });
  if (!confirmed) return;

  const btn = document.getElementById(role === 'fe' ? 'btnFeCherryReturnPrevBranch' : 'btnBeCherryReturnPrevBranch');
  if (btn) btn.disabled = true;

  showToast(`Đang chuyển về nhánh '${prevBranch}'...`);

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role, branch: prevBranch, create_new: false })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Đã quay về nhánh '${prevBranch}' thành công!`);
      clearCherrySuccessBox(role);
      const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
      if (returnWrap) returnWrap.classList.add('hidden');
      await loadCherryPickInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    } else {
      showToast(`Không thể quay về nhánh: ${data.message || 'Lỗi checkout.'}`);
    }
  } catch (err) {
    showToast('Lỗi khi checkout nhánh: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.doReturnToPrevCherryBranch = doReturnToPrevCherryBranch;

async function doCherryPickAbort(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Hủy bỏ Cherry-Pick',
    content: `Bạn có chắc muốn hủy bỏ quá trình cherry-pick đang dở dang trên ${roleName}? Tất cả thay đổi chưa lưu của commit này sẽ được hoàn tác.`,
    okText: 'Hủy bỏ cherry-pick',
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/cherry-pick/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hủy bỏ cherry-pick thành công.' : 'Lỗi khi hủy bỏ cherry-pick.'));
    clearCherrySuccessBox(role);
    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi hủy bỏ cherry-pick: ' + err.message);
  }
}

async function doCherryPickContinue(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Tiếp tục Cherry-Pick',
    content: `Bạn đã xử lý xong các file xung đột (conflict) trên ${roleName} và muốn tiếp tục hoàn tất commit?`,
    okText: 'Tiếp tục'
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/cherry-pick/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hoàn tất cherry-pick tiếp tục.' : 'Lỗi khi tiếp tục cherry-pick.'));
    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi tiếp tục cherry-pick: ' + err.message);
  }
}

// ==========================================
// GIT PULL STAGING / MASTER SYNC
// ==========================================
let _isCheckingSync = false;
const _expandedSyncPullDiffs = new Set();
const _expandedCommitDiffs = new Set();

function toggleCommitDiff(role, branch, commitHash, event) {
  if (event) event.stopPropagation();
  const key = `${role}_${branch}_${commitHash}`;
  const detailEl = document.getElementById(`commitDetail_${key}`);
  const arrowEl = document.getElementById(`commitArrow_${key}`);
  if (!detailEl) return;
  const isHidden = detailEl.classList.contains('hidden');
  if (isHidden) {
    detailEl.classList.remove('hidden');
    _expandedCommitDiffs.add(key);
    if (arrowEl) arrowEl.classList.add('rotate-180');
  } else {
    detailEl.classList.add('hidden');
    _expandedCommitDiffs.delete(key);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
  }
}
window.toggleCommitDiff = toggleCommitDiff;

function toggleSyncPullDiff(role, branch, event) {
  if (event) event.stopPropagation();
  const key = `${role}_${branch}`;
  const detailEl = document.getElementById(`syncPullDetail_${key}`);
  const arrowEl = document.getElementById(`syncPullArrow_${key}`);
  if (!detailEl) return;
  const isHidden = detailEl.classList.contains('hidden');
  if (isHidden) {
    detailEl.classList.remove('hidden');
    _expandedSyncPullDiffs.add(key);
    if (arrowEl) arrowEl.classList.add('rotate-180');
  } else {
    detailEl.classList.add('hidden');
    _expandedSyncPullDiffs.delete(key);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
  }
}
window.toggleSyncPullDiff = toggleSyncPullDiff;

function renderBranchSyncStatus(role, branch, info) {
  const badgeEl = document.getElementById(`${role}_${branch}_statusBadge`);
  const boxEl = document.getElementById(`${role}_${branch}_commitsBox`);
  const upperRole = role.charAt(0).toUpperCase() + role.slice(1);
  const upperBranch = branch.charAt(0).toUpperCase() + branch.slice(1);
  const btnTextEl = document.getElementById(`btn${upperRole}Pull${upperBranch}Text`);
  const btnEl = document.getElementById(`btn${upperRole}Pull${upperBranch}`);

  if (!info) return;

  if (info.needs_pull) {
    if (badgeEl) {
      badgeEl.classList.remove('hidden');
      badgeEl.innerHTML = `
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm">
              <span class="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>Có ${info.behind_count} commit mới</span>
            </span>
          `;
    }

    if (btnTextEl) {
      btnTextEl.textContent = `Pull ${upperBranch} (${info.behind_count} mới)`;
    }
    if (btnEl) {
      btnEl.classList.add('ring-2', 'ring-amber-400/50');
    }

    if (boxEl) {
      const syncKey = `${role}_${branch}`;
      const isExpanded = _expandedSyncPullDiffs.has(syncKey);
      const commitsHtml = (info.commits || []).map(c => {
        const commitKey = `${role}_${branch}_${c.hash}`;
        const isCommitExpanded = _expandedCommitDiffs.has(commitKey);
        const commitFiles = c.files || [];
        const commitAdds = commitFiles.reduce((acc, f) => acc + (Number(f.additions) || 0), 0);
        const commitDels = commitFiles.reduce((acc, f) => acc + (Number(f.deletions) || 0), 0);

        const commitFilesHtml = commitFiles.length > 0 ? `
          <div class="space-y-1 max-h-60 overflow-y-auto pr-1">
            ${commitFiles.map(f => `
              <div class="sync-file-item flex items-center justify-between gap-2 py-1 px-2.5 rounded bg-black/40 border border-white/5 text-[10.5px]">
                <span class="sync-file-path truncate text-[#0958d9] dark:text-sky-300 font-mono font-medium hover:underline cursor-pointer"
                      title="Xem toàn bộ mã nguồn file: ${escapeHtml(f.path)}"
                      onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')">
                  ${escapeHtml(f.path)}
                </span>
                <div class="flex items-center gap-1.5 shrink-0 font-mono">
                  <span class="text-[#73c991] font-bold">+${f.additions || 0}</span>
                  <span class="text-[#f14c4c] font-bold">-${f.deletions || 0}</span>
                  <button type="button"
                    onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')"
                    class="sync-file-view-btn p-1 rounded hover:bg-sky-500/15 text-sky-400 hover:text-sky-300 transition flex items-center justify-center cursor-pointer"
                    title="Xem toàn bộ mã nguồn file (${escapeHtml(f.path)}) (Full code)">
                    <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        ` : '<div class="text-slate-400 text-xs py-1">Không có file thay đổi riêng</div>';

        const commitDiffHtml = c.diff ? `
          <div class="mt-2.5">
            <div class="flex items-center justify-between text-[11px] text-slate-300 mb-1.5 px-0.5">
              <span class="sync-commit-header font-bold text-amber-300 flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                <span>Diff của commit ${escapeHtml(c.hash)}:</span>
              </span>
              ${commitFiles.length > 0 ? `
                <button type="button"
                  onclick="event.stopPropagation(); openFileEditor('${escapeHtml(commitFiles[0].path)}', '${escapeHtml(role)}')"
                  class="sync-diff-view-full-btn inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-sans font-medium text-sky-400 hover:text-sky-300 hover:bg-sky-500/15 border border-sky-500/30 transition cursor-pointer"
                  title="Xem toàn bộ mã nguồn file (${escapeHtml(commitFiles[0].path)}) (Full code)">
                  <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span>Xem file</span>
                </button>
              ` : ''}
            </div>
            <div class="sync-diff-wrapper rounded-md bg-[#1e1e1e] border border-[#333333] max-h-[500px] min-h-[140px] overflow-auto text-[11.5px] font-mono leading-relaxed shadow-inner">
              ${typeof formatDiffColoredHtml === 'function' ? formatDiffColoredHtml(c.diff) : `<pre class="text-[#d4d4d4] p-3 whitespace-pre-wrap">${escapeHtml(c.diff)}</pre>`}
            </div>
          </div>
        ` : '';

        return `
          <div class="commit-item-card rounded-md border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] transition overflow-hidden">
            <div class="flex items-center justify-between gap-2 py-1.5 px-2.5 cursor-pointer select-none text-[11px]"
                 onclick="toggleCommitDiff('${role}', '${branch}', '${escapeHtml(c.hash)}', event)"
                 title="Nhấp để xem các file và diff của commit ${escapeHtml(c.hash)}">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span class="text-cyan-400 font-bold shrink-0 font-mono">${escapeHtml(c.hash)}</span>
                <span class="text-slate-200 truncate font-sans font-medium" title="${escapeHtml(c.subject)}">${escapeHtml(c.subject)}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span class="text-slate-400 text-[10px] shrink-0 font-sans">${formatCommitAuthor(c.author, c.is_me)} • ${escapeHtml(formatRelativeDate(c.date))}</span>
                ${commitFiles.length > 0 ? `
                  <span class="px-1.5 py-0.5 rounded text-[9.5px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800/80" title="${commitFiles.length} file thay đổi (+${commitAdds} -${commitDels})">
                    ${commitFiles.length} file
                  </span>
                ` : ''}
                <button type="button" onclick="toggleCommitDiff('${role}', '${branch}', '${escapeHtml(c.hash)}', event)"
                  class="p-0.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                  title="${isCommitExpanded ? 'Thu gọn chi tiết commit' : 'Xem các file thay đổi của commit này'}">
                  <svg id="commitArrow_${commitKey}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isCommitExpanded ? 'rotate-180' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
            </div>
            <div id="commitDetail_${commitKey}" class="${isCommitExpanded ? '' : 'hidden'} commit-detail-box p-2.5 pt-1.5 border-t border-white/5 bg-black/25 space-y-2">
              <div class="sync-commit-header text-[10.5px] font-semibold text-amber-300 flex items-center justify-between">
                <span>Các file đã sửa trong commit ${escapeHtml(c.hash)} (${commitFiles.length} file):</span>
                <span class="font-mono text-[10px] text-slate-300">+${commitAdds} / -${commitDels}</span>
              </div>
              ${commitFilesHtml}
              ${commitDiffHtml}
            </div>
          </div>
        `;
      }).join('');

      const totalFilesList = info.files || [];
      const globalDiffHtml = totalFilesList.length > 0 ? `
        <div class="pt-1.5 border-t border-amber-500/20">
          <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold cursor-pointer select-none hover:text-amber-200 py-1"
               onclick="toggleSyncPullDiff('${role}', '${branch}', event)">
            <span class="flex items-center gap-1.5">
              <svg class="w-3 h-3 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/>
              </svg>
              <span>Xem toàn bộ thay đổi gộp (${totalFilesList.length} file)</span>
            </span>
            <button type="button" class="p-0.5 text-amber-400 hover:text-white transition cursor-pointer"
                    title="${isExpanded ? 'Thu gọn toàn bộ thay đổi gộp' : 'Xem toàn bộ thay đổi gộp'}">
              <svg id="syncPullArrow_${syncKey}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
          <div id="syncPullDetail_${syncKey}" class="${isExpanded ? '' : 'hidden'} pt-2 space-y-2">
            <div class="space-y-1 max-h-64 overflow-y-auto pr-1">
              ${totalFilesList.map(f => `
                <div class="sync-file-item flex items-center justify-between gap-2 py-1 px-2.5 rounded bg-black/30 border border-white/5 text-[10.5px]">
                  <span class="sync-file-path truncate text-[#0958d9] dark:text-sky-300 font-mono font-medium hover:underline cursor-pointer"
                        title="Xem toàn bộ mã nguồn file: ${escapeHtml(f.path)}"
                        onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')">
                    ${escapeHtml(f.path)}
                  </span>
                  <div class="flex items-center gap-1.5 shrink-0 font-mono">
                    <span class="text-[#73c991] font-bold">+${f.additions || 0}</span>
                    <span class="text-[#f14c4c] font-bold">-${f.deletions || 0}</span>
                    <button type="button"
                      onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')"
                      class="sync-file-view-btn p-1 rounded hover:bg-sky-500/15 text-sky-400 hover:text-sky-300 transition flex items-center justify-center cursor-pointer"
                      title="Xem toàn bộ mã nguồn file (${escapeHtml(f.path)}) (Full code)">
                      <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
            ${info.diff ? `
              <div class="mt-2.5">
                <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold mb-1.5 px-0.5">
                  <span class="sync-commit-header flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <span>Diff gộp tất cả commit:</span>
                  </span>
                  ${totalFilesList.length > 0 ? `
                    <button type="button"
                      onclick="event.stopPropagation(); openFileEditor('${escapeHtml(totalFilesList[0].path)}', '${escapeHtml(role)}')"
                      class="sync-diff-view-full-btn inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-sans font-medium text-sky-400 hover:text-sky-300 hover:bg-sky-500/15 border border-sky-500/30 transition cursor-pointer"
                      title="Xem toàn bộ mã nguồn file (${escapeHtml(totalFilesList[0].path)}) (Full code)">
                      <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                      <span>Xem file</span>
                    </button>
                  ` : ''}
                </div>
                <div class="sync-diff-wrapper rounded-md bg-[#1e1e1e] border border-[#333333] max-h-[500px] min-h-[160px] overflow-auto text-[11.5px] font-mono leading-relaxed shadow-inner">
                  ${typeof formatDiffColoredHtml === 'function' ? formatDiffColoredHtml(info.diff) : `<pre class="text-[#d4d4d4] p-3 whitespace-pre-wrap">${escapeHtml(info.diff)}</pre>`}
                </div>
              </div>
            ` : ''}
          </div>
        </div>
      ` : '';

      boxEl.innerHTML = `
            <div class="sync-commits-box bg-[#091220] border border-amber-500/30 rounded-lg p-2.5 space-y-2 text-xs font-mono">
              <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold pb-1 border-b border-amber-500/20">
                <span class="flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
                  </svg>
                  <span>Các commit mới cần pull về:</span>
                </span>
                ${info.diff_stat ? `<span class="text-[10px] text-slate-400 font-normal truncate max-w-[280px]">${escapeHtml(info.diff_stat)}</span>` : ''}
              </div>
              <div class="space-y-1.5 max-h-[720px] overflow-y-auto pr-1">
                ${commitsHtml || '<div class="text-slate-400 text-xs py-1">Không có chi tiết commit</div>'}
              </div>
              ${globalDiffHtml}
            </div>
          `;
      boxEl.classList.remove('hidden');
    }
  } else {
    if (badgeEl) {
      badgeEl.classList.remove('hidden');
      badgeEl.innerHTML = `
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-medium bg-emerald-950/70 text-emerald-400 border border-emerald-700/60 shadow-sm">
              <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
              <span>Đã mới nhất (0 commit)</span>
            </span>
          `;
    }

    if (btnTextEl) {
      btnTextEl.textContent = `Pull ${upperBranch}`;
    }
    if (btnEl) {
      btnEl.classList.remove('ring-2', 'ring-amber-400/50');
    }

    if (boxEl) {
      const latest = info.latest_commit;
      boxEl.innerHTML = `
            <div class="sync-commits-box bg-[#091220]/60 border border-emerald-700/30 rounded-lg px-2.5 py-1.5 text-xs font-mono flex items-center justify-between text-slate-300">
              <span class="flex items-center gap-1.5 text-emerald-400 text-[11px] shrink-0">
                <svg class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
                <span>Đã đồng bộ với origin/${escapeHtml(branch)}</span>
              </span>
              ${latest ? `
                <span class="text-[10px] text-slate-400 truncate ml-2 text-right" title="${escapeHtml(latest.subject)}">
                  <span class="text-cyan-400 font-bold">${escapeHtml(latest.hash)}</span> • ${formatCommitAuthor(latest.author, latest.is_me)} (${escapeHtml(formatRelativeDate(latest.date))})
                </span>
              ` : ''}
            </div>
          `;
      boxEl.classList.remove('hidden');
    }
  }
}

async function checkSyncPullUpdates(doFetch = true) {
  if (_isCheckingSync) return;
  _isCheckingSync = true;

  const btn = document.getElementById('btnCheckSyncUpdates');
  const spinner = document.getElementById('syncCheckSpinner');
  const icon = document.getElementById('syncCheckIcon');
  const summaryBadge = document.getElementById('syncCheckSummaryBadge');
  const timeEl = document.getElementById('syncCheckLastTime');

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  if (icon) icon.classList.add('hidden');
  if (summaryBadge) {
    summaryBadge.textContent = 'Đang kiểm tra remote...';
    summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-cyan-950/70 text-cyan-300 border border-cyan-800';
  }

  try {
    const res = await fetch(`/api/git/sync-check?fetch=${doFetch ? '1' : '0'}`);
    const data = await res.json();
    if (data && data.success) {
      if (timeEl && data.last_checked) {
        timeEl.textContent = `(lúc ${data.last_checked})`;
      }

      if (data.fe) {
        renderBranchSyncStatus('fe', 'staging', data.fe.staging);
        renderBranchSyncStatus('fe', 'master', data.fe.master);
        renderBranchSyncStatus('fe', 'beta', data.fe.beta);
      }
      if (data.be) {
        renderBranchSyncStatus('be', 'staging', data.be.staging);
        renderBranchSyncStatus('be', 'master', data.be.master);
        renderBranchSyncStatus('be', 'beta', data.be.beta);
      }

      let totalBehind = 0;
      const needingBranches = [];
      const notifs = [];

      ['fe', 'be'].forEach(r => {
        ['staging', 'master', 'beta'].forEach(b => {
          const info = data[r] && data[r][b];
          if (info && info.needs_pull) {
            totalBehind += info.behind_count || 1;
            needingBranches.push(`${r.toUpperCase()} ${b}`);
            notifs.push({
              id: `${r}_${b}`,
              role: r,
              roleName: r === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)',
              branch: b,
              behind_count: info.behind_count || 1,
              diff_stat: info.diff_stat || '',
              latest: info.latest_commit || (info.commits && info.commits[0]) || null,
              commits: info.commits || []
            });
          }
        });
      });

      updateGitNotifications(notifs);

      if (summaryBadge) {
        if (totalBehind > 0) {
          summaryBadge.textContent = `Có ${totalBehind} commit mới cần pull (${needingBranches.join(', ')})`;
          summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold';
        } else {
          summaryBadge.textContent = 'Tất cả nhánh Staging, Master & Beta đã đồng bộ mới nhất';
          summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-emerald-950/70 text-emerald-300 border border-emerald-700/60 font-semibold';
        }
      }
    }
  } catch (err) {
    console.error('Lỗi khi kiểm tra sync pull:', err);
    if (summaryBadge) {
      summaryBadge.textContent = 'Lỗi kết nối kiểm tra';
      summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-rose-950/70 text-rose-300 border border-rose-800';
    }
  } finally {
    _isCheckingSync = false;
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
    if (icon) icon.classList.remove('hidden');
  }
}
window.checkSyncPullUpdates = checkSyncPullUpdates;

async function loadPullSyncInfo() {
  try {
    const res = await fetch('/api/git/info');
    const data = await res.json();
    if (data) {
      const feBranchEl = document.getElementById('feSyncCurrBranch');
      const beBranchEl = document.getElementById('beSyncCurrBranch');
      if (feBranchEl && data.fe) feBranchEl.textContent = data.fe.current_branch || 'unknown';
      if (beBranchEl && data.be) beBranchEl.textContent = data.be.current_branch || 'unknown';
    }
  } catch (err) {
    console.error('Lỗi khi tải thông tin Pull Sync:', err);
  }
  checkSyncPullUpdates(true);
}
window.loadPullSyncInfo = loadPullSyncInfo;

async function doSyncPull(target, branch) {
  const targetLabel = target === 'both' ? 'Cả Frontend & Backend' : (target === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)');

  const isReturn = target === 'fe'
    ? (branch === 'staging' ? document.getElementById('feReturnStaging')?.checked : (branch === 'beta' ? document.getElementById('feReturnBeta')?.checked : document.getElementById('feReturnMaster')?.checked))
    : (branch === 'staging' ? document.getElementById('beReturnStaging')?.checked : (branch === 'beta' ? document.getElementById('beReturnBeta')?.checked : document.getElementById('beReturnMaster')?.checked));

  const currBranch = document.getElementById(target === 'fe' ? 'feSyncCurrBranch' : 'beSyncCurrBranch')?.textContent.trim() || '';
  let returnNote = '';
  if (isReturn && currBranch && currBranch !== branch) {
    returnNote = `\n\n(Hệ thống sẽ chuyển sang "${branch}", pull code mới nhất, sau đó tự động quay về lại nhánh "${currBranch}")`;
  } else {
    returnNote = `\n\n(Hệ thống sẽ chuyển sang "${branch}", pull code mới nhất và ở lại nhánh "${branch}")`;
  }

  const confirmed = await antdConfirm({
    title: `Xác nhận Pull ${branch.toUpperCase()}`,
    content: `Bạn có chắc muốn tự động checkout và pull nhánh "${branch}" cho ${targetLabel}?${returnNote}`,
    okText: `Pull ${branch}`
  });
  if (!confirmed) return;

  const upperRole = target === 'fe' ? 'Fe' : 'Be';
  const upperBranch = branch.charAt(0).toUpperCase() + branch.slice(1);
  const btnId = `btn${upperRole}Pull${upperBranch}`;
  const spinnerId = `${target}Pull${upperBranch}Spinner`;
  const btn = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');

  showToast(`Đang checkout và pull nhánh '${branch}' cho ${targetLabel}...`);

  try {
    const res = await fetch('/api/git/sync-pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: target, branch: branch, return_to_current: !!isReturn })
    });
    const data = await res.json();

    // Xử lý hiển thị từng cột FE / BE
    ['fe', 'be'].forEach(role => {
      if (target !== 'both' && target !== role) return;
      const roleResult = data.results && data.results[role];
      if (!roleResult) return;

      const conflictBox = document.getElementById(role === 'fe' ? 'feSyncConflictBox' : 'beSyncConflictBox');
      const conflictFiles = document.getElementById(role === 'fe' ? 'feSyncConflictFiles' : 'beSyncConflictFiles');
      const conflictTitle = document.getElementById(role === 'fe' ? 'feSyncConflictTitle' : 'beSyncConflictTitle');
      const resultBox = document.getElementById(role === 'fe' ? 'feSyncResultBox' : 'beSyncResultBox');
      const resultOutput = document.getElementById(role === 'fe' ? 'feSyncResultOutput' : 'beSyncResultOutput');
      const resultTitle = document.getElementById(role === 'fe' ? 'feSyncResultTitle' : 'beSyncResultTitle');

      if (roleResult.conflict) {
        if (conflictBox) conflictBox.classList.remove('hidden');
        if (conflictTitle) conflictTitle.textContent = `Xung đột (Conflict) khi pull nhánh '${branch}' trên ${role === 'fe' ? 'Frontend' : 'Backend'}!`;
        if (conflictFiles) {
          if (roleResult.conflicted_files && roleResult.conflicted_files.length > 0) {
            conflictFiles.innerHTML = roleResult.conflicted_files.map(f => `<div class="text-rose-300 font-mono text-[11px]">• ${escapeHtml(f)}</div>`).join('');
          } else {
            conflictFiles.textContent = roleResult.output || 'Có xung đột mã nguồn khi merge.';
          }
        }
        if (resultBox) resultBox.classList.add('hidden');
      } else if (roleResult.success) {
        if (conflictBox) conflictBox.classList.add('hidden');
        markPullSuccess(role, branch);
        if (resultBox) {
          resultBox.classList.remove('hidden');
          const finalMsg = roleResult.returned_to_initial
            ? `Đã pull thành công (${branch}) & quay về '${roleResult.final_branch}'`
            : `Đã pull thành công (${branch})`;
          if (resultTitle) {
            resultTitle.innerHTML = `<svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg><span>${escapeHtml(finalMsg)}</span>`;
          }
          if (resultOutput) resultOutput.textContent = roleResult.output || 'Already up to date.';
        }
        if (roleResult.final_branch) {
          const currEl = document.getElementById(role === 'fe' ? 'feSyncCurrBranch' : 'beSyncCurrBranch');
          if (currEl) currEl.textContent = roleResult.final_branch;
        }
      } else {
        if (resultBox) {
          resultBox.classList.remove('hidden');
          if (resultTitle) resultTitle.textContent = `Thất bại khi pull '${branch}'`;
          if (resultOutput) resultOutput.textContent = roleResult.message || 'Lỗi không xác định.';
        }
      }
    });

    const hasUncommitted = Boolean(
      data.needs_stash ||
      (data.message && (
        data.message.includes('commit hoặc stash') ||
        data.message.includes('overwritten by checkout') ||
        data.message.includes('Please commit your changes or stash them')
      ))
    );

    if (data.conflict) {
      showToast(`Phát hiện xung đột khi pull nhánh '${branch}'!`);
      await antdAlert({
        title: 'Xảy ra xung đột (Conflict)',
        content: `Quá trình pull nhánh '${branch}' gặp xung đột mã nguồn.\n\nVui lòng kiểm tra danh sách file xung đột hiển thị trên giao diện, giải quyết và commit hoặc bấm "Hủy bỏ Merge (git merge --abort)" để quay lại an toàn.`,
        type: 'error'
      });
    } else if (data.success) {
      showToast('Đã pull thành công');
    } else if (hasUncommitted) {
      showToast('Phát hiện có thay đổi dở dang cản trở pull!');
      const action = await antdPromptStash({
        title: 'Lỗi Pull nhánh',
        content: data.message || 'Không thể chuyển sang nhánh đích do có thay đổi dở dang chưa commit/stash.',
        okText: 'Git stash nó',
        cancelText: 'Đã hiểu'
      });

      if (action === 'stash') {
        showToast('Đang thực hiện git stash để cất code dở dang...');
        try {
          const stashRes = await fetch('/api/git/stash', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target })
          });
          const stashData = await stashRes.json();
          if (stashData.success) {
            showToast('Đã Git Stash thành công! Đang tự động thử pull lại...');
            setTimeout(() => doSyncPull(target, branch, isReturn), 600);
            return;
          } else {
            await antdAlert({
              title: 'Lỗi Git Stash',
              content: stashData.message || 'Không thể thực hiện git stash.',
              type: 'error'
            });
          }
        } catch (err) {
          showToast('Lỗi khi gọi git stash: ' + err.message);
        }
      }
    } else {
      showToast(data.message || 'Thao tác pull gặp lỗi.');
      await antdAlert({
        title: 'Lỗi Pull nhánh',
        content: data.message || 'Không thể pull nhánh.',
        type: 'error'
      });
    }

    await loadPullSyncInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi pull nhánh: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
  }
}
window.doSyncPull = doSyncPull;

async function doAbortMerge(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Hủy bỏ Merge',
    content: `Bạn có chắc muốn hủy bỏ merge (git merge --abort) trên ${roleName}? Trạng thái repo sẽ được hoàn tác an toàn về trước lúc pull.`,
    okText: 'Hủy bỏ merge',
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/merge/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hủy bỏ merge thành công.' : 'Lỗi khi hủy merge.'));

    const conflictBox = document.getElementById(role === 'fe' ? 'feSyncConflictBox' : 'beSyncConflictBox');
    if (conflictBox) conflictBox.classList.add('hidden');

    await loadPullSyncInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
  } catch (err) {
    showToast('Lỗi kết nối khi hủy merge: ' + err.message);
  }
}
window.doAbortMerge = doAbortMerge;

// ==========================================
// GIT MERGE MANAGEMENT (SUB-VIEW 4)
// ==========================================
let mergeBranchState = {
  fe: { current_branch: '', selected_target: '', selected_source: '', branches: [], source_search: '', target_search: '' },
  be: { current_branch: '', selected_target: '', selected_source: '', branches: [], source_search: '', target_search: '' }
};

function toggleMergeDropdown(role, type) {
  const targetId = role === 'fe' ? (type === 'target' ? 'feMergeTargetDropdownMenu' : 'feMergeSourceDropdownMenu') : (type === 'target' ? 'beMergeTargetDropdownMenu' : 'beMergeSourceDropdownMenu');
  const menu = document.getElementById(targetId);

  // Đóng tất cả dropdown merge khác đang mở
  ['fe', 'be'].forEach(r => {
    ['target', 'source'].forEach(t => {
      const id = r === 'fe' ? (t === 'target' ? 'feMergeTargetDropdownMenu' : 'feMergeSourceDropdownMenu') : (t === 'target' ? 'beMergeTargetDropdownMenu' : 'beMergeSourceDropdownMenu');
      if (id !== targetId) {
        const other = document.getElementById(id);
        if (other) other.classList.add('hidden');
      }
    });
  });

  if (!menu) return;
  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    const searchId = role === 'fe' ? (type === 'target' ? 'feMergeTargetSearchInput' : 'feMergeSourceSearchInput') : (type === 'target' ? 'beMergeTargetSearchInput' : 'beMergeSourceSearchInput');
    const searchInput = document.getElementById(searchId);
    if (searchInput) {
      searchInput.value = '';
      setTimeout(() => searchInput.focus(), 60);
    }
    filterMergeDropdown(role, type);
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleMergeDropdown = toggleMergeDropdown;

function filterMergeDropdown(role, type) {
  const listId = role === 'fe' ? (type === 'target' ? 'feMergeTargetOptionsList' : 'feMergeSourceOptionsList') : (type === 'target' ? 'beMergeTargetOptionsList' : 'beMergeSourceOptionsList');
  const searchId = role === 'fe' ? (type === 'target' ? 'feMergeTargetSearchInput' : 'feMergeSourceSearchInput') : (type === 'target' ? 'beMergeTargetSearchInput' : 'beMergeSourceSearchInput');
  const listEl = document.getElementById(listId);
  const searchInput = document.getElementById(searchId);
  if (!listEl) return;

  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = mergeBranchState[role]?.branches || [];
  const currentBranch = mergeBranchState[role]?.current_branch || '';
  const selectedBranch = type === 'target' ? mergeBranchState[role]?.selected_target : mergeBranchState[role]?.selected_source;

  const filtered = branches.filter(b => b.name.toLowerCase().includes(keyword));

  if (type === 'source') {
    const countEl = document.getElementById(role === 'fe' ? 'feMergeSourceCount' : 'beMergeSourceCount');
    if (countEl) countEl.textContent = `(${filtered.length} nhánh)`;
  }

  if (filtered.length === 0) {
    listEl.innerHTML = '<div class="p-3 text-center text-slate-400 text-xs">Không tìm thấy nhánh phù hợp</div>';
    return;
  }

  listEl.innerHTML = filtered.map(b => {
    const isSelected = b.name === selectedBranch;
    const isCurrent = b.name === currentBranch;
    const activeClass = isSelected ? 'active-branch' : '';
    const currentBadge = isCurrent
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Đang đứng</span>`
      : '';

    return `
      <div onclick="selectMergeBranch('${role}', '${type}', '${escapeHtml(b.name).replace(/'/g, "\\'")}')"
        class="merge-branch-opt ${activeClass} px-2.5 py-1.5 rounded transition cursor-pointer flex items-center justify-between gap-2 text-xs">
        <span class="truncate font-mono">${escapeHtml(b.name)}</span>
        ${currentBadge}
      </div>
    `;
  }).join('');
}
window.filterMergeDropdown = filterMergeDropdown;

function selectMergeBranch(role, type, branchName) {
  const menuId = role === 'fe' ? (type === 'target' ? 'feMergeTargetDropdownMenu' : 'feMergeSourceDropdownMenu') : (type === 'target' ? 'beMergeTargetDropdownMenu' : 'beMergeSourceDropdownMenu');
  const menu = document.getElementById(menuId);
  if (menu) menu.classList.add('hidden');

  if (type === 'target') {
    mergeBranchState[role].selected_target = branchName;
  } else {
    mergeBranchState[role].selected_source = branchName;
  }

  const selectId = role === 'fe' ? (type === 'target' ? 'feMergeTargetSelect' : 'feMergeSourceSelect') : (type === 'target' ? 'beMergeTargetSelect' : 'beMergeSourceSelect');
  const textId = role === 'fe' ? (type === 'target' ? 'feMergeSelectedTargetText' : 'feMergeSelectedSourceText') : (type === 'target' ? 'beMergeSelectedTargetText' : 'beMergeSelectedSourceText');

  const inputEl = document.getElementById(selectId);
  const textEl = document.getElementById(textId);
  if (inputEl) inputEl.value = branchName;
  if (textEl) textEl.textContent = branchName || 'Chọn nhánh...';
}
window.selectMergeBranch = selectMergeBranch;

function setMergeSourceToCurrent(role) {
  const current = mergeBranchState[role].current_branch;
  if (!current) return;
  selectMergeBranch(role, 'source', current);
  showToast(`Đã chọn nhánh merge là nhánh hiện tại: ${current}`);
}
window.setMergeSourceToCurrent = setMergeSourceToCurrent;

function setMergeTargetToCurrent(role) {
  const current = mergeBranchState[role].current_branch;
  if (!current) return;
  selectMergeBranch(role, 'target', current);
  showToast(`Đã chọn nhánh cần merge là nhánh hiện tại: ${current}`);
}
window.setMergeTargetToCurrent = setMergeTargetToCurrent;

async function loadMergeInfo() {
  try {
    const [infoRes, statusRes] = await Promise.all([
      fetch('/api/git/info').then(r => r.json()).catch(() => null),
      fetch('/api/git/merge/status').then(r => r.json()).catch(() => null)
    ]);

    if (infoRes) {
      ['fe', 'be'].forEach(role => {
        const roleInfo = infoRes[role];
        if (!roleInfo) return;
        mergeBranchState[role].current_branch = roleInfo.current_branch || '';
        mergeBranchState[role].branches = roleInfo.branches || [];

        // Cập nhật text hiển thị nhánh hiện tại
        const topEl = document.getElementById(role === 'fe' ? 'feMergeTopBranch' : 'beMergeTopBranch');
        if (topEl) topEl.textContent = roleInfo.current_branch || 'unknown';

        const branchNames = (roleInfo.branches || []).map(b => b.name);
        const currBranch = roleInfo.current_branch || '';
        const isBaseBranch = ['staging', 'master', 'main', 'beta'].includes(currBranch.toLowerCase());

        // 1. Nhánh merge (ở TRÊN - Source):
        // Nếu đang ở nhánh feature, ưu tiên chọn ngay nhánh feature đó để merge
        let defaultSource = mergeBranchState[role].selected_source;
        if (!defaultSource || !branchNames.includes(defaultSource)) {
          if (!isBaseBranch && currBranch && branchNames.includes(currBranch)) {
            defaultSource = currBranch;
          } else {
            const featureBranch = branchNames.find(n => !['staging', 'master', 'main', 'beta'].includes(n.toLowerCase()));
            defaultSource = featureBranch || (currBranch ? currBranch : branchNames[0] || '');
          }
        }
        selectMergeBranch(role, 'source', defaultSource);

        // 2. Nhánh cần merge (ở DƯỚI - Target):
        // Mặc định là 'staging' (hoặc 'master'), bảo đảm khác nhánh merge
        let defaultTarget = mergeBranchState[role].selected_target;
        if (!defaultTarget || !branchNames.includes(defaultTarget) || defaultTarget === defaultSource) {
          if (isBaseBranch && currBranch && defaultSource !== currBranch) {
            defaultTarget = currBranch;
          } else if (branchNames.includes('staging') && defaultSource !== 'staging') {
            defaultTarget = 'staging';
          } else if (branchNames.includes('master') && defaultSource !== 'master') {
            defaultTarget = 'master';
          } else {
            const other = branchNames.find(n => n !== defaultSource);
            defaultTarget = other || branchNames[0] || '';
          }
        }
        selectMergeBranch(role, 'target', defaultTarget);
      });
    }

    // Kiểm tra trạng thái merge / conflict hiện có từ server
    if (statusRes) {
      ['fe', 'be'].forEach(role => {
        const s = statusRes[role];
        if (!s) return;
        const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
        const conflictFiles = document.getElementById(role === 'fe' ? 'feMergeConflictFiles' : 'beMergeConflictFiles');
        const conflictLogText = document.getElementById(role === 'fe' ? 'feMergeConflictLogText' : 'beMergeConflictLogText');

        if (s.in_progress || s.has_conflicts) {
          if (conflictBox) conflictBox.classList.remove('hidden');
          if (conflictFiles) {
            if (s.conflicted_files && s.conflicted_files.length > 0) {
              conflictFiles.innerHTML = s.conflicted_files.map(f => `
                <div class="text-amber-200 font-mono text-[11px] flex items-center justify-between gap-2 py-0.5 border-b border-amber-900/40 last:border-0">
                  <span class="flex items-center gap-1.5 truncate">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
                    <span class="text-rose-400 font-bold shrink-0">[CONFLICT]</span>
                    <span class="truncate" title="${escapeHtml(f)}">${escapeHtml(f)}</span>
                  </span>
                  <button type="button" onclick="copyToClipboard('${escapeHtml(f)}')" class="text-[10px] text-amber-400/80 hover:text-white px-1.5 py-0.5 rounded hover:bg-amber-800/40 shrink-0">Sao chép</button>
                </div>
              `).join('');
            } else {
              conflictFiles.innerHTML = '<div class="text-amber-300">Đang trong tiến trình merge chưa hoàn tất.</div>';
            }
          }
          if (conflictLogText) {
            conflictLogText.textContent = s.status_raw || s.merge_msg || 'Merge in progress. Vui lòng giải quyết xung đột.';
          }
        }
      });
    }
  } catch (err) {
    console.error('Lỗi khi tải thông tin Merge:', err);
  }
}
window.loadMergeInfo = loadMergeInfo;

function formatGitOutputVsCode(rawText) {
  if (!rawText || !rawText.trim()) {
    return '<span class="vscode-git-muted">Không có log chi tiết.</span>';
  }

  const lines = rawText.split('\n');
  const formatted = lines.map(line => {
    // 1. Diffstat lines: e.g. " .../booking-form-control/BookingFormBase.tsx       | 22 ++++++++++++++++++++++"
    const diffStatMatch = line.match(/^(\s*)(.+?)\s*\|\s*(\d+)\s*([+-]*)\s*$/);
    if (diffStatMatch) {
      const indent = diffStatMatch[1];
      const filePath = escapeHtml(diffStatMatch[2]);
      const count = diffStatMatch[3];
      const signs = diffStatMatch[4];

      let signsHtml = '';
      if (signs) {
        const plusCount = (signs.match(/\+/g) || []).length;
        const minusCount = (signs.match(/-/g) || []).length;
        if (plusCount > 0) signsHtml += `<span class="vscode-git-add font-bold">${'+'.repeat(plusCount)}</span>`;
        if (minusCount > 0) signsHtml += `<span class="vscode-git-del font-bold">${'-'.repeat(minusCount)}</span>`;
      }

      return `${indent}<span class="vscode-git-file">${filePath}</span> <span class="vscode-git-pipe">|</span> <span class="vscode-git-num">${count}</span> ${signsHtml}`;
    }

    // 2. Summary lines: e.g. " 2 files changed, 32 insertions(+)" or "1 file changed, 6 insertions(+), 6 deletions(-)"
    const summaryMatch = line.match(/^(\s*)(\d+\s+files?\s+changed)(?:,\s*(\d+\s+insertions?\(\+\)))?(?:,\s*(\d+\s+deletions?\(-\)))?(.*)$/);
    if (summaryMatch) {
      const indent = summaryMatch[1];
      const filesPart = `<span class="vscode-git-files font-semibold">${escapeHtml(summaryMatch[2])}</span>`;
      let insPart = '';
      let delPart = '';
      if (summaryMatch[3]) {
        insPart = `, <span class="vscode-git-add font-semibold">${escapeHtml(summaryMatch[3])}</span>`;
      }
      if (summaryMatch[4]) {
        delPart = `, <span class="vscode-git-del font-semibold">${escapeHtml(summaryMatch[4])}</span>`;
      }
      const rest = summaryMatch[5] ? escapeHtml(summaryMatch[5]) : '';
      return `${indent}${filesPart}${insPart}${delPart}${rest}`;
    }

    // 3. Strategy line: e.g. "Merge made by the 'ort' strategy."
    if (line.includes("Merge made by the '") || line.includes("Merge made by the ")) {
      return line.replace(/(Merge made by the\s+['"]?)([^'"]+)(['"]?\s+strategy\.)/g, (m, p1, p2, p3) => {
        return `<span class="vscode-git-info">${escapeHtml(p1)}</span><span class="vscode-git-strategy font-bold">${escapeHtml(p2)}</span><span class="vscode-git-info">${escapeHtml(p3)}</span>`;
      });
    }

    // 4. Fast-forward
    if (line.trim() === 'Fast-forward') {
      return `<span class="vscode-git-add font-bold">Fast-forward</span>`;
    }

    // 5. Updating hash..hash
    if (line.match(/^(\s*)Updating\s+([0-9a-fA-F]+)\.\.([0-9a-fA-F]+)/)) {
      return line.replace(/Updating\s+([0-9a-fA-F]+)\.\.([0-9a-fA-F]+)/, (m, h1, h2) => {
        return `<span class="vscode-git-muted">Updating </span><span class="vscode-git-hash">${h1}</span><span class="vscode-git-muted">..</span><span class="vscode-git-hash">${h2}</span>`;
      });
    }

    // 6. Auto-merging
    if (line.startsWith('Auto-merging ')) {
      return `<span class="vscode-git-keyword font-semibold">Auto-merging</span> <span class="vscode-git-file">${escapeHtml(line.slice(13))}</span>`;
    }

    // 7. CONFLICT
    if (line.includes('CONFLICT')) {
      return `<span class="vscode-git-conflict font-bold">${escapeHtml(line)}</span>`;
    }

    // 8. Automatic merge failed
    if (line.includes('Automatic merge failed')) {
      return `<span class="vscode-git-del font-semibold">${escapeHtml(line)}</span>`;
    }

    // 9. Already up to date
    if (line.includes('Already up to date')) {
      return `<span class="vscode-git-add font-semibold">${escapeHtml(line)}</span>`;
    }

    return escapeHtml(line);
  });

  return formatted.join('\n');
}
window.formatGitOutputVsCode = formatGitOutputVsCode;

async function doExecuteMerge(role) {
  const roleName = role === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)';
  const sourceSelect = document.getElementById(role === 'fe' ? 'feMergeSourceSelect' : 'beMergeSourceSelect');
  const targetSelect = document.getElementById(role === 'fe' ? 'feMergeTargetSelect' : 'beMergeTargetSelect');
  const noFFCheckbox = document.getElementById(role === 'fe' ? 'feMergeNoFF' : 'beMergeNoFF');
  const returnCheckbox = document.getElementById(role === 'fe' ? 'feMergeReturnCurrent' : 'beMergeReturnCurrent');
  const commitMsgInput = document.getElementById(role === 'fe' ? 'feMergeCommitMsg' : 'beMergeCommitMsg');

  const sourceBranch = (sourceSelect?.value || '').trim();
  const targetBranch = (targetSelect?.value || '').trim();
  const noFF = !!noFFCheckbox?.checked;
  const returnCurrent = !!returnCheckbox?.checked;
  const commitMsg = (commitMsgInput?.value || '').trim();

  if (!sourceBranch) {
    showToast('Vui lòng chọn nhánh merge chứa code muốn gộp.');
    return;
  }
  if (!targetBranch) {
    showToast('Vui lòng chọn nhánh cần merge nhận code.');
    return;
  }
  if (sourceBranch === targetBranch) {
    showToast('Nhánh merge và nhánh cần merge không được trùng nhau.');
    return;
  }

  const confirmed = await antdConfirm({
    title: `Xác nhận Merge ${role === 'fe' ? 'Frontend' : 'Backend'}`,
    content: `Bạn có chắc muốn hợp nhất code:\n\n• Nhánh merge (A): "${sourceBranch}"\n• Hợp nhất vào nhánh cần merge (B): "${targetBranch}"\n\n${noFF ? '• Sử dụng tùy chọn: --no-ff\n' : ''}${returnCurrent ? '• Tự động quay về nhánh cũ sau khi merge\n' : ''}Hệ thống sẽ tự động kiểm tra và hiển thị log chi tiết bên dưới nếu xảy ra conflict.`,
    okText: 'Thực hiện Merge'
  });
  if (!confirmed) return;

  const btnId = role === 'fe' ? 'btnFeDoMerge' : 'btnBeDoMerge';
  const spinnerId = role === 'fe' ? 'feMergeSpinner' : 'beMergeSpinner';
  const btnTextId = role === 'fe' ? 'feMergeBtnText' : 'beMergeBtnText';
  const btn = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  const btnText = document.getElementById(btnTextId);

  const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
  const conflictFiles = document.getElementById(role === 'fe' ? 'feMergeConflictFiles' : 'beMergeConflictFiles');
  const conflictLogText = document.getElementById(role === 'fe' ? 'feMergeConflictLogText' : 'beMergeConflictLogText');
  const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
  const successText = document.getElementById(role === 'fe' ? 'feMergeSuccessText' : 'beMergeSuccessText');
  const successLogText = document.getElementById(role === 'fe' ? 'feMergeSuccessLogText' : 'beMergeSuccessLogText');
  const errorBox = document.getElementById(role === 'fe' ? 'feMergeErrorBox' : 'beMergeErrorBox');
  const errorDetail = document.getElementById(role === 'fe' ? 'feMergeErrorDetail' : 'beMergeErrorDetail');
  const returnWrap = document.getElementById(role === 'fe' ? 'feMergeReturnBranchWrap' : 'beMergeReturnBranchWrap');

  // Ghi nhớ nhánh lúc nãy trước khi thực hiện merge
  const preMergeBranch = (mergeBranchState[role]?.current_branch || '').trim();

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  if (btnText) btnText.textContent = `Đang merge ${sourceBranch} ➔ ${targetBranch}...`;

  if (conflictBox) conflictBox.classList.add('hidden');
  if (successBox) successBox.classList.add('hidden');
  if (errorBox) errorBox.classList.add('hidden');
  if (returnWrap) returnWrap.classList.add('hidden');

  showToast(`Đang merge nhánh '${sourceBranch}' vào '${targetBranch}' trên ${roleName}...`);

  try {
    const res = await fetch('/api/git/merge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        source_branch: sourceBranch,
        target_branch: targetBranch,
        no_ff: noFF,
        return_to_current: returnCurrent,
        commit_message: commitMsg
      })
    });
    const data = await res.json();

    // Lưu lại nhánh lúc nãy để sau khi push có thể quay về
    const initialBranch = data.initial_branch || preMergeBranch || sourceBranch;
    if (initialBranch) {
      mergeBranchState[role].previous_branch = initialBranch;
    }

    if (data.conflict) {
      if (conflictBox) {
        conflictBox.classList.remove('hidden');
        conflictBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      if (conflictFiles) {
        if (data.conflicted_files && data.conflicted_files.length > 0) {
          conflictFiles.innerHTML = data.conflicted_files.map(f => `
            <div class="text-amber-200 font-mono text-[11px] flex items-center justify-between gap-2 py-0.5 border-b border-amber-900/40 last:border-0">
              <span class="flex items-center gap-1.5 truncate">
                <span class="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
                <span class="text-rose-400 font-bold shrink-0">[CONFLICT]</span>
                <span class="truncate" title="${escapeHtml(f)}">${escapeHtml(f)}</span>
              </span>
              <button type="button" onclick="copyToClipboard('${escapeHtml(f)}')" class="text-[10px] text-amber-400/80 hover:text-white px-1.5 py-0.5 rounded hover:bg-amber-800/40 shrink-0">Sao chép</button>
            </div>
          `).join('');
        } else {
          conflictFiles.innerHTML = '<div class="text-amber-300">Có xung đột mã nguồn trong quá trình merge.</div>';
        }
      }
      if (conflictLogText) {
        conflictLogText.innerHTML = formatGitOutputVsCode(data.output || 'CONFLICT: Merge conflict in working files.');
      }
      showToast(`⚠️ Xảy ra xung đột khi merge nhánh '${sourceBranch}'!`);
      await antdAlert({
        title: 'Xảy ra xung đột (Merge Conflict)',
        content: `Quá trình merge từ nhánh "${sourceBranch}" vào "${targetBranch}" bị xung đột mã nguồn.\n\nHệ thống đã hiển thị chi tiết danh sách file bị conflict và Console Log bên dưới. Bạn có thể giải quyết conflict thủ công trong editor rồi nhấn "Đã sửa xong & Tiếp tục", hoặc nhấn "Hủy bỏ Merge (--abort)".`,
        type: 'error'
      });
    } else if (data.success) {
      if (successBox) {
        successBox.classList.remove('hidden');
        successBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      if (successText) {
        successText.innerHTML = `Đã hợp nhất thành công mã nguồn từ <b>${escapeHtml(sourceBranch)}</b> vào nhánh <b>${escapeHtml(targetBranch)}</b>.${data.head_commit ? ` Commit: <span class="font-mono text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800 text-[11px]">${escapeHtml(data.head_commit)}</span>` : ''}`;
      }
      if (successLogText) {
        successLogText.innerHTML = formatGitOutputVsCode(data.output || 'Already up to date.');
      }
      showToast(`Merge thành công nhánh '${sourceBranch}' vào '${targetBranch}'!`);
    } else {
      if (errorBox) {
        errorBox.classList.remove('hidden');
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      if (errorDetail) {
        errorDetail.textContent = data.message || data.output || 'Lỗi không xác định khi merge.';
      }
      showToast(data.message || 'Merge thất bại.');
      await antdAlert({
        title: 'Không thể Merge',
        content: data.message || 'Lệnh git merge thất bại. Vui lòng kiểm tra working tree và thử lại.',
        type: 'error'
      });
    }

    await loadMergeInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi gọi lệnh merge: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
    if (btnText) btnText.textContent = `Thực hiện Merge ${role === 'fe' ? 'Frontend' : 'Backend'}`;
  }
}
window.doExecuteMerge = doExecuteMerge;

async function doMergeAbort(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Hủy bỏ Merge (git merge --abort)',
    content: `Bạn có chắc muốn hủy bỏ tiến trình merge trên ${roleName}? Mọi xung đột chưa giải quyết sẽ được hoàn tác an toàn về trạng thái trước khi merge.`,
    okText: 'Hủy bỏ merge',
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/merge/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hủy bỏ merge thành công.' : 'Lỗi khi hủy merge.'));

    const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
    if (conflictBox) conflictBox.classList.add('hidden');

    await loadMergeInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
  } catch (err) {
    showToast('Lỗi kết nối khi hủy merge: ' + err.message);
  }
}
window.doMergeAbort = doMergeAbort;

async function doMergeContinue(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  showToast(`Đang kiểm tra và hoàn tất merge cho ${roleName}...`);

  try {
    const res = await fetch('/api/git/merge/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();

    if (data.has_conflicts) {
      showToast(`Vẫn còn file bị xung đột chưa giải quyết!`);
      const conflictFiles = document.getElementById(role === 'fe' ? 'feMergeConflictFiles' : 'beMergeConflictFiles');
      if (conflictFiles && data.conflicted_files) {
        conflictFiles.innerHTML = data.conflicted_files.map(f => `
          <div class="text-amber-200 font-mono text-[11px] flex items-center justify-between gap-2 py-0.5 border-b border-amber-900/40 last:border-0">
            <span class="flex items-center gap-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
              <span class="text-rose-400 font-bold shrink-0">[CÒN CONFLICT]</span>
              <span class="truncate" title="${escapeHtml(f)}">${escapeHtml(f)}</span>
            </span>
            <button type="button" onclick="copyToClipboard('${escapeHtml(f)}')" class="text-[10px] text-amber-400/80 hover:text-white px-1.5 py-0.5 rounded hover:bg-amber-800/40 shrink-0">Sao chép</button>
          </div>
        `).join('');
      }
      await antdAlert({
        title: 'Chưa giải quyết hết xung đột',
        content: `Vẫn còn ${data.conflicted_files?.length || 0} file đang bị xung đột.\n\nVui lòng chỉnh sửa code, xóa các conflict markers (<<<<<<, ======, >>>>>>), lưu file lại và thử lại.`,
        type: 'error'
      });
      return;
    }

    if (data.success) {
      showToast('Đã hoàn tất merge thành công!');
      const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
      const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
      const successText = document.getElementById(role === 'fe' ? 'feMergeSuccessText' : 'beMergeSuccessText');
      const successLogText = document.getElementById(role === 'fe' ? 'feMergeSuccessLogText' : 'beMergeSuccessLogText');

      if (conflictBox) conflictBox.classList.add('hidden');
      if (successBox) successBox.classList.remove('hidden');
      if (successText) successText.innerHTML = `Đã giải quyết xung đột và hoàn tất merge thành công.${data.head_commit ? ` Commit: <span class="font-mono text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800 text-[11px]">${escapeHtml(data.head_commit)}</span>` : ''}`;
      if (successLogText) {
        successLogText.innerHTML = formatGitOutputVsCode(data.output || 'Merge commit created successfully.');
      }

      await loadMergeInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
      if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
    } else {
      showToast(data.message || 'Không thể tiếp tục merge.');
    }
  } catch (err) {
    showToast('Lỗi khi tiếp tục merge: ' + err.message);
  }
}
window.doMergeContinue = doMergeContinue;

async function doMergePush(role) {
  const targetSelect = document.getElementById(role === 'fe' ? 'feMergeTargetSelect' : 'beMergeTargetSelect');
  const targetBranch = (targetSelect?.value || '').trim() || mergeBranchState[role].current_branch;
  if (!targetBranch) {
    showToast('Không xác định được nhánh đích để push.');
    return;
  }

  const confirmed = await antdConfirm({
    title: `Push code nhánh ${targetBranch}`,
    content: `Bạn có chắc muốn đẩy (git push) nhánh "${targetBranch}" lên remote repository của ${role === 'fe' ? 'Frontend' : 'Backend'}?`,
    okText: 'Push code'
  });
  if (!confirmed) return;

  const btnId = role === 'fe' ? 'btnFeMergePush' : 'btnBeMergePush';
  const btn = document.getElementById(btnId);
  if (btn) btn.disabled = true;

  showToast(`Đang push nhánh '${targetBranch}' lên remote...`);

  try {
    const res = await fetch('/api/git/push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role, branch: targetBranch })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Đã push nhánh '${targetBranch}' thành công lên remote!`);

      const prevBranch = (mergeBranchState[role]?.previous_branch || mergeBranchState[role]?.source_branch || '').trim();
      if (prevBranch && prevBranch !== targetBranch) {
        showToast(`Đang tự động chuyển về lại nhánh '${prevBranch}'...`);
        try {
          const coRes = await fetch('/api/git/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: role, branch: prevBranch, create_new: false })
          });
          const coData = await coRes.json();
          if (coData.success) {
            showToast(`Đã tự động quay về nhánh '${prevBranch}' thành công!`);
          } else {
            showToast(`Đã push thành công nhưng không thể quay về nhánh cũ: ${coData.message}`, 'warning');
          }
        } catch (coErr) {
          showToast(`Lỗi khi quay về nhánh cũ: ${coErr.message}`, 'error');
        }
      }

      // Đóng UI Merge Success Box
      const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
      if (successBox) successBox.classList.add('hidden');
      const returnWrap = document.getElementById(role === 'fe' ? 'feMergeReturnBranchWrap' : 'beMergeReturnBranchWrap');
      if (returnWrap) returnWrap.classList.add('hidden');

      await loadMergeInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    } else {
      showToast(`Push thất bại: ${data.message || 'Lỗi không xác định.'}`);
      await antdAlert({
        title: 'Push thất bại',
        content: data.message || 'Không thể push code lên remote.',
        type: 'error'
      });
    }
  } catch (err) {
    showToast('Lỗi kết nối khi push: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.doMergePush = doMergePush;

async function doReturnToPrevBranch(role) {
  const prevBranch = (mergeBranchState[role]?.previous_branch || mergeBranchState[role]?.source_branch || '').trim();
  if (!prevBranch) {
    showToast('Không tìm thấy thông tin nhánh lúc nãy để quay về.');
    return;
  }
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: `Quay về lại nhánh lúc nãy (${prevBranch})`,
    content: `Bạn có muốn checkout quay lại nhánh cũ "${prevBranch}" trên ${roleName}?`,
    okText: 'Quay về nhánh'
  });
  if (!confirmed) return;

  const btn = document.getElementById(role === 'fe' ? 'btnFeReturnPrevBranch' : 'btnBeReturnPrevBranch');
  if (btn) btn.disabled = true;

  showToast(`Đang chuyển về nhánh '${prevBranch}'...`);

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role, branch: prevBranch, create_new: false })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Đã quay về nhánh '${prevBranch}' thành công!`);
      const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
      if (successBox) successBox.classList.add('hidden');
      const returnWrap = document.getElementById(role === 'fe' ? 'feMergeReturnBranchWrap' : 'beMergeReturnBranchWrap');
      if (returnWrap) returnWrap.classList.add('hidden');
      await loadMergeInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    } else {
      showToast(`Không thể quay về nhánh: ${data.message || 'Lỗi checkout.'}`);
    }
  } catch (err) {
    showToast('Lỗi khi checkout nhánh: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.doReturnToPrevBranch = doReturnToPrevBranch;

// ==========================================
// WORK LOGS MANAGEMENT
// ==========================================
let cachedLogs = [];
let currentLogFilter = 'all';
let expandedLogIds = new Set();
let lastLogsSignature = '';

async function loadWorkLogs(force = false) {
  const container = document.getElementById('logListContainer');
  if (!container) return;
  try {
    const res = await fetch('/api/logs');
    const data = await res.json();
    const logsList = Array.isArray(data) ? data : [];
    const newSignature = logsList.length + '_' + (logsList[0]?.id || logsList[0]?.timestamp || logsList[0]?.created_at || '');

    if (!force && newSignature === lastLogsSignature) {
      return;
    }
    lastLogsSignature = newSignature;
    cachedLogs = logsList;
    renderFilteredLogs();
  } catch (err) {
    if (!cachedLogs || cachedLogs.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-cyan-400 text-xs">Lỗi tải nhật ký: ${escapeHtml(err.message)}</div>`;
    }
  }
}

function setLogTypeFilter(filterType) {
  currentLogFilter = filterType;
  const isLight = document.body.classList.contains('light-mode');
  const activeCls = 'active-log-filter px-2.5 py-1 rounded bg-[rgb(25,156,255)] text-white font-bold text-xs shadow-sm cursor-pointer select-none';
  const inactiveCls = isLight
    ? 'px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 text-xs transition cursor-pointer select-none'
    : 'px-2.5 py-1 rounded text-slate-300 hover:text-white text-xs transition cursor-pointer select-none';

  ['all', 'TASK', 'GIT'].forEach(t => {
    const btn = document.getElementById('logFilter_' + t);
    if (btn) {
      if (t === filterType) {
        btn.className = activeCls;
      } else {
        btn.className = inactiveCls;
      }
    }
  });
  renderFilteredLogs();
}

function renderFilteredLogs() {
  const container = document.getElementById('logListContainer');
  const searchInput = document.getElementById('logSearchInput');
  if (!container) return;

  const q = (searchInput?.value || '').toLowerCase().trim();

  const filtered = cachedLogs.filter(item => {
    const itemType = (item.type || (item.turns ? 'MULTI_TURN_DISCUSSION' : (item.target ? 'TASK' : 'OTHER'))).toUpperCase();
    if (currentLogFilter === 'TASK') {
      if (itemType.startsWith('GIT_')) return false;
    } else if (currentLogFilter === 'GIT') {
      if (!itemType.startsWith('GIT_')) return false;
    }

    if (!q) return true;
    const typeLabel = itemType === 'GIT_SYNC_PULL' ? 'đồng bộ git pull' : (itemType === 'GIT_SWITCH' ? 'chuyển nhánh' : (itemType.includes('MERGE') ? 'git merge gộp nhánh' : (itemType.includes('CHERRY') ? 'cherry-pick cherry pick' : '')));
    const text = `${item.title || ''} ${item.prompt || ''} ${item.topic || ''} ${item.task || ''} ${item.details || ''} ${item.result || ''} ${item.content || ''} ${item.reply || ''} ${item.target || ''} ${item.created_at || ''} ${typeLabel}`.toLowerCase();
    return text.includes(q);
  });

  if (filtered.length === 0) {
    container.innerHTML = `
          <div class="bg-[#13223f] border border-[#244170] rounded-lg p-12 text-center text-slate-400">
            <svg class="w-10 h-10 mx-auto text-slate-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div class="text-sm font-medium text-slate-300">Không tìm thấy bản ghi log nào</div>
            <p class="text-xs text-slate-500 mt-1">Các phiên làm việc hoặc thao tác Git sẽ tự động được ghi lại tại đây.</p>
          </div>
        `;
    return;
  }

  container.innerHTML = filtered.map((item, idx) => renderLogItemHtml(item, idx)).join('');
}

function formatLogTime(raw) {
  if (!raw) return '';
  if (raw.includes(' - ') && raw.length <= 25) return raw;
  try {
    const d = new Date(raw);
    if (!isNaN(d.getTime())) {
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      const ss = String(d.getSeconds()).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const MM = String(d.getMonth() + 1).padStart(2, '0');
      const yyyy = d.getFullYear();
      return `${hh}:${mm}:${ss} - ${dd}/${MM}/${yyyy}`;
    }
  } catch (e) { }
  return raw;
}

function renderLogItemHtml(item, idx) {
  const id = item.id || `log_${idx}`;
  const rawType = (item.type || (item.turns ? 'MULTI_TURN_DISCUSSION' : (item.target ? 'TASK' : 'OTHER'))).toUpperCase();
  const title = item.title || item.prompt || item.topic || item.task || (item.content ? item.content.slice(0, 100) : 'Phiên làm việc');
  const rawCreatedAt = item.created_at || item.timestamp || '';
  const createdAt = formatLogTime(rawCreatedAt);
  const status = (item.status || 'SUCCESS').toUpperCase();
  const duration = item.duration_sec ? formatDuration(item.duration_sec) : '';
  const target = item.target || (item.from ? `${item.from}->${item.to}` : '');

  let typeBadge = '';
  if (rawType === 'TASK') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#182c4f] border border-[#2e528f] text-cyan-300">Tác vụ</span>';
  } else if (rawType === 'FIX_BUG') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#13223f] border border-cyan-800 text-cyan-300">Fix Bug</span>';
  } else if (rawType === 'GIT_SYNC_PULL') {
    typeBadge = '<span class="badge-git-sync-pull px-2 py-0.5 rounded text-[11px] font-semibold">Đồng bộ Git (Pull)</span>';
  } else if (rawType === 'GIT_SWITCH' || rawType === 'GIT_PULL') {
    typeBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-950/80 border border-purple-800 text-purple-300">${rawType === 'GIT_PULL' ? 'Git Pull' : 'Chuyển Nhánh'}</span>`;
  } else if (rawType === 'GIT_PUSH') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/80 border border-emerald-800 text-emerald-300">Git Push</span>';
  } else if (rawType === 'GIT_MERGE') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-950/80 border border-blue-800 text-blue-300">Git Merge</span>';
  } else if (rawType === 'GIT_MERGE_CONTINUE') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-950/80 border border-blue-800 text-blue-300">Tiếp Tục Merge</span>';
  } else if (rawType === 'GIT_CHERRY_PICK') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-950/80 border border-indigo-800 text-indigo-300">Cherry-Pick</span>';
  } else if (rawType === 'GIT_CHERRY_PICK_ABORT' || rawType === 'GIT_MERGE_ABORT') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950/80 border border-rose-800 text-rose-300">Hủy Thao Tác</span>';
  } else if (rawType === 'GIT_CHERRY_PICK_CONTINUE') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/80 border border-emerald-800 text-emerald-300">Tiếp Tục Cherry-Pick</span>';
  } else if (['MULTI_TURN_DISCUSSION', 'AUTONOMOUS_CALL', 'COMMUNICATION'].includes(rawType) || item.from) {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#182c4f] border border-cyan-700 text-cyan-300">Trao đổi FE ↔ BE</span>';
  } else {
    typeBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300">${escapeHtml(rawType)}</span>`;
  }

  let targetBadge = '';
  if (target === 'fe') {
    targetBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950/70 border border-cyan-800 text-cyan-400">FE</span>';
  } else if (target === 'be') {
    targetBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-950/70 border border-emerald-800 text-emerald-400">BE</span>';
  } else if (target === 'both') {
    targetBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/70 border border-indigo-800 text-indigo-300">FE & BE</span>';
  } else if (item.from && item.to) {
    targetBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/70 border border-indigo-800 text-indigo-300">${item.from.toUpperCase()} → ${item.to.toUpperCase()}</span>`;
  }

  let statusBadge = '';
  if (status === 'SUCCESS' || status === 'COMPLETED') {
    statusBadge = '<span class="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Hoàn tất</span>';
  } else if (status === 'RUNNING') {
    statusBadge = '<span class="inline-flex items-center gap-1 text-[11px] text-cyan-400 font-medium"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span> Đang chạy</span>';
  } else {
    statusBadge = '<span class="inline-flex items-center gap-1 text-[11px] text-amber-400 font-medium"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> ' + escapeHtml(status) + '</span>';
  }

  const hasDetails = Boolean(item.details || item.result || item.content || item.reply || (item.turns && item.turns.length > 0));
  const isExpanded = expandedLogIds.has(String(id));

  return `
        <div id="logItemCard_${escapeHtml(id)}" class="log-item-card ${isExpanded ? 'log-item-active' : ''} bg-[#13223f] border border-[#244170] rounded-lg p-4 shadow-sm transition">
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0 cursor-pointer" onclick="toggleLogDetails('${escapeHtml(id)}')">
              <div class="flex flex-wrap items-center gap-2 mb-1.5">
                ${typeBadge}
                ${targetBadge}
                ${statusBadge}
                <span class="text-[11px] text-slate-300 font-mono ml-auto">${escapeHtml(createdAt)} ${duration ? '• ' + duration : ''}</span>
              </div>
              <div class="text-sm font-semibold text-white hover:text-cyan-300 transition truncate">
                ${escapeHtml(title)}
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <button type="button" onclick="deleteSingleLogItem('${escapeHtml(id)}', event)"
                class="log-item-delete-btn p-1.5 bg-[#ef4444] hover:bg-red-600 text-white rounded transition cursor-pointer flex items-center justify-center shadow-sm"
                title="Xóa bản ghi lịch sử này">
                <svg class="w-3.5 h-3.5 fill-none stroke-white" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="10" y2="17"></line>
                  <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
              </button>
              ${hasDetails ? `
                <div class="p-1.5 text-slate-400 hover:text-white rounded text-xs cursor-pointer flex items-center justify-center" onclick="toggleLogDetails('${escapeHtml(id)}')">
                  <svg id="logIcon_${escapeHtml(id)}" class="w-4 h-4 transform transition-transform ${isExpanded ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              ` : ''}
            </div>
          </div>

          ${hasDetails ? `
            <div id="logDetail_${escapeHtml(id)}" class="${isExpanded ? '' : 'hidden'} mt-3 pt-3 border-t border-[#244170] text-xs">
              ${item.prompt && item.prompt !== title ? `<div class="mb-2 text-slate-300 font-medium"><b>Yêu cầu:</b> ${escapeHtml(item.prompt)}</div>` : ''}
              ${item.content && item.content !== title ? `<div class="mb-2 text-slate-300 font-medium"><b>Nội dung:</b> ${escapeHtml(item.content)}</div>` : ''}
              ${item.details ? `<div class="bg-[#0e192c] rounded-md p-3 text-slate-200 font-mono text-[11.5px] whitespace-pre-wrap border border-[#244170] leading-relaxed">${escapeHtml(item.details)}</div>` : ''}
              ${item.result ? `<div class="bg-[#0e192c] rounded-md p-3 border border-[#244170] mt-2 text-slate-200 markdown-body">${safeMarkdown(item.result)}</div>` : ''}
              ${item.reply ? `<div class="bg-[#0e192c] rounded-md p-3 border border-[#244170] mt-2 text-slate-200 markdown-body"><b>Phản hồi:</b><br/>${safeMarkdown(item.reply)}</div>` : ''}
              ${item.turns && item.turns.length > 0 ? `
                <div class="space-y-2 mt-2">
                  <div class="text-[11px] font-semibold text-slate-300">Diễn biến hội thoại (${item.turns.length} lượt):</div>
                  ${item.turns.map(t => `
                    <div class="bg-[#0e192c] border border-[#244170] rounded-md p-3">
                      <div class="flex items-center justify-between text-[11px] mb-1">
                        <span class="font-bold ${t.speaker === 'fe' ? 'text-cyan-400' : 'text-emerald-400'}">${t.speaker === 'fe' ? 'Frontend Agent' : 'Backend Agent'}</span>
                        <span class="text-slate-400 font-mono">${t.timestamp || ''}</span>
                      </div>
                      <div class="text-slate-200 text-xs markdown-body">${safeMarkdown(t.content)}</div>
                    </div>
                  `).join('')}
                </div>
              ` : ''}
            </div>
          ` : ''}
        </div>
      `;
}

function toggleLogDetails(id) {
  id = String(id);
  const el = document.getElementById('logDetail_' + id);
  const icon = document.getElementById('logIcon_' + id);
  const card = document.getElementById('logItemCard_' + id);
  if (!el) return;
  if (el.classList.contains('hidden')) {
    el.classList.remove('hidden');
    if (icon) icon.classList.add('rotate-180');
    if (card) card.classList.add('log-item-active');
    expandedLogIds.add(id);
  } else {
    el.classList.add('hidden');
    if (icon) icon.classList.remove('rotate-180');
    if (card) card.classList.remove('log-item-active');
    expandedLogIds.delete(id);
  }
}

async function deleteSingleLogItem(logId, e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  const conf = await antdConfirm({
    title: 'Xóa bản ghi lịch sử?',
    content: 'Bạn có chắc chắn muốn xóa bản ghi lịch sử này? Thao tác này không thể hoàn tác.',
    danger: true,
    okText: 'Xóa',
    cancelText: 'Hủy'
  });
  if (!conf) return;

  try {
    const res = await fetch('/api/logs/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: logId })
    });
    const d = await res.json();
    if (d.success) {
      cachedLogs = cachedLogs.filter(item => String(item.id || item.timestamp) !== String(logId));
      lastLogsSignature = '';
      renderFilteredLogs();
      showToast('Đã xóa bản ghi lịch sử.');
    } else {
      showToast(d.message || 'Lỗi khi xóa bản ghi.', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi gửi yêu cầu xóa.', 'error');
  }
}
window.deleteSingleLogItem = deleteSingleLogItem;

async function clearLogs() {
  const confirmed = await antdConfirm({
    title: 'Xóa toàn bộ lịch sử',
    content: 'Bạn có chắc chắn muốn xóa toàn bộ lịch sử log? Thao tác này không thể hoàn tác.',
    danger: true,
    okText: 'Xóa vĩnh viễn'
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/logs/clear', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      cachedLogs = [];
      lastLogsSignature = '';
      expandedLogIds.clear();
      renderFilteredLogs();
    } else {
      await antdAlert({ title: 'Lỗi', content: 'Không thể xóa log: ' + data.message, type: 'error' });
    }
  } catch (err) {
    await antdAlert({ title: 'Lỗi', content: 'Lỗi xóa log: ' + err.message, type: 'error' });
  }
}

// --- CHẾ ĐỘ GIAO DIỆN DARK MODE / LIGHT MODE ---
function updateThemeUI(theme) {
  const btn = document.getElementById('themeToggleBtn');
  const icon = document.getElementById('themeToggleIcon');
  const text = document.getElementById('themeToggleText');
  if (theme === 'dark') {
    document.body.classList.remove('light-mode');
    document.body.classList.add('dark-mode');
    if (icon) icon.innerHTML = '🌙';
    if (text) text.textContent = 'Tối';
    if (btn) btn.title = 'Đang là chế độ Tối (Dark Mode). Nhấn để chuyển sang Sáng (Light Mode)';
  } else {
    document.body.classList.remove('dark-mode');
    document.body.classList.add('light-mode');
    if (icon) icon.innerHTML = '☀️';
    if (text) text.textContent = 'Sáng';
    if (btn) btn.title = 'Đang là chế độ Sáng (Light Mode). Nhấn để chuyển sang Tối (Dark Mode)';
  }
  if (typeof switchGitSubTab === 'function') {
    switchGitSubTab(activeGitSubTab, false);
  }
}

function toggleTheme() {
  const current = localStorage.getItem('easysalon_theme') || 'light';
  const nextTheme = current === 'light' ? 'dark' : 'light';
  localStorage.setItem('easysalon_theme', nextTheme);
  updateThemeUI(nextTheme);
  showToast(`Đã chuyển sang chế độ ${nextTheme === 'dark' ? 'Tối (Dark Mode)' : 'Sáng (Light Mode)'}.`);
}

function initTheme() {
  const savedTheme = localStorage.getItem('easysalon_theme') || 'light';
  updateThemeUI(savedTheme);
}

// --- TỰ ĐỘNG LƯU VÀ PHÍM TẮT CTRL+S ---
const DRAFT_STORAGE_KEY = 'easySalon_studio_drafts';

function getDraftData() {
  return {
    taskActionType: currentTaskActionType,
    taskTarget: document.getElementById('taskTargetSelect')?.value || 'both',
    taskPrompt: document.getElementById('taskPromptInput')?.value || '',
    taskLog: document.getElementById('taskLogInput')?.value || '',
    taskSkills: selectedTaskSkills,
    activeTab: activeTab || 'task',
    savedAt: new Date().toLocaleTimeString('vi-VN')
  };
}

function saveDraft(manual = false) {
  try {
    const data = getDraftData();
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(data));
    if (manual) showToast('Đã lưu dữ liệu nháp vào trình duyệt.');
  } catch (err) {
    console.warn('Lỗi khi lưu nháp:', err);
  }
}

function restoreDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) {
      if (!editingTaskId) {
        renderParallelTaskTabs();
      }
      renderFeedFilterTabs();
      updateTaskActionButtons();
      return;
    }
    const draft = JSON.parse(raw);
    if (!draft) {
      if (!editingTaskId) {
        renderParallelTaskTabs();
      }
      renderFeedFilterTabs();
      updateTaskActionButtons();
      return;
    }

    if (draft.taskActionType) {
      setTaskActionType(draft.taskActionType);
    }
    if (draft.taskPrompt) {
      const el = document.getElementById('taskPromptInput');
      if (el && !el.value) el.value = draft.taskPrompt;
    }
    if (draft.taskLog) {
      const el = document.getElementById('taskLogInput');
      if (el && !el.value) el.value = draft.taskLog;
    }
    if (draft.taskTarget) {
      const el = document.getElementById('taskTargetSelect');
      if (el) {
        el.value = draft.taskTarget;
      }
    }
    if (draft.taskSkills && Array.isArray(draft.taskSkills) && draft.taskSkills.length > 0) {
      selectedTaskSkills = draft.taskSkills;
      try {
        localStorage.setItem('easysalon_selected_skills', JSON.stringify(selectedTaskSkills));
      } catch (e) { }
    } else {
      try {
        const savedSkills = localStorage.getItem('easysalon_selected_skills');
        if (savedSkills) {
          const arr = JSON.parse(savedSkills);
          if (Array.isArray(arr) && arr.length > 0) {
            selectedTaskSkills = arr;
          }
        }
      } catch (e) { }
    }
    renderSkillPicker('task');
    updateFixBugPromptPreview();
    syncFormToCurrentTask();
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    renderFeedFilterTabs();
    updateTaskActionButtons();
  } catch (err) {
    console.warn('Lỗi phục hồi bản nháp:', err);
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    renderFeedFilterTabs();
    updateTaskActionButtons();
  }
}

function setupAutoSaveAndKeybindings() {
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
      e.preventDefault();
      saveDraft(true);
    }
  });

  const watchSelectors = [
    '#taskPromptInput', '#taskTargetSelect', '#taskLogInput'
  ];
  watchSelectors.forEach(sel => {
    const el = document.querySelector(sel);
    if (el) {
      el.addEventListener('input', () => saveDraft(false));
      el.addEventListener('change', () => saveDraft(false));
    }
  });
}

// Tự động cập nhật ngầm mỗi 2 giây
setInterval(() => {
  if (activeTab === 'task') pollStatus();
  else if (activeTab === 'log') loadWorkLogs(false);
}, 2000);

// --- AUTO-WATCH & HOT RELOAD KHI CÓ CODE MỚI ---
let _devWatchState = null;
let _devWatchReloading = false;

async function checkDevWatch() {
  if (_devWatchReloading) return;
  try {
    const res = await fetch('/api/dev-watch', { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    if (!data || !data.version) return;

    if (!_devWatchState) {
      _devWatchState = data;
      return;
    }

    if (data.version !== _devWatchState.version) {
      const prev = _devWatchState;
      _devWatchState = data;

      // 1. Luôn tự động lưu nháp dữ liệu đang nhập trước khi cập nhật
      saveDraft(false);

      // 2. Nếu chỉ thay đổi CSS (<style>), Hot-Swap CSS trực tiếp không cần reload trang
      if (data.css_hash !== prev.css_hash && data.dom_js_hash === prev.dom_js_hash && data.py_hash === prev.py_hash) {
        const htmlRes = await fetch(window.location.pathname, { cache: 'no-store' });
        if (htmlRes.ok) {
          const htmlText = await htmlRes.text();
          const doc = new DOMParser().parseFromString(htmlText, 'text/html');
          const newStyles = doc.querySelectorAll('head style');
          const oldStyles = document.querySelectorAll('head style');
          if (newStyles.length > 0 && newStyles.length === oldStyles.length) {
            newStyles.forEach((st, idx) => {
              oldStyles[idx].textContent = st.textContent;
            });
            showToast('Đã tự động cập nhật CSS mới (Hot Reload)');
            return;
          }
        }
      }

      // 3. Nếu thay đổi HTML / JS / Backend: lưu vị trí cuộn + con trỏ đang gõ rồi tự động đồng bộ
      _devWatchReloading = true;
      try {
        sessionStorage.setItem('easysalon_hot_reload_scroll', String(window.scrollY || 0));
        sessionStorage.setItem('easysalon_hot_reload_git_subtab', String(activeGitSubTab || 'switch'));
        const activeEl = document.activeElement;
        if (activeEl && activeEl.id && (activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'INPUT')) {
          sessionStorage.setItem('easysalon_hot_reload_focus', JSON.stringify({
            id: activeEl.id,
            start: activeEl.selectionStart || 0,
            end: activeEl.selectionEnd || 0
          }));
        }
        sessionStorage.setItem('easysalon_hot_reloaded', '1');
      } catch (e) { }
      window.location.reload();
    }
  } catch (err) {
    // Server có thể đang khởi động lại trong tích tắc (<100ms), bỏ qua lỗi tạm thời
  }
}

function setupDevHotReload() {
  try {
    if (sessionStorage.getItem('easysalon_hot_reloaded') === '1') {
      sessionStorage.removeItem('easysalon_hot_reloaded');
      const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
      const urlSubTab = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
      const savedSubTab = urlSubTab || sessionStorage.getItem('easysalon_hot_reload_git_subtab');
      sessionStorage.removeItem('easysalon_hot_reload_git_subtab');
      if (savedSubTab && activeTab === 'branch' && typeof switchGitSubTab === 'function') {
        switchGitSubTab(savedSubTab, false);
      }
      const savedScroll = parseInt(sessionStorage.getItem('easysalon_hot_reload_scroll') || '0', 10);
      if (savedScroll > 0) {
        setTimeout(() => window.scrollTo(0, savedScroll), 60);
      }
      const focusRaw = sessionStorage.getItem('easysalon_hot_reload_focus');
      if (focusRaw) {
        sessionStorage.removeItem('easysalon_hot_reload_focus');
        const fInfo = JSON.parse(focusRaw);
        const el = fInfo && fInfo.id ? document.getElementById(fInfo.id) : null;
        if (el) {
          setTimeout(() => {
            el.focus();
            if (typeof el.setSelectionRange === 'function') {
              el.setSelectionRange(fInfo.start, fInfo.end);
            }
          }, 80);
        }
      }
      setTimeout(() => showToast('Đã tự động cập nhật code mới'), 150);
    }
  } catch (e) { }

  checkDevWatch();
  setInterval(checkDevWatch, 1500);
}


window.addEventListener('DOMContentLoaded', () => {
  // Gán sự kiện click trực tiếp cho tất cả các tab
  TABS.forEach(t => {
    const btn = document.getElementById('tabBtn_' + t);
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        switchTab(t);
      });
    }
  });

  // 1. Ưu tiên endpoint trên URL (ví dụ: /git-control, /git-control/checkout-branch, /history, /diagram, /task)
  // 2. Nếu ở root (/ hoặc /index.html), kiểm tra tab trong localStorage
  // 3. Mặc định là 'task'
  let initialTab = (typeof window.getTabFromUrl === 'function') ? window.getTabFromUrl() : null;
  const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
  if (!initialTab || currentPath === '/' || currentPath === '/index.html') {
    try {
      const savedTab = localStorage.getItem('activeAgentStudioTab');
      if (savedTab && TABS.includes(savedTab)) {
        initialTab = savedTab;
      }
    } catch (e) { }
  }
  if (!initialTab || !TABS.includes(initialTab)) {
    initialTab = 'task';
  }

  // Xác định chính xác subtab nếu tab là branch
  const urlSubTab = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
  const targetSubTab = urlSubTab || window.initGitSubTab || 'pull_sync';
  if (initialTab === 'branch') {
    window.initGitSubTab = targetSubTab;
    activeGitSubTab = targetSubTab;
  }

  // Cập nhật URL đồng bộ với tab và git subtab (dùng replaceState để không tạo thêm entry thừa)
  let expectedPath = (window.TAB_ROUTES && window.TAB_ROUTES[initialTab]) || ('/' + initialTab);
  if (initialTab === 'branch') {
    const subRoutes = window.GIT_SUBTAB_ROUTES || {
      'pull_sync': '/git-control',
      'branch': '/git-control/checkout-branch',
      'switch': '/git-control/switch-branch',
      'cherry_pick': '/git-control/cherry-pick',
      'merge': '/git-control/merge'
    };
    expectedPath = subRoutes[targetSubTab] || '/git-control';
  }
  if (window.location.pathname !== expectedPath) {
    try {
      window.history.replaceState({ tab: initialTab, subTab: initialTab === 'branch' ? targetSubTab : null }, '', expectedPath);
    } catch (e) { }
  }
  switchTab(initialTab, false);
  if (initialTab === 'branch') {
    switchGitSubTab(targetSubTab, false);
  }
  initTheme();
  setupScrollListeners();
  loadCustomSkills();
  renderDiagramColumns();
  fetchDiagramData(false);
  loadGitBranchInfo();
  loadCherryPickInfo();
  loadPullSyncInfo();
  loadMergeInfo();
  setupAutoSaveAndKeybindings();
  restoreDraft();
  updateFixBugPromptPreview();
  setupDevHotReload();

  // Tự động kiểm tra cập nhật remote định kỳ 60s để cập nhật notification badge trên header
  setInterval(() => {
    checkSyncPullUpdates(true);
  }, 60000);
});

  </script>
</body>
</html>
"""


def main():
    import argparse
    parser = argparse.ArgumentParser(description="EasySalon Multi-Agent Studio Web Server")
    parser.add_argument('--port', type=int, default=WEB_PORT, help=f"Port to listen on (default {WEB_PORT})")
    parser.add_argument('--host', default=WEB_HOST, help=f"Host to bind to (default {WEB_HOST})")
    args = parser.parse_args()

    port = args.port
    host = args.host

    # Tự động kích hoạt 2 terminal ngầm của FE và BE
    print("\n" + "=" * 70)
    print(">> Kiểm tra và tự động kích hoạt 2 Terminal ngầm (FE & BE)...")
    ensure_background_terminals()
    print("=" * 70)

    class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True
        request_queue_size = 128

    try:
        server = ThreadedHTTPServer((host, port), AgentStudioHandler)
        from easysalon_studio import print_startup_banner
        print_startup_banner(host, port)
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
