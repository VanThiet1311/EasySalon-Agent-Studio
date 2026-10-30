# EasySalon Agent Studio

Nền tảng điều khiển và phối hợp AI Agent đa tác nhân (Multi-Agent Collaboration) giữa **Frontend (React/TypeScript)** và **Backend (.NET API)** dành riêng cho dự án EasySalon.

---

## ⚙️ Cấu Hình Môi Trường (.env)

Khi chia sẻ thư mục này sang máy khác hoặc cho người khác, chỉ cần thiết lập file `.env`:

```bash
# Tạo file .env từ file mẫu
cp .env.example .env
```

Mở file `.env` và điều chỉnh lại đường dẫn tới 2 dự án trên máy mới:
```env
# Đường dẫn thư mục mã nguồn Frontend (React/TypeScript)
FE_WORKSPACE=/path/to/easysalon-webapp

# Đường dẫn thư mục mã nguồn Backend (.NET API)
BE_WORKSPACE=/path/to/easysalon-api

# Cổng khởi chạy Web UI (tùy chọn, mặc định 8765)
WEB_PORT=8765
WEB_HOST=0.0.0.0
```

---

## 🚀 1. Các Cách Sử Dụng Linh Hoạt

### ⚡ Khởi Chạy Nhanh (1 Câu Lệnh Duy Nhất)
Chỉ cần mở terminal tại thư mục này và gõ:
```bash
run
# hoặc:
./run
```
> Lệnh này sẽ tự động khởi chạy **EasySalon Web Studio** và mở cổng `8765`.
> Sau đó mở trình duyệt tại: **[http://localhost:8765](http://localhost:8765)**

---

### 🌐 Cách 1: Giao Diện Web Studio Tương Tác Trực Quan Trên Trình Duyệt (`web`)
Bạn cũng có thể chỉ định cổng tùy ý:
```bash
./run web --port 8765
# hoặc:
python3 bridge.py web --port 8765
```
Sau đó mở trình duyệt tại địa chỉ: **[http://localhost:8765](http://localhost:8765)**
* **Giao diện Web Dark Mode hiện đại**: Thiết kế chuyên biệt cho pair programming.
* **Tương tác trực quan**: Có ô nhập chủ đề/prompt tự do, gợi ý chủ đề nhanh (1-click), dropdown chọn module (`booking-bedroom`, `warehouse`, `commission`...).
* **Xem thời gian thực**: Theo dõi từng lượt phát biểu của 👨‍💻 Frontend và 🤖 Backend xuất hiện trực tiếp trước mắt kèm hiệu ứng phân tích codebase.
* **Xem lại lịch sử**: Bấm nút "Lịch sử" để tra cứu lại mọi cuộc trao đổi trước đây.

---

### ⭐ Cách 2: Tự Động Thảo Luận Đa Lượt Qua Terminal (`discuss`)
Khi bạn muốn **2 bên tự động trò chuyện, phản biện và bàn luận đa lượt** về bất kỳ chủ đề/logic nào mà bạn prompt:

```bash
# Ví dụ 1: Thảo luận logic & DTO chức năng đặt giường
python3 /run/media/thietnv/Data/Call-Fe-Be-Easysalon/bridge.py discuss \
  --prompt "Bàn luận để thiết kế API & Flow hiển thị trạng thái giường cho BedRoomPosition" \
  --rounds 4

# Ví dụ 2: Kiểm tra đối chiếu ngắn gọn
python3 /run/media/thietnv/Data/Call-Fe-Be-Easysalon/bridge.py discuss \
  -p "Đối chiếu xem Formik CustomerForm ở FE và DTO CreateCustomerDto ở BE có lệch trường nào không?" \
  --starter fe \
  --rounds 3
```

> 🎯 **Điểm nổi bật:**
> * **Hoàn toàn theo prompt của bạn**: Không áp đặt format cứng nhắc, hai bên tự đọc codebase thực tế của mình và trao đổi sâu sắc.
> * **Hiển thị trực quan thời gian thực**: Từng lượt nói của 👨‍💻 Frontend và 🤖 Backend xuất hiện trực tiếp trên terminal với màu sắc và khung thoại rõ ràng.
> * **Tự động lưu biên bản**: Toàn bộ diễn biến thảo luận được tự động lưu vào file `LATEST_DISCUSSION.md`.

---

### Cách 2: Tự Động Truy Vấn Lấy Dữ Liệu Nhanh 1 Lượt (`call`)
Khi bạn chỉ cần một bên trả lời nhanh một câu hỏi cụ thể:
* **Từ FE hỏi BE:**
  ```bash
  python3 /run/media/thietnv/Data/Call-Fe-Be-Easysalon/bridge.py call --to be --prompt "Cho tôi biết endpoint và DTO của BedRoomPositionController"
  ```
* **Từ BE hỏi FE:**
  ```bash
  python3 /run/media/thietnv/Data/Call-Fe-Be-Easysalon/bridge.py call --to fe --prompt "Kiểm tra xem CustomerTable đang dùng những field nào"
  ```

---

### Cách 3: Kích Hoạt Cửa Sổ VS Code & Mở Terminal Tương Tác
Khi bạn muốn **bật cửa sổ Terminal thật sự** để chat trực tiếp:
* **Mở Terminal Backend:**
  ```bash
  python3 /run/media/thietnv/Data/Call-Fe-Be-Easysalon/bridge.py open-terminal --target be
  ```
* **Mở Terminal Frontend:**
  ```bash
  python3 /run/media/thietnv/Data/Call-Fe-Be-Easysalon/bridge.py open-terminal --target fe
  ```

---

## 💬 2. Xem Lại Lịch Sử & Quản Lý

* **Xem lại cuộc hội thoại / thảo luận gần nhất**:
  ```bash
  python3 /run/media/thietnv/Data/Call-Fe-Be-Easysalon/bridge.py show
  ```
* **Xem toàn văn biên bản thảo luận Markdown**:
  ```bash
  cat /run/media/thietnv/Data/Call-Fe-Be-Easysalon/LATEST_DISCUSSION.md
  ```

---

## 🤖 3. Điều Khiển Qua Telegram Bot (@easysalon_bot)

Hệ thống tích hợp sẵn dịch vụ Bot Telegram để bạn có thể kiểm tra và điều khiển từ điện thoại:

* **Tên Bot:** `@easysalon_bot`
* **Các tính năng nổi bật trên Bot:**
  * `🔄 Kiểm tra Staging / Master`: Tự động kiểm tra remote `origin` xem có bao nhiêu commit mới cần pull trên Frontend & Backend kèm danh sách commit cụ thể.
  * `⬇️ Pull Git một chạm`: Bấm nút Inline Keyboard để pull Staging / Master ngay lập tức.
  * `📊 Git Status`: Xem nhánh hiện tại, commit, số file sửa đổi dở dang (`dirty_count`).
  * `⚡ Giao việc từ xa`: Gõ `/task fe <nội dung>` hoặc `/fixbug be <mô tả lỗi>`.
  * `📋 Quản lý hàng đợi & nhật ký`: `/queue`, `/logs`, `/stop`.
