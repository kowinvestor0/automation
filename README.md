# 🚀 Auto Make Money - Hệ Thống Sản Xuất & Lên Lịch Video Hàng Loạt Đa Kênh TikTok (96+ Video/Ngày)

Hệ thống tự động hóa sản xuất video ngắn TikTok chuẩn chuẩn kiếm tiền (>60s) ở quy mô lớn: **Cung cấp đủ 6 video HOÀN TOÀN ĐỘC LẬP cho MỖI KÊNH TIKTOK MỖI NGÀY** (Ví dụ: 16 kênh = **96 video/ngày**, 32 kênh = **192 video/ngày**), hỗ trợ không giới hạn số lượng tài khoản Planly và bảo vệ kênh chống quét bot 100%.

---

## 🌟 Tính Năng Cốt Lõi

### 1. Cung Cấp 6 Video Độc Quyền Cho Từng Kênh TikTok Mỗi Ngày
- **Không trùng lặp câu chuyện**: Không còn chia góc nhìn từ 1 sự kiện. Mỗi video trong ngày là **một câu chuyện hoàn toàn khác biệt** từ các ngách nội dung triệu view: Khoa học, Vũ trụ, Công nghệ AI, Rãnh đại dương, Hóa thạch tiền sử, Siêu công trình kỷ lục.
- **Quy mô hàng loạt (Massive Bulk Scale)**:
  - 1 tài khoản (16 kênh) = **96 video độc quyền mỗi ngày**.
  - 2 tài khoản (32 kênh) = **192 video độc quyền mỗi ngày**.
  - Không giới hạn số lượng tài khoản Planly và kênh TikTok liên kết.
- **Chuẩn kiếm tiền TikTok (>60 Giây)**: Mọi video đều có thời lượng 65s - 85s (10 phân cảnh đối thoại hấp dẫn) để tối ưu quỹ tiền thưởng Creator Rewards Program.

### 2. Khai Thác 700+ Chủ Đề Viral An Toàn Không Lo Bản Quyền
- Tự động quét và phân loại hơn **700 bài viết và khám phá nóng nhất mỗi ngày** từ 10+ ngách nội dung hàng đầu thế giới (NASA, Phys.org, The Verge, Nature Geoscience, Ocean Exploration...).
- **Chống quét chính sách (Strict Blacklist Filter)**: Loại bỏ 100% từ khóa nhạy cảm về chính trị Mỹ, bầu cử, tranh cãi pháp lý để video luôn an toàn tuyệt đối trước bộ lọc kiểm duyệt của TikTok.

### 3. Dựng Phim Chuyển Cảnh Đa Phân Cảnh (Dynamic Scene Montage)
- **Đổi cảnh liên tục mỗi 4 - 8 giây**: Mỗi video 60s - 80s được cắt ghép từ **8 đến 10 clip B-roll dọc 9:16 riêng biệt** bám sát từng câu thoại.
- **Bộ nhớ chống trùng hình ảnh (Zero-Duplicate Tracker)**: Ghi nhớ hơn 400 clip B-roll gần nhất. Khi tạo 96 video trong ngày, hệ thống sử dụng hàng trăm clip độc quyền, không video nào dùng trùng hình ảnh của video nào.
- **Phụ đề Karaoke chữ nổi 3D**: Highlight từng chữ theo nhịp nói của MC AI (Phong cách MrBeast / Alex Hormozi), luân phiên 8 giọng đọc nam/nữ tự nhiên.

### 4. Lịch Đăng Giờ Vàng Chống Bot TikTok (Anti-Bot Safe Peak Scheduling)
- **Phân bổ 6 khung giờ vàng xem video tại Mỹ**: `09:00`, `11:45`, `14:30`, `17:15`, `19:45`, `22:15`.
- **Độ lệch phút ngẫu nhiên (+2 đến +14 phút)**: Mỗi kênh và mỗi bài đăng có mốc thời gian riêng biệt (ví dụ: `10:15`, `10:17`, `10:20`, `10:23`...). **Tuyệt đối không đăng cùng 1 giây**, loại bỏ 100% nguy cơ bị TikTok quét phát hiện bot mạng lưới.
- **Chú thích tương tác tự nhiên**: Luân phiên 6 mẫu câu hỏi tương tác, loại bỏ hoàn toàn các mẫu tiêu đề rập khuôn gây nghi ngờ.

---

## 🛠️ Cài Đặt & Khởi Chạy

### Cách 1: Cài Đặt 1-Click (Dành Cho Mọi Máy Tính Windows)
Chạy file cài đặt [AutoMakeMoney_Setup_1.0.0.exe](AutoMakeMoney_Setup_1.0.0.exe) để tự động cài đặt ứng dụng vào máy tính, có icon ngoài màn hình Desktop.

### Cách 2: Chạy Tự Động Xếp Lịch Kịp Giờ (Headless Runner)
Nhấp đúp file **`run_schedule_now.bat`** để hệ thống tự động:
1. Đếm tổng số kênh trên tất cả tài khoản Planly (Ví dụ: 15 kênh x 6 = 90 video).
2. Kiểm tra kho video và tự động bổ sung đủ số lượng video độc quyền còn thiếu.
3. Tự động đẩy lên Planly và phân bổ đều vào các khung giờ vàng chống bot.

```bash
# Chạy mô phỏng kiểm tra lịch (Dry-Run):
python run_headless.py --dry-run

# Tự động tạo 96 video độc quyền và xếp lịch cho toàn bộ các kênh:
python run_headless.py --generate-batch 96
```

### Cách 3: Mở Bảng Điều Khiển Giao Diện (Desktop App)
```bash
python app.py
```
*Hệ thống tự động phát hiện và xử lý cổng mạng (Port 8888), ngăn ngừa hoàn toàn hiện tượng xung đột cổng `[Errno 10048]`.*

---

## 🔒 Quản Lý Đa Tài Khoản & Bảo Mật
- Thêm hoặc xóa tài khoản Planly linh hoạt thông qua giao diện hoặc file cấu hình `data/accounts.json`.
- Mọi token, mã xác thực và dữ liệu kênh đều được lưu trữ an toàn trên máy cục bộ, không bao giờ đồng bộ công khai lên GitHub.
