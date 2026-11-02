#!/usr/bin/env python3
"""Quản lý cấu hình Model Context Protocol (MCP) đồng bộ cho Gemini CLI (agy) và OpenCode (9router)."""

import base64
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request

GEMINI_CONFIG_DIR = os.path.expanduser("~/.gemini/config")
GEMINI_MCP_FILE = os.path.join(GEMINI_CONFIG_DIR, "mcp_config.json")

OPENCODE_CONFIG_DIR = os.path.expanduser("~/.config/opencode")
OPENCODE_CONFIG_FILE = os.path.join(OPENCODE_CONFIG_DIR, "opencode.json")


def _read_json_file(file_path: str, default: dict) -> dict:
    if not os.path.exists(file_path):
        return dict(default)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def _atomic_write_json(file_path: str, data: dict):
    dir_name = os.path.dirname(file_path)
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="mcp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, file_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _get_live_opencode_statuses() -> dict:
    """Kiểm tra trạng thái kết nối thực tế của các MCP server qua OpenCode CLI."""
    import shutil
    import subprocess
    statuses = {}
    if shutil.which("opencode"):
        try:
            p = subprocess.run(["opencode", "mcp", "list"], capture_output=True, text=True, timeout=3)
            for line in (p.stdout + "\n" + p.stderr).splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=2)
                if len(parts) >= 2 and parts[0] in ("✓", "✗"):
                    name = parts[1]
                    st = "connected" if parts[0] == "✓" else "failed"
                    detail = parts[2] if len(parts) > 2 else st
                    statuses[name] = {"status": st, "detail": detail}
        except Exception:
            pass
    return statuses


def get_all_mcp_servers() -> list:
    """Đọc và hợp nhất danh sách MCP server từ cả Gemini CLI và OpenCode CLI."""
    gemini_data = _read_json_file(GEMINI_MCP_FILE, {"mcpServers": {}})
    gemini_servers = gemini_data.get("mcpServers", {})
    if not isinstance(gemini_servers, dict):
        gemini_servers = {}

    opencode_data = _read_json_file(OPENCODE_CONFIG_FILE, {})
    opencode_mcp = opencode_data.get("mcp", {})
    opencode_servers = opencode_mcp.get("servers", {}) if isinstance(opencode_mcp, dict) else {}
    if not isinstance(opencode_servers, dict):
        opencode_servers = {}

    all_names = sorted(list(set(list(gemini_servers.keys()) + list(opencode_servers.keys()))))
    live_statuses = _get_live_opencode_statuses()
    result = []

    for name in all_names:
        g_cfg = gemini_servers.get(name) or {}
        o_cfg = opencode_servers.get(name) or {}

        # Xác định type: stdio hay http
        is_http = bool(g_cfg.get("url") or o_cfg.get("url") or o_cfg.get("type") in ("remote", "http"))
        mcp_type = "http" if is_http else "stdio"

        # Command & Args
        command = g_cfg.get("command") or ""
        args = g_cfg.get("args") or []
        if not command and o_cfg.get("command"):
            o_cmd = o_cfg.get("command")
            if isinstance(o_cmd, list) and o_cmd:
                command = o_cmd[0]
                args = o_cmd[1:]
            elif isinstance(o_cmd, str):
                parts = o_cmd.split()
                command = parts[0] if parts else ""
                args = parts[1:]

        # Env vars
        env = {}
        if isinstance(g_cfg.get("env"), dict):
            env.update(g_cfg["env"])
        if isinstance(o_cfg.get("environment"), dict):
            env.update(o_cfg["environment"])
        elif isinstance(o_cfg.get("env"), dict):
            env.update(o_cfg["env"])

        # URL & Headers
        url = g_cfg.get("url") or o_cfg.get("url") or ""
        headers = {}
        if isinstance(g_cfg.get("headers"), dict):
            headers.update(g_cfg["headers"])
        if isinstance(o_cfg.get("headers"), dict):
            headers.update(o_cfg["headers"])

        # Status
        disabled = bool(g_cfg.get("disabled") or o_cfg.get("disabled", False))

        # Check preset
        is_jira = (
            "jira" in name.lower()
            or any("jira" in k.lower() for k in env.keys())
            or "@answerai/jira-mcp" in " ".join([command] + [str(a) for a in args])
        )
        is_github = (
            "github" in name.lower()
            or "GITHUB_PERSONAL_ACCESS_TOKEN" in env
            or "server-github" in " ".join([command] + [str(a) for a in args])
        )
        is_postgres = (
            "postgres" in name.lower()
            or "server-postgres" in " ".join([command] + [str(a) for a in args])
        )
        is_gitlab = (
            "gitlab" in name.lower()
            or "GITLAB_PERSONAL_ACCESS_TOKEN" in env
            or "server-gitlab" in " ".join([command] + [str(a) for a in args])
        )
        preset_name = "jira" if is_jira else ("github" if is_github else ("postgres" if is_postgres else ("gitlab" if is_gitlab else "custom")))

        # Full command string for display
        cmd_str = ""
        if mcp_type == "stdio":
            parts = [command] + [str(a) for a in args]
            cmd_str = " ".join([p for p in parts if p])
        else:
            cmd_str = url

        live_opencode = live_statuses.get(name)
        live_status = live_opencode.get("status") if live_opencode else None
        live_detail = live_opencode.get("detail", "") if live_opencode else ""

        computed_status = "disabled" if disabled else (live_status or "ready")

        result.append({
            "name": name,
            "type": mcp_type,
            "command": command,
            "args": args,
            "command_str": cmd_str,
            "env": env,
            "url": url,
            "headers": headers,
            "disabled": disabled,
            "in_gemini": name in gemini_servers,
            "in_opencode": name in opencode_servers,
            "preset": "jira" if is_jira else "custom",
            "status": computed_status,
            "live_status": live_status,
            "live_detail": live_detail,
        })

    return result


def save_mcp_server(name: str, config: dict, target: str = "both") -> dict:
    """Thêm hoặc cập nhật MCP server vào cả Gemini CLI và OpenCode CLI.
    
    target: 'gemini' | 'opencode' | 'both'
    """
    cleaned_name = re.sub(r"[^a-zA-Z0-9_-]", "", name.strip())
    if not cleaned_name:
        raise ValueError("Tên MCP server không hợp lệ (chỉ chấp nhận chữ, số, gạch nối và gạch dưới).")

    mcp_type = config.get("type", "stdio").strip().lower()
    command = str(config.get("command") or "").strip()
    args = config.get("args") or []
    if isinstance(args, str):
        args = [a.strip() for a in args.split() if a.strip()]

    env = config.get("env") or {}
    if not isinstance(env, dict):
        env = {}
    # Clean env values
    cleaned_env = {str(k).strip(): str(v).strip() for k, v in env.items() if str(k).strip()}

    url = str(config.get("url") or "").strip()
    headers = config.get("headers") or {}
    if not isinstance(headers, dict):
        headers = {}
    cleaned_headers = {str(k).strip(): str(v).strip() for k, v in headers.items() if str(k).strip()}

    disabled = bool(config.get("disabled", False))

    if mcp_type == "http" and not url:
        raise ValueError("Vui lòng nhập URL cho HTTP MCP Server.")
    if mcp_type == "stdio" and not command:
        raise ValueError("Vui lòng nhập lệnh thực thi (command) cho Stdio MCP Server.")

    # 1. Cập nhật Gemini CLI (~/.gemini/config/mcp_config.json)
    if target in ("gemini", "both"):
        gemini_data = _read_json_file(GEMINI_MCP_FILE, {"mcpServers": {}})
        if "mcpServers" not in gemini_data or not isinstance(gemini_data["mcpServers"], dict):
            gemini_data["mcpServers"] = {}

        g_entry = {"disabled": disabled}
        if mcp_type == "http":
            g_entry["url"] = url
            if cleaned_headers:
                g_entry["headers"] = cleaned_headers
        else:
            g_entry["command"] = command
            g_entry["args"] = args
            if cleaned_env:
                g_entry["env"] = cleaned_env

        gemini_data["mcpServers"][cleaned_name] = g_entry
        _atomic_write_json(GEMINI_MCP_FILE, gemini_data)

    # 2. Cập nhật OpenCode CLI (~/.config/opencode/opencode.json)
    if target in ("opencode", "both"):
        opencode_data = _read_json_file(OPENCODE_CONFIG_FILE, {})
        if "mcp" not in opencode_data or not isinstance(opencode_data["mcp"], dict):
            opencode_data["mcp"] = {}
        if "servers" not in opencode_data["mcp"] or not isinstance(opencode_data["mcp"]["servers"], dict):
            opencode_data["mcp"]["servers"] = {}

        if mcp_type == "http":
            o_entry = {
                "type": "remote",
                "url": url,
            }
            if cleaned_headers:
                o_entry["headers"] = cleaned_headers
            if disabled:
                o_entry["disabled"] = True
        else:
            full_cmd = [command] + list(args)
            o_entry = {
                "type": "local",
                "command": full_cmd,
            }
            if cleaned_env:
                o_entry["environment"] = cleaned_env
            if disabled:
                o_entry["disabled"] = True

        opencode_data["mcp"]["servers"][cleaned_name] = o_entry
        _atomic_write_json(OPENCODE_CONFIG_FILE, opencode_data)

    return {
        "success": True,
        "name": cleaned_name,
        "message": f"Đã lưu thành công MCP server '{cleaned_name}' vào cấu hình hệ thống.",
    }


def remove_mcp_server(name: str) -> dict:
    """Xóa MCP server khỏi cả Gemini CLI và OpenCode CLI."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Tên MCP server không được để trống.")

    # Xóa khỏi Gemini
    gemini_data = _read_json_file(GEMINI_MCP_FILE, {"mcpServers": {}})
    if "mcpServers" in gemini_data and isinstance(gemini_data["mcpServers"], dict):
        if cleaned_name in gemini_data["mcpServers"]:
            del gemini_data["mcpServers"][cleaned_name]
            _atomic_write_json(GEMINI_MCP_FILE, gemini_data)

    # Xóa khỏi OpenCode
    opencode_data = _read_json_file(OPENCODE_CONFIG_FILE, {})
    if "mcp" in opencode_data and isinstance(opencode_data["mcp"], dict):
        servers = opencode_data["mcp"].get("servers", {})
        if isinstance(servers, dict) and cleaned_name in servers:
            del servers[cleaned_name]
            if not servers:
                del opencode_data["mcp"]["servers"]
                if not opencode_data["mcp"]:
                    del opencode_data["mcp"]
            _atomic_write_json(OPENCODE_CONFIG_FILE, opencode_data)

    return {
        "success": True,
        "name": cleaned_name,
        "message": f"Đã xóa hoàn toàn MCP server '{cleaned_name}'.",
    }


def toggle_mcp_server(name: str, enabled: bool) -> dict:
    """Bật hoặc tắt tạm thời một MCP server."""
    cleaned_name = name.strip()
    disabled = not enabled

    # Toggle trong Gemini
    gemini_data = _read_json_file(GEMINI_MCP_FILE, {"mcpServers": {}})
    if "mcpServers" in gemini_data and cleaned_name in gemini_data["mcpServers"]:
        gemini_data["mcpServers"][cleaned_name]["disabled"] = disabled
        _atomic_write_json(GEMINI_MCP_FILE, gemini_data)

    # Toggle trong OpenCode
    opencode_data = _read_json_file(OPENCODE_CONFIG_FILE, {})
    if "mcp" in opencode_data and isinstance(opencode_data["mcp"], dict):
        servers = opencode_data["mcp"].get("servers", {})
        if isinstance(servers, dict) and cleaned_name in servers:
            servers[cleaned_name]["disabled"] = disabled
            _atomic_write_json(OPENCODE_CONFIG_FILE, opencode_data)

    status_str = "kích hoạt" if enabled else "tắt"
    return {
        "success": True,
        "name": cleaned_name,
        "enabled": enabled,
        "message": f"Đã {status_str} MCP server '{cleaned_name}'.",
    }


def test_jira_connection(host: str, email: str, api_token: str) -> dict:
    """Kiểm tra xác thực với Jira Cloud REST API bằng Host, Email và API Token."""
    host = (host or "").strip().rstrip("/")
    email = (email or "").strip()
    api_token = (api_token or "").strip()

    if not host:
        return {"success": False, "message": "Vui lòng nhập Jira Host / URL (ví dụ: https://easysalon.atlassian.net)."}
    if not email:
        return {"success": False, "message": "Vui lòng nhập Email tài khoản Jira / Atlassian."}
    if not api_token:
        return {"success": False, "message": "Vui lòng nhập Jira API Token."}

    if not (host.startswith("http://") or host.startswith("https://")):
        host = "https://" + host

    auth_str = f"{email}:{api_token}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")

    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "EasySalon-Studio/1.0",
    }

    # Thử gọi Jira Cloud API v3 /rest/api/3/myself, nếu 404 thử v2
    endpoints = [f"{host}/rest/api/3/myself", f"{host}/rest/api/2/myself"]

    last_error = ""
    for ep in endpoints:
        try:
            req = urllib.request.Request(ep, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    display_name = body.get("displayName") or body.get("name") or email
                    email_addr = body.get("emailAddress") or email
                    account_type = body.get("accountType") or "atlassian"
                    return {
                        "success": True,
                        "user": display_name,
                        "email": email_addr,
                        "account_type": account_type,
                        "message": f"Kết nối Jira thành công! Tài khoản: {display_name} ({email_addr})",
                    }
        except urllib.error.HTTPError as he:
            if he.code == 401:
                return {
                    "success": False,
                    "status_code": 401,
                    "message": "Xác thực thất bại (401 Unauthorized): Email hoặc API Token không chính xác.",
                }
            elif he.code == 403:
                return {
                    "success": False,
                    "status_code": 403,
                    "message": "Không có quyền truy cập (403 Forbidden): Tài khoản bị chặn hoặc chưa cấp quyền API.",
                }
            elif he.code == 404:
                last_error = f"Không tìm thấy endpoint tại {ep} (404 Not Found)."
                continue
            else:
                return {
                    "success": False,
                    "status_code": he.code,
                    "message": f"Lỗi Jira API HTTP {he.code}: {he.reason}",
                }
        except urllib.error.URLError as ue:
            return {
                "success": False,
                "message": f"Không thể kết nối tới Jira Host '{host}': {ue.reason}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Lỗi khi kiểm tra kết nối Jira: {str(e)}",
            }

    return {
        "success": False,
        "message": f"Không thể kết nối tới Jira Host '{host}'. {last_error}",
    }


def test_github_connection(token: str) -> dict:
    """Kiểm tra xác thực với GitHub REST API bằng Personal Access Token."""
    token = (token or "").strip()
    if not token:
        return {"success": False, "message": "Vui lòng nhập GitHub Personal Access Token."}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EasySalon-Studio/1.0",
    }
    try:
        req = urllib.request.Request("https://api.github.com/user", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                login = body.get("login") or ""
                name = body.get("name") or login
                return {
                    "success": True,
                    "user": login,
                    "message": f"Kết nối GitHub thành công! Tài khoản: {name} (@{login})",
                }
    except urllib.error.HTTPError as he:
        if he.code == 401:
            return {"success": False, "message": "Xác thực thất bại (401): GitHub Token không chính xác hoặc đã hết hạn."}
        return {"success": False, "message": f"Lỗi GitHub API: {he.code} {he.reason}"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi kết nối tới GitHub: {str(e)}"}


def test_gitlab_connection(host: str, token: str) -> dict:
    """Kiểm tra xác thực với GitLab REST API bằng Host và Token."""
    host = (host or "").strip().rstrip("/")
    if not host:
        host = "https://gitlab.com"
    if not (host.startswith("http://") or host.startswith("https://")):
        host = "https://" + host
    token = (token or "").strip()
    if not token:
        return {"success": False, "message": "Vui lòng nhập GitLab Personal Access Token."}

    headers = {
        "PRIVATE-TOKEN": token,
        "User-Agent": "EasySalon-Studio/1.0",
    }
    try:
        req = urllib.request.Request(f"{host}/api/v4/user", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                username = body.get("username") or ""
                name = body.get("name") or username
                return {
                    "success": True,
                    "user": username,
                    "message": f"Kết nối GitLab thành công! Tài khoản: {name} (@{username})",
                }
    except urllib.error.HTTPError as he:
        if he.code == 401:
            return {"success": False, "message": "Xác thực thất bại (401): GitLab Token không chính xác hoặc không đủ quyền."}
        return {"success": False, "message": f"Lỗi GitLab API: {he.code} {he.reason}"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi kết nối tới GitLab Host '{host}': {str(e)}"}


def save_jira_mcp_preset(host: str, email: str, api_token: str, server_name: str = "jira") -> dict:
    """Helper cấu hình nhanh Atlassian Jira MCP Server chuẩn stdio npx."""
    host = (host or "").strip().rstrip("/")
    if not (host.startswith("http://") or host.startswith("https://")):
        host = "https://" + host
    email = (email or "").strip()
    api_token = (api_token or "").strip()

    cfg = {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "-p", "@answerai/jira-mcp", "answerai-jira-mcp"],
        "env": {
            "JIRA_HOST": host,
            "JIRA_BASE_URL": host,
            "JIRA_EMAIL": email,
            "JIRA_USER_EMAIL": email,
            "JIRA_API_TOKEN": api_token,
        },
        "disabled": False,
    }
    return save_mcp_server(server_name, cfg, target="both")


def save_github_mcp_preset(token: str, server_name: str = "github") -> dict:
    """Helper cấu hình nhanh GitHub MCP Server chuẩn stdio npx."""
    token = (token or "").strip()
    if not token:
        raise ValueError("Vui lòng nhập GitHub Personal Access Token.")
    cfg = {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": token,
        },
        "disabled": False,
    }
    return save_mcp_server(server_name, cfg, target="both")


def save_postgres_mcp_preset(conn_url: str, server_name: str = "postgres") -> dict:
    """Helper cấu hình nhanh PostgreSQL MCP Server chuẩn stdio npx."""
    conn_url = (conn_url or "").strip()
    if not conn_url:
        raise ValueError("Vui lòng nhập PostgreSQL Connection String URL.")
    cfg = {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres", conn_url],
        "env": {},
        "disabled": False,
    }
    return save_mcp_server(server_name, cfg, target="both")


def save_gitlab_mcp_preset(host: str, token: str, server_name: str = "gitlab") -> dict:
    """Helper cấu hình nhanh GitLab MCP Server chuẩn stdio npx."""
    host = (host or "").strip().rstrip("/")
    if not host:
        host = "https://gitlab.com"
    if not (host.startswith("http://") or host.startswith("https://")):
        host = "https://" + host
    token = (token or "").strip()
    if not token:
        raise ValueError("Vui lòng nhập GitLab Personal Access Token.")
    api_url = host if host.endswith("/api/v4") else f"{host}/api/v4"
    cfg = {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-gitlab"],
        "env": {
            "GITLAB_PERSONAL_ACCESS_TOKEN": token,
            "GITLAB_API_URL": api_url,
        },
        "disabled": False,
    }
    return save_mcp_server(server_name, cfg, target="both")
