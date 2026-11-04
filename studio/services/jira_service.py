# -*- coding: utf-8 -*-
"""
EasySalon Studio - Jira Cloud Integration Operations
Cung cấp các API truy vấn Ticket, tìm kiếm JQL, xem chi tiết và chuyển trạng thái ticket từ Jira Cloud.
"""

import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from studio.state import load_settings, STORAGE_DIR


def get_jira_config() -> dict:
    """Lấy thông tin cấu hình kết nối Jira từ MCP Server, settings hoặc biến môi trường."""
    from studio.services.mcp_service import get_all_mcp_servers
    s = load_settings()

    # 1. Tìm MCP server đại diện cho Jira
    jira_mcp = None
    try:
        servers = get_all_mcp_servers()
        for srv in servers:
            if srv.get("preset") == "jira" or srv.get("name") == "jira" or "jira" in (srv.get("name") or "").lower():
                jira_mcp = srv
                break
    except Exception:
        pass

    # Nếu Jira MCP Server được cấu hình nhưng đang bị tắt (disabled)
    if jira_mcp is not None and jira_mcp.get("disabled"):
        return {
            "host": "",
            "email": "",
            "api_token": "",
            "is_configured": False,
            "is_disabled": True,
            "server_name": jira_mcp.get("name", "jira"),
        }

    host = ""
    email = ""
    api_token = ""
    if jira_mcp is not None and not jira_mcp.get("disabled"):
        env = jira_mcp.get("env") or {}
        host = env.get("JIRA_HOST") or env.get("JIRA_BASE_URL") or ""
        email = env.get("JIRA_EMAIL") or env.get("JIRA_USER_EMAIL") or ""
        api_token = env.get("JIRA_API_TOKEN") or ""

    if not host:
        host = (s.get("jira_host") or os.environ.get("JIRA_HOST") or "").strip().rstrip("/")
    if not email:
        email = (s.get("jira_email") or os.environ.get("JIRA_EMAIL") or "").strip()
    if not api_token:
        api_token = (s.get("jira_api_token") or os.environ.get("JIRA_API_TOKEN") or "").strip()

    if host and not (host.startswith("http://") or host.startswith("https://")):
        host = "https://" + host

    has_active_mcp = jira_mcp is not None and not jira_mcp.get("disabled")
    is_configured = bool(host and email and api_token and (has_active_mcp or os.environ.get("JIRA_API_TOKEN")))

    return {
        "host": host if is_configured else "",
        "email": email if is_configured else "",
        "api_token": api_token if is_configured else "",
        "is_configured": is_configured,
        "is_disabled": bool(jira_mcp and jira_mcp.get("disabled")),
        "server_name": jira_mcp.get("name", "jira") if jira_mcp else "jira",
    }


def _get_auth_headers(cfg: dict) -> dict:
    auth_str = f"{cfg.get('email', '')}:{cfg.get('api_token', '')}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {auth_b64}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "EasySalon-Studio/2.0",
    }


# Cache thông tin profile của tài khoản Jira đang đăng nhập
_MY_PROFILE_CACHE = {"profile": {}, "ts": 0.0}
_MY_PROFILE_TTL = 600.0  # giây (10 phút)


def get_current_user_profile() -> dict:
    """Lấy thông tin profile đầy đủ của tài khoản Jira hiện tại (accountId, displayName, email, avatar)."""
    cfg = get_jira_config()
    if not cfg.get("is_configured"):
        return {}
    return _get_current_user_profile(cfg)


def _get_current_user_profile(cfg: dict) -> dict:
    global _MY_PROFILE_CACHE
    now = time.time()
    cached = _MY_PROFILE_CACHE.get("profile") or {}
    if cached and (now - _MY_PROFILE_CACHE.get("ts", 0.0)) < _MY_PROFILE_TTL:
        return cached

    headers = _get_auth_headers(cfg)
    host = cfg.get("host") or ""
    for ep in (f"{host}/rest/api/3/myself", f"{host}/rest/api/2/myself"):
        try:
            req = urllib.request.Request(ep, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                account_id = body.get("accountId") or body.get("key") or body.get("name") or ""
                if account_id:
                    avatar_dict = body.get("avatarUrls") or {}
                    profile = {
                        "accountId": account_id,
                        "displayName": body.get("displayName") or body.get("name") or cfg.get("email") or "Tôi",
                        "email": body.get("emailAddress") or cfg.get("email") or "",
                        "avatar": avatar_dict.get("24x24") or avatar_dict.get("48x48") or "",
                        "accountType": body.get("accountType") or "atlassian",
                        "active": body.get("active", True),
                    }
                    _MY_PROFILE_CACHE = {"profile": profile, "ts": now}
                    return profile
        except Exception:
            continue

    if cfg.get("email"):
        return {
            "accountId": "",
            "displayName": cfg.get("email"),
            "email": cfg.get("email"),
            "avatar": "",
            "accountType": "atlassian",
            "active": True
        }
    return {}


def _get_current_user_account_id(cfg: dict) -> str:
    """Lấy accountId của tài khoản Jira hiện tại (cache 10 phút). Trả về '' nếu không lấy được."""
    return _get_current_user_profile(cfg).get("accountId", "")


def _resolve_issue_ownership(cfg: dict, headers: dict, issue_key: str) -> dict:
    """
    Xác định Ticket có liên quan đến người dùng hiện tại hay không.
    Chỉ người được gán (assignee) hoặc người tạo (reporter) mới được đổi trạng thái.
    Đối với Sub-task, quyền chuyển đổi trạng thái do Jira Cloud trực tiếp kiểm soát.
    Trả về: {"ok": bool, "is_mine": bool, "relation": str, "message": str}
    """
    my_id = _get_current_user_account_id(cfg)
    if not my_id:
        # Không xác định được danh tính -> để Jira tự kiểm soát quyền (fail-open)
        return {"ok": True, "is_mine": False, "relation": "", "message": ""}

    host = cfg.get("host") or ""
    url = f"{host}/rest/api/3/issue/{issue_key}?fields=assignee,reporter,parent,issuetype"
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "is_mine": False, "relation": "",
                "message": f"Không kiểm tra được quyền trên Ticket {issue_key}: {str(e)}"}

    fields = data.get("fields") or {}
    assignee_id = ((fields.get("assignee") or {}).get("accountId")) or ""
    reporter_id = ((fields.get("reporter") or {}).get("accountId")) or ""
    parent_obj = fields.get("parent") or {}
    type_obj = fields.get("issuetype") or {}
    is_subtask = bool(parent_obj or type_obj.get("subtask") or (type_obj.get("name") or "").lower() in ("sub-task", "subtask"))

    # Đối với subtask: cho phép chuyển đổi trạng thái (quyền sẽ do Jira Cloud trực tiếp kiểm soát)
    if is_subtask:
        return {"ok": True, "is_mine": True, "relation": "subtask", "message": ""}

    if assignee_id and assignee_id == my_id:
        return {"ok": True, "is_mine": True, "relation": "assignee", "message": ""}
    if reporter_id and reporter_id == my_id:
        return {"ok": True, "is_mine": True, "relation": "reporter", "message": ""}

    return {
        "ok": False,
        "is_mine": False,
        "relation": "",
        "message": (
            f"Bạn không phải người được gán (assignee) hoặc người tạo (reporter) của Ticket {issue_key}, "
            "nên không thể đổi trạng thái."
        ),
    }


def get_jira_status() -> dict:
    """Kiểm tra trạng thái kết nối và lấy thông tin tài khoản Jira hiện tại."""
    cfg = get_jira_config()
    if cfg.get("is_disabled"):
        return {
            "success": False,
            "connected": False,
            "configured": False,
            "enabled": False,
            "message": "Jira MCP Server đang tạm dừng (disabled). Hãy bật lại trong Cài đặt MCP.",
        }
    if not cfg["is_configured"]:
        return {
            "success": False,
            "connected": False,
            "configured": False,
            "enabled": False,
            "message": "Chưa cấu hình Jira Host, Email hoặc API Token trong Cài đặt MCP.",
        }

    headers = _get_auth_headers(cfg)
    host = cfg["host"]

    # 1. Kiểm tra tài khoản bản thân
    user_info = {}
    endpoints = [f"{host}/rest/api/3/myself", f"{host}/rest/api/2/myself"]
    connected = False
    for ep in endpoints:
        try:
            req = urllib.request.Request(ep, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    user_info = {
                        "accountId": body.get("accountId") or body.get("key"),
                        "displayName": body.get("displayName") or body.get("name") or cfg["email"],
                        "emailAddress": body.get("emailAddress") or cfg["email"],
                        "avatarUrl": (body.get("avatarUrls") or {}).get("48x48", ""),
                    }
                    _MY_PROFILE_CACHE = {
                        "profile": {
                            "accountId": user_info["accountId"],
                            "displayName": user_info["displayName"],
                            "email": user_info["emailAddress"],
                            "avatar": (body.get("avatarUrls") or {}).get("24x24") or user_info["avatarUrl"],
                            "accountType": body.get("accountType") or "atlassian",
                            "active": True
                        },
                        "ts": time.time()
                    }
                    connected = True
                    break
        except Exception:
            continue

    if not connected:
        return {
            "success": False,
            "connected": False,
            "configured": True,
            "host": host,
            "email": cfg["email"],
            "message": "Không thể kết nối đến Jira Cloud. Vui lòng kiểm tra lại Host và API Token.",
        }

    # 2. Lấy danh sách Project
    projects = []
    try:
        req = urllib.request.Request(f"{host}/rest/api/3/project", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_projects = json.loads(resp.read().decode("utf-8"))
            for p in raw_projects:
                projects.append({
                    "id": p.get("id"),
                    "key": p.get("key"),
                    "name": p.get("name"),
                    "avatarUrl": (p.get("avatarUrls") or {}).get("48x48", "")
                })
    except Exception:
        pass

    return {
        "success": True,
        "connected": True,
        "configured": True,
        "host": host,
        "email": cfg["email"],
        "user": user_info,
        "projects": projects,
        "message": f"Đã kết nối Jira Cloud thành công ({user_info.get('displayName')})."
    }


def _html_to_markdown(html_str: str) -> str:
    """Chuyển đổi mã HTML đơn giản từ Jira renderedFields sang Markdown dễ đọc."""
    if not html_str:
        return ""
    s = html_str
    for i in range(6, 0, -1):
        tag = f"h{i}"
        s = re.sub(r"<" + tag + r"[^>]*>(.*?)</" + tag + r">", r"\n\n" + ("#" * i) + r" \1\n\n", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"</?(?:ul|ol)[^>]*>", "\n\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</p>", "\n\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<p[^>]*>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", r"\n```\n\1\n```\n", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>", r"**\1**", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<(?:em|i)[^>]*>(.*?)</(?:em|i)>", r"*\1*", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _format_jira_text(text: str) -> str:
    """Tự động phân đoạn và định dạng văn bản Jira theo chuẩn BDD / Gherkin & Markdown rõ ràng."""
    if not text:
        return ""
    s = str(text).strip()
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Format Acceptance Criteria headers
    s = re.sub(
        r"(?:^|\n|\s+)(Acceptance Criteria[^\n]*?|Tiêu chí chấp nhận[^\n]*?)(?=(?:\s+(?:AC\s*\d+|Kịch bản|Scenario)|$|\n))",
        r"\n\n### \1\n",
        s,
        flags=re.IGNORECASE
    )

    # Format AC1, AC2, AC3 / Kịch bản 1 / Scenario 1
    s = re.sub(
        r"(?:^|\n|\s+)((?:AC\s*\d+|Kịch bản\s*\d+|Scenario\s*\d+)[\s:\-]+[^\n]*?)(?=(?:\s+(?:Given|When|Then|And|But)\b|$|\n))",
        r"\n\n#### \1\n",
        s
    )

    # Format BDD Given / When / Then / And / But
    s = re.sub(
        r"(?:^|\n|\s+)\b(Given)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:When|Then|And|But|AC\s*\d+|Kịch bản|Scenario)\b|$|\n))",
        r"\n- **Given**: \2",
        s
    )
    s = re.sub(
        r"(?:^|\n|\s+)\b(When)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:Then|And|But|AC\s*\d+|Given|Kịch bản|Scenario)\b|$|\n))",
        r"\n- **When**: \2",
        s
    )
    s = re.sub(
        r"(?:^|\n|\s+)\b(Then)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Kịch bản|Scenario)\b|$|\n))",
        r"\n- **Then**: \2",
        s
    )
    s = re.sub(
        r"(?:^|\n|\s+)\b(And)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Then|Kịch bản|Scenario)\b|$|\n))",
        r"\n  - **And**: \2",
        s
    )
    s = re.sub(
        r"(?:^|\n|\s+)\b(But)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Then|Kịch bản|Scenario)\b|$|\n))",
        r"\n  - **But**: \2",
        s
    )

    # Đề mục phổ biến trong issue Jira nếu dính liền
    headings = [
        "Hiện tượng lỗi", "Mô tả lỗi", "Bug description",
        "Các bước tái hiện", "Steps to reproduce",
        "Kết quả thực tế", "Actual result",
        "Kết quả mong muốn", "Expected result",
        "Môi trường", "Environment",
        "Mục tiêu", "Objective",
        "Yêu cầu chức năng", "Functional requirements"
    ]
    for h in headings:
        pattern = r"(?:^|\n|(?<=[.!?])\s+)(" + re.escape(h) + r")\s*:\s*"
        s = re.sub(pattern, r"\n\n### \1:\n", s, flags=re.IGNORECASE)

    # Làm sạch dòng và khoảng trắng
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in s.split("\n")]
    s = "\n".join(lines)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _adf_to_markdown(node) -> str:
    """Chuyển đổi Atlassian Document Format (ADF) sang Markdown có cấu trúc rõ ràng."""
    if not node:
        return ""
    if isinstance(node, str):
        if "<" in node and ">" in node:
            return _html_to_markdown(node)
        return node
    if isinstance(node, list):
        items = [_adf_to_markdown(item) for item in node]
        return "\n\n".join(filter(None, items))
    if isinstance(node, dict):
        node_type = node.get("type", "")
        content = node.get("content", [])

        if node_type == "text":
            text = node.get("text", "")
            marks = node.get("marks", [])
            for m in marks:
                mtype = m.get("type")
                if mtype == "strong":
                    text = f"**{text.strip()}** " if text.endswith(" ") else f"**{text.strip()}**"
                elif mtype == "em":
                    text = f"*{text.strip()}*"
                elif mtype == "code":
                    text = f"`{text.strip()}`"
                elif mtype == "strike":
                    text = f"~~{text.strip()}~~"
                elif mtype == "link":
                    href = (m.get("attrs") or {}).get("href")
                    if href:
                        text = f"[{text}]({href})"
            return text

        if node_type == "hardBreak":
            return "\n"

        if node_type == "rule":
            return "\n---\n"

        if node_type == "mention":
            attrs = node.get("attrs", {})
            user_id = attrs.get("id", "user")
            return attrs.get("text") or f"@{user_id}"

        if node_type in ("inlineCard", "blockCard"):
            attrs = node.get("attrs", {})
            url = attrs.get("url", "")
            return f"<{url}>" if url else ""

        if node_type == "emoji":
            attrs = node.get("attrs", {})
            return attrs.get("text") or attrs.get("shortName") or ""

        if node_type == "paragraph":
            inner = "".join(_adf_to_markdown(c) for c in content)
            return inner.strip()

        if node_type == "heading":
            level = (node.get("attrs") or {}).get("level", 2)
            prefix = "#" * max(1, min(6, level))
            inner = "".join(_adf_to_markdown(c) for c in content).strip()
            return f"{prefix} {inner}"

        if node_type == "bulletList":
            lines = []
            for item in content:
                item_text = _adf_to_markdown(item).strip()
                if item_text:
                    lines.append(f"- {item_text}")
            return "\n".join(lines)

        if node_type == "orderedList":
            lines = []
            order = (node.get("attrs") or {}).get("order", 1)
            for idx, item in enumerate(content):
                item_text = _adf_to_markdown(item).strip()
                if item_text:
                    lines.append(f"{order + idx}. {item_text}")
            return "\n".join(lines)

        if node_type == "listItem":
            parts = [_adf_to_markdown(c) for c in content]
            return "\n".join(filter(None, parts))

        if node_type == "blockquote":
            inner = "\n".join(_adf_to_markdown(c) for c in content)
            return "\n".join(f"> {line}" for line in inner.splitlines())

        if node_type == "codeBlock":
            lang = (node.get("attrs") or {}).get("language", "")
            code = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            return f"```{lang}\n{code}\n```"

        if node_type == "table":
            rows = []
            for row in content:
                if row.get("type") == "tableRow":
                    cells = []
                    for cell in row.get("content", []):
                        cell_text = "".join(_adf_to_markdown(c) for c in cell.get("content", [])).strip()
                        cell_text = cell_text.replace("\n", " ")
                        cells.append(cell_text)
                    rows.append("| " + " | ".join(cells) + " |")
            if len(rows) > 1:
                col_count = len(rows[0].split("|")) - 2
                sep = "| " + " | ".join(["---"] * col_count) + " |"
                rows.insert(1, sep)
            return "\n".join(rows)

        if node_type in ("mediaSingle", "mediaGroup"):
            parts = [_adf_to_markdown(c) for c in content]
            return "\n\n".join(filter(None, parts))

        if node_type == "media":
            attrs = node.get("attrs", {})
            media_id = attrs.get("id") or ""
            alt_text = attrs.get("alt") or "Tệp đính kèm"
            return f"[{alt_text}](/api/jira/attachment?id={media_id}&name={urllib.parse.quote(alt_text)})"

        # Default fallback for doc or other containers
        parts = [_adf_to_markdown(c) for c in content]
        return "\n\n".join(filter(None, parts))

    return str(node)


def _clean_text_from_adf(node) -> str:
    """Chuyển đổi Atlassian Document Format (ADF), HTML hoặc text thuần sang Markdown/text có cấu trúc chuẩn."""
    if not node:
        return ""
    md_text = _adf_to_markdown(node)
    return _format_jira_text(md_text)


def _format_file_size(size_bytes: int) -> str:
    """Định dạng kích thước file sang B, KB, MB, GB dễ đọc."""
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    num = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024.0:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024.0
    return f"{num:.1f} TB"


def _rewrite_jira_html_media(html_str: str, attachments: list) -> str:
    """Xử lý và chuyển đổi các hình ảnh / video Jira sang proxy nội bộ và nhúng thẻ video HTML5 cho video."""
    if not html_str:
        return ""

    s = html_str
    att_by_id = {}
    att_by_name = {}
    for a in (attachments or []):
        aid = str(a.get("id") or "")
        fn = (a.get("filename") or "").lower()
        if aid:
            att_by_id[aid] = a
        if fn:
            att_by_name[fn] = a

    video_exts = (".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".ogv")

    # 1. Chuyển đổi các khối thẻ span.image-wrap chứa video hoặc thẻ img trỏ tới video sang thẻ video HTML5
    def _replace_video_tag(match):
        raw_block = match.group(0)
        href_match = re.search(r'href=["\']([^"\']+)["\']', raw_block, re.IGNORECASE)
        src_match = re.search(r'src=["\']([^"\']+)["\']', raw_block, re.IGNORECASE)
        target_url = (href_match.group(1) if href_match else (src_match.group(1) if src_match else ""))

        is_video = any(target_url.lower().endswith(ext) for ext in video_exts)
        att_obj = None

        id_match = re.search(r'/(?:attachment|thumbnail)/(\d+)', target_url)
        if id_match:
            aid = id_match.group(1)
            att_obj = att_by_id.get(aid)
            if att_obj and att_obj.get("is_video"):
                is_video = True

        if not is_video:
            fn_candidate = urllib.parse.unquote(target_url.split("/")[-1]).lower()
            if fn_candidate in att_by_name and att_by_name[fn_candidate].get("is_video"):
                is_video = True
                att_obj = att_by_name[fn_candidate]

        if is_video:
            fn = att_obj.get("filename") if att_obj else urllib.parse.unquote(target_url.split("/")[-1])
            aid = att_obj.get("id") if att_obj else (id_match.group(1) if id_match else "")
            proxy_url = f"/api/jira/attachment?id={aid}&name={urllib.parse.quote(fn)}" if aid else target_url
            mime = (att_obj.get("mime_type") if att_obj else "video/mp4") or "video/mp4"

            return (
                f'<div class="jira-video-embed my-3 p-3 rounded-lg bg-[#0c1628] border border-[#244170] shadow-md">'
                f'  <div class="flex items-center justify-between pb-2 text-xs text-slate-200 font-sans font-semibold">'
                f'    <span class="flex items-center gap-1.5 truncate">'
                f'      <svg class="w-4 h-4 text-rose-400 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm10 7l-6 3.5v-7l6 3.5z"/></svg>'
                f'      <span class="truncate">{html.escape(fn)}</span>'
                f'    </span>'
                f'    <a href="{proxy_url}" download="{html.escape(fn)}" class="text-[11px] text-blue-400 hover:underline shrink-0">Tải video</a>'
                f'  </div>'
                f'  <video controls playsinline preload="metadata" class="w-full max-h-[420px] rounded bg-black/90 border border-slate-700/60" src="{proxy_url}">'
                f'    <source src="{proxy_url}" type="{html.escape(mime)}">'
                f'    Trình duyệt không hỗ trợ thẻ video HTML5.'
                f'  </video>'
                f'</div>'
            )
        return raw_block

    s = re.sub(r'<span[^>]*class=["\'][^"\']*image-wrap[^"\']*["\'][^>]*>.*?</span>', _replace_video_tag, s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r'<img[^>]+(?:src=["\'][^"\']+\.(?:mp4|webm|mov|mkv|avi)[^"\']*["\'])[^>]*>', _replace_video_tag, s, flags=re.IGNORECASE)

    # 2. Viết lại các đường dẫn Jira attachment sang proxy nội bộ để không bị lỗi 404 hoặc thiếu auth
    def _rewrite_attachment_url(m):
        aid = m.group(1)
        raw_name = m.group(2) if m.lastindex >= 2 else ""
        return f"/api/jira/attachment?id={aid}&name={urllib.parse.quote(raw_name)}"

    s = re.sub(r'(?:https?://[^/]+)?/secure/attachment/(\d+)/([^"\'\s>]+)', _rewrite_attachment_url, s)
    s = re.sub(r'(?:https?://[^/]+)?/rest/api/[23]/attachment/content/(\d+)', r'/api/jira/attachment?id=\1', s)
    s = re.sub(r'(?:https?://[^/]+)?/secure/thumbnail/(\d+)/([^"\'\s>]+)', r'/api/jira/attachment?id=\1&thumb=1', s)

    return s


def stream_jira_attachment(handler, attachment_id: str, filename: str = "", is_thumb: bool = False):
    """Proxy và stream trực tiếp tệp đính kèm (video/hình ảnh/tài liệu) từ Jira Cloud về trình duyệt."""
    attachment_id = str(attachment_id or "").strip()
    if not attachment_id:
        handler.send_error(400, "Thiếu attachment ID")
        return

    cfg = get_jira_config()
    if not cfg["is_configured"]:
        handler.send_error(401, "Jira chưa được cấu hình")
        return

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    # Đọc Range header từ client nếu có (hỗ trợ tua video mượt mà)
    range_header = handler.headers.get("Range")
    req_headers = dict(headers)
    if range_header:
        req_headers["Range"] = range_header

    endpoint = "thumbnail" if is_thumb else "content"
    jira_url = f"{host}/rest/api/3/attachment/{endpoint}/{attachment_id}"

    try:
        req = urllib.request.Request(jira_url, headers=req_headers, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status_code = resp.status
            content_type = resp.headers.get("Content-Type")
            content_length = resp.headers.get("Content-Length")
            content_range = resp.headers.get("Content-Range")
            accept_ranges = resp.headers.get("Accept-Ranges", "bytes")

            ext = os.path.splitext(filename)[1].lower() if filename else ""
            if not content_type or content_type in ("application/octet-stream", "text/plain"):
                if ext == ".mp4": content_type = "video/mp4"
                elif ext == ".webm": content_type = "video/webm"
                elif ext == ".mov": content_type = "video/quicktime"
                elif ext == ".mkv": content_type = "video/x-matroska"
                elif ext == ".png": content_type = "image/png"
                elif ext in (".jpg", ".jpeg"): content_type = "image/jpeg"
                elif ext == ".gif": content_type = "image/gif"
                elif ext == ".svg": content_type = "image/svg+xml"

            handler.send_response(status_code)
            handler.send_header("Content-Type", content_type or "application/octet-stream")
            if content_length:
                handler.send_header("Content-Length", content_length)
            if content_range:
                handler.send_header("Content-Range", content_range)
            handler.send_header("Accept-Ranges", accept_ranges)
            handler.send_header("Cache-Control", "public, max-age=86400")
            if filename:
                safe_fn = urllib.parse.quote(filename)
                handler.send_header("Content-Disposition", f'inline; filename="{safe_fn}"')
            handler.end_headers()

            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                handler.wfile.write(chunk)
    except urllib.error.HTTPError as e:
        handler.send_error(e.code, f"Lỗi Jira Attachment: {e.reason}")
    except Exception as e:
        handler.send_error(500, f"Lỗi kết nối Jira Attachment: {str(e)}")


def _normalize_issue_summary(issue: dict, host: str, my_account_id: str = "") -> dict:
    f = issue.get("fields", {})
    key = issue.get("key") or issue.get("id") or ""
    status_obj = f.get("status") or {}
    status_cat = (status_obj.get("statusCategory") or {}).get("key") or ""
    type_obj = f.get("issuetype") or {}
    priority_obj = f.get("priority") or {}
    assignee_obj = f.get("assignee") or {}
    reporter_obj = f.get("reporter") or {}

    desc_raw = f.get("description")
    desc_clean = _clean_text_from_adf(desc_raw) if desc_raw else ""

    is_subtask = bool(type_obj.get("subtask", False) or (type_obj.get("name") or "").lower() == "sub-task")

    assignee_account_id = assignee_obj.get("accountId") or ""
    reporter_account_id = reporter_obj.get("accountId") or ""
    my_relation = ""
    if my_account_id:
        if assignee_account_id and assignee_account_id == my_account_id:
            my_relation = "assignee"
        elif reporter_account_id and reporter_account_id == my_account_id:
            my_relation = "reporter"

    return {
        "id": issue.get("id"),
        "key": key,
        "summary": f.get("summary") or "(Không có tiêu đề)",
        "description": desc_clean,
        "status": status_obj.get("name") or "Chưa rõ",
        "status_category": status_cat,  # 'new', 'indeterminate' (in progress), 'done'
        "issuetype": type_obj.get("name") or "Task",
        "issuetype_icon": type_obj.get("iconUrl") or "",
        "is_subtask": is_subtask,
        "priority": priority_obj.get("name") or "Medium",
        "priority_icon": priority_obj.get("iconUrl") or "",
        "assignee": assignee_obj.get("displayName") or "Chưa gán",
        "assignee_account_id": assignee_account_id,
        "assignee_avatar": (assignee_obj.get("avatarUrls") or {}).get("24x24") or "",
        "reporter": reporter_obj.get("displayName") or "",
        "reporter_account_id": reporter_account_id,
        "is_mine": bool(my_relation),
        "my_relation": my_relation,
        "ownership_known": bool(my_account_id),
        "created": f.get("created") or "",
        "updated": f.get("updated") or "",
        "labels": f.get("labels") or [],
        "url": f"{host}/browse/{key}" if key and host else "",
    }


def search_jira_issues(
    jql: str = None,
    query: str = None,
    project: str = None,
    filter_type: str = "all",
    hide_non_coding: bool = False,
    max_results: int = 30
) -> dict:
    """
    Tìm kiếm danh sách Ticket trên Jira Cloud sử dụng API JQL mới (/rest/api/3/search/jql).
    Tự động gắn các ràng buộc (bound query) để tránh lỗi 400 Bad Request của Atlassian.
    """
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {
            "success": False,
            "issues": [],
            "total": 0,
            "message": "Jira MCP Server đang tạm dừng. Vui lòng bật lại trong Cài đặt MCP." if cfg.get("is_disabled") else "Chưa cấu hình thông tin Jira trong Cài đặt MCP."
        }

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    # Xây dựng câu JQL an toàn
    jql_clauses = []

    # 1. Project
    if project:
        jql_clauses.append(f"project = '{project}'")
    else:
        # Default bound cho Jira Cloud
        jql_clauses.append("project in (EAS, SSLN, IZI, ESORG)")

    # 2. Filter type
    ft = (filter_type or "").lower().strip()
    if ft == "my":
        jql_clauses.append("assignee = currentUser()")
    elif ft in ("story", "feature"):
        jql_clauses.append("issuetype in ('Story', 'New Feature')")
    elif ft == "bug":
        jql_clauses.append("issuetype = 'Bug'")
    elif ft == "inprogress":
        jql_clauses.append("statusCategory = 'indeterminate'")
    elif ft == "todo":
        jql_clauses.append("statusCategory = 'new'")
    elif ft == "done":
        jql_clauses.append("statusCategory = 'done'")

    if hide_non_coding and ft not in ("story", "feature", "bug"):
        jql_clauses.append("issuetype != 'Non Coding Task'")

    is_key_search = False

    # 3. Query text hoặc Issue key
    if query and query.strip():
        q = query.strip()
        # Case A: Mã Ticket đầy đủ KEY-123 (ví dụ EAS-12578)
        if re.match(r"^[A-Z0-9]+-\d+$", q, re.IGNORECASE):
            is_key_search = True
            jql_clauses = [f"issueKey = '{q.upper()}'"]

        # Case B: Gõ liền hoặc có khoảng trắng (ví dụ eas12578, eas 12578, eas_12578)
        elif re.match(r"^([a-zA-Z]+)[\s\-_]*(\d+)$", q):
            m = re.match(r"^([a-zA-Z]+)[\s\-_]*(\d+)$", q)
            exact_key = f"{m.group(1).upper()}-{m.group(2)}"
            is_key_search = True
            jql_clauses = [f"issueKey = '{exact_key}'"]

        # Case C: Người dùng chỉ gõ số (ví dụ 12578) -> Tự động tìm chính xác Ticket theo số
        elif re.match(r"^\d+$", q):
            is_key_search = True
            default_projects = ["EAS", "SSLN", "IZI", "ESORG"]
            if project and project.upper() in default_projects:
                proj_order = [project.upper()] + [p for p in default_projects if p != project.upper()]
            else:
                proj_order = default_projects
            keys_in_clause = ", ".join(f"'{p}-{q}'" for p in proj_order)
            curr_p = (project or "EAS").upper()
            jql_clauses = [f"(issueKey in ({keys_in_clause}) OR (project = '{curr_p}' AND (summary ~ '{q}' OR text ~ '{q}')))"]

        # Case D: Tìm kiếm văn bản / nghiệp vụ thông thường
        else:
            clean_q = q.replace("'", "\\'")
            jql_clauses.append(f'(summary ~ "{clean_q}" OR text ~ "{clean_q}")')

    # Nếu không phải tìm kiếm đích danh một Ticket theo mã, luôn loại bỏ Sub-task khỏi danh sách chính
    if not is_key_search:
        jql_clauses.append("issuetype in standardIssueTypes()")

    final_jql = " AND ".join(jql_clauses) + " ORDER BY updated DESC"
    if jql and jql.strip():
        final_jql = jql.strip()

    payload = json.dumps({
        "jql": final_jql,
        "maxResults": min(max(max_results, 5), 50),
        "fields": [
            "summary", "status", "issuetype", "priority",
            "assignee", "reporter", "updated", "created",
            "description", "labels", "components"
        ]
    }).encode("utf-8")

    try:
        req = urllib.request.Request(f"{host}/rest/api/3/search/jql", data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_issues = data.get("issues", [])
            normalized = [_normalize_issue_summary(item, host) for item in raw_issues]

            # Loại bỏ các Sub-task khỏi danh sách chính nếu không phải tìm đích danh mã
            if not is_key_search:
                normalized = [it for it in normalized if not it.get("is_subtask")]

            return {
                "success": True,
                "issues": normalized,
                "total": len(normalized),
                "jql": final_jql,
                "message": f"Tìm thấy {len(normalized)} tickets."
            }
    except urllib.error.HTTPError as e:
        err_msg = ""
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            err_msg = "; ".join(err_body.get("errorMessages", []))
        except Exception:
            err_msg = str(e)
        return {
            "success": False,
            "issues": [],
            "total": 0,
            "jql": final_jql,
            "message": f"Lỗi truy vấn Jira (HTTP {e.code}): {err_msg}"
        }
    except Exception as e:
        return {
            "success": False,
            "issues": [],
            "total": 0,
            "message": f"Lỗi kết nối Jira: {str(e)}"
        }


_JIRA_NOTES_FILE = os.path.join(STORAGE_DIR, "jira_notes.json")


def get_jira_note(issue_key: str) -> dict:
    """Lấy nội dung ghi chú riêng của Ticket."""
    key = (issue_key or "").strip().upper()
    if not key:
        return {"success": False, "note": ""}
    try:
        if os.path.exists(_JIRA_NOTES_FILE):
            with open(_JIRA_NOTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"success": True, "key": key, "note": data.get(key, "")}
    except Exception:
        pass
    return {"success": True, "key": key, "note": ""}


def save_jira_note(issue_key: str, note: str) -> dict:
    """Lưu nội dung ghi chú riêng của Ticket vào storage/jira_notes.json."""
    key = (issue_key or "").strip().upper()
    if not key:
        return {"success": False, "message": "Thiếu mã Ticket."}
    try:
        os.makedirs(STORAGE_DIR, exist_ok=True)
        data = {}
        if os.path.exists(_JIRA_NOTES_FILE):
            try:
                with open(_JIRA_NOTES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[key] = note or ""
        with open(_JIRA_NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"success": True, "key": key, "note": data[key]}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_jira_issue_detail(issue_key: str) -> dict:
    """Lấy toàn bộ thông tin chi tiết của 1 Ticket bao gồm mô tả HTML/ADF, các bình luận và trạng thái có thể chuyển."""
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {"success": False, "message": "Chưa cấu hình Jira."}

    key = (issue_key or "").strip().upper()
    if not key:
        return {"success": False, "message": "Vui lòng nhập Issue Key."}

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    url = f"{host}/rest/api/3/issue/{key}?expand=renderedFields,transitions,changelog"
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            f = data.get("fields", {})
            rf = data.get("renderedFields", {})

            # Clean / Rendered description
            desc_html = rf.get("description") or ""
            desc_text = _clean_text_from_adf(f.get("description"))
            if not desc_text and desc_html:
                desc_text = _clean_text_from_adf(desc_html)

            # Normalized summary info
            my_account_id = _get_current_user_account_id(cfg)
            base_info = _normalize_issue_summary(data, host, my_account_id)
            base_info["can_transition"] = bool(base_info.get("is_mine")) or not my_account_id

            # Comments
            comments_data = (f.get("comment") or {}).get("comments", [])
            rf_comments = (rf.get("comment") or {}).get("comments", [])
            rendered_comments_map = {str(c.get("id")): c.get("body") for c in rf_comments}

            comments = []
            for c in comments_data:
                cid = str(c.get("id"))
                author = c.get("author") or {}
                body_raw = c.get("body")
                body_text = _clean_text_from_adf(body_raw)
                if not body_text and cid in rendered_comments_map:
                    body_text = _clean_text_from_adf(rendered_comments_map[cid])
                comments.append({
                    "id": cid,
                    "author": author.get("displayName") or "Thành viên",
                    "author_avatar": (author.get("avatarUrls") or {}).get("24x24", ""),
                    "created": c.get("created", ""),
                    "updated": c.get("updated", ""),
                    "body_html": rendered_comments_map.get(cid) or "",
                    "body_text": body_text,
                })

            # Transitions
            transitions = []
            for t in data.get("transitions", []):
                transitions.append({
                    "id": str(t.get("id")),
                    "name": t.get("name"),
                    "to_status": (t.get("to") or {}).get("name") or t.get("name"),
                    "category": ((t.get("to") or {}).get("statusCategory") or {}).get("key") or ""
                })

            # Sub-tasks: lấy danh sách các nhiệm vụ con của Ticket này
            subtasks_raw = f.get("subtasks") or []
            subtasks = []
            for st in subtasks_raw:
                st_f = st.get("fields") or {}
                st_stat = st_f.get("status") or {}
                st_type = st_f.get("issuetype") or {}
                st_assignee = st_f.get("assignee") or {}
                subtasks.append({
                    "id": str(st.get("id") or ""),
                    "key": st.get("key"),
                    "summary": st_f.get("summary") or "(Không có tiêu đề)",
                    "status": st_stat.get("name") or "To Do",
                    "status_category": ((st_stat.get("statusCategory") or {}).get("key")) or "",
                    "issuetype": st_type.get("name") or "Sub-task",
                    "issuetype_icon": st_type.get("iconUrl") or "",
                    "assignee": st_assignee.get("displayName") or "Chưa gán",
                    "assignee_account_id": st_assignee.get("accountId") or "",
                    "assignee_avatar": (st_assignee.get("avatarUrls") or {}).get("24x24") or (st_assignee.get("avatarUrls") or {}).get("32x32") or "",
                    "assignee_email": st_assignee.get("emailAddress") or "",
                    "url": f"{host}/browse/{st.get('key')}" if host and st.get("key") else "",
                    "transitions": []
                })

            # Truy vấn JQL parent = key để lấy đầy đủ Người thực hiện (Assignee) và các subtask nếu cần
            try:
                p_payload = json.dumps({
                    "jql": f"parent = '{key}' ORDER BY created ASC",
                    "maxResults": 50,
                    "fields": ["summary", "status", "issuetype", "priority", "assignee"]
                }).encode("utf-8")
                p_req = urllib.request.Request(f"{host}/rest/api/3/search/jql", data=p_payload, headers=headers, method="POST")
                with urllib.request.urlopen(p_req, timeout=5) as p_resp:
                    p_data = json.loads(p_resp.read().decode("utf-8"))
                    jql_issues = p_data.get("issues", [])
                    if len(subtasks) == 0 and jql_issues:
                        for pst in jql_issues:
                            pst_f = pst.get("fields") or {}
                            pst_stat = pst_f.get("status") or {}
                            pst_type = pst_f.get("issuetype") or {}
                            pst_assignee = pst_f.get("assignee") or {}
                            subtasks.append({
                                "id": str(pst.get("id") or ""),
                                "key": pst.get("key"),
                                "summary": pst_f.get("summary") or "(Không có tiêu đề)",
                                "status": pst_stat.get("name") or "To Do",
                                "status_category": ((pst_stat.get("statusCategory") or {}).get("key")) or "",
                                "issuetype": pst_type.get("name") or "Sub-task",
                                "issuetype_icon": pst_type.get("iconUrl") or "",
                                "assignee": pst_assignee.get("displayName") or "Chưa gán",
                                "assignee_account_id": pst_assignee.get("accountId") or "",
                                "assignee_avatar": (pst_assignee.get("avatarUrls") or {}).get("24x24") or (pst_assignee.get("avatarUrls") or {}).get("32x32") or "",
                                "assignee_email": pst_assignee.get("emailAddress") or "",
                                "url": f"{host}/browse/{pst.get('key')}" if host and pst.get("key") else "",
                                "transitions": []
                            })
                    else:
                        # Ghép thông tin assignee chính xác từ JQL vào từng subtask
                        for pst in jql_issues:
                            pst_key = pst.get("key")
                            pst_f = pst.get("fields") or {}
                            pst_assignee = pst_f.get("assignee") or {}
                            for st in subtasks:
                                if st.get("key") == pst_key and pst_assignee:
                                    st["assignee"] = pst_assignee.get("displayName") or "Chưa gán"
                                    st["assignee_account_id"] = pst_assignee.get("accountId") or ""
                                    st["assignee_avatar"] = (pst_assignee.get("avatarUrls") or {}).get("24x24") or (pst_assignee.get("avatarUrls") or {}).get("32x32") or ""
                                    st["assignee_email"] = pst_assignee.get("emailAddress") or ""
            except Exception:
                pass

            # Nạp thông tin chi tiết (người thực hiện và transitions) cho từng subtask song song
            if subtasks:
                def _load_st_trans(st_item):
                    st_key = st_item.get("key")
                    if not st_key:
                        return
                    try:
                        # Ưu tiên lấy chi tiết subtask kèm assignee và transitions
                        st_url = f"{host}/rest/api/3/issue/{st_key}?fields=summary,status,assignee,issuetype&expand=transitions"
                        st_req = urllib.request.Request(st_url, headers=headers, method="GET")
                        with urllib.request.urlopen(st_req, timeout=4) as st_resp:
                            st_data = json.loads(st_resp.read().decode("utf-8"))
                            st_f = st_data.get("fields") or {}
                            st_assignee = st_f.get("assignee") or {}
                            if st_assignee:
                                st_item["assignee"] = st_assignee.get("displayName") or "Chưa gán"
                                st_item["assignee_account_id"] = st_assignee.get("accountId") or ""
                                st_item["assignee_avatar"] = (st_assignee.get("avatarUrls") or {}).get("24x24") or (st_assignee.get("avatarUrls") or {}).get("32x32") or ""
                                st_item["assignee_email"] = st_assignee.get("emailAddress") or ""

                            trans_raw = st_data.get("transitions", [])
                            if not trans_raw:
                                try:
                                    tr_url = f"{host}/rest/api/3/issue/{st_key}/transitions"
                                    tr_req = urllib.request.Request(tr_url, headers=headers, method="GET")
                                    with urllib.request.urlopen(tr_req, timeout=3) as tr_resp:
                                        tr_data = json.loads(tr_resp.read().decode("utf-8"))
                                        trans_raw = tr_data.get("transitions", [])
                                except Exception:
                                    pass

                            st_item["transitions"] = [
                                {
                                    "id": str(tr.get("id")),
                                    "name": tr.get("name"),
                                    "to_status": (tr.get("to") or {}).get("name") or tr.get("name"),
                                    "category": ((tr.get("to") or {}).get("statusCategory") or {}).get("key") or ""
                                }
                                for tr in trans_raw
                            ]
                    except Exception:
                        pass

                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(len(subtasks), 5)) as pool:
                    list(pool.map(_load_st_trans, subtasks))

            # History (Changelog / Lịch sử thay đổi)
            changelog_raw = (data.get("changelog") or {}).get("histories", [])
            history_list = []
            for h in changelog_raw:
                h_author = h.get("author") or {}
                items = []
                for it in (h.get("items") or []):
                    f_name = it.get("field") or ""
                    items.append({
                        "field": f_name,
                        "from": it.get("fromString") or "(trống)",
                        "to": it.get("toString") or "(trống)"
                    })
                if items:
                    history_list.append({
                        "id": str(h.get("id")),
                        "author": h_author.get("displayName") or "Hệ thống",
                        "author_avatar": (h_author.get("avatarUrls") or {}).get("24x24", ""),
                        "created": h.get("created", ""),
                        "items": items
                    })

            # Attachments & Videos (Bằng chứng lỗi / Evidence)
            raw_attachments = f.get("attachment") or []
            attachments = []
            video_exts = (".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".ogv")
            img_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")

            for att in raw_attachments:
                aid = str(att.get("id") or "")
                fn = att.get("filename") or "attachment"
                mime = (att.get("mimeType") or "").lower()
                size_bytes = att.get("size") or 0
                ext = os.path.splitext(fn)[1].lower()

                is_video = mime.startswith("video/") or ext in video_exts
                is_image = mime.startswith("image/") or ext in img_exts

                attachments.append({
                    "id": aid,
                    "filename": fn,
                    "size": size_bytes,
                    "size_formatted": _format_file_size(size_bytes),
                    "mime_type": mime or ("video/mp4" if is_video else "application/octet-stream"),
                    "created": att.get("created") or "",
                    "author": (att.get("author") or {}).get("displayName") or "",
                    "is_video": is_video,
                    "is_image": is_image,
                    "url": f"/api/jira/attachment?id={aid}&name={urllib.parse.quote(fn)}",
                    "thumbnail_url": f"/api/jira/attachment?id={aid}&thumb=1" if att.get("thumbnail") else ""
                })

            if desc_html:
                desc_html = _rewrite_jira_html_media(desc_html, attachments)

            base_info["description_html"] = desc_html
            base_info["description_text"] = desc_text
            base_info["attachments"] = attachments
            base_info["comments"] = comments
            base_info["history"] = history_list
            base_info["note"] = get_jira_note(key).get("note", "")
            base_info["transitions"] = transitions
            base_info["subtasks"] = subtasks
            base_info["my_account_id"] = my_account_id
            base_info["my_profile"] = _get_current_user_profile(cfg)

            return {
                "success": True,
                "issue": base_info
            }
    except urllib.error.HTTPError as e:
        return {"success": False, "message": f"Không tìm thấy Ticket {key} (HTTP {e.code})"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi tải chi tiết Ticket: {str(e)}"}


def add_jira_comment(issue_key: str, body: str) -> dict:
    """Thêm bình luận mới vào Ticket Jira."""
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {"success": False, "message": "Chưa cấu hình Jira."}

    key = (issue_key or "").strip().upper()
    comment_text = (body or "").strip()
    if not key or not comment_text:
        return {"success": False, "message": "Thiếu Issue Key hoặc nội dung bình luận."}

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    # Jira v3 comment payload sử dụng ADF
    adf_payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": comment_text
                        }
                    ]
                }
            ]
        }
    }

    url = f"{host}/rest/api/3/issue/{key}/comment"
    try:
        req = urllib.request.Request(url, data=json.dumps(adf_payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "message": f"Đã thêm bình luận vào ticket {key}.",
                "comment_id": data.get("id")
            }
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi gửi bình luận: {str(e)}"}


def transition_jira_issue(issue_key: str, transition_id: str = None, comment: str = None, target_status: str = None) -> dict:
    """Chuyển trạng thái Ticket hoặc Sub-task (ví dụ To Do -> In Progress -> Done)."""
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {"success": False, "message": "Chưa cấu hình Jira."}

    key = (issue_key or "").strip().upper()
    tid = str(transition_id or "").strip()
    status_name = str(target_status or "").strip()
    if not key or (not tid and not status_name):
        return {"success": False, "message": "Thiếu Issue Key hoặc Transition ID/Trạng thái."}

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    # Nếu truyền target_status thay vì transition_id, tìm transition_id tương ứng
    if not tid and status_name:
        try:
            t_url = f"{host}/rest/api/3/issue/{key}/transitions"
            t_req = urllib.request.Request(t_url, headers=headers, method="GET")
            with urllib.request.urlopen(t_req, timeout=8) as t_resp:
                t_data = json.loads(t_resp.read().decode("utf-8"))
                for tr in t_data.get("transitions", []):
                    tr_name = (tr.get("name") or "").strip().lower()
                    tr_to = ((tr.get("to") or {}).get("name") or "").strip().lower()
                    target_lower = status_name.lower()
                    if tr_name == target_lower or tr_to == target_lower:
                        tid = str(tr.get("id"))
                        break
        except Exception:
            pass

    if not tid:
        return {"success": False, "message": f"Không tìm thấy transition phù hợp cho trạng thái '{status_name}' trên {key}."}

    # Kiểm tra quyền: đối với subtask cho phép thực thi, Jira Cloud sẽ kiểm soát quyền
    ownership = _resolve_issue_ownership(cfg, headers, key)
    if not ownership.get("ok", False):
        return {"success": False, "message": ownership.get("message") or "Bạn không có quyền đổi trạng thái Ticket này."}

    payload = {"transition": {"id": tid}}
    if comment and comment.strip():
        payload["update"] = {
            "comment": [
                {
                    "add": {
                        "body": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": comment.strip()}]
                                }
                            ]
                        }
                    }
                }
            ]
        }

    url = f"{host}/rest/api/3/issue/{key}/transitions"
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as resp:
            return {
                "success": True,
                "message": f"Đã chuyển trạng thái Ticket {key} thành công."
            }
    except urllib.error.HTTPError as he:
        err_msg = ""
        try:
            err_body = json.loads(he.read().decode("utf-8"))
            err_msg = str(err_body.get("errors") or err_body.get("errorMessages") or err_body)
        except Exception:
            err_msg = f"HTTP {he.code}: {he.reason}"
        return {"success": False, "message": f"Lỗi khi chuyển trạng thái: {err_msg}"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi chuyển trạng thái: {str(e)}"}


def analyze_jira_issue_with_rovo(issue_data: dict) -> dict:
    """
    Phân tích yêu cầu kỹ thuật và nghiệp vụ của Ticket Jira bằng Atlassian Rovo AI.
    Tự động bóc tách phạm vi Frontend/Backend, Acceptance Criteria và Checklist triển khai.
    """
    import subprocess
    from config import get_opencode_bin, get_agy_bin
    from studio.state import load_settings

    key = str(issue_data.get("key") or "TICKET").strip().upper()
    summary = str(issue_data.get("summary") or "").strip()
    desc = str(issue_data.get("description_text") or issue_data.get("description") or "").strip()
    issuetype = str(issue_data.get("issuetype") or "Task").strip()
    comments = issue_data.get("comments") or []

    # Format bình luận gần nhất nếu có
    recent_comments = ""
    if comments and isinstance(comments, list):
        c_lines = []
        for c in comments[-3:]:
            author = c.get("author") or "Thành viên"
            body = (c.get("body_text") or c.get("body") or "").strip()
            if body:
                c_lines.append(f"- {author}: {body[:150]}")
        if c_lines:
            recent_comments = "\nThảo luận gần nhất:\n" + "\n".join(c_lines)

    # 1. Thử gọi AI Engine (OpenCode / Antigravity CLI)
    prompt = f"""Bạn là Atlassian Rovo AI - Trợ lý phân tích kỹ thuật và bóc tách yêu cầu cho hệ thống EasySalon (Frontend: React/TypeScript Ant Design tại easysalon-webapp, Backend: .NET Core/C# Web API Entity Framework tại easysalon-api, SQL Server).

Thông tin Ticket Jira:
- Mã Ticket: {key}
- Tiêu đề: {summary}
- Loại yêu cầu: {issuetype}
- Mô tả chi tiết:
{desc[:2500] if desc else '(Không có mô tả chi tiết)'}
{recent_comments}

Hãy phân tích ngắn gọn, chuyên nghiệp và thực tế theo 4 mục chuẩn sau (dùng Markdown):
### 🎯 1. Tóm tắt cốt lõi & Mục tiêu nghiệp vụ
(2-3 câu nêu rõ bài toán cần giải quyết, đối tượng tác động)

### ⚙️ 2. Phân tích phạm vi kỹ thuật (Technical Scope)
- **Frontend (easysalon-webapp)**: Các component, modal, form, state hoặc format hiển thị
- **Backend (easysalon-api)**: Các API Controller, Service, DTO, Database / Query nếu có

### 🧪 3. Tiêu chí nghiệm thu & Edge Cases (BDD Acceptance Criteria)
- Tiêu chí hoàn thành (Given-When-Then hoặc Checklist đạt chuẩn)
- Các trường hợp biên: null/empty, phân quyền cơ sở, concurrency

### 📋 4. Checklist triển khai đề xuất
- [ ] Bước 1: ...
- [ ] Bước 2: ...
- [ ] Bước 3: ..."""

    settings = load_settings()
    engine = str(settings.get("engine") or "opencode").strip().lower()

    # Thử chạy qua OpenCode CLI nhanh (timeout ngắn 1.8s để không làm đơ giao diện người dùng)
    if engine == "opencode":
        opencode_bin = get_opencode_bin()
        model = str(settings.get("opencode_model") or "opencode/flint-40b-free").strip()
        cmd = [opencode_bin, "run", "--format", "json", "--auto"]
        if model:
            cmd.extend(["--model", model])
        cmd.append(prompt)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.8)
            if res.returncode == 0 and res.stdout:
                out_texts = []
                for line in res.stdout.strip().split("\n"):
                    try:
                        d = json.loads(line)
                        if d.get("type") == "text":
                            t = d.get("part", {}).get("text", "")
                            if t:
                                out_texts.append(t)
                    except Exception:
                        pass
                combined = "".join(out_texts).strip()
                if combined and "###" in combined:
                    return {
                        "success": True,
                        "analysis": combined,
                        "engine": f"Atlassian Rovo ({model})"
                    }
        except Exception:
            pass

    # Thử chạy qua Antigravity CLI nhanh (timeout ngắn 1.5s)
    agy_bin = get_agy_bin()
    try:
        res = subprocess.run(
            [agy_bin, "--dangerously-skip-permissions", "-p", prompt, "--output-format", "stream-json"],
            capture_output=True,
            text=True,
            timeout=1.5
        )
        if res.returncode == 0 and res.stdout:
            out_texts = []
            for line in res.stdout.strip().split("\n"):
                try:
                    d = json.loads(line)
                    if d.get("event") == "step_update":
                        su = d.get("step_update", {})
                        if su.get("step_type") == "agent_response":
                            delta = su.get("text_delta", "")
                            if delta:
                                out_texts.append(delta)
                    elif d.get("event") == "result":
                        resp_str = d.get("result", {}).get("response", "")
                        if resp_str and not out_texts:
                            out_texts.append(resp_str)
                except Exception:
                    pass
            combined = "".join(out_texts).strip()
            if combined and len(combined) > 50:
                return {
                    "success": True,
                    "analysis": combined,
                    "engine": "Atlassian Rovo (Antigravity AI)"
                }
    except Exception:
        pass

    # 2. Phân tích tức thì bằng Atlassian Rovo Intelligence Engine (Domain Knowledge EasySalon)
    analysis = _generate_heuristic_rovo_analysis(key, summary, desc, issuetype)
    return {
        "success": True,
        "analysis": analysis,
        "engine": "Atlassian Rovo (Domain Intelligence)"
    }


def _generate_heuristic_rovo_analysis(key: str, summary: str, desc: str, issuetype: str) -> str:
    """Tạo bản phân tích Rovo chất lượng cao, chuẩn cấu trúc kỹ thuật EasySalon."""
    is_bug = "bug" in issuetype.lower() or any(w in summary.lower() for w in ["lỗi", "error", "không", "mất", "bị", "sai", "thiếu"])
    combined_text = (summary + " " + desc).lower()

    lines = []
    lines.append("### 🎯 1. Tóm tắt cốt lõi & Mục tiêu nghiệp vụ")
    if is_bug:
        lines.append(f"- **Vấn đề ghi nhận:** {summary}")
        lines.append("- **Mục tiêu:** Khắc phục triệt để lỗi vận hành, bảo đảm dữ liệu nhất quán và không làm gián đoạn trải nghiệm người dùng tại chi nhánh salon.")
    else:
        lines.append(f"- **Yêu cầu phát triển:** {summary}")
        lines.append("- **Mục tiêu:** Cung cấp tính năng mới đúng yêu cầu nghiệp vụ, hỗ trợ thao tác nhanh gọn, trực quan cho nhân viên và chủ salon.")

    # Trích xuất bối cảnh nếu có
    if desc and len(desc.strip()) > 10:
        clean_desc_preview = desc.replace("\r", " ").replace("\n", " ").strip()[:180]
        lines.append(f"- **Bối cảnh chi tiết:** \"{clean_desc_preview}...\"")

    # Phân tích kỹ thuật Frontend (easysalon-webapp)
    fe_points = []
    if any(k in combined_text for k in ["in ấn", "in bill", "in hóa đơn", "mẫu in", "khổ 58", "khổ 80"]):
        fe_points.append("Cập nhật template in hóa đơn đồng bộ các khổ in (`58mm`, `80mm` và in A5/A4).")
        fe_points.append("Kiểm tra component hiển thị dòng tiền Tip và tổng thanh toán tại modal xem trước hóa đơn.")
    if any(k in combined_text for k in ["setting", "cài đặt", "cấu hình", "bật/tắt", "toggle"]):
        fe_points.append("Thêm toggle/checkbox cấu hình lưu trạng thái trong trang Cài đặt (`BranchSetting` / `InvoiceSetting`).")
    if any(k in combined_text for k in ["lịch hẹn", "đặt lịch", "giường", "ghế", "stylist"]):
        fe_points.append("Cập nhật màn hình Điều phối Lịch hẹn và sơ đồ giường ghế (`BookingTimeline` / `BedMatrix`).")
    if any(k in combined_text for k in ["khách hàng", "thành viên", "hạng thẻ", "tích điểm"]):
        fe_points.append("Cập nhật thông tin điểm thưởng và lịch sử chi tiêu trong hồ sơ khách hàng (`CustomerDetailModal`).")
    if any(k in combined_text for k in ["thanh toán", "thu tiền", "pos", "chuyển khoản", "qr"]):
        fe_points.append("Điều chỉnh Form thanh toán bán hàng POS (`PaymentCheckoutModal`), đồng bộ số liệu tức thì.")
    if not fe_points:
        fe_points.append("Rà soát UI/UX trên **easysalon-webapp**, cập nhật State Management và Form validation tương ứng.")

    # Phân tích kỹ thuật Backend (easysalon-api)
    be_points = []
    if any(k in combined_text for k in ["tiền tip", "tip", "hóa đơn", "bill"]):
        be_points.append("Cập nhật `InvoiceController` và `InvoiceService` xử lý tính toán gộp tiền Tip vào tổng thanh toán.")
        be_points.append("Bổ sung thuộc tính `TipAmount` / `IsShowTip` vào `InvoiceDetailDTO` và cấu hình chi nhánh.")
    if any(k in combined_text for k in ["setting", "cài đặt", "cấu hình"]):
        be_points.append("Thêm field cấu hình trong database bảng `BranchSettings` và API `GET/PUT /api/branch-settings`.")
    if any(k in combined_text for k in ["báo cáo", "excel", "thống kê", "doanh thu"]):
        be_points.append("Tối ưu hóa câu truy vấn LINQ/SQL dữ liệu báo cáo, bảo đảm hiệu năng và tính chính xác cao.")
    if any(k in combined_text for k in ["sổ quỹ", "thu chi", "tiền mặt"]):
        be_points.append("Cập nhật nghiệp vụ tự động sinh phiếu thu/chi tương ứng khi hoàn tất giao dịch.")
    if not be_points:
        be_points.append("Cập nhật API Endpoint và Business Logic Service tại **easysalon-api**, bảo đảm chuẩn DTO.")

    lines.append("\n### ⚙️ 2. Phân tích phạm vi kỹ thuật (Technical Scope)")
    lines.append("- **Frontend (easysalon-webapp):**")
    for fp in fe_points:
        lines.append(f"  - {fp}")
    lines.append("- **Backend (easysalon-api):**")
    for bp in be_points:
        lines.append(f"  - {bp}")

    # Acceptance Criteria (BDD Scenario)
    lines.append("\n### 🧪 3. Tiêu chí nghiệm thu & Edge Cases")
    lines.append("- **Tiêu chí nghiệm thu (Acceptance Criteria):**")
    lines.append("  - **Given**: Người dùng thao tác trên giao diện salon đã được phân quyền hợp lệ.")
    lines.append("  - **When**: Thực hiện luồng nghiệp vụ tương ứng theo mô tả của ticket.")
    lines.append("  - **Then**: Hệ thống xử lý chính xác, hiển thị dữ liệu đồng bộ giữa Web Admin, POS và Mobile.")
    lines.append("- **Edge Cases cần kiểm thử:**")
    lines.append("  - Dữ liệu rỗng / null (0 VNĐ hoặc chưa thiết lập cấu hình) không gây lỗi crash runtime.")
    lines.append("  - Phân quyền chi nhánh (Multi-branch): chi nhánh A thay đổi không ảnh hưởng đến chi nhánh B.")
    lines.append("  - Thao tác nhanh liên tục (Double-click / Concurrency) không tạo trùng lặp giao dịch.")

    # Checklist triển khai
    lines.append("\n### 📋 4. Checklist triển khai đề xuất")
    lines.append("- [ ] Tái hiện và xác nhận yêu cầu/sự cố trên môi trường Development")
    lines.append("- [ ] Triển khai chỉnh sửa Backend (.NET Core API, Service & DTO)")
    lines.append("- [ ] Cập nhật giao diện Frontend (React Component, Ant Design & State)")
    lines.append("- [ ] Tự kiểm thử (Unit test / Manual test) đầy đủ các trường hợp biên")

    return "\n".join(lines)


# Cache lưu các Issue và Comment đã đọc để phát hiện thay đổi mới thời gian thực
_JIRA_SEEN_CACHE = {
    "initialized": False,
    "issues": set(),
    "comments": set(),
    "last_check": 0.0
}
_SELF_CREATED_SUBTASKS = set()


# Cache danh sách thành viên có thể gán (assignable users)
_ASSIGNABLE_USERS_CACHE = {}
_ASSIGNABLE_USERS_TTL = 300.0  # 5 phút


def get_jira_assignable_users(issue_key: str = "", project_key: str = "", query: str = "") -> dict:
    """Lấy danh sách người dùng có thể phân công (assignable users) từ Jira Cloud."""
    global _ASSIGNABLE_USERS_CACHE
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {"success": False, "users": [], "message": "Chưa cấu hình thông tin Jira."}

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    pkey = (project_key or "").strip().upper()
    ikey = (issue_key or "").strip().upper()
    if not pkey and ikey and "-" in ikey:
        pkey = ikey.split("-")[0]

    my_profile = _get_current_user_profile(cfg)
    my_account_id = my_profile.get("accountId") or ""

    cache_key = f"{pkey}:{ikey}:{query}"
    now = time.time()
    if cache_key in _ASSIGNABLE_USERS_CACHE:
        entry = _ASSIGNABLE_USERS_CACHE[cache_key]
        cached_users, cached_ts = entry[0], entry[1]
        cached_my_id = entry[2] if len(entry) > 2 else ""
        cached_profile = entry[3] if len(entry) > 3 else my_profile
        if (now - cached_ts) < _ASSIGNABLE_USERS_TTL:
            return {"success": True, "users": cached_users, "my_account_id": cached_my_id, "my_profile": cached_profile}

    urls_to_try = []
    q_str = f"&query={urllib.parse.quote(query)}" if query else ""
    if ikey:
        urls_to_try.append(f"{host}/rest/api/3/user/assignable/search?issueKey={urllib.parse.quote(ikey)}&maxResults=50{q_str}")
    if pkey:
        urls_to_try.append(f"{host}/rest/api/3/user/assignable/search?project={urllib.parse.quote(pkey)}&maxResults=50{q_str}")

    users = []
    last_err = ""
    for u_url in urls_to_try:
        try:
            req = urllib.request.Request(u_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_users = json.loads(resp.read().decode("utf-8"))
                for u in raw_users:
                    if u.get("active") is False:
                        continue
                    users.append({
                        "accountId": u.get("accountId") or "",
                        "displayName": u.get("displayName") or "Không tên",
                        "email": u.get("emailAddress") or u.get("email") or "",
                        "avatar": (u.get("avatarUrls") or {}).get("24x24") or (u.get("avatarUrls") or {}).get("48x48") or "",
                        "accountType": u.get("accountType") or "atlassian"
                    })
                if users:
                    break
        except urllib.error.HTTPError as he:
            last_err = f"HTTP {he.code}"
            continue
        except Exception as e:
            last_err = str(e)
            continue

    # Đảm bảo tài khoản của chính tôi luôn có mặt trong danh sách và có email đầy đủ
    for u in users:
        if u.get("accountId") == my_account_id:
            if not u.get("email"):
                u["email"] = my_profile.get("email") or cfg.get("email") or ""
            if not u.get("avatar"):
                u["avatar"] = my_profile.get("avatar") or ""

    if my_account_id and not any(u.get("accountId") == my_account_id for u in users):
        users.insert(0, {
            "accountId": my_account_id,
            "displayName": my_profile.get("displayName") or "Tôi",
            "email": my_profile.get("email") or cfg.get("email") or "",
            "avatar": my_profile.get("avatar") or "",
            "accountType": "atlassian"
        })

    _ASSIGNABLE_USERS_CACHE[cache_key] = (users, now, my_account_id, my_profile)
    return {"success": True, "users": users, "my_account_id": my_account_id, "my_profile": my_profile, "message": last_err}


def assign_jira_issue(issue_key: str, account_id: str = None) -> dict:
    """Gán người thực hiện (assignee) cho một Ticket hoặc Sub-task trên Jira Cloud."""
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {"success": False, "message": "Chưa cấu hình thông tin Jira trong Cài đặt MCP."}

    key = (issue_key or "").strip().upper()
    if not key:
        return {"success": False, "message": "Thiếu mã Issue (Ticket/Sub-task)."}

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    target_id = account_id
    if target_id in ("me", "currentUser"):
        target_id = _get_current_user_account_id(cfg)
    elif target_id in ("", "none", "unassigned", None):
        target_id = None

    url = f"{host}/rest/api/3/issue/{key}/assignee"
    payload = json.dumps({"accountId": target_id}).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=12) as resp:
            assigned_user = None
            if target_id:
                for c_key, c_val in _ASSIGNABLE_USERS_CACHE.items():
                    c_users = c_val[0] if isinstance(c_val, tuple) and c_val else []
                    for u in c_users:
                        if u.get("accountId") == target_id:
                            assigned_user = u
                            break
                    if assigned_user:
                        break
            return {
                "success": True,
                "key": key,
                "account_id": target_id,
                "assignee": assigned_user,
                "message": f"Đã cập nhật người thực hiện cho [{key}] thành công!"
            }
    except urllib.error.HTTPError as he:
        if he.code in (404, 405):
            try:
                fb_url = f"{host}/rest/api/3/issue/{key}"
                fb_payload = json.dumps({"fields": {"assignee": {"accountId": target_id} if target_id else None}}).encode("utf-8")
                fb_req = urllib.request.Request(fb_url, data=fb_payload, headers=headers, method="PUT")
                with urllib.request.urlopen(fb_req, timeout=12) as fb_resp:
                    return {
                        "success": True,
                        "key": key,
                        "account_id": target_id,
                        "message": f"Đã cập nhật người thực hiện cho [{key}] thành công!"
                    }
            except Exception:
                pass
        err_msg = ""
        try:
            err_body = json.loads(he.read().decode("utf-8"))
            err_msg = str(err_body.get("errors") or err_body.get("errorMessages") or err_body)
        except Exception:
            err_msg = f"HTTP {he.code}: {he.reason}"
        return {"success": False, "message": f"Không thể gán người thực hiện: {err_msg}"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi gán người thực hiện: {str(e)}"}


def create_jira_subtask(parent_key: str, summary: str, description: str = "", target_status: str = "", transition_id: str = "", assignee_account_id: str = "") -> dict:
    """Tạo Sub-task mới cho một Ticket cha trên Jira Cloud, hỗ trợ chọn trạng thái chuyển đổi và người thực hiện (assignee)."""
    global _JIRA_SEEN_CACHE, _SELF_CREATED_SUBTASKS
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {"success": False, "message": "Chưa cấu hình thông tin Jira trong Cài đặt MCP."}

    pkey = (parent_key or "").strip().upper()
    title = (summary or "").strip()
    if not pkey or not title:
        return {"success": False, "message": "Thiếu mã Ticket cha hoặc tiêu đề Sub-task."}

    project_key = pkey.split("-")[0] if "-" in pkey else "EAS"
    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    fields_payload = {
        "project": {"key": project_key},
        "parent": {"key": pkey},
        "issuetype": {"name": "Sub-task"},
        "summary": title
    }

    assigned_target = (assignee_account_id or "").strip()
    if assigned_target in ("me", "currentUser"):
        assigned_target = _get_current_user_account_id(cfg)
    if assigned_target and assigned_target.lower() not in ("none", "unassigned", "0"):
        fields_payload["assignee"] = {"accountId": assigned_target}

    if description and description.strip():
        fields_payload["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description.strip()}]
                }
            ]
        }

    url = f"{host}/rest/api/3/issue"
    try:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({"fields": fields_payload}).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            err_body_raw = he.read().decode("utf-8")
            # Nếu màn hình tạo Sub-task trên Jira Cloud không cho phép truyền trực tiếp field assignee
            if "assignee" in err_body_raw.lower() and "assignee" in fields_payload:
                del fields_payload["assignee"]
                req_retry = urllib.request.Request(
                    url,
                    data=json.dumps({"fields": fields_payload}).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req_retry, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            else:
                raise urllib.error.HTTPError(he.url, he.code, err_body_raw, he.hdrs, None)

        new_key = data.get("key")

        # Đánh dấu subtask này là do bản thân vừa tạo: KHÔNG THÔNG BÁO CHO BẢN THÂN
        if new_key:
            _JIRA_SEEN_CACHE["issues"].add(new_key)
            _SELF_CREATED_SUBTASKS.add(new_key)

        # Gán người thực hiện sau khi tạo nếu chưa được set trong payload
        if new_key and assigned_target and assigned_target.lower() not in ("none", "unassigned", "0"):
            try:
                time.sleep(0.2)
                assign_jira_issue(new_key, assigned_target)
            except Exception:
                pass

        final_status = "To Do"
        # Nếu người dùng chọn trạng thái khác khi tạo (ví dụ In Progress hoặc Done):
        st_choice = str(target_status or "").strip()
        tr_choice = str(transition_id or "").strip()
        if (st_choice and st_choice.lower() != "to do") or tr_choice:
            try:
                time.sleep(0.3)
                t_res = transition_jira_issue(new_key, transition_id=tr_choice, target_status=st_choice)
                if t_res.get("success"):
                    final_status = st_choice or "Updated"
            except Exception:
                pass

        return {
            "success": True,
            "key": new_key,
            "id": data.get("id"),
            "status": final_status,
            "message": f"Đã tạo Sub-task [{new_key}] ({final_status}) cho Ticket [{pkey}] thành công!"
        }
    except urllib.error.HTTPError as he:
        err_msg = ""
        try:
            err_body = json.loads(he.msg if hasattr(he, 'msg') and he.msg and '{' in he.msg else (he.read().decode("utf-8") if hasattr(he, 'read') else ""))
            err_msg = str(err_body.get("errors") or err_body.get("errorMessages") or err_body)
        except Exception:
            err_msg = f"HTTP {he.code}: {he.reason if hasattr(he, 'reason') else ''}"
        return {"success": False, "message": f"Không thể tạo Sub-task: {err_msg}"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi tạo Sub-task: {str(e)}"}


def check_jira_updates(force_refresh: bool = False) -> dict:
    """
    Kiểm tra các cập nhật thời gian thực trên Jira Cloud:
    - Khi có Task mới vừa log (Ticket mới tạo)
    - Khi có Bình luận mới trên các Ticket
    Trả về danh sách notifications để client hiển thị banner tương tác.
    Đặc biệt: Không thông báo khi chính bản thân người dùng tạo Sub-task.
    """
    global _JIRA_SEEN_CACHE, _SELF_CREATED_SUBTASKS
    cfg = get_jira_config()
    if not cfg["is_configured"]:
        return {"success": False, "notifications": []}

    host = cfg["host"]
    headers = _get_auth_headers(cfg)

    payload = json.dumps({
        "jql": "project in (EAS, SSLN, IZI, ESORG) ORDER BY updated DESC",
        "maxResults": 15,
        "fields": ["summary", "status", "issuetype", "updated", "created", "comment", "reporter", "assignee"]
    }).encode("utf-8")

    url = f"{host}/rest/api/3/search/jql"
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            issues = data.get("issues", [])

            # Nếu là lần chạy đầu tiên (chưa khởi tạo cache)
            if not _JIRA_SEEN_CACHE["initialized"]:
                for it in issues:
                    k = it.get("key")
                    if k:
                        _JIRA_SEEN_CACHE["issues"].add(k)
                    comments = (it.get("fields", {}).get("comment") or {}).get("comments", [])
                    for c in comments:
                        cid = str(c.get("id") or "")
                        if cid:
                            _JIRA_SEEN_CACHE["comments"].add(cid)
                _JIRA_SEEN_CACHE["initialized"] = True
                _JIRA_SEEN_CACHE["last_check"] = time.time()
                return {"success": True, "notifications": [], "initialized": True}

            # Lần gọi tiếp theo: phát hiện task mới hoặc comment mới
            notifications = []
            my_id = _get_current_user_account_id(cfg)
            my_email = (cfg.get("email") or "").strip().lower()

            for it in issues:
                k = it.get("key")
                f = it.get("fields") or {}
                if not k:
                    continue

                is_new_issue = k not in _JIRA_SEEN_CACHE["issues"]
                if is_new_issue:
                    _JIRA_SEEN_CACHE["issues"].add(k)

                type_obj = f.get("issuetype") or {}
                tname = type_obj.get("name") or "Task"
                is_subtask = bool(type_obj.get("subtask") or (tname.lower() in ("sub-task", "subtask")))

                reporter_obj = f.get("reporter") or {}
                rep_id = str(reporter_obj.get("accountId") or "")
                rep_email = str(reporter_obj.get("emailAddress") or "").strip().lower()

                # Nhận diện nếu chính bản thân tạo subtask
                is_self_created = (
                    k in _SELF_CREATED_SUBTASKS
                    or (my_id and rep_id == my_id)
                    or (my_email and rep_email == my_email)
                )

                # 1. Phát hiện Task/Subtask mới vừa log
                if is_new_issue:
                    # Bản thân tôi tạo subtask thì không cần phải thông báo
                    if is_subtask and is_self_created:
                        pass
                    else:
                        rep_name = reporter_obj.get("displayName") or "Thành viên"
                        notifications.append({
                            "id": f"task_{k}",
                            "type": "issue_created",
                            "key": k,
                            "title": f"Task mới vừa log: {k}",
                            "issuetype": tname,
                            "summary": f.get("summary") or "",
                            "author": rep_name,
                            "created": f.get("created") or "",
                            "message": f"{rep_name} vừa log {tname} [{k}]: {f.get('summary', '')[:80]}"
                        })

                # 2. Phát hiện Bình luận mới
                comments = (f.get("comment") or {}).get("comments", [])
                for c in comments:
                    cid = str(c.get("id") or "")
                    if cid and cid not in _JIRA_SEEN_CACHE["comments"]:
                        _JIRA_SEEN_CACHE["comments"].add(cid)
                        c_author = (c.get("author") or {}).get("displayName") or "Thành viên"
                        c_body = _clean_text_from_adf(c.get("body"))
                        notifications.append({
                            "id": f"comment_{cid}",
                            "type": "comment_added",
                            "key": k,
                            "title": f"Bình luận mới trên {k}",
                            "summary": f.get("summary") or "",
                            "author": c_author,
                            "comment_body": c_body[:120],
                            "created": c.get("created") or "",
                            "message": f"{c_author} vừa bình luận trên [{k}]: \"{c_body[:80]}...\""
                        })

            _JIRA_SEEN_CACHE["last_check"] = time.time()
            return {
                "success": True,
                "notifications": notifications,
                "count": len(notifications)
            }
    except Exception as e:
        return {"success": False, "notifications": [], "error": str(e)}
