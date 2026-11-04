#!/usr/bin/env python3
"""HTTP Request Handler cho EasySalon Agent Studio."""

import datetime
from concurrent.futures import ThreadPoolExecutor
import http.server
import json
import os
import re
import shutil
import subprocess
import time
import traceback
import urllib.parse
import uuid

from config import BASE_DIR, FE_WORKSPACE, BE_WORKSPACE, get_fe_workspace, get_be_workspace, get_workspace
from studio.state import (
    app_state,
    state_lock,
    save_queue_state_unlocked,
    load_messages,
    save_messages,
    add_work_log,
    load_settings,
    save_settings,
    is_nine_router_online,
    get_gemini_cli_status,
    start_nine_router_background,
    start_gemini_cli_background,
    get_opencode_models,
    get_gemini_cli_models,
)
from studio.terminals import (
    get_terminal_feed,
    enqueue_task_item,
    start_queue_worker,
    close_task_terminals,
    kill_process_tree,
    queue_cond,
    sync_active_task_models,
)
from studio.git_ops import (
    get_git_repo_details,
    get_git_commits,
    get_git_cherry_pick_status,
    switch_git_branch,
    rename_git_branch,
    pull_git_branch,
    execute_git_cherry_pick,
    abort_git_cherry_pick,
    continue_git_cherry_pick,
    push_git_branch,
    sync_pull_branch,
    execute_git_stash,
    get_git_stash_list,
    execute_git_stash_pop,
    abort_git_merge,
    get_git_merge_status,
    execute_git_merge,
    continue_git_merge,
    compute_merge_diff,
    check_sync_pull_status,
    parse_git_conflict_content,
    resolve_conflict_content,
    get_git_active_conflict_status,
    get_git_conflict_file_info,
    resolve_git_conflict_file,
    abort_git_conflict,
    continue_git_conflict,
    get_file_blame_and_author_details,
)
from studio.diagram import get_custom_skills, get_diagram_data
from studio.dev_watch import get_dev_watch_state

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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_DELETE(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path == '/api/notes':
                params = urllib.parse.parse_qs(parsed.query)
                note_id = params.get('id', [None])[0]
                from studio.services.notes_service import delete_note
                res = delete_note(note_id)
                self.send_json(res)
            else:
                self.send_error(404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            traceback.print_exc()
            self.send_json({'success': False, 'message': str(e)}, 500)

    @staticmethod
    def _resolve_file_workspace(raw_target):
        t = str(raw_target or 'fe').strip().lower()
        is_be = ('be' in t) or ('backend' in t) or ('api' in t)
        target = 'be' if is_be else 'fe'
        ws = get_be_workspace() if is_be else get_fe_workspace()
        alt_target = 'fe' if is_be else 'be'
        alt_ws = get_fe_workspace() if is_be else get_be_workspace()
        return ws, target, alt_ws, alt_target

    def do_GET(self):
        try:
            self._handle_GET()
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_json({'success': False, 'message': f'Server Error: {str(e)}'}, 500)
            except Exception:
                pass

    def _handle_GET(self):
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
            '/notes',
            '/note',
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
        elif path.startswith('/node_modules/monaco-editor/'):
            rel_path = path[len('/node_modules/monaco-editor/'):]
            safe_path = os.path.normpath(os.path.join(BASE_DIR, 'node_modules', 'monaco-editor', rel_path))
            if safe_path.startswith(os.path.join(BASE_DIR, 'node_modules', 'monaco-editor')) and os.path.isfile(safe_path):
                ext = os.path.splitext(safe_path)[1].lower()
                mime = 'application/javascript' if ext == '.js' else ('text/css' if ext == '.css' else 'application/octet-stream')
                with open(safe_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', f'{mime}; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)
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
        elif path.startswith('/style/') or path.startswith('/styles/'):
            css_name = os.path.basename(path)
            css_path = os.path.join(BASE_DIR, 'frontend', 'style', css_name)
            if not os.path.exists(css_path):
                css_path = os.path.join(BASE_DIR, 'frontend', css_name)
            if os.path.exists(css_path):
                with open(css_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/css; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)
        elif path in ('/styles.css', '/style.css'):
            css_path = os.path.join(BASE_DIR, 'frontend', 'style', 'style.css')
            if not os.path.exists(css_path):
                css_path = os.path.join(BASE_DIR, 'frontend', 'styles.css')
            if os.path.exists(css_path):
                with open(css_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/css; charset=utf-8')
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
                        'queue_status': ts.get('queue_status', 'running' if ts.get('is_running') else 'done'),
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
                elif latest_session:
                    cur_tid = latest_session.get('task_id') or latest_session.get('id')
                    clean_cur_tid = str(cur_tid).replace('queued_', '') if cur_tid else ''
                    has_matching = any(
                        k in (cur_tid, clean_cur_tid, f"queued_{clean_cur_tid}")
                        for k in app_state['active_tasks']
                    ) or any(
                        q.get('id') in (cur_tid, clean_cur_tid, f"queued_{clean_cur_tid}")
                        for q in app_state.get('task_queue', [])
                    )
                    if not has_matching:
                        latest_session = None
                        app_state['current_session'] = None

                data = {
                    'is_running': any(t.get('is_running') for t in app_state['active_tasks'].values()) or app_state.get('is_running', False),
                    'tasks': tasks_out,
                    'queue': list(app_state.get('task_queue', [])),
                    'settings': dict(app_state.get('settings', load_settings())),
                    'mode': latest_mode,
                    'active_round': app_state.get('active_round', 0),
                    'total_rounds': app_state.get('total_rounds', 0),
                    'active_speaker': app_state.get('active_speaker', ''),
                    'status_text': latest_status,
                    'current_session': latest_session
                }
            self.send_json(data)
        elif path == '/api/settings':
            from studio.state import detect_opencode_active_model, save_settings
            from studio.terminals import sync_active_task_models
            detected = detect_opencode_active_model()
            with state_lock:
                st = dict(app_state.get('settings', load_settings()))
                if detected:
                    is_free_or_agent = ('free' in detected.lower()) or detected.endswith('-agent')
                    clean_detected = detected if is_free_or_agent else re.sub(r'-(low|medium|high|xhigh|max)$', '', detected, flags=re.IGNORECASE)
                    if clean_detected and st.get('opencode_model') != clean_detected:
                        st['opencode_model'] = clean_detected
                        app_state['settings'] = st
                        try:
                            save_settings(st)
                            sync_active_task_models(st)
                        except Exception:
                            pass
            from config import get_agy_bin, get_opencode_bin
            current_fe = get_fe_workspace()
            current_be = get_be_workspace()
            agy_path = get_agy_bin()
            opencode_path = get_opencode_bin()
            env_info = {
                'fe_workspace': current_fe,
                'be_workspace': current_be,
                'agy_bin': agy_path,
                'opencode_bin': opencode_path,
                'fe_exists': os.path.exists(current_fe),
                'be_exists': os.path.exists(current_be),
                'agy_exists': bool(shutil.which(agy_path) or (os.path.exists(agy_path) and os.access(agy_path, os.X_OK))),
                'opencode_exists': bool(shutil.which(opencode_path) or (os.path.exists(opencode_path) and os.access(opencode_path, os.X_OK))),
            }
            self.send_json({
                'success': True,
                'settings': st,
                'env_info': env_info,
                'nine_router_online': is_nine_router_online(),
                'gemini_cli_status': get_gemini_cli_status()
            })
        elif path == '/api/workspace/detect':
            qs = urllib.parse.parse_qs(parsed.query)
            target = (qs.get('target', ['fe'])[0] or 'fe').strip().lower()
            name = (qs.get('name', [''])[0] or '').strip()
            folder_name = name or ('easysalon-webapp' if target == 'fe' else 'easysalon-api')
            candidates = [
                f'/run/media/thietnv/Data/Project/{folder_name}',
                f'/run/media/thietnv/Data/{folder_name}',
                os.path.join(os.path.dirname(BASE_DIR), 'Project', folder_name),
                os.path.join(os.path.dirname(BASE_DIR), folder_name),
                os.path.expanduser(f'~/Project/{folder_name}'),
                os.path.expanduser(f'~/Projects/{folder_name}'),
                os.path.expanduser(f'~/{folder_name}'),
            ]
            found_path = None
            for p in candidates:
                if os.path.isdir(p):
                    found_path = os.path.abspath(p)
                    break
            if not found_path:
                data_dir = '/run/media/thietnv/Data'
                if os.path.isdir(data_dir):
                    try:
                        for root, dirs, _ in os.walk(data_dir):
                            if folder_name in dirs:
                                found_path = os.path.abspath(os.path.join(root, folder_name))
                                break
                            if root.count(os.sep) - data_dir.count(os.sep) >= 2:
                                dirs.clear()
                    except Exception:
                        pass
            self.send_json({
                'success': True,
                'path': found_path or f'/run/media/thietnv/Data/Project/{folder_name}',
                'exists': bool(found_path and os.path.exists(found_path)),
                'folder': folder_name
            })
        elif path == '/api/cli/detect':
            qs = urllib.parse.parse_qs(parsed.query)
            target = (qs.get('target', ['agy'])[0] or 'agy').strip().lower()
            from config import detect_installed_cli_path
            res = detect_installed_cli_path(target)
            self.send_json({
                'success': True,
                'target': res.get('target', target),
                'path': res.get('path', ''),
                'exists': res.get('exists', False),
                'platform': res.get('platform', 'linux'),
                'fallback': res.get('fallback', '')
            })
        elif path == '/api/opencode/models':
            models = get_opencode_models()
            from studio.state import detect_opencode_active_model, save_settings
            from studio.terminals import sync_active_task_models
            detected = detect_opencode_active_model()
            with state_lock:
                st = dict(app_state.get('settings', load_settings()))
                if detected:
                    is_free_or_agent = ('free' in detected.lower()) or detected.endswith('-agent')
                    clean_detected = detected if is_free_or_agent else re.sub(r'-(low|medium|high|xhigh|max)$', '', detected, flags=re.IGNORECASE)
                    if clean_detected and st.get('opencode_model') != clean_detected:
                        st['opencode_model'] = clean_detected
                        app_state['settings'] = st
                        try:
                            save_settings(st)
                            sync_active_task_models(st)
                        except Exception:
                            pass
            curr_model = st.get('opencode_model', '')
            self.send_json({
                'success': True,
                'nine_router_online': is_nine_router_online(),
                'models': models,
                'detected_model': detected,
                'current_model': curr_model
            })
        elif path == '/api/gemini/models':
            models = get_gemini_cli_models()
            with state_lock:
                st = dict(app_state.get('settings', load_settings()))
            curr_model = st.get('model', 'gemini-3.8-flash-high')
            curr_effort = st.get('effort', 'high')
            self.send_json({
                'success': True,
                'models': models,
                'current_model': curr_model,
                'current_effort': curr_effort,
                'cli_status': get_gemini_cli_status()
            })
        elif path == '/api/mcp/list':
            import studio.mcp_ops as mcp_ops
            servers = mcp_ops.get_all_mcp_servers()
            self.send_json({
                'success': True,
                'servers': servers
            })
        elif path == '/api/jira/status':
            import studio.jira_ops as jira_ops
            res = jira_ops.get_jira_status()
            self.send_json(res)
        elif path == '/api/jira/issues':
            import studio.jira_ops as jira_ops
            params = urllib.parse.parse_qs(parsed.query)
            jql = params.get('jql', [None])[0]
            query = params.get('query', [None])[0]
            project = params.get('project', [None])[0]
            filter_type = params.get('filter', ['all'])[0]
            hide_nc = str(params.get('hide_non_coding', ['false'])[0]).lower() in ('1', 'true', 'yes')
            max_r = int(params.get('max_results', ['30'])[0]) if params.get('max_results') else 30
            res = jira_ops.search_jira_issues(jql=jql, query=query, project=project, filter_type=filter_type, hide_non_coding=hide_nc, max_results=max_r)
            self.send_json(res)
        elif path in ('/api/jira/current-user', '/api/jira/myself'):
            import studio.jira_ops as jira_ops
            prof = jira_ops.get_current_user_profile() if hasattr(jira_ops, 'get_current_user_profile') else {}
            self.send_json({
                'success': bool(prof),
                'user': prof
            })
        elif path == '/api/jira/issue':
            import studio.jira_ops as jira_ops
            params = urllib.parse.parse_qs(parsed.query)
            key = params.get('key', [None])[0]
            res = jira_ops.get_jira_issue_detail(key)
            self.send_json(res)
        elif path == '/api/jira/assignable-users':
            import studio.jira_ops as jira_ops
            params = urllib.parse.parse_qs(parsed.query)
            issue_key = params.get('issue_key', [None])[0] or params.get('key', [None])[0]
            project_key = params.get('project', [None])[0] or params.get('project_key', [None])[0]
            query = params.get('query', [''])[0]
            res = jira_ops.get_jira_assignable_users(issue_key=issue_key, project_key=project_key, query=query)
            self.send_json(res)
        elif path == '/api/jira/note':
            import studio.jira_ops as jira_ops
            params = urllib.parse.parse_qs(parsed.query)
            key = params.get('key', [None])[0]
            res = jira_ops.get_jira_note(key)
            self.send_json(res)
        elif path == '/api/jira/attachment':
            import studio.jira_ops as jira_ops
            params = urllib.parse.parse_qs(parsed.query)
            att_id = params.get('id', [None])[0]
            fn = params.get('name', [''])[0]
            is_thumb = bool(params.get('thumb', [False])[0])
            jira_ops.stream_jira_attachment(self, att_id, filename=fn, is_thumb=is_thumb)
            return
        elif path.startswith('/secure/attachment/'):
            parts = [p for p in path.split('/') if p]
            att_id = parts[2] if len(parts) > 2 else ''
            fn = parts[3] if len(parts) > 3 else ''
            import studio.jira_ops as jira_ops
            jira_ops.stream_jira_attachment(self, att_id, filename=fn)
            return
        elif path.startswith('/rest/api/3/attachment/content/') or path.startswith('/rest/api/2/attachment/content/'):
            att_id = path.split('/')[-1]
            import studio.jira_ops as jira_ops
            jira_ops.stream_jira_attachment(self, att_id)
            return
        elif path == '/api/notes':
            from studio.services.notes_service import get_all_notes
            notes = get_all_notes()
            self.send_json({'success': True, 'notes': notes})
        elif path == '/api/jira/updates':
            import studio.jira_ops as jira_ops
            res = jira_ops.check_jira_updates()
            self.send_json(res)
        elif path == '/api/account/status':
            with state_lock:
                st = dict(app_state.get('settings', load_settings()))
            self.send_json({
                'success': True,
                'status': get_gemini_cli_status(),
                'settings': st
            })
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
        elif path == '/api/git/merge/status':
            fe_status = get_git_merge_status(get_fe_workspace())
            be_status = get_git_merge_status(get_be_workspace())
            self.send_json({
                'fe': fe_status,
                'be': be_status
            })
        elif path == '/api/git/merge/diff':
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('target', ['fe'])[0]
            base_commit = qs.get('base_commit', [''])[0]
            head_commit = qs.get('head_commit', [''])[0]
            ws = get_workspace(target)
            diff_data = compute_merge_diff(ws, base_commit=base_commit, head_commit=head_commit)
            self.send_json({
                'success': True,
                'target': target,
                'merge_diff': diff_data
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
        elif path in ('/api/file/content', '/api/file/stat'):
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('target', ['fe'])[0]
            file_path = qs.get('path', [''])[0].strip()
            if not file_path:
                self.send_json({'success': False, 'message': 'Thiếu đường dẫn file.'}, 400)
                return
            ws, target, alt_ws, alt_target = self._resolve_file_workspace(target)
            clean_path = os.path.normpath(file_path).lstrip('/')
            abs_file = os.path.abspath(os.path.join(ws, clean_path))
            abs_ws = os.path.abspath(ws)
            if not (abs_file == abs_ws or abs_file.startswith(abs_ws + os.sep)):
                alt_clean = os.path.normpath(file_path).lstrip('/')
                alt_abs = os.path.abspath(os.path.join(alt_ws, alt_clean))
                alt_abs_ws = os.path.abspath(alt_ws)
                if (alt_abs == alt_abs_ws or alt_abs.startswith(alt_abs_ws + os.sep)) and os.path.exists(alt_abs):
                    abs_file = alt_abs
                    ws = alt_ws
                    target = alt_target
                else:
                    self.send_json({'success': False, 'message': 'Đường dẫn file không hợp lệ.'}, 400)
                    return
            if not os.path.exists(abs_file):
                alt_file = os.path.abspath(os.path.join(alt_ws, clean_path))
                if os.path.exists(alt_file):
                    abs_file = alt_file
                    ws = alt_ws
                    target = alt_target
                else:
                    self.send_json({'success': False, 'message': f'Không tìm thấy file: {file_path}'}, 404)
                    return
            try:
                st = os.stat(abs_file)
                resp = {
                    'success': True,
                    'path': clean_path,
                    'target': target,
                    'mtime': st.st_mtime,
                    'size': st.st_size,
                    'abs_path': abs_file
                }
                if path == '/api/file/content':
                    with open(abs_file, 'r', encoding='utf-8', errors='replace') as fp:
                        resp['content'] = fp.read()
                self.send_json(resp)
            except Exception as e:
                self.send_json({'success': False, 'message': f'Lỗi khi đọc file: {str(e)}'}, 500)
        elif path == '/api/file/blame':
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('target', ['fe'])[0]
            file_path = qs.get('path', [''])[0].strip()
            if not file_path:
                self.send_json({'success': False, 'message': 'Thiếu đường dẫn file.'}, 400)
                return
            ws, target, alt_ws, alt_target = self._resolve_file_workspace(target)
            data = get_file_blame_and_author_details(ws, file_path)
            if not data.get('success'):
                alt_data = get_file_blame_and_author_details(alt_ws, file_path)
                if alt_data.get('success'):
                    data = alt_data
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
        elif path == '/api/dev-watch':
            st = get_dev_watch_state()
            self.send_json({
                'version': st['version'],
                'css_hash': st['css_hash'],
                'dom_js_hash': st['dom_js_hash'],
                'py_hash': st['py_hash'],
                'updated_at': st['updated_at']
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        try:
            self._handle_POST()
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_json({'success': False, 'message': f'Server Error: {str(e)}'}, 500)
            except Exception:
                pass

    def _handle_POST(self):
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
            original_prompt = body.get('original_prompt', '').strip()
            task_id = body.get('task_id', '').strip() or f"task_{datetime.datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}"
            task_title = body.get('title', '').strip() or f"Làm task: {prompt[:35]}"

            with state_lock:
                if task_id in app_state['active_tasks'] and app_state['active_tasks'][task_id].get('is_running'):
                    self.send_json({'success': False, 'message': f'Tác vụ [{task_title}] đang chạy. Vui lòng chờ hoàn tất hoặc dừng trước khi chạy lại.'}, 400)
                    return

            if not prompt and not error_log:
                self.send_json({'success': False, 'message': 'Vui lòng nhập nội dung task hoặc mã lỗi.'}, 400)
                return

            target = body.get('target', 'both')
            starter = body.get('starter', 'fe')
            rounds = body.get('rounds', 4)
            skills_raw = body.get('skills', None) or body.get('skill', None) or body.get('module', '')
            if isinstance(skills_raw, list):
                skills_list = [str(s).strip() for s in skills_raw if str(s).strip()]
            elif isinstance(skills_raw, str):
                skills_list = [s.strip() for s in skills_raw.split(',') if s.strip()]
            else:
                skills_list = []

            task_mode = body.get('mode', 'task')
            effort = str(body.get('effort') or '').strip().lower()
            engine = str(body.get('engine') or '').strip().lower()
            settings_update = {}
            if effort in ('low', 'medium', 'high', 'xhigh', 'max'):
                settings_update['effort'] = effort
            if engine in ('gemini_cli', 'opencode'):
                settings_update['engine'] = engine
            if settings_update:
                with state_lock:
                    saved = save_settings(settings_update)
                    app_state['settings'] = saved

            start_queue_worker()
            q_res = enqueue_task_item({
                'id': task_id,
                'title': task_title,
                'mode': task_mode,
                'effort': effort,
                'engine': engine or app_state.get('settings', {}).get('engine', 'gemini_cli'),
                'target': target,
                'starter': starter,
                'rounds': rounds,
                'skills': skills_list,
                'prompt': prompt,
                'original_prompt': original_prompt,
                'error_log': error_log,
                'createdAt': datetime.datetime.now().strftime('%H:%M:%S')
            })
            is_queued = (q_res['queue_status'] == 'queued')
            msg = (
                f"Đã đưa [{task_title}] vào hàng đợi (Vị trí #{q_res['queue_position']}) — Lệnh: {q_res['converted_prompt'][:60]}"
                if is_queued else
                f"Đã gửi lệnh xuống AI Terminal [{task_title}]: {q_res['converted_prompt'][:60]}"
            )
            self.send_json({
                'success': True,
                'task_id': task_id,
                'queue_status': q_res['queue_status'],
                'queue_position': q_res['queue_position'],
                'converted_prompt': q_res['converted_prompt'],
                'message': msg
            })

        elif path == '/api/fixbug':
            task_id = body.get('task_id', '').strip() or f"fix_{datetime.datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:4]}"
            task_title = body.get('title', '').strip() or "Fix bug"

            with state_lock:
                if task_id in app_state['active_tasks'] and app_state['active_tasks'][task_id].get('is_running'):
                    self.send_json({'success': False, 'message': f'Tác vụ [{task_title}] đang chạy.'}, 400)
                    return

            skills_raw = body.get('skills', None) or body.get('skill', None) or body.get('module', '')
            if isinstance(skills_raw, list):
                skills_list = [str(s).strip() for s in skills_raw if str(s).strip()]
            elif isinstance(skills_raw, str):
                skills_list = [s.strip() for s in skills_raw.split(',') if s.strip()]
            else:
                skills_list = []
            scope = body.get('scope', 'both')
            description = body.get('description', '').strip()
            error_log = body.get('error_log', '').strip()
            original_prompt = body.get('original_prompt', '').strip()

            if not description and not error_log:
                self.send_json({'success': False, 'message': 'Vui lòng nhập mô tả lỗi hoặc dán log lỗi.'}, 400)
                return

            effort = str(body.get('effort') or '').strip().lower()
            engine = str(body.get('engine') or '').strip().lower()
            settings_update = {}
            if effort in ('low', 'medium', 'high', 'xhigh', 'max'):
                settings_update['effort'] = effort
            if engine in ('gemini_cli', 'opencode'):
                settings_update['engine'] = engine
            if settings_update:
                with state_lock:
                    saved = save_settings(settings_update)
                    app_state['settings'] = saved

            start_queue_worker()
            q_res = enqueue_task_item({
                'id': task_id,
                'title': task_title,
                'mode': 'fixbug',
                'effort': effort,
                'engine': engine or app_state.get('settings', {}).get('engine', 'gemini_cli'),
                'scope': scope,
                'skills': skills_list,
                'fix_desc': description,
                'original_prompt': original_prompt,
                'fix_err': error_log,
                'createdAt': datetime.datetime.now().strftime('%H:%M:%S')
            })
            is_queued = (q_res['queue_status'] == 'queued')
            msg = (
                f"Đã đưa Fix Bug [{task_title}] vào hàng đợi (Vị trí #{q_res['queue_position']}) — Lệnh: {q_res['converted_prompt'][:60]}"
                if is_queued else
                f"Đã khởi chạy Fix Bug [{task_title}]: {q_res['converted_prompt'][:60]}"
            )
            self.send_json({
                'success': True,
                'task_id': task_id,
                'queue_status': q_res['queue_status'],
                'queue_position': q_res['queue_position'],
                'converted_prompt': q_res['converted_prompt'],
                'message': msg
            })

        elif path == '/api/queue/sync':
            incoming_queue = body.get('queue', [])
            if isinstance(incoming_queue, list):
                with state_lock:
                    existing_by_id = {q.get('id'): q for q in app_state.get('task_queue', []) if q.get('id')}
                    merged_queue = []
                    for item in incoming_queue:
                        if not isinstance(item, dict) or not item.get('id'):
                            continue
                        tid = item['id']
                        ts = app_state['active_tasks'].get(tid)
                        if ts and ts.get('is_running'):
                            item['status'] = 'running'
                            item['isRunning'] = True
                        elif tid in existing_by_id and existing_by_id[tid].get('status') in ('queued', 'running', 'done'):
                            # Giữ nguyên trạng thái đang chờ/đang chạy trên server trừ khi client cập nhật draft
                            if existing_by_id[tid].get('status') in ('queued', 'running'):
                                item['status'] = existing_by_id[tid]['status']
                        merged_queue.append(item)
                    app_state['task_queue'] = merged_queue
                    save_queue_state_unlocked()
            self.send_json({'success': True, 'queue': app_state.get('task_queue', [])})

        elif path == '/api/queue/remove':
            task_id = body.get('task_id', '').strip()
            with state_lock:
                if task_id in ('completed', 'done', 'finished'):
                    finished_ids = set()
                    for tid, ts in app_state['active_tasks'].items():
                        if not ts.get('is_running') and (
                            ts.get('queue_status') in ('done', 'completed', 'stopped')
                            or (ts.get('session') and ts['session'].get('status') in ('COMPLETED', 'STOPPED', 'DONE'))
                        ):
                            finished_ids.add(tid)
                            finished_ids.add(str(tid).replace('queued_', ''))
                            finished_ids.add(f"queued_{str(tid).replace('queued_', '')}")
                    for tid in list(app_state['active_tasks'].keys()):
                        clean_tid = str(tid).replace('queued_', '')
                        if tid in finished_ids or clean_tid in finished_ids:
                            ts = app_state['active_tasks'].pop(tid, None)
                            if ts and ts.get('current_process'):
                                kill_process_tree(ts['current_process'])
                            close_task_terminals(tid)
                            close_task_terminals(clean_tid)
                    app_state['task_queue'] = [
                        q for q in app_state.get('task_queue', [])
                        if q.get('id') not in finished_ids and str(q.get('id', '')).replace('queued_', '') not in finished_ids and q.get('status') not in ('done', 'completed', 'stopped')
                    ]
                    cur_sess = app_state.get('current_session')
                    if cur_sess:
                        cur_tid = cur_sess.get('task_id') or cur_sess.get('id')
                        clean_cur = str(cur_tid).replace('queued_', '') if cur_tid else ''
                        if cur_tid in finished_ids or clean_cur in finished_ids or not app_state['active_tasks']:
                            app_state['current_session'] = next((t.get('session') for t in app_state['active_tasks'].values() if t.get('session')), None)
                    save_queue_state_unlocked()
                elif task_id == 'all':
                    for tid, ts in list(app_state['active_tasks'].items()):
                        proc = ts.get('current_process')
                        if proc:
                            kill_process_tree(proc)
                        close_task_terminals(tid)
                        app_state['active_tasks'].pop(tid, None)
                    if app_state.get('current_process'):
                        kill_process_tree(app_state['current_process'])
                        app_state['current_process'] = None
                    app_state['task_queue'] = []
                    app_state['is_running'] = False
                    app_state['current_session'] = None
                    save_queue_state_unlocked()
                elif task_id:
                    clean_id = str(task_id).replace('queued_', '')
                    matching_ids = {task_id, clean_id, f"queued_{clean_id}"}
                    for tid in list(app_state['active_tasks'].keys()):
                        clean_tid = str(tid).replace('queued_', '')
                        if tid in matching_ids or clean_tid in matching_ids:
                            ts = app_state['active_tasks'].get(tid)
                            if ts:
                                ts['is_running'] = False
                                ts['queue_status'] = 'stopped'
                                ts['status_text'] = 'Đã dừng và xóa tác vụ.'
                                if ts.get('session'):
                                    ts['session']['status'] = 'STOPPED'
                                proc = ts.get('current_process')
                                if proc:
                                    kill_process_tree(proc)
                            app_state['active_tasks'].pop(tid, None)
                    cur_proc = app_state.get('current_process')
                    cur_sess = app_state.get('current_session')
                    if cur_proc and cur_sess:
                        cur_tid = cur_sess.get('task_id') or cur_sess.get('id')
                        clean_cur = str(cur_tid).replace('queued_', '') if cur_tid else ''
                        if cur_tid in matching_ids or clean_cur in matching_ids:
                            kill_process_tree(cur_proc)
                            app_state['current_process'] = None
                    for mid in matching_ids:
                        close_task_terminals(mid)
                    app_state['task_queue'] = [
                        q for q in app_state.get('task_queue', [])
                        if q.get('id') not in matching_ids and str(q.get('id', '')).replace('queued_', '') not in matching_ids
                    ]
                    app_state['is_running'] = any(t.get('is_running') for t in app_state['active_tasks'].values())
                    cur_sess = app_state.get('current_session')
                    if cur_sess:
                        cur_tid = cur_sess.get('task_id') or cur_sess.get('id')
                        clean_cur = str(cur_tid).replace('queued_', '') if cur_tid else ''
                        if cur_tid in matching_ids or clean_cur in matching_ids or not app_state['active_tasks']:
                            app_state['current_session'] = next((t.get('session') for t in app_state['active_tasks'].values() if t.get('session')), None)
                    save_queue_state_unlocked()
            self.send_json({'success': True})

        elif path == '/api/stop':
            task_id = body.get('task_id')
            with state_lock:
                if task_id and task_id != 'all':
                    clean_id = str(task_id).replace('queued_', '')
                    matching_ids = {task_id, clean_id, f"queued_{clean_id}"}
                    for tid in list(app_state['active_tasks'].keys()):
                        clean_tid = str(tid).replace('queued_', '')
                        if tid in matching_ids or clean_tid in matching_ids:
                            ts = app_state['active_tasks'][tid]
                            proc = ts.get('current_process')
                            if proc:
                                kill_process_tree(proc)
                            ts['is_running'] = False
                            ts['queue_status'] = 'stopped'
                            ts['status_text'] = 'Đã dừng tác vụ.'
                            if ts.get('session'):
                                ts['session']['status'] = 'STOPPED'
                    cur_proc = app_state.get('current_process')
                    cur_sess = app_state.get('current_session')
                    if cur_proc and cur_sess:
                        cur_tid = cur_sess.get('task_id') or cur_sess.get('id')
                        clean_cur = str(cur_tid).replace('queued_', '') if cur_tid else ''
                        if cur_tid in matching_ids or clean_cur in matching_ids:
                            kill_process_tree(cur_proc)
                            app_state['current_process'] = None
                    for q in app_state.get('task_queue', []):
                        clean_qid = str(q.get('id', '')).replace('queued_', '')
                        if q.get('id') in matching_ids or clean_qid in matching_ids:
                            q['status'] = 'stopped'
                            q['isRunning'] = False
                    for mid in matching_ids:
                        close_task_terminals(mid)
                else:
                    for tid, ts in list(app_state['active_tasks'].items()):
                        proc = ts.get('current_process')
                        if proc:
                            kill_process_tree(proc)
                        ts['is_running'] = False
                        ts['queue_status'] = 'stopped'
                        ts['status_text'] = 'Đã dừng tác vụ.'
                        if ts.get('session'):
                            ts['session']['status'] = 'STOPPED'
                        close_task_terminals(tid)
                    for q in app_state.get('task_queue', []):
                        if q.get('status') in ('running', 'queued'):
                            q['status'] = 'stopped'
                            q['isRunning'] = False
                    if app_state.get('current_process'):
                        kill_process_tree(app_state['current_process'])
                        app_state['current_process'] = None
                    app_state['current_session'] = None
                app_state['is_running'] = any(t.get('is_running') for t in app_state['active_tasks'].values())
                app_state['status_text'] = 'Đã dừng tiến trình.' if not app_state['is_running'] else 'Đang chạy'
                save_queue_state_unlocked()
            with queue_cond:
                queue_cond.notify_all()
            self.send_json({'success': True, 'message': 'Đã dừng tiến trình.'})

        elif path == '/api/settings':
            new_settings = body.get('settings') if isinstance(body.get('settings'), dict) else body
            with state_lock:
                saved = save_settings(new_settings)
                app_state['settings'] = saved
            sync_active_task_models(saved)
            self.send_json({
                'success': True,
                'settings': saved,
                'nine_router_online': is_nine_router_online(),
                'gemini_cli_status': get_gemini_cli_status(),
                'message': "Đã lưu cấu hình thành công!"
            })

        elif path == '/api/opencode/set-model':
            new_model = str(body.get('model') or '').strip()
            new_effort = str(body.get('effort') or '').strip().lower()
            if not new_model:
                self.send_json({'success': False, 'message': 'Thiếu tham số model'})
                return
            clean_model = re.sub(r'-(low|medium|high)$', '', new_model, flags=re.IGNORECASE)
            with state_lock:
                st = dict(app_state.get('settings', load_settings()))
                st['opencode_model'] = clean_model
                if new_effort in ('low', 'medium', 'high'):
                    st['effort'] = new_effort
                saved = save_settings(st)
                app_state['settings'] = saved
            sync_active_task_models(saved)
            self.send_json({
                'success': True,
                'message': f'Đã chuyển sang mô hình OpenCode: {clean_model}',
                'opencode_model': clean_model,
                'settings': saved
            })

        elif path == '/api/gemini/set-model':
            new_model = str(body.get('model') or '').strip()
            new_effort = str(body.get('effort') or '').strip().lower()
            if not new_model:
                self.send_json({'success': False, 'message': 'Thiếu tham số model'})
                return
            with state_lock:
                st = dict(app_state.get('settings', load_settings()))
                st['model'] = new_model
                if new_effort in ('low', 'medium', 'high', 'xhigh', 'max'):
                    st['effort'] = new_effort
                saved = save_settings(st)
                app_state['settings'] = saved
            sync_active_task_models(saved)
            self.send_json({
                'success': True,
                'message': f'Đã chuyển sang mô hình Gemini CLI: {new_model}',
                'model': new_model,
                'settings': saved
            })

        elif path in ('/api/9router/start', '/api/engine/start-9router'):
            res = start_nine_router_background()
            self.send_json(res)

        elif path in ('/api/gemini/start', '/api/engine/start-gemini'):
            res = start_gemini_cli_background()
            self.send_json(res)

        elif path == '/api/mcp/add':
            import studio.mcp_ops as mcp_ops
            name = str(body.get('name') or '').strip()
            config = body.get('config') if isinstance(body.get('config'), dict) else body
            target = str(body.get('target') or 'both').strip()
            try:
                res = mcp_ops.save_mcp_server(name, config, target=target)
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/add-jira':
            import studio.mcp_ops as mcp_ops
            host = str(body.get('host') or '').strip()
            email = str(body.get('email') or '').strip()
            api_token = str(body.get('api_token') or '').strip()
            name = str(body.get('name') or 'jira').strip()
            try:
                res = mcp_ops.save_jira_mcp_preset(host, email, api_token, server_name=name)
                with state_lock:
                    saved = save_settings({
                        'jira_host': host,
                        'jira_email': email,
                        'jira_api_token': api_token,
                    })
                    app_state['settings'] = saved
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/add-github':
            import studio.mcp_ops as mcp_ops
            token = str(body.get('token') or body.get('api_token') or '').strip()
            name = str(body.get('name') or 'github').strip()
            try:
                res = mcp_ops.save_github_mcp_preset(token, server_name=name)
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/add-postgres':
            import studio.mcp_ops as mcp_ops
            conn_url = str(body.get('url') or body.get('conn_url') or '').strip()
            name = str(body.get('name') or 'postgres').strip()
            try:
                res = mcp_ops.save_postgres_mcp_preset(conn_url, server_name=name)
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/add-mysql':
            import studio.mcp_ops as mcp_ops
            conn_url = str(body.get('url') or body.get('conn_url') or '').strip()
            name = str(body.get('name') or 'mysql').strip()
            host = str(body.get('host') or '').strip()
            port = body.get('port') or 3306
            user = str(body.get('user') or body.get('username') or '').strip()
            password = str(body.get('password') or '')
            database = str(body.get('database') or body.get('schema') or '').strip()
            try:
                res = mcp_ops.save_mysql_mcp_preset(
                    conn_url=conn_url,
                    server_name=name,
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                )
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/test-mysql':
            import studio.mcp_ops as mcp_ops
            conn_url = str(body.get('url') or body.get('conn_url') or '').strip()
            host = str(body.get('host') or '').strip()
            port = body.get('port') or 3306
            user = str(body.get('user') or body.get('username') or '').strip()
            password = str(body.get('password') or '')
            database = str(body.get('database') or body.get('schema') or '').strip()
            try:
                res = mcp_ops.test_mysql_connection(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    conn_url=conn_url,
                )
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/add-gitlab':
            import studio.mcp_ops as mcp_ops
            host = str(body.get('host') or '').strip()
            token = str(body.get('token') or body.get('api_token') or '').strip()
            name = str(body.get('name') or 'gitlab').strip()
            try:
                res = mcp_ops.save_gitlab_mcp_preset(host, token, server_name=name)
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/add-slack':
            import studio.mcp_ops as mcp_ops
            token = str(body.get('token') or body.get('bot_token') or '').strip()
            team_id = str(body.get('team_id') or '').strip()
            name = str(body.get('name') or 'slack').strip()
            try:
                res = mcp_ops.save_slack_mcp_preset(token, team_id=team_id, server_name=name)
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/remove':
            import studio.mcp_ops as mcp_ops
            name = str(body.get('name') or '').strip()
            try:
                res = mcp_ops.remove_mcp_server(name)
                if name.lower() == 'jira':
                    with state_lock:
                        saved = save_settings({
                            'jira_host': '',
                            'jira_email': '',
                            'jira_api_token': '',
                        })
                        app_state['settings'] = saved
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/mcp/toggle':
            import studio.mcp_ops as mcp_ops
            name = str(body.get('name') or '').strip()
            enabled = bool(body.get('enabled', True))
            try:
                res = mcp_ops.toggle_mcp_server(name, enabled)
                self.send_json(res)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 400)

        elif path == '/api/jira/comment':
            import studio.jira_ops as jira_ops
            key = str(body.get('key') or body.get('issue_key') or '').strip()
            comment_text = str(body.get('comment') or body.get('body') or '').strip()
            res = jira_ops.add_jira_comment(key, comment_text)
            self.send_json(res)

        elif path == '/api/jira/transition':
            import studio.jira_ops as jira_ops
            key = str(body.get('key') or body.get('issue_key') or '').strip()
            tid = str(body.get('transition_id') or body.get('id') or '').strip()
            target_status = str(body.get('status') or body.get('target_status') or '').strip()
            comment_text = str(body.get('comment') or '').strip()
            res = jira_ops.transition_jira_issue(key, transition_id=tid, comment=comment_text, target_status=target_status)
            self.send_json(res)

        elif path == '/api/jira/create-subtask':
            import studio.jira_ops as jira_ops
            parent_key = str(body.get('parent_key') or body.get('key') or '').strip()
            summary = str(body.get('summary') or body.get('title') or '').strip()
            description = str(body.get('description') or '').strip()
            target_status = str(body.get('status') or body.get('target_status') or '').strip()
            transition_id = str(body.get('transition_id') or '').strip()
            assignee_id = str(body.get('assignee_id') or body.get('assignee_account_id') or body.get('assignee') or '').strip()
            res = jira_ops.create_jira_subtask(parent_key, summary, description, target_status=target_status, transition_id=transition_id, assignee_account_id=assignee_id)
            self.send_json(res)

        elif path == '/api/jira/assign':
            import studio.jira_ops as jira_ops
            key = str(body.get('key') or body.get('issue_key') or '').strip()
            account_id = body.get('account_id')
            res = jira_ops.assign_jira_issue(key, account_id=account_id)
            self.send_json(res)

        elif path == '/api/jira/note':
            import studio.jira_ops as jira_ops
            key = str(body.get('key') or body.get('issue_key') or '').strip()
            note = str(body.get('note') or '')
            res = jira_ops.save_jira_note(key, note)
            self.send_json(res)

        elif path == '/api/notes':
            from studio.services.notes_service import save_note
            res = save_note(body)
            self.send_json(res)

        elif path == '/api/notes/delete':
            from studio.services.notes_service import delete_note
            note_id = body.get('id')
            res = delete_note(note_id)
            self.send_json(res)

        elif path == '/api/jira/rovo-analyze':
            import studio.jira_ops as jira_ops
            res = jira_ops.analyze_jira_issue_with_rovo(body)
            self.send_json(res)

        elif path == '/api/mcp/test-jira':
            import studio.mcp_ops as mcp_ops
            host = str(body.get('host') or '').strip()
            email = str(body.get('email') or '').strip()
            api_token = str(body.get('api_token') or '').strip()
            res = mcp_ops.test_jira_connection(host, email, api_token)
            self.send_json(res)

        elif path == '/api/mcp/test-github':
            import studio.mcp_ops as mcp_ops
            token = str(body.get('token') or body.get('api_token') or '').strip()
            res = mcp_ops.test_github_connection(token)
            self.send_json(res)

        elif path == '/api/mcp/test-gitlab':
            import studio.mcp_ops as mcp_ops
            host = str(body.get('host') or '').strip()
            token = str(body.get('token') or body.get('api_token') or '').strip()
            res = mcp_ops.test_gitlab_connection(host, token)
            self.send_json(res)

        elif path == '/api/mcp/test-slack':
            import studio.mcp_ops as mcp_ops
            token = str(body.get('token') or body.get('bot_token') or '').strip()
            res = mcp_ops.test_slack_connection(token)
            self.send_json(res)

        elif path == '/api/test-api-key':
            provider = str(body.get('provider', 'gemini')).lower().strip()
            api_key = str(body.get('api_key', '')).strip()
            endpoint = str(body.get('endpoint', '')).strip()

            if not api_key and provider != 'custom':
                self.send_json({'success': False, 'message': 'Vui lòng nhập API Key để kiểm tra.'}, 400)
                return

            try:
                if provider == 'gemini':
                    # Kiểm tra Google Gemini API
                    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'EasySalonStudio'})
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        if resp.status == 200:
                            self.send_json({'success': True, 'message': 'Kết nối Google Gemini thành công! API Key hợp lệ và sẵn sàng sử dụng.'})
                            return
                elif provider == 'claude':
                    # Kiểm tra Anthropic Claude API
                    url = "https://api.anthropic.com/v1/models"
                    req = urllib.request.Request(url, headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'User-Agent': 'EasySalonStudio'
                    })
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        if resp.status == 200:
                            self.send_json({'success': True, 'message': 'Kết nối Anthropic Claude thành công! API Key hợp lệ và sẵn sàng sử dụng.'})
                            return
                elif provider in ('openai', 'custom'):
                    base_url = endpoint if (provider == 'custom' and endpoint) else 'https://api.openai.com/v1'
                    base_url = base_url.rstrip('/')
                    url = f"{base_url}/models"
                    headers = {'User-Agent': 'EasySalonStudio'}
                    if api_key:
                        headers['Authorization'] = f'Bearer {api_key}'
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        if resp.status == 200:
                            self.send_json({'success': True, 'message': f'Kết nối {provider.upper()} thành công! Endpoint và API Key hợp lệ.'})
                            return
                self.send_json({'success': False, 'message': 'Không thể kết nối đến nhà cung cấp API.'})
            except urllib.error.HTTPError as he:
                self.send_json({'success': False, 'message': f'API Key không hợp lệ hoặc bị từ chối (HTTP {he.code}: {he.reason})'})
            except Exception as e:
                self.send_json({'success': False, 'message': f'Lỗi kiểm tra kết nối API: {str(e)}'})

        elif path == '/api/test-gemini-cli':
            from config import get_agy_bin
            agy_bin = get_agy_bin()
            t0 = time.time()
            cli_status = get_gemini_cli_status()
            try:
                res = subprocess.run([agy_bin, '--version'], capture_output=True, text=True, timeout=3.0)
                elapsed = round(time.time() - t0, 3)
                cli_status = get_gemini_cli_status()
                if res.returncode == 0:
                    ver = res.stdout.strip() or cli_status.get('version') or '1.4.10'
                    self.send_json({
                        'success': True,
                        'message': f"Antigravity CLI phản hồi bình thường! Phiên bản v{ver} ({elapsed}s)",
                        'status': cli_status,
                        'elapsed': elapsed
                    })
                else:
                    self.send_json({
                        'success': False,
                        'message': f"Antigravity CLI trả về mã lỗi {res.returncode}: {res.stderr.strip() or 'Lỗi không xác định'}",
                        'status': cli_status
                    })
            except FileNotFoundError:
                self.send_json({
                    'success': False,
                    'message': f"Không tìm thấy file thực thi Antigravity CLI tại đường dẫn '{agy_bin}'.",
                    'status': cli_status
                })
            except Exception as e:
                self.send_json({
                    'success': False,
                    'message': f"Lỗi kiểm tra Antigravity CLI: {str(e)}",
                    'status': cli_status
                })

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
            target_workspace = (data.get('target_workspace') or '').strip() or 'both'

            if not current_branch or not target_branch:
                self.send_json({'success': False, 'message': 'Thiếu thông tin nhánh current/target.'}, 400)
                return

            # Chỉ cho phép checkout nếu target_branch không phải là current_branch
            if current_branch.lower() == target_branch.lower():
                self.send_json({'success': False, 'message': 'Nhánh đích không được giống nhánh hiện tại.'}, 400)
                return

            results = []
            all_ok = True

            # Checkout Frontend
            if target_workspace in ('fe', 'both'):
                ok, msg = switch_git_branch(get_fe_workspace(), target_branch, base_branch=current_branch)
                results.append(f"Frontend: {msg}")
                add_work_log('GIT_SWITCH', f'Checkout FE sang "{target_branch}" từ "{current_branch}"', msg, 'SUCCESS' if ok else 'ERROR', target='fe')
                if not ok: all_ok = False

            # Checkout Backend
            if target_workspace in ('be', 'both'):
                ok, msg = switch_git_branch(get_be_workspace(), target_branch, base_branch=current_branch)
                results.append(f"Backend: {msg}")
                add_work_log('GIT_SWITCH', f'Checkout BE sang "{target_branch}" từ "{current_branch}"', msg, 'SUCCESS' if ok else 'ERROR', target='be')
                if not ok: all_ok = False

            # Xóa cache sơ đồ
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None

            self.send_json({
                'success': all_ok,
                'message': '\n'.join(results)
            })

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

        elif path in ('/api/git/sync-check', '/api/git/sync-pull/check'):
            do_fetch = body.get('fetch', True)
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
                fe_details = res_fe.get('message', '')
                if res_fe.get('output') and res_fe.get('output') not in fe_details:
                    fe_details += f"\n\n--- Chi tiết Git Output ---\n{res_fe.get('output')}"
                fe_count = len(res_fe.get('pulled_commits', []))
                fe_suffix = f" ({fe_count} commit mới)" if fe_count > 0 else ""
                add_work_log(
                    'GIT_SYNC_PULL',
                    f"Pull {branch} Frontend" + (" (quay về nhánh cũ)" if return_to_current else "") + fe_suffix,
                    fe_details,
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
                be_details = res_be.get('message', '')
                if res_be.get('output') and res_be.get('output') not in be_details:
                    be_details += f"\n\n--- Chi tiết Git Output ---\n{res_be.get('output')}"
                be_count = len(res_be.get('pulled_commits', []))
                be_suffix = f" ({be_count} commit mới)" if be_count > 0 else ""
                add_work_log(
                    'GIT_SYNC_PULL',
                    f"Pull {branch} Backend" + (" (quay về nhánh cũ)" if return_to_current else "") + be_suffix,
                    be_details,
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

        elif path == '/api/git/merge':
            target = body.get('target', 'fe')
            source_branch = body.get('source_branch', '').strip()
            target_branch = body.get('target_branch', '').strip()
            no_ff = bool(body.get('no_ff', False))
            return_to_current = bool(body.get('return_to_current', False))
            commit_message = body.get('commit_message', '').strip()
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'

            res = execute_git_merge(
                ws,
                source_branch,
                target_branch=target_branch,
                no_ff=no_ff,
                commit_message=commit_message,
                return_to_current=return_to_current
            )
            status_str = 'SUCCESS' if res.get('success') else ('CONFLICT' if res.get('conflict') else 'ERROR')
            add_work_log(
                'GIT_MERGE',
                f"Merge {source_branch} ➔ {res.get('target_branch', target_branch or 'current')} ({repo_label})",
                res.get('message', ''),
                status_str,
                target=target
            )
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None
            self.send_json(res)

        elif path == '/api/git/merge/continue':
            target = body.get('target', 'fe')
            commit_message = body.get('commit_message', '').strip()
            ws = get_workspace(target)
            repo_label = 'Frontend' if target == 'fe' else 'Backend'

            res = continue_git_merge(ws, commit_message=commit_message or None)
            add_work_log(
                'GIT_MERGE_CONTINUE',
                f"Tiếp tục Merge {repo_label}",
                res.get('message', ''),
                'SUCCESS' if res.get('success') else 'ERROR',
                target=target
            )
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None
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
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None
            self.send_json(res)

        elif path == '/api/git/merge/diff':
            target = body.get('target', 'fe')
            base_commit = body.get('base_commit', '')
            head_commit = body.get('head_commit', '')
            ws = get_workspace(target)
            diff_data = compute_merge_diff(ws, base_commit=base_commit, head_commit=head_commit)
            self.send_json({
                'success': True,
                'target': target,
                'merge_diff': diff_data
            })

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
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None
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
            with state_lock:
                app_state['diagram_cache'] = None
                app_state['diagram_cache_key'] = None
            self.send_json(res)

        elif path == '/api/logs/clear':
            save_messages([])
            self.send_json({'success': True, 'message': 'Đã xóa toàn bộ lịch sử log.'})

        elif path == '/api/logs/delete':
            log_id = str(body.get('id') or body.get('log_id') or '').strip()
            if log_id:
                messages = load_messages()
                messages = [m for m in messages if str(m.get('id', '')) != log_id and str(m.get('timestamp', '')) != log_id]
                save_messages(messages)
                self.send_json({'success': True, 'message': 'Đã xóa bản ghi lịch sử.'})
            else:
                self.send_json({'success': False, 'message': 'Thiếu ID bản ghi.'}, status=400)

        elif path == '/api/file/save':
            raw_target = body.get('target', 'fe')
            file_path = (body.get('path') or '').strip()
            content = body.get('content', '')
            if not file_path:
                self.send_json({'success': False, 'message': 'Thiếu đường dẫn file.'}, 400)
                return
            ws, target, alt_ws, alt_target = self._resolve_file_workspace(raw_target)
            clean_path = os.path.normpath(file_path).lstrip('/')
            abs_file = os.path.abspath(os.path.join(ws, clean_path))
            abs_ws = os.path.abspath(ws)
            if not (abs_file == abs_ws or abs_file.startswith(abs_ws + os.sep)):
                alt_clean = os.path.normpath(file_path).lstrip('/')
                alt_file = os.path.abspath(os.path.join(alt_ws, alt_clean))
                alt_abs_ws = os.path.abspath(alt_ws)
                if (alt_file == alt_abs_ws or alt_file.startswith(alt_abs_ws + os.sep)) and os.path.exists(alt_file):
                    abs_file = alt_file
                    ws = alt_ws
                    target = alt_target
                else:
                    self.send_json({'success': False, 'message': 'Đường dẫn file không hợp lệ.'}, 400)
                    return
            try:
                os.makedirs(os.path.dirname(abs_file), exist_ok=True)
                with open(abs_file, 'w', encoding='utf-8') as fp:
                    fp.write(content)
                st = os.stat(abs_file)
                self.send_json({
                    'success': True,
                    'message': f'Đã lưu file {clean_path} thành công.',
                    'path': clean_path,
                    'target': target,
                    'mtime': st.st_mtime,
                    'size': st.st_size
                })
            except Exception as e:
                self.send_json({'success': False, 'message': f'Lỗi khi ghi file: {str(e)}'}, 500)
        elif path == '/api/telegram/notify':
            task_id = body.get('task_id', '')
            title = body.get('title', 'Tác vụ AI Agent')
            task_type = body.get('type', 'TASK')
            try:
                duration = float(body.get('duration', 0))
            except Exception:
                duration = 0.0
            changed_files = body.get('changed_files', [])
            try:
                from studio.telegram_bot import notify_task_completed
                threading.Thread(
                    target=notify_task_completed,
                    kwargs={
                        'task_id': task_id,
                        'title': title,
                        'task_type': task_type,
                        'duration': duration,
                        'changed_files': changed_files
                    },
                    daemon=True
                ).start()
                self.send_json({'success': True, 'message': 'Đã gửi thông báo Telegram.'})
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 500)
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
        st = get_dev_watch_state()
        tpl = st.get('html_template') or ''
        rendered_html = (
            tpl
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
