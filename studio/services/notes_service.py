"""Quản lý ghi chú (Notes) của hệ thống Easysalon-Tool, lưu trữ tại storage/notes.json."""

import json
import os
import threading
import time
import uuid
from datetime import datetime
from studio.state import STORAGE_DIR

_NOTES_FILE = os.path.join(STORAGE_DIR, "notes.json")
_notes_lock = threading.RLock()


def _get_default_notes() -> list:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [
        {
            "id": "note-welcome",
            "title": "Ghi chú công việc & Lưu ý kỹ thuật",
            "content": (
                "# Sổ tay ghi chú dự án EasySalon\n\n"
                "- Ghi chú được **tự động lưu** và đồng bộ an toàn.\n"
                "- Nhấn nút **Đưa vào Tác vụ** ở góc phải để đưa nhanh nội dung ghi chú sang Prompt của Agent.\n"
                "- Hỗ trợ liên kết trực tiếp với mã Ticket Jira để quản lý tài liệu theo từng tính năng.\n\n"
                "### Checklist gợi ý khi phát triển:\n"
                "- [ ] Kiểm tra branch Git hiện tại và pull mã nguồn mới nhất\n"
                "- [ ] Kiểm tra video minh chứng lỗi từ Ticket Jira (định dạng mp4/webm)\n"
                "- [ ] Thực thi kiểm thử 78 test cases: `python3 -m unittest discover -s tests`\n"
                "- [ ] Đẩy commit với thông điệp rõ ràng theo chuẩn Conventional Commits"
            ),
            "category": "general",
            "jira_key": "",
            "created_at": now_str,
            "updated_at": now_str
        }
    ]


def get_all_notes() -> list:
    """Lấy toàn bộ danh sách ghi chú, sắp xếp theo thời gian cập nhật mới nhất."""
    with _notes_lock:
        if not os.path.exists(_NOTES_FILE):
            default_notes = _get_default_notes()
            try:
                os.makedirs(STORAGE_DIR, exist_ok=True)
                with open(_NOTES_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_notes, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return default_notes

        try:
            with open(_NOTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    data.sort(key=lambda n: n.get("updated_at", ""), reverse=True)
                    return data
                elif isinstance(data, dict):
                    # Chuyển đổi nếu data là dict theo key
                    notes = []
                    for k, v in data.items():
                        if isinstance(v, dict):
                            v.setdefault("id", k)
                            notes.append(v)
                        elif isinstance(v, str):
                            notes.append({
                                "id": f"note-{k}",
                                "title": f"Ghi chú {k}",
                                "content": v,
                                "category": "jira",
                                "jira_key": k,
                                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                    notes.sort(key=lambda n: n.get("updated_at", ""), reverse=True)
                    return notes
        except Exception:
            return _get_default_notes()
    return []


def save_note(note_data: dict) -> dict:
    """Tạo mới hoặc cập nhật một ghi chú."""
    if not isinstance(note_data, dict):
        return {"success": False, "message": "Dữ liệu ghi chú không hợp lệ"}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note_id = str(note_data.get("id") or "").strip()
    if not note_id:
        note_id = f"note-{int(time.time())}-{uuid.uuid4().hex[:6]}"

    title = str(note_data.get("title") or "Ghi chú không tên").strip()
    content = str(note_data.get("content") or "")
    category = str(note_data.get("category") or "general").strip()
    raw_jira = str(note_data.get("jira_key") or "").strip()
    if raw_jira.lower().startswith(("http://", "https://")):
        jira_key = raw_jira
    else:
        jira_key = raw_jira.upper()

    with _notes_lock:
        notes = get_all_notes()
        found = False
        target_note = None

        for n in notes:
            if n.get("id") == note_id:
                n["title"] = title
                n["content"] = content
                n["category"] = category
                n["jira_key"] = jira_key
                n["updated_at"] = now_str
                found = True
                target_note = n
                break

        if not found:
            target_note = {
                "id": note_id,
                "title": title,
                "content": content,
                "category": category,
                "jira_key": jira_key,
                "created_at": now_str,
                "updated_at": now_str
            }
            notes.insert(0, target_note)

        try:
            os.makedirs(STORAGE_DIR, exist_ok=True)
            with open(_NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            return {"success": True, "note": target_note}
        except Exception as e:
            return {"success": False, "message": f"Lỗi khi lưu ghi chú: {str(e)}"}


def delete_note(note_id: str) -> dict:
    """Xóa một ghi chú theo ID."""
    note_id = str(note_id or "").strip()
    if not note_id:
        return {"success": False, "message": "Thiếu mã ghi chú"}

    with _notes_lock:
        notes = get_all_notes()
        filtered = [n for n in notes if n.get("id") != note_id]
        if len(filtered) == len(notes):
            return {"success": False, "message": "Không tìm thấy ghi chú để xóa"}

        try:
            os.makedirs(STORAGE_DIR, exist_ok=True)
            with open(_NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump(filtered, f, ensure_ascii=False, indent=2)
            return {"success": True, "id": note_id}
        except Exception as e:
            return {"success": False, "message": f"Lỗi khi xóa ghi chú: {str(e)}"}
