#!/usr/bin/env python3
"""Các thao tác Git (chuyển nhánh, pull, sync-pull, cherry-pick, merge, push, lịch sử commit)."""

import os
import re
import subprocess
import threading
import time

_repo_locks = {}
_repo_locks_guard = threading.Lock()

def get_repo_lock(workspace: str) -> threading.Lock:
    """Trả về mutex lock tương ứng cho mỗi workspace để tuần tự hóa các thao tác Git, tránh xung đột index.lock."""
    ws_key = os.path.realpath(workspace) if workspace else ""
    with _repo_locks_guard:
        if ws_key not in _repo_locks:
            _repo_locks[ws_key] = threading.Lock()
        return _repo_locks[ws_key]


def is_git_running_in_dir(workspace: str) -> bool:
    """Kiểm tra xem có tiến trình git nào đang hoạt động trong workspace không."""
    try:
        ws_real = os.path.realpath(workspace) if workspace else ""
        if not ws_real:
            return False
        res = subprocess.run(['pgrep', '-x', 'git'], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            pids = res.stdout.strip().split()
            for pid in pids:
                try:
                    cwd = os.path.realpath(f'/proc/{pid}/cwd')
                    if cwd == ws_real or cwd.startswith(ws_real + '/'):
                        return True
                except Exception:
                    continue
        return False
    except Exception:
        return False


def clean_stale_git_locks(workspace: str, max_age_seconds: float = 10.0) -> list:
    """
    Tự động quét và dọn sạch các file .lock trong .git (index.lock, HEAD.lock, ...)
    nếu không có tiến trình git nào đang chạy hoặc file lock đã tồn tại quá lâu (stale).
    """
    if not workspace or not os.path.exists(workspace):
        return []
    dot_git = os.path.join(workspace, '.git')
    if not os.path.isdir(dot_git):
        return []

    lock_candidates = []
    # 1. Trực tiếp trong .git
    for fname in ('index.lock', 'HEAD.lock', 'config.lock', 'packed-refs.lock', 'shallow.lock', 'MERGE_HEAD.lock'):
        p = os.path.join(dot_git, fname)
        if os.path.exists(p):
            lock_candidates.append(p)

    # 2. Trong refs/
    refs_dir = os.path.join(dot_git, 'refs')
    if os.path.isdir(refs_dir):
        for root, _, files in os.walk(refs_dir):
            for f in files:
                if f.endswith('.lock'):
                    lock_candidates.append(os.path.join(root, f))

    if not lock_candidates:
        return []

    git_running = is_git_running_in_dir(workspace)
    now = time.time()
    removed = []

    for lp in lock_candidates:
        try:
            mtime = os.path.getmtime(lp)
            age = now - mtime
            if not git_running or age > max_age_seconds:
                os.remove(lp)
                removed.append(lp)
        except Exception:
            pass

    return removed

def format_git_relative_date(raw_date: str) -> str:
    """
    Chuẩn hóa thời gian tương đối Git (hoặc chuỗi thời gian) sang tiếng Việt ngắn gọn.
    Quy tắc đặc biệt: khi số phút vượt quá 60 phút (hoặc dạng X hour, Y min), hiển thị dạng XhYY (ví dụ 80p / 80 phút -> 1h20).
    """
    if not raw_date:
        return ''
    s = str(raw_date).strip()
    if not s:
        return ''

    is_ago = bool(re.search(r'\bago\b', s, re.IGNORECASE)) or ('trước' in s)
    clean_s = re.sub(r'\bago\b', '', s, flags=re.IGNORECASE)
    clean_s = re.sub(r'\btrước\b', '', clean_s, flags=re.IGNORECASE).strip()

    # Case 1: X hours, Y mins (e.g. 1 hour, 20 minutes)
    m_h_m = re.search(r'(\d+)\s*(?:hours?|giờ|hrs?|h)\s*(?:,?\s*and\s*)?,?\s*(\d+)\s*(?:minutes?|phút|mins?|min|m|p)?(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_h_m:
        h = int(m_h_m.group(1))
        m = int(m_h_m.group(2))
        h += m // 60
        m = m % 60
        res = f"{h}h{m:02d}" if m > 0 else f"{h}h"
        return f"{res} trước" if is_ago else res

    # Case 2: Only hours (e.g. 1 hour, 2 hours, 1h, 2h)
    m_h = re.search(r'(\d+)\s*(?:hours?|giờ|hrs?|h)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_h:
        h = int(m_h.group(1))
        res = f"{h}h"
        return f"{res} trước" if is_ago else res

    # Case 3: Only minutes (e.g. 80 minutes, 80 min, 80p, 80 phút)
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

    # Case 5: Days
    m_d = re.search(r'(\d+)\s*(?:days?|ngày)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_d:
        d = int(m_d.group(1))
        res = f"{d} ngày"
        return f"{res} trước" if is_ago else res

    # Case 6: Weeks
    m_w = re.search(r'(\d+)\s*(?:weeks?|tuần)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_w:
        w = int(m_w.group(1))
        res = f"{w} tuần"
        return f"{res} trước" if is_ago else res

    # Case 7: Months
    m_mo = re.search(r'(\d+)\s*(?:months?|tháng)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_mo:
        mo = int(m_mo.group(1))
        res = f"{mo} tháng"
        return f"{res} trước" if is_ago else res

    # Case 8: Years
    m_y = re.search(r'(\d+)\s*(?:years?|năm)(?:$|\s|[.,!])', clean_s, re.IGNORECASE)
    if m_y:
        y = int(m_y.group(1))
        res = f"{y} năm"
        return f"{res} trước" if is_ago else res

    lower_s = clean_s.lower()
    if 'just now' in lower_s or 'moment ago' in lower_s:
        return 'vừa xong'
    if 'yesterday' in lower_s:
        return 'hôm qua'

    return s

def get_git_info(workspace):
    try:
        branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, timeout=3).decode().strip()
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=workspace, timeout=3).decode().strip()
        return branch or 'detached', commit
    except Exception:
        return 'unknown', 'unknown'


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
        commit_date = format_git_relative_date(commit_info[2]) if len(commit_info) > 2 else ''
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
                'date': format_git_relative_date(parts[1]) if len(parts) > 1 else '',
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
    with get_repo_lock(workspace):
        clean_stale_git_locks(workspace)
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
            if res.returncode != 0 and 'index.lock' in msg:
                clean_stale_git_locks(workspace)
                time.sleep(0.5)
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
    Nếu switch_branch=False, chỉ tạo nhánh mới mà không checkout sang nhánh đó (git branch <branch> <base_branch>).
    """
    with get_repo_lock(workspace):
        clean_stale_git_locks(workspace)
        try:
            branch_name = branch_name.strip()
            base_branch = (base_branch or '').strip()
            if not branch_name:
                return False, "Tên nhánh không được để trống."

            # Trường hợp 1: Người dùng yêu cầu tạo nhánh mới
            if create_new:
                is_from_head = not base_branch or base_branch.upper() in ('HEAD', 'CURRENT', 'CURRENT_BRANCH')

                if not switch_branch:
                    # Chỉ tạo nhánh mà không chuyển
                    cmd = ['git', 'branch', branch_name]
                    if not is_from_head:
                        cmd.append(base_branch)

                    res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=25)
                    msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
                    if res.returncode == 0:
                        from_info = " từ nhánh hiện tại (HEAD)" if is_from_head else f" từ nhánh '{base_branch}'"
                        return True, f"Đã tạo nhánh mới '{branch_name}'{from_info} thành công (vẫn giữ nhánh hiện tại)."

                    if not is_from_head and ('not a valid object name' in msg or 'fatal: Cannot update paths' in msg or 'fatal: invalid reference' in msg):
                        cmd_rem = ['git', 'branch', branch_name, f'origin/{base_branch}']
                        res_rem = subprocess.run(cmd_rem, cwd=workspace, capture_output=True, text=True, timeout=25)
                        if res_rem.returncode == 0:
                            return True, f"Đã tạo nhánh mới '{branch_name}' từ remote 'origin/{base_branch}' thành công (vẫn giữ nhánh hiện tại)."

                    if 'already exists' in msg:
                        return False, f"Nhánh '{branch_name}' đã tồn tại sẵn."

                    return False, f"Không thể tạo nhánh mới '{branch_name}'. Chi tiết: {msg}"

                # Tạo nhánh và chuyển sang nhánh đó
                cmd = ['git', 'checkout', '-b', branch_name]
                if not is_from_head:
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
                    from_info = " từ nhánh hiện tại (HEAD)" if is_from_head else f" từ nhánh '{base_branch}'"
                    return True, f"Đã tạo mới và chuyển sang nhánh '{branch_name}'{from_info} thành công."

                # Nếu base_branch không tìm thấy ở local, thử với origin/<base_branch>
                if not is_from_head and ('not a valid object name' in msg or 'fatal: Cannot update paths' in msg or 'fatal: invalid reference' in msg):
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


def rename_git_branch(workspace: str, new_name: str, old_name: str = '') -> tuple[bool, str]:
    """
    Đổi tên nhánh git (git branch -m [old_name] <new_name>).
    Nếu old_name rỗng hoặc 'HEAD' hoặc 'CURRENT' hoặc 'CURRENT_BRANCH', đổi tên nhánh hiện tại:
    git branch -m <new_name>
    Nếu old_name được cung cấp, đổi tên nhánh old_name:
    git branch -m <old_name> <new_name>
    """
    with get_repo_lock(workspace):
        clean_stale_git_locks(workspace)
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
                    'date': format_git_relative_date(parts[3]),
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
    with get_repo_lock(workspace):
        clean_stale_git_locks(workspace)
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

        # Thu thập thông tin chi tiết của các commit trước khi cherry-pick
        picked_details = []
        for c in commit_list:
            try:
                c_info = subprocess.check_output(
                    ['git', 'log', '-1', '--pretty=format:%h - %s (%an, %ar)', c],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                picked_details.append(c_info if c_info else c)
            except Exception:
                picked_details.append(c)

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
            head_info = ''
            head_msg = ''
            try:
                head_info = subprocess.check_output(
                    ['git', 'log', '-1', '--pretty=format:%h - %s (%an, %ar)'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                head_msg = subprocess.check_output(['git', 'log', '-1', '--pretty=%B'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
            except Exception:
                pass

            commit_ids_str = ', '.join([c[:8] if len(c) > 8 else c for c in commit_list])
            return {
                'success': True,
                'current_branch': curr_branch,
                'message': f"Đã cherry-pick commit {commit_ids_str} vào nhánh '{curr_branch}' thành công!",
                'commit_message': head_msg or head_info,
                'output': output_msg,
                'status': status_info
            }
        else:
            is_conflict = status_info['has_conflicts'] or ('conflict' in output_msg.lower()) or ('fix conflicts' in output_msg.lower())
            msg_parts = []
            if is_conflict:
                msg_parts.append(f"Xảy ra xung đột (Conflict) khi cherry-pick vào nhánh '{curr_branch}'!")
                if picked_details:
                    msg_parts.append(f"Commit đang cherry-pick ({len(picked_details)}):")
                    for cd in picked_details:
                        msg_parts.append(f"• {cd}")
                if status_info.get('conflicted_files'):
                    msg_parts.append(f"Các file bị xung đột ({len(status_info['conflicted_files'])}):")
                    for cf in status_info['conflicted_files']:
                        msg_parts.append(f"• {cf}")
            else:
                msg_parts.append(f"Lỗi khi thực hiện cherry-pick vào nhánh '{curr_branch}':")
            if output_msg:
                msg_parts.append(output_msg)

            return {
                'success': False,
                'conflict': is_conflict,
                'current_branch': curr_branch,
                'conflicted_files': status_info['conflicted_files'],
                'message': '\n\n'.join(msg_parts).strip() if msg_parts else (output_msg or 'Lỗi khi thực hiện cherry-pick.'),
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

        # Kiểm tra xem remote origin/<target_branch> đã tồn tại chưa
        remote_ref = f'origin/{target_branch}'
        has_remote = subprocess.run(
            ['git', 'rev-parse', '--verify', remote_ref],
            cwd=workspace, capture_output=True, text=True
        ).returncode == 0

        unpushed_count = -1
        if has_remote:
            try:
                count_str = subprocess.check_output(
                    ['git', 'rev-list', f'{remote_ref}..{target_branch}', '--count'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                unpushed_count = int(count_str)
            except Exception:
                unpushed_count = -1

        # Nếu remote đã có nhánh và số commit chưa push bằng 0 (Everything up-to-date)
        if has_remote and unpushed_count == 0:
            return {
                'success': True,
                'already_pushed': True,
                'branch': target_branch,
                'message': f"Nhánh remote '{target_branch}' đã ở trạng thái mới nhất (Everything up-to-date), không có commit mới nào cần push."
            }

        # Nếu người dùng muốn sửa lại commit message trước khi push (chỉ thực hiện khi còn unpushed commit)
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
            is_already_synced = 'Everything up-to-date' in msg
            return {
                'success': True,
                'already_pushed': is_already_synced,
                'branch': target_branch,
                'message': (
                    f"Nhánh remote '{target_branch}' đã ở trạng thái mới nhất (Everything up-to-date)."
                    if is_already_synced
                    else f"Đã push code lên nhánh remote '{target_branch}' thành công!\n{msg}".strip()
                )
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
    Tự động xếp hàng đồng bộ và làm sạch file lock cũ để tránh lỗi '.git/index.lock: File exists'.
    """
    with get_repo_lock(workspace):
        clean_stale_git_locks(workspace)
        try:
            target_branch = target_branch.strip()
            if not target_branch:
                return {'success': False, 'conflict': False, 'message': 'Tên nhánh không được để trống.'}

            curr_branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()

            # Case 1: Người dùng chọn "ở yên nhánh hiện tại" (return_to_current=True) và ta đang ở nhánh khác:
            # Thử cập nhật trực tiếp qua Fast-Forward fetch (git fetch origin branch:branch)
            # Ưu điểm: KHÔNG chạm vào working tree, KHÔNG chuyển nhánh, an toàn tuyệt đối 100% với file uncommitted!
            if return_to_current and curr_branch and curr_branch != target_branch:
                try:
                    old_target_head = subprocess.check_output(['git', 'rev-parse', target_branch], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
                except Exception:
                    old_target_head = ''

                ff_res = subprocess.run(
                    ['git', 'fetch', 'origin', f'{target_branch}:{target_branch}'],
                    cwd=workspace, capture_output=True, text=True, timeout=40
                )
                ff_msg = (ff_res.stdout.strip() + '\n' + ff_res.stderr.strip()).strip()

                if ff_res.returncode == 0:
                    try:
                        new_target_head = subprocess.check_output(['git', 'rev-parse', target_branch], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
                    except Exception:
                        new_target_head = ''

                    pulled_commits = []
                    if old_target_head and new_target_head and old_target_head != new_target_head:
                        try:
                            log_raw = subprocess.check_output(
                                ['git', 'log', '--pretty=format:%h%x09%an%x09%ad%x09%s', '--date=short', f"{old_target_head}..{new_target_head}"],
                                cwd=workspace, text=True, stderr=subprocess.DEVNULL
                            ).strip()
                            for line in log_raw.splitlines():
                                parts = line.split('\t')
                                if len(parts) >= 4:
                                    pulled_commits.append({
                                        'hash': parts[0].strip(),
                                        'author': parts[1].strip(),
                                        'date': parts[2].strip(),
                                        'subject': parts[3].strip()
                                    })
                        except Exception:
                            pulled_commits = []

                    head_commit = subprocess.check_output(['git', 'log', '-1', '--oneline', target_branch], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
                    if pulled_commits:
                        commit_summary = "\n".join([f"• {c['hash']} ({c['author']}): {c['subject']}" for c in pulled_commits])
                        success_msg = f"Đã pull thành công {len(pulled_commits)} commit mới về nhánh '{target_branch}' (bạn vẫn ở yên nhánh '{curr_branch}'):\n{commit_summary}"
                    else:
                        success_msg = f"Đã pull thành công (Nhánh '{target_branch}' đã ở bản mới nhất, bạn vẫn ở yên nhánh '{curr_branch}')."

                    return {
                        'success': True,
                        'conflict': False,
                        'target_branch': target_branch,
                        'final_branch': curr_branch,
                        'returned_to_initial': True,
                        'message': success_msg,
                        'pulled_commits': pulled_commits,
                        'output': ff_msg or 'Fast-forward fetch up to date.',
                        'head_commit': head_commit
                    }
                # Nếu fetch refspec thất bại (ví dụ non-fast-forward do local có commit riêng), tiếp tục fallback về luồng checkout/pull

            # 1. Kiểm tra uncommitted changes ở working tree
            status_res = subprocess.run(['git', 'status', '--porcelain'], cwd=workspace, capture_output=True, text=True, timeout=10)
            dirty_files = [l.strip() for l in status_res.stdout.splitlines() if l.strip()]

            # 2. Checkout sang nhánh đích
            if curr_branch != target_branch:
                branches_raw = subprocess.check_output(['git', 'branch', '--list', target_branch], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
                if branches_raw:
                    checkout_cmd = ['git', 'checkout', target_branch]
                else:
                    checkout_cmd = ['git', 'checkout', '-b', target_branch, f'origin/{target_branch}']

                chk_res = subprocess.run(checkout_cmd, cwd=workspace, capture_output=True, text=True, timeout=30)
                if chk_res.returncode != 0 and 'index.lock' in (chk_res.stdout + chk_res.stderr):
                    clean_stale_git_locks(workspace)
                    time.sleep(0.5)
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
            try:
                old_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
            except Exception:
                old_head = ''

            pull_res = subprocess.run(['git', 'pull', 'origin', target_branch], cwd=workspace, capture_output=True, text=True, timeout=60)
            pull_output = (pull_res.stdout.strip() + '\n' + pull_res.stderr.strip()).strip()
            if pull_res.returncode != 0 and 'index.lock' in pull_output:
                clean_stale_git_locks(workspace)
                time.sleep(0.5)
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
                try:
                    new_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
                except Exception:
                    new_head = ''

                pulled_commits = []
                if old_head and new_head and old_head != new_head:
                    try:
                        log_raw = subprocess.check_output(
                            ['git', 'log', '--pretty=format:%h%x09%an%x09%ad%x09%s', '--date=short', f"{old_head}..{new_head}"],
                            cwd=workspace, text=True, stderr=subprocess.DEVNULL
                        ).strip()
                        for line in log_raw.splitlines():
                            parts = line.split('\t')
                            if len(parts) >= 4:
                                pulled_commits.append({
                                    'hash': parts[0].strip(),
                                    'author': parts[1].strip(),
                                    'date': parts[2].strip(),
                                    'subject': parts[3].strip()
                                })
                    except Exception:
                        pulled_commits = []

                head_commit = subprocess.check_output(['git', 'log', '-1', '--oneline'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
                final_branch = target_branch
                if return_to_current and curr_branch and curr_branch != target_branch:
                    ret_res = subprocess.run(['git', 'checkout', curr_branch], cwd=workspace, capture_output=True, text=True, timeout=30)
                    if ret_res.returncode == 0:
                        final_branch = curr_branch

                if pulled_commits:
                    commit_summary = "\n".join([f"• {c['hash']} ({c['author']}): {c['subject']}" for c in pulled_commits])
                    success_msg = f"Đã pull thành công {len(pulled_commits)} commit mới:\n{commit_summary}"
                else:
                    success_msg = "Đã pull thành công (Mã nguồn đã ở bản mới nhất, không có commit mới)."

                return {
                    'success': True,
                    'conflict': False,
                    'target_branch': target_branch,
                    'final_branch': final_branch,
                    'returned_to_initial': (final_branch == curr_branch and curr_branch != target_branch),
                    'message': success_msg,
                    'pulled_commits': pulled_commits,
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
    """Hủy bỏ (git merge --abort) khi gặp xung đột lúc pull hoặc merge."""
    try:
        res = subprocess.run(['git', 'merge', '--abort'], cwd=workspace, capture_output=True, text=True, timeout=20)
        msg = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            return {'success': True, 'message': 'Đã hủy bỏ merge thành công, workspace an toàn.'}
        return {'success': False, 'message': msg or 'Lỗi khi hủy bỏ merge.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def get_git_merge_status(workspace):
    """Kiểm tra xem repository có đang trong tiến trình merge hoặc bị conflict không."""
    try:
        merge_head = os.path.join(workspace, '.git', 'MERGE_HEAD')
        in_progress = os.path.exists(merge_head)

        status_raw = subprocess.check_output(
            ['git', 'status', '--short'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip()
        conflicted_files = []
        for line in status_raw.splitlines():
            line_str = line.strip()
            if line_str.startswith(('UU ', 'AA ', 'UD ', 'DU ', 'DD ', 'AU ', 'UA ')) or line.startswith(('UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA')):
                conflicted_files.append(line[3:].strip())

        curr_branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip() or 'HEAD detached'

        merge_msg = ''
        merge_msg_file = os.path.join(workspace, '.git', 'MERGE_MSG')
        if os.path.exists(merge_msg_file):
            try:
                with open(merge_msg_file, 'r', encoding='utf-8', errors='ignore') as f:
                    merge_msg = f.read().strip()
            except Exception:
                pass

        return {
            'in_progress': in_progress,
            'current_branch': curr_branch,
            'has_conflicts': len(conflicted_files) > 0,
            'conflicted_files': conflicted_files,
            'merge_msg': merge_msg,
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


def compute_merge_diff(workspace, base_commit=None, head_commit=None):
    """Tính toán chi tiết diff, thống kê file và nội dung code thay đổi của merge commit."""
    res = {
        'diff_stat': '',
        'files': [],
        'diff': '',
        'head_commit': '',
        'base_commit': base_commit or ''
    }
    if not workspace or not os.path.exists(workspace):
        return res
    try:
        if not head_commit:
            head_commit = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip()
        res['head_commit'] = head_commit

        diff_range = ''
        if base_commit and str(base_commit).strip() and str(base_commit).strip() != head_commit:
            diff_range = f"{str(base_commit).strip()}..{head_commit}"
        else:
            try:
                subprocess.check_call(
                    ['git', 'rev-parse', f"{head_commit}^1"],
                    cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                diff_range = f"{head_commit}^1..{head_commit}"
            except Exception:
                diff_range = head_commit

        if diff_range:
            try:
                res['diff_stat'] = subprocess.check_output(
                    ['git', 'diff', '--shortstat', diff_range],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                pass

            try:
                numstat_raw = subprocess.check_output(
                    ['git', 'diff', '--numstat', diff_range],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                if numstat_raw:
                    for line in numstat_raw.splitlines():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            res['files'].append({
                                'adds': int(parts[0]) if parts[0].isdigit() else 0,
                                'dels': int(parts[1]) if parts[1].isdigit() else 0,
                                'path': parts[2]
                            })
            except Exception:
                pass

            try:
                diff_raw = subprocess.check_output(
                    ['git', 'diff', '-U3', diff_range],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                )
                if len(diff_raw) > 80000:
                    res['diff'] = diff_raw[:80000] + "\n\n... (Diff quá dài, đã rút gọn) ..."
                else:
                    res['diff'] = diff_raw
            except Exception:
                pass
    except Exception:
        pass
    return res


def execute_git_merge(workspace, source_branch, target_branch=None, no_ff=False, commit_message=None, return_to_current=False):
    """
    Thực hiện merge code từ nhánh nguồn (source_branch) vào nhánh đích (target_branch).
    Nếu target_branch không được chỉ định hoặc trùng nhánh hiện tại, merge trực tiếp vào nhánh hiện tại.
    Nếu xảy ra xung đột (conflict), trả về danh sách file conflict và toàn bộ output log.
    """
    try:
        if not workspace or not os.path.exists(workspace):
            return {'success': False, 'conflict': False, 'message': 'Thư mục workspace không tồn tại.'}

        source_branch = (source_branch or '').strip()
        if not source_branch:
            return {'success': False, 'conflict': False, 'message': 'Vui lòng chọn nhánh nguồn (Source branch) muốn merge.'}

        # 1. Kiểm tra trạng thái working directory
        status_res = subprocess.run(['git', 'status', '--short'], cwd=workspace, capture_output=True, text=True)
        conflicted_now = []
        modified_files = []
        for line in status_res.stdout.splitlines():
            l_str = line.strip()
            if l_str.startswith(('UU ', 'AA ', 'UD ', 'DU ', 'DD ', 'AU ', 'UA ')) or line.startswith(('UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA')):
                conflicted_now.append(line[3:].strip())
            elif not l_str.startswith('??'):
                modified_files.append(line[3:].strip() if len(line) > 3 else l_str)

        if conflicted_now:
            return {
                'success': False,
                'conflict': True,
                'conflicted_files': conflicted_now,
                'message': f"Repository đang có {len(conflicted_now)} file bị xung đột chưa giải quyết. Vui lòng hoàn tất hoặc hủy trước."
            }

        # 2. Lấy nhánh hiện tại
        curr_branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip() or 'HEAD detached'

        dest_branch = (target_branch or '').strip() or curr_branch

        if source_branch == dest_branch:
            return {
                'success': False,
                'conflict': False,
                'message': f"Nhánh nguồn và nhánh đích giống nhau ('{source_branch}'). Không thể merge chính nó."
            }

        # 3. Checkout sang nhánh đích nếu hiện tại đang ở nhánh khác
        if curr_branch != dest_branch:
            co_res = subprocess.run(
                ['git', 'checkout', dest_branch],
                cwd=workspace, capture_output=True, text=True, timeout=30
            )
            if co_res.returncode != 0:
                co_err = (co_res.stderr.strip() or co_res.stdout.strip())
                return {
                    'success': False,
                    'conflict': False,
                    'message': f"Không thể checkout nhánh đích '{dest_branch}': {co_err}"
                }

        # Lưu lại commit trước khi merge trên nhánh đích
        dest_before_commit = ''
        try:
            dest_before_commit = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            pass

        # Lấy danh sách các commit từ source_branch chuẩn bị gộp vào dest_branch
        incoming_commits = []
        try:
            commits_raw = subprocess.check_output(
                ['git', 'log', f"{dest_branch}..{source_branch}", '--pretty=format:%h - %s (%an, %ar)'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if commits_raw:
                incoming_commits = [line.strip() for line in commits_raw.splitlines() if line.strip()]
        except Exception:
            pass

        # 4. Thực hiện lệnh git merge
        cmd = ['git', 'merge']
        if no_ff:
            cmd.append('--no-ff')
        if commit_message and commit_message.strip():
            cmd.extend(['-m', commit_message.strip()])
        cmd.append(source_branch)

        merge_res = subprocess.run(
            cmd,
            cwd=workspace, capture_output=True, text=True, timeout=60
        )
        merge_output = (merge_res.stdout.strip() + '\n' + merge_res.stderr.strip()).strip()

        # 5. Kiểm tra conflict
        post_status = subprocess.run(['git', 'status', '--short'], cwd=workspace, capture_output=True, text=True)
        conflicted_files = []
        for line in post_status.stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith(('UU ', 'AA ', 'UD ', 'DU ', 'DD ', 'AU ', 'UA ')) or line.startswith(('UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA')):
                conflicted_files.append(line[3:].strip())

        merge_head_exists = os.path.exists(os.path.join(workspace, '.git', 'MERGE_HEAD'))
        is_conflict = len(conflicted_files) > 0 or merge_head_exists or ('conflict' in merge_output.lower()) or ('fix conflicts' in merge_output.lower())

        if is_conflict:
            msg_parts = [f"Xảy ra xung đột (Conflict) khi merge nhánh '{source_branch}' vào '{dest_branch}'!"]
            if incoming_commits:
                msg_parts.append(f"Các commit đang gộp ({len(incoming_commits)}):")
                for c in incoming_commits[:10]:
                    msg_parts.append(f"• {c}")
                if len(incoming_commits) > 10:
                    msg_parts.append(f"... và {len(incoming_commits) - 10} commit khác.")
            if conflicted_files:
                msg_parts.append(f"Các file bị xung đột ({len(conflicted_files)} file):")
                for cf in conflicted_files:
                    msg_parts.append(f"• {cf}")
            if merge_output:
                msg_parts.append(f"Console Output:\n{merge_output}")

            return {
                'success': False,
                'conflict': True,
                'initial_branch': curr_branch,
                'source_branch': source_branch,
                'target_branch': dest_branch,
                'conflicted_files': conflicted_files,
                'output': merge_output,
                'message': '\n\n'.join(msg_parts).strip()
            }

        if merge_res.returncode == 0:
            head_commit = ''
            head_commit_oneline = ''
            try:
                head_commit = subprocess.check_output(
                    ['git', 'log', '-1', '--pretty=format:%h - %s (%an, %ar)'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
                head_commit_oneline = subprocess.check_output(
                    ['git', 'log', '-1', '--oneline'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                pass

            # Nếu incoming_commits trống nhưng có commit mới được gộp
            if not incoming_commits and dest_before_commit:
                try:
                    after_diff = subprocess.check_output(
                        ['git', 'log', f"{dest_before_commit}..HEAD", '--pretty=format:%h - %s (%an, %ar)'],
                        cwd=workspace, text=True, stderr=subprocess.DEVNULL
                    ).strip()
                    if after_diff:
                        incoming_commits = [line.strip() for line in after_diff.splitlines() if line.strip()]
                except Exception:
                    pass

            merge_diff_data = compute_merge_diff(workspace, base_commit=dest_before_commit, head_commit=head_commit_oneline or 'HEAD')

            final_branch = dest_branch
            returned_to_initial = False
            if return_to_current and curr_branch and curr_branch != dest_branch:
                ret_res = subprocess.run(['git', 'checkout', curr_branch], cwd=workspace, capture_output=True, text=True, timeout=30)
                if ret_res.returncode == 0:
                    final_branch = curr_branch
                    returned_to_initial = True

            msg_parts = [f"Đã merge thành công nhánh '{source_branch}' vào '{dest_branch}'."]
            if head_commit:
                msg_parts.append(f"HEAD commit mới:\n• {head_commit}")

            if incoming_commits:
                msg_parts.append(f"Danh sách commit được gộp ({len(incoming_commits)} commit):")
                for c in incoming_commits[:20]:
                    msg_parts.append(f"• {c}")
                if len(incoming_commits) > 20:
                    msg_parts.append(f"... và {len(incoming_commits) - 20} commit khác.")
            elif 'Already up to date' in merge_output or 'already up-to-date' in merge_output.lower():
                msg_parts.append("Trạng thái: Nhánh đích đã cập nhật đầy đủ, không có commit mới.")

            if merge_output and merge_output != 'Already up to date.':
                msg_parts.append(f"Chi tiết thay đổi:\n{merge_output}")

            if returned_to_initial and curr_branch:
                msg_parts.append(f"(Đã quay về nhánh ban đầu: '{curr_branch}')")

            return {
                'success': True,
                'conflict': False,
                'initial_branch': curr_branch,
                'source_branch': source_branch,
                'target_branch': dest_branch,
                'final_branch': final_branch,
                'returned_to_initial': returned_to_initial,
                'head_commit': head_commit_oneline or head_commit,
                'head_commit_detail': head_commit,
                'commits_merged': incoming_commits,
                'output': merge_output or 'Already up to date.',
                'message': '\n\n'.join(msg_parts).strip(),
                'merge_diff': merge_diff_data
            }
        else:
            return {
                'success': False,
                'conflict': False,
                'initial_branch': curr_branch,
                'source_branch': source_branch,
                'target_branch': dest_branch,
                'output': merge_output,
                'message': merge_output or f"Merge thất bại khi gộp '{source_branch}' vào '{dest_branch}'."
            }
    except subprocess.TimeoutExpired:
        return {'success': False, 'conflict': False, 'message': f"Quá thời gian quy định (timeout 60s) khi merge nhánh '{source_branch}'."}
    except Exception as e:
        return {'success': False, 'conflict': False, 'message': str(e)}


def continue_git_merge(workspace, commit_message=None):
    """Tiếp tục (Continue/Commit) sau khi người dùng đã giải quyết xong xung đột."""
    try:
        if not workspace or not os.path.exists(workspace):
            return {'success': False, 'message': 'Thư mục workspace không tồn tại.'}

        status_raw = subprocess.check_output(
            ['git', 'status', '--short'],
            cwd=workspace, text=True, stderr=subprocess.DEVNULL
        ).strip()
        conflicted_files = []
        for line in status_raw.splitlines():
            line_str = line.strip()
            if line_str.startswith(('UU ', 'AA ', 'UD ', 'DU ', 'DD ', 'AU ', 'UA ')) or line.startswith(('UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA')):
                conflicted_files.append(line[3:].strip())

        if conflicted_files:
            return {
                'success': False,
                'has_conflicts': True,
                'conflicted_files': conflicted_files,
                'message': f"Vẫn còn {len(conflicted_files)} file đang bị xung đột chưa được giải quyết xong."
            }

        cmd = ['git', 'merge', '--continue']
        res = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=30)
        if res.returncode != 0:
            if commit_message and commit_message.strip():
                res = subprocess.run(['git', 'commit', '-m', commit_message.strip()], cwd=workspace, capture_output=True, text=True, timeout=30)
            else:
                res = subprocess.run(['git', 'commit', '--no-edit'], cwd=workspace, capture_output=True, text=True, timeout=30)

        output = (res.stdout.strip() + '\n' + res.stderr.strip()).strip()
        if res.returncode == 0:
            head_commit = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%h - %s (%an, %ar)'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
            merge_diff_data = compute_merge_diff(workspace, head_commit='HEAD')
            msg_parts = ['Đã hoàn tất merge sau khi xử lý xung đột thành công!']
            if head_commit:
                msg_parts.append(f"HEAD commit mới:\n• {head_commit}")
            if output:
                msg_parts.append(f"Chi tiết:\n{output}")
            return {
                'success': True,
                'message': '\n\n'.join(msg_parts).strip(),
                'output': output,
                'head_commit': head_commit,
                'merge_diff': merge_diff_data
            }
        return {'success': False, 'message': output or 'Không thể hoàn tất merge.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def check_sync_pull_status(workspace, branches=('staging', 'master', 'beta'), do_fetch=True):
    """
    Kiểm tra xem các nhánh chỉ định (mặc định staging, master và beta)
    có commit mới nào trên remote (origin/staging, origin/master) cần pull về không.
    Trả về dict chi tiết cho từng nhánh gồm:
    - exists: bool (nhánh local có tồn tại không)
    - remote_exists: bool (nhánh remote có tồn tại không)
    - needs_pull: bool (có commit mới cần pull không)
    - behind_count: int (số commit cần pull)
    - ahead_count: int (số commit local chưa push)
    - diff_stat: str (tóm tắt thay đổi files)
    - commits: list[dict] (danh sách commit cần pull: hash, subject, author, date)
    - latest_commit: dict (commit mới nhất trên remote)
    """
    results = {}
    if not workspace or not os.path.exists(workspace):
        return results

    current_author = ""
    current_email = ""
    try:
        current_author = subprocess.check_output(['git', 'config', 'user.name'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        pass
    try:
        current_email = subprocess.check_output(['git', 'config', 'user.email'], cwd=workspace, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        pass

    def _is_me(name):
        if not name:
            return False
        n_low = name.lower().strip()
        c_low = current_author.lower().strip() if current_author else ""
        e_low = current_email.lower().strip() if current_email else ""
        if c_low and (c_low in n_low or n_low in c_low):
            return True
        if e_low and (e_low in n_low or n_low in e_low):
            return True
        return bool('thiết' in n_low or 'thiet' in n_low)

    if do_fetch:
        repo_lock = get_repo_lock(workspace)
        acquired = repo_lock.acquire(timeout=1.0)
        if acquired:
            try:
                clean_stale_git_locks(workspace)
                fetch_targets = [b.strip() for b in branches if b.strip()]
                subprocess.run(
                    ['git', 'fetch', '-q', 'origin'] + fetch_targets,
                    cwd=workspace, capture_output=True, timeout=12
                )
            except Exception:
                pass
            finally:
                repo_lock.release()

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

        # 1. Kiểm tra remote origin/{br}
        rem_check = subprocess.run(
            ['git', 'rev-parse', '--verify', f'origin/{br}'],
            cwd=workspace, capture_output=True, text=True
        )
        if rem_check.returncode == 0:
            branch_res['remote_exists'] = True
        else:
            results[br] = branch_res
            continue

        # 2. Lấy commit mới nhất trên remote
        try:
            latest_raw = subprocess.check_output(
                ['git', 'log', '-1', '--format=%h|%s|%an|%cr|%ct|%cI', f'origin/{br}'],
                cwd=workspace, text=True, stderr=subprocess.DEVNULL
            ).strip()
            if latest_raw:
                p = latest_raw.split('|', 5)
                author_val = p[2].strip() if len(p) > 2 else ''
                epoch_sec = int(p[4].strip()) if len(p) > 4 and p[4].strip().isdigit() else None
                branch_res['latest_commit'] = {
                    'hash': p[0].strip(),
                    'subject': p[1].strip() if len(p) > 1 else '',
                    'author': author_val,
                    'is_me': _is_me(author_val),
                    'date': format_git_relative_date(p[3].strip()) if len(p) > 3 else '',
                    'timestamp': epoch_sec * 1000 if epoch_sec else None,
                    'iso_date': p[5].strip() if len(p) > 5 else ''
                }
        except Exception:
            pass

        # 3. Kiểm tra local branch {br}
        loc_check = subprocess.run(
            ['git', 'rev-parse', '--verify', br],
            cwd=workspace, capture_output=True, text=True
        )
        if loc_check.returncode == 0:
            branch_res['exists'] = True
        else:
            # Nhánh local chưa có, cần tạo và pull từ remote
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

        # 4. Đếm số commit behind (cần pull) và ahead
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

        # 5. Nếu cần pull (behind_count > 0), lấy danh sách commit và diff stat
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
                    ['git', 'log', f'{br}..origin/{br}', '--format=%h|%s|%an|%cr|%ct|%cI', '-n', '15'],
                    cwd=workspace, text=True, stderr=subprocess.DEVNULL
                ).strip().splitlines()
                commit_list = []
                for line in commits_raw:
                    if not line.strip():
                        continue
                    p = line.split('|', 5)
                    h = p[0].strip()
                    subject_val = p[1].strip() if len(p) > 1 else ''
                    author_val = p[2].strip() if len(p) > 2 else ''
                    date_val = p[3].strip() if len(p) > 3 else ''
                    epoch_sec = int(p[4].strip()) if len(p) > 4 and p[4].strip().isdigit() else None
                    iso_str = p[5].strip() if len(p) > 5 else ''

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
                                    'timestamp': epoch_sec * 1000 if epoch_sec else None,
                                    'iso_date': iso_str
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
                        'timestamp': epoch_sec * 1000 if epoch_sec else None,
                        'iso_date': iso_str,
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
            'current': current_code,
            'incoming': incoming_code,
            'start': m.start(),
            'end': m.end()
        })
        lines_before += m.group(0).count('\n')
        last_end = m.end()
    return blocks


def resolve_conflict_content(content, action, block_index=None):
    """
    Giải quyết khối conflict trong content:
    - action: 'current' / 'accept_current' | 'incoming' / 'accept_incoming' | 'both' / 'accept_both'
    - block_index: int (chỉ giải quyết 1 khối cụ thể) hoặc None/'all' (giải quyết tất cả các khối)
    """
    pattern = re.compile(
        r'(<<<<<<<[^\n]*\n)([\s\S]*?)(?:\|\|\|\|\|\|\|[^\n]*\n[\s\S]*?)?(=======\n)([\s\S]*?)(>>>>>>>[^\n]*(?:\n|$))'
    )
    matches = list(pattern.finditer(content))
    if not matches:
        return content

    action_norm = str(action or '').lower().replace('accept_', '').strip()
    if action_norm in ('current', 'ours', 'head'):
        target_mode = 'current'
    elif action_norm in ('incoming', 'theirs'):
        target_mode = 'incoming'
    elif action_norm in ('both', 'all'):
        target_mode = 'both'
    else:
        target_mode = action_norm

    if block_index is not None and str(block_index).lower() != 'all':
        try:
            idx = int(block_index)
        except (ValueError, TypeError):
            idx = -1
        if 0 <= idx < len(matches):
            m = matches[idx]
            cur = m.group(2)
            inc = m.group(4)
            if target_mode == 'current':
                repl = cur
            elif target_mode == 'incoming':
                repl = inc
            elif target_mode == 'both':
                repl = cur + inc
            else:
                return content
            return content[:m.start()] + repl + content[m.end():]
        return content

    # Giải quyết toàn bộ khối trong file
    def repl_all(m):
        cur = m.group(2)
        inc = m.group(4)
        if target_mode == 'current':
            return cur
        elif target_mode == 'incoming':
            return inc
        elif target_mode == 'both':
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
        'conflict_blocks': blocks,
        'raw_content': content
    }


def resolve_git_conflict_file(workspace, file_path, action, block_index=None):
    """
    Thực hiện giải quyết xung đột (Current/Incoming/Both) trên 1 file hoặc toàn bộ file ('all')
    và tự động git add nếu đã hết conflict.
    """
    if not workspace or not file_path:
        return {'success': False, 'message': 'Thiếu workspace hoặc đường dẫn file.'}

    action_norm = str(action or '').lower().replace('accept_', '').strip()
    if action_norm in ('current', 'ours', 'head'):
        canonical_action = 'accept_current'
    elif action_norm in ('incoming', 'theirs'):
        canonical_action = 'accept_incoming'
    elif action_norm in ('both', 'all'):
        canonical_action = 'accept_both'
    elif action_norm == 'stage_only':
        canonical_action = 'stage_only'
    else:
        canonical_action = action

    # Trường hợp giải quyết hàng loạt toàn bộ file bị conflict
    if file_path in ('all', '*'):
        status_info = get_git_active_conflict_status(workspace)
        files = status_info.get('conflicted_files', [])
        resolved_count = 0
        for f in files:
            res = resolve_git_conflict_file(workspace, f, canonical_action, block_index=None)
            if res.get('success'):
                resolved_count += 1
        try:
            subprocess.run(['git', 'add', '-A'], cwd=workspace, capture_output=True)
        except Exception:
            pass
        post_status = get_git_active_conflict_status(workspace)
        return {
            'success': True,
            'file_path': 'all',
            'action_applied': canonical_action,
            'resolved_files_count': resolved_count,
            'all_conflicts_resolved': len(post_status['conflicted_files']) == 0,
            'conflicted_files': post_status['conflicted_files']
        }

    clean_path = os.path.normpath(file_path).lstrip('/')
    abs_file = os.path.abspath(os.path.join(workspace, clean_path))
    abs_ws = os.path.abspath(workspace)
    if not abs_file.startswith(abs_ws):
        return {'success': False, 'message': 'Đường dẫn file không hợp lệ.'}

    # Nếu chỉ muốn stage_only (đánh dấu đã giải quyết thủ công)
    if canonical_action == 'stage_only':
        try:
            subprocess.run(['git', 'add', clean_path], cwd=workspace, check=True, capture_output=True)
            status_info = get_git_active_conflict_status(workspace)
            return {
                'success': True,
                'file_path': clean_path,
                'action_applied': 'stage_only',
                'file_staged': True,
                'all_conflicts_resolved': len(status_info['conflicted_files']) == 0,
                'conflicted_files': status_info['conflicted_files']
            }
        except Exception as e:
            return {'success': False, 'message': f'Lỗi git add: {str(e)}'}

    # Nếu chọn giải quyết toàn bộ file bằng Current (Ours) hoặc Incoming (Theirs)
    if block_index is None and canonical_action in ('accept_current', 'accept_incoming'):
        flag = '--ours' if canonical_action == 'accept_current' else '--theirs'
        try:
            co_res = subprocess.run(['git', 'checkout', flag, '--', clean_path], cwd=workspace, capture_output=True, text=True)
            if co_res.returncode == 0:
                subprocess.run(['git', 'add', clean_path], cwd=workspace, check=True, capture_output=True)
                status_info = get_git_active_conflict_status(workspace)
                return {
                    'success': True,
                    'file_path': clean_path,
                    'action_applied': canonical_action,
                    'block_index': None,
                    'remaining_conflicts_in_file': 0,
                    'file_staged': True,
                    'all_conflicts_resolved': len(status_info['conflicted_files']) == 0,
                    'conflicted_files': status_info['conflicted_files']
                }
        except Exception:
            pass

    if not os.path.exists(abs_file):
        return {'success': False, 'message': f'Không tìm thấy file: {clean_path}'}

    try:
        with open(abs_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {'success': False, 'message': f'Không thể đọc file: {str(e)}'}

    new_content = resolve_conflict_content(content, canonical_action, block_index=block_index)
    try:
        with open(abs_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        return {'success': False, 'message': f'Không thể ghi file: {str(e)}'}

    # Kiểm tra xem file còn marker conflict không
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
        'action_applied': canonical_action,
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


def get_file_blame_and_author_details(workspace: str, file_path: str) -> dict:
    """
    Trích xuất thông tin Git blame và tác giả (Creator, Last Modifier, Line-by-line blame, Commit bodies).
    Tương tự như GitLens trên VS Code để phục vụ tính năng hover và hiển thị tác giả.
    """
    if file_path.startswith(workspace):
        clean_path = os.path.relpath(file_path, workspace)
    else:
        clean_path = os.path.normpath(file_path).lstrip('/')
    abs_file = os.path.abspath(os.path.join(workspace, clean_path))
    if not os.path.exists(abs_file):
        return {'success': False, 'message': f'File không tồn tại: {file_path}'}

    current_author = ""
    current_email = ""
    try:
        current_author = subprocess.run(['git', 'config', 'user.name'], cwd=workspace, capture_output=True, text=True, timeout=1.5).stdout.strip()
        current_email = subprocess.run(['git', 'config', 'user.email'], cwd=workspace, capture_output=True, text=True, timeout=1.5).stdout.strip()
    except Exception:
        pass

    def _is_me(name):
        if not name:
            return False
        n_low = name.lower().strip()
        c_low = current_author.lower().strip() if current_author else ""
        e_low = current_email.lower().strip() if current_email else ""
        if c_low and (c_low in n_low or n_low in c_low):
            return True
        if e_low and (e_low in n_low or n_low in e_low):
            return True
        return bool('thiết' in n_low or 'thiet' in n_low)

    creator = None
    last_mod = None

    try:
        c1 = subprocess.run(
            ['git', 'log', '--reverse', '--format=%h%x00%an%x00%ae%x00%at%x00%s%x00%b', '-1', '--', clean_path],
            cwd=workspace, capture_output=True, text=True, timeout=3.0
        )
        if c1.returncode == 0 and c1.stdout.strip():
            parts = c1.stdout.strip().split('\x00')
            if len(parts) >= 5:
                author_name = parts[1]
                creator = {
                    'hash': parts[0],
                    'author': 'You' if _is_me(author_name) else author_name,
                    'raw_author': author_name,
                    'is_me': _is_me(author_name),
                    'email': parts[2],
                    'time': int(parts[3]) if parts[3].isdigit() else 0,
                    'summary': parts[4],
                    'body': parts[5].strip() if len(parts) > 5 else ''
                }
    except Exception:
        pass

    try:
        c2 = subprocess.run(
            ['git', 'log', '-1', '--format=%h%x00%an%x00%ae%x00%at%x00%s%x00%b', '--', clean_path],
            cwd=workspace, capture_output=True, text=True, timeout=3.0
        )
        if c2.returncode == 0 and c2.stdout.strip():
            parts = c2.stdout.strip().split('\x00')
            if len(parts) >= 5:
                author_name = parts[1]
                last_mod = {
                    'hash': parts[0],
                    'author': 'You' if _is_me(author_name) else author_name,
                    'raw_author': author_name,
                    'is_me': _is_me(author_name),
                    'email': parts[2],
                    'time': int(parts[3]) if parts[3].isdigit() else 0,
                    'summary': parts[4],
                    'body': parts[5].strip() if len(parts) > 5 else ''
                }
    except Exception:
        pass

    lines = {}
    commits = {}
    try:
        res = subprocess.run(
            ['git', 'blame', '--line-porcelain', '--', clean_path],
            cwd=workspace, capture_output=True, text=True, timeout=5.0
        )
        if res.returncode == 0 and res.stdout:
            cur_hash = ''
            cur_author = ''
            cur_mail = ''
            cur_time = 0
            cur_summary = ''
            line_num = 1

            for raw in res.stdout.splitlines():
                if raw.startswith('\t'):
                    is_uncommitted = cur_hash.startswith('00000000') or not cur_hash
                    author_display = 'You' if (is_uncommitted or _is_me(cur_author)) else cur_author
                    lines[line_num] = {
                        'hash': 'uncommitted' if is_uncommitted else cur_hash[:9],
                        'author': author_display,
                        'raw_author': cur_author,
                        'is_me': is_uncommitted or _is_me(cur_author),
                        'email': cur_mail,
                        'time': cur_time,
                        'summary': 'Uncommitted changes' if is_uncommitted else cur_summary
                    }
                    line_num += 1
                elif raw.startswith('author '):
                    cur_author = raw[7:].strip()
                elif raw.startswith('author-mail '):
                    cur_mail = raw[12:].strip('<> ')
                elif raw.startswith('author-time '):
                    try:
                        cur_time = int(raw[12:].strip())
                    except Exception:
                        cur_time = 0
                elif raw.startswith('summary '):
                    cur_summary = raw[8:].strip()
                elif len(raw.split(' ')[0]) == 40:
                    cur_hash = raw.split(' ')[0]

            unique_hashes = list({v['hash'] for v in lines.values() if v['hash'] and v['hash'] != 'uncommitted'})
            for h in unique_hashes[:30]:
                try:
                    show_res = subprocess.run(
                        ['git', 'show', '-s', '--format=%h%x00%an%x00%ae%x00%at%x00%s%x00%b', h],
                        cwd=workspace, capture_output=True, text=True, timeout=1.5
                    )
                    if show_res.returncode == 0 and show_res.stdout:
                        sp = show_res.stdout.split('\x00')
                        if len(sp) >= 5:
                            c_author = sp[1]
                            commit_obj = {
                                'hash': sp[0],
                                'author': 'You' if _is_me(c_author) else c_author,
                                'raw_author': c_author,
                                'is_me': _is_me(c_author),
                                'email': sp[2],
                                'time': int(sp[3]) if sp[3].isdigit() else 0,
                                'summary': sp[4],
                                'body': sp[5].strip() if len(sp) > 5 else ''
                            }
                            commits[h] = commit_obj
                            if sp[0] not in commits:
                                commits[sp[0]] = commit_obj
                except Exception:
                    pass
    except Exception:
        pass

    if creator:
        commits['creator'] = creator
        if creator.get('hash'):
            commits[creator['hash']] = creator
    if last_mod:
        commits['last_mod'] = last_mod
        if last_mod.get('hash'):
            commits[last_mod['hash']] = last_mod

    return {
        'success': True,
        'path': clean_path,
        'creator': creator,
        'last_modifier': last_mod,
        'lines': lines,
        'commits': commits
    }



