# ANTIGRAVITY & AI AGENT INSTRUCTIONS FOR EASYSALON-TOOL

> **QUAN TRỌNG**: Đọc kỹ các quy tắc dưới đây trước khi sửa đổi bất kỳ đoạn code nào trong dự án này.

## 1. UI SETTINGS - MÀU NỀN ACTIVE VÀ PHONG CÁCH
- **Màu nền khi Active**: Khi các tab trong Settings (Sidebar tab, Model family tab, Effort card, Engine card) ở trạng thái active (`.is-active`), background **LUÔN LUÔN là màu xanh dương (#1677ff)** (`linear-gradient(135deg, #1677ff 0%, #0958d9 100%)`). Text luôn màu trắng (`#ffffff`). Tuyệt đối không dùng màu cyan đậm (`bg-cyan-950`) hay màu tối cho trạng thái active.
- **Hạn chế icon / emoji**: Loại bỏ các emoji rườm rà (`🧠`, `🚀`, `⚡`, `⚖️`, `🟣`, `🟢`, `💡`, `⚙️`) trên tiêu đề, thẻ chọn và nhãn. Giữ giao diện tối giản, thanh lịch, chuẩn Ant Design / modern SaaS.
- **Font chữ theo hệ thống đồng bộ**:
  - Dùng font hệ thống `'Be Vietnam Pro', Inter, system-ui, -apple-system, sans-serif` (`font-sans`) cho mọi văn bản thông thường, nhãn, badge (ví dụ: *"Hỗ trợ 3 mức: Low, Medium, High"*, *"3 mức"*, *"Tốc độ cao"*, *"Khuyên dùng"*).
  - Không bao giờ áp dụng `font-mono` cho chữ thông thường hay chữ tiếng Việt. Chỉ dùng `font-mono` cho code, file path, commit hash, terminal log và command.

## 2. GIT CONFLICT & ROLLBACK
- Tất cả các hộp conflict Git (Pull, Cherry-pick, Merge) phải có nút:
  `Trở lại trạng thái chưa merge hay cherry-pick` (kích hoạt `doAbortConflictAction(role)` -> `git merge --abort` / `git cherry-pick --abort`).
- Hiển thị terminal giả lập VS Code giải quyết xung đột với CodeLens (`Accept Current Change`, `Accept Incoming Change`, `Accept Both Changes`).

## 3. QUY TẮC KIỂM THỬ (TESTING RULES)
- **ĐƯỢC PHÉP CHẠY TEST (NGOẠI TRỪ DATABASE & JIRA)**: Được phép chạy kiểm thử khi cần thiết, nhưng **TUYỆT ĐỐI NÉ / KHÔNG CHẠY các bài test liên quan đến Database và Jira** (như `test_mysql*`, `test_database*`, `test_jira*`, các test mutate dữ liệu DB hoặc gọi đến Jira).
- **Bảo toàn tính toàn vẹn của code & kiểm thử**:
  - Hàm `switchDiagramViewTab(tab)` trong `frontend/app.js` phải giữ đúng regex matching kết thúc bằng `\n    }` (4 spaces) và gọi `renderTreeView(window.diagramData.tree_nodes)`.
  - Luôn giữ các escape an toàn như `escapeHtml(m.title)`, `escapeHtml(m.skill)`, `escapeHtml(m.name)`.
