# Planly: cách video được xếp lên lịch

Đây là phần dễ sai nhất và cũng là phần bạn đã bị đốt trước đây. Đọc hết trước lượt
chạy thật đầu tiên.

Toàn bộ phần này nằm trong `hub/planly.py` và `hub/publish.py`.

---

## Một lượt đăng gồm 5 việc

1. **Gom video.** Đọc mọi thư mục `output/*/meta.json` của nhà máy vừa chạy. Thư mục
   nào đã đăng rồi thì bỏ qua (ghi trong `state.json`).
2. **Upload.** Mỗi video upload lên Planly **đúng một lần**, dù nó sẽ được đăng ở
   bao nhiêu kênh. Ba bước: xin chỗ (`media/start-upload`) → đẩy file thẳng lên S3 →
   báo xong (`media/finish-upload`). Planly đọc độ phân giải ở bước cuối.
3. **Tính khung giờ.** Từ `times`, `mode`, `timezone_offset`, `lead_minutes`, và
   danh sách khung đã dùng trong `state.json`.
4. **Chia video cho kênh.** Theo `distribute`.
5. **Tạo lịch.** Một lệnh `schedule-groups/create` duy nhất. Các cặp (kênh, video)
   được gộp thành nhóm theo **giờ đăng + video**, không phải chỉ theo giờ — xem
   mục "Vì sao gộp theo nhóm" bên dưới.
   Có `dry_run` thì dừng ngay trước bước này.

---

## `same_time` và `spread`

Giả sử `times = ["09:00", "12:00", "15:00", "18:00", "21:00", "23:00"]`,
`gap_minutes = 120`, và lượt chạy bắt đầu lúc 08:00 sáng.

| mode | Kết quả | Dùng khi |
|---|---|---|
| `same_time` | 09:00, 12:00, 15:00, 18:00, 21:00, 23:00 | Bạn muốn **cả 8 kênh đăng cùng một phút** — đúng cách bạn đang xếp tay. Đây là mặc định. |
| `spread` | 09:00, 11:00, 13:00, 15:00, 17:00, 19:00 | Chỉ lấy **mốc đầu tiên** trong `times` làm điểm xuất phát rồi cộng dồn `gap_minutes`. Các mốc còn lại bị bỏ qua. |

`same_time` **không** làm các kênh lệch nhau. Mọi kênh được tính từ cùng một danh
sách khung giờ, nên bài thứ nhất của cả 8 kênh rơi vào đúng 09:00, bài thứ hai rơi
vào đúng 12:00.

Vài chi tiết của `same_time`:

- Cần nhiều khung hơn số mốc trong ngày thì nó **tràn sang ngày hôm sau**. Ví dụ cần
  8 khung: 6 mốc hôm nay, rồi 09:00 và 12:00 ngày mai.
- Mốc nào đã trôi qua, hoặc gần hơn `lead_minutes` phút so với bây giờ, thì bị bỏ.
  Chạy lúc 20:45 với `lead_minutes = 30` thì mốc 21:00 bị bỏ (chỉ còn 15 phút), khung
  đầu tiên là 23:00.
- Thứ tự bạn viết trong `times` không quan trọng, chương trình tự sắp lại.
- `times` là **giờ nơi bạn ở**. `timezone_offset: 7` nghĩa là UTC+7. Chương trình
  quy đổi sang UTC lúc gửi lên Planly, nên lịch Planly hiện đúng giờ bạn nghĩ.

---

## `unique` và `mirror`

### `unique` — mặc định, và là cái bạn muốn

Video được chia bài như chia bài tây: video thứ 1 cho kênh 1, video thứ 2 cho kênh 2,
… đến kênh cuối thì quay lại kênh 1.

**Ví dụ đầy đủ: 8 kênh, 48 video trong một lượt.**

Mỗi kênh nhận 6 video, không kênh nào trùng clip với kênh nào:

| Khung giờ | Kênh 1 | Kênh 2 | Kênh 3 | … | Kênh 8 |
|---|---|---|---|---|---|
| 09:00 | video 1 | video 2 | video 3 | … | video 8 |
| 12:00 | video 9 | video 10 | video 11 | … | video 16 |
| 15:00 | video 17 | video 18 | video 19 | … | video 24 |
| 18:00 | video 25 | video 26 | video 27 | … | video 32 |
| 21:00 | video 33 | video 34 | video 35 | … | video 40 |
| 23:00 | video 41 | video 42 | video 43 | … | video 48 |

48 bài, 48 clip khác nhau, 6 khung giờ, cả 8 kênh đăng cùng phút. Đúng như bạn xếp tay.

**Số video không chia hết cho số kênh** thì mấy kênh đầu nhận nhiều hơn một cái.
10 video cho 8 kênh: kênh 1 và 2 được 2 video (09:00 và 12:00), 6 kênh còn lại được
1 video (chỉ 09:00).

**Số video ít hơn số kênh** thì có kênh không được gì, và log nói thẳng:

```
warning: 6 video(s) for 8 channel(s) - nothing left for: K7 (tiktok), K8 (tiktok)
```

### `mirror` — mọi kênh đăng cùng một clip

6 video, 8 kênh, `mirror` → mỗi kênh nhận cả 6 video. Vẫn ra 48 bài, nhưng chỉ có 6
clip khác nhau, và 09:00 là cả 8 kênh cùng đăng **y hệt một video**.

Chỉ dùng khi 8 kênh của bạn ở 8 nền tảng khác nhau và bạn cố ý muốn cùng nội dung
lên khắp nơi. Nếu 8 kênh cùng nền tảng thì đây là cách nhanh nhất để bị gắn cờ
spam. Mặc định là `unique` vì lý do đó.

### Phép tính cần nhìn thẳng

`unique` + 48 bài/ngày = **cần 48 video mới mỗi ngày**. Mặc định hiện tại là
`run.us.count = 3` và `run.mx.count = 3`, tức 6 video một lượt — chỉ đủ cho 6 kênh,
mỗi kênh 1 bài.

Muốn đủ 48 thì hoặc tăng `count`, hoặc cho workflow chạy nhiều lượt trong ngày. Mỗi
video tốn khoảng 90–150 giây render, nên 48 video là 75–120 phút máy chạy mỗi ngày,
tức 2200–3600 phút/tháng. Repo private chỉ có 2000 phút miễn phí/tháng. Repo public
không giới hạn phút. Cân nhắc con số này trước khi tăng `count`.

---

## Hai nhà máy, hai danh sách kênh

Phần đăng chạy **riêng cho từng nhà máy**. Mặc định cả hai dùng chung một danh
sách kênh, nghĩa là video tiếng Anh và video tiếng Tây Ban Nha rải lên cùng một
rổ acc.

Muốn tách ra thì đặt **route** — xem mục "Luồng video nào đăng lên acc nào" ngay
dưới. Đặt xong thì US chỉ đăng lên kênh tiếng Anh, MX chỉ đăng lên kênh tiếng
Tây Ban Nha, và không cần chạy hai lượt tay nữa.

Hai luồng không đè giờ của nhau: khung giờ được giữ chỗ **theo từng kênh**, nên
kênh US đăng 09:00 và kênh MX cũng đăng 09:00 là chuyện bình thường.

---

## Luồng video nào đăng lên acc nào

Mặc định mọi video đổ chung một rổ rồi chia lần lượt cho tất cả các kênh. Nghĩa
là một video tiếng Tây Ban Nha có thể rơi vào một kênh tiếng Anh, chỉ vì đến
lượt kênh đó.

**Route** là để chỉ định: luồng nào đăng lên những acc nào.

### Làm trong app

Tab **Đăng bài** → khung **Kênh Planly** → ô chọn **Luồng video**.

1. Chọn một luồng, ví dụ `Xưởng US (tiếng Anh)`.
2. Tích những kênh mà luồng đó được phép đăng lên.
3. Đổi sang luồng khác, tích tiếp.
4. Bấm **Lưu**.

Luồng nào không tích riêng thì dùng danh sách **Chung**.

### Thứ tự ưu tiên

Tìm từ hẹp đến rộng, dừng ở cái đầu tiên có kênh:

| Thứ tự | Khóa | Nghĩa |
|---|---|---|
| 1 | `us:humor` | Riêng niche hài của xưởng US |
| 2 | `us` | Cả xưởng US |
| 3 | `channels` | Danh sách Chung |

Nên có thể để cả xưởng US đăng lên 8 kênh, riêng niche hài tách ra 2 kênh khác.

### Trong file

Nếu muốn sửa tay, nó nằm ở `settings.public.json`:

```json
"publish": {
  "channels": ["all"],
  "routes": {
    "us": ["id-kenh-1", "id-kenh-2"],
    "mx": ["id-kenh-3", "id-kenh-4"],
    "us:humor": ["id-kenh-5"]
  }
}
```

Lấy id kênh bằng nút **Tải danh sách kênh** trong app — nó in ra tên kèm id.

File này **có** đẩy lên GitHub, nên các lần chạy trên mây dùng đúng route anh
vừa đặt. Nhớ commit và push sau khi đổi.

### Mỗi luồng giữ lượt riêng

Vòng xoay chia acc được nhớ **theo từng route**. Xưởng US đăng một lượt thì chỉ
con trỏ của route `us` nhích lên; route `mx` vẫn đứng nguyên chỗ của nó. Hai
luồng không đẩy nhau đi.

### Đặt sai thì sao

| Tình huống | Hệ thống làm gì |
|---|---|
| Route ghi id kênh không còn tồn tại | Cảnh báo nêu đúng id đó, vẫn đăng lên các kênh còn lại |
| Route mà **mọi** kênh đều không còn | Báo lỗi, không đăng gì cho luồng đó, các luồng khác vẫn chạy |
| Route để trống | Coi như chưa đặt, dùng danh sách Chung |

---

## Vì sao video phải dưới 60 giây

Giao diện lịch của Planly **không hiển thị** bài có video dài hơn 60 giây. Bài vẫn
được tạo, vẫn đăng đúng giờ — nhưng bạn mở lịch ra không thấy nó, và tưởng là hỏng.

Chương trình kiểm tra `duration_seconds` trong `meta.json` và cảnh báo:

```
warning: Ten video: 72s is longer than 60s - Planly will not show it on the calendar.
```

Nó **chỉ cảnh báo, không bao giờ chặn**. `max_seconds` là một tham số, bạn có quyền
nâng lên nếu cố ý.

Cách giữ video ngắn: `"target_seconds"` trong `factories/us/config.json` và
`factories/mx/config.json`, mặc định `45`. Kịch bản đôi khi dài quá tay và đẩy video
lên 60–70 giây; hạ xuống `40` là an toàn. Hoặc chạy một lượt với `--seconds 40`.

---

## `dry_run` làm gì và **không** làm gì

| Việc | `dry_run: true` | `dry_run: false` |
|---|---|---|
| Render video | có | có |
| Lấy danh sách kênh từ Planly | có | có |
| **Upload file lên thư viện media của Planly** | **có** | có |
| Tính khung giờ, chia video cho kênh | có | có |
| In bảng "video nào, kênh nào, giờ nào" | có | có |
| Tạo lịch đăng trên Planly | **không** | có |
| Ghi nhớ khung giờ đã dùng vào `state.json` | **không** | có |
| Đánh dấu video là đã đăng | **không** | có |

Hai hệ quả cần nhớ:

- **Dry run vẫn upload thật.** Chạy dry run năm lần là năm bản sao của cùng một
  video nằm trong thư viện media của Planly. Không hại gì, nhưng bừa — thỉnh thoảng
  vào dọn.
- **Dry run không ghi nhớ gì.** Chạy dry run rồi chạy tiếp lượt thật thì lượt thật
  tính lại từ đầu và cho ra đúng những khung giờ đó. Đó là điều bạn muốn: cái bạn
  xem trước chính là cái sẽ xảy ra.

Tắt hẳn phần đăng thì dùng `publish.enabled = false`. Lúc đó chương trình không gọi
lên Planly một lần nào, log chỉ ghi `Publishing is off (publish.enabled = false).`

---

## Khung giờ được nhớ giữa các lượt như thế nào

Sau mỗi lượt **thật**, các khung giờ vừa dùng được ghi vào `state.json`:

```json
{
  "planly_taken": {
    "id-cua-kenh-1": ["2026-08-29T02:00:00.000Z", "2026-08-29T05:00:00.000Z"]
  },
  "published": ["20260829-081500_ten-chu-de"]
}
```

- Lượt sau đọc **toàn bộ** khung đã đặt của **mọi kênh** gộp lại, và tránh hết. Nhờ
  vậy lượt thứ hai trong ngày không chồng lên lượt thứ nhất — nếu lượt 1 đã dùng cả
  6 mốc hôm nay thì lượt 2 nhảy sang 09:00 ngày mai.
- Đầu mỗi lượt, khung giờ đã trôi qua bị xoá khỏi danh sách. Chúng không thể va vào
  ai nữa, giữ lại chỉ làm file phình.
- Mỗi kênh giữ tối đa 600 khung (khoảng 3 tháng ở nhịp 6 bài/ngày).
- `published` là danh sách thư mục video đã giao cho Planly. Chạy lại lượt cũ không
  làm video bị đăng hai lần.

**Trên GitHub Actions**, `state.json` được `actions/cache` giữ giữa các lần chạy. Nếu
cache bị mất (GitHub dọn cache không dùng sau 7 ngày, hoặc bạn xoá tay), chương trình
mất trí nhớ: nó có thể xếp bài vào một khung giờ đã có bài, và có thể đăng lại video
cũ. Không hỏng gì, nhưng lịch sẽ trông lạ. Cách kiểm tra duy nhất là mở lịch Planly
nhìn.

---

## Xoá một bài đã xếp

**Cách thường:** mở Planly, vào lịch, bấm vào bài đó, xoá. Không có gì đặc biệt.

**Cách hàng loạt**, khi lỡ tạo nhầm mấy chục bài. Mở PowerShell tại thư mục cài đặt
và chạy Python:

```python
from hub import planly
from hub.settings import secret

key = secret("PLANLY_API_KEY")
team = planly.resolve_team(key)

for s in planly.list_schedules(key, team):
    print(s)                       # xem cấu trúc, lấy đúng tên trường id
```

Nhìn kết quả, chọn ra id của bài cần xoá, rồi:

```python
planly.delete_schedule(key, "id-cua-bai-can-xoa")
```

`list_schedules` nhận thêm `start` và `end` dạng `YYYY-MM-DD` nếu bạn muốn lọc theo
ngày. Đọc kỹ trước khi xoá — không có bước hoàn tác.

**Xoá bài trên Planly không trả lại khung giờ.** `state.json` vẫn coi khung đó đã
dùng, nên lượt sau vẫn tránh nó. Muốn dùng lại khung đó thì mở `state.json` (ở
`%APPDATA%\AutomationHub` trên máy, ở thư mục gốc repo khi chạy trên Actions) và xoá
dòng giờ tương ứng trong `planly_taken`. Xoá cả file cũng được — mất trí nhớ thì
chương trình chỉ tính lại từ đầu, không hỏng gì.

---

## Bảng tham số `publish`

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `enabled` | `false` | Công tắc tổng. `false` thì không gọi Planly lần nào |
| `dry_run` | `true` | Làm hết trừ bước tạo lịch |
| `team_id` | `""` | **Bắt buộc.** API Planly không có lệnh liệt kê team, để trống là không chạy được. Trên GitHub thì đặt bằng secret `PLANLY_TEAM_ID` |
| `channels` | `["all"]` | `["all"]` = mọi kênh đang nối, hoặc liệt kê id cụ thể |
| `routes` | `{}` | Luồng nào đăng lên acc nào. Khóa là `us`, `mx`, hoặc `us:humor`. Trống là mọi luồng dùng `channels` |
| `mode` | `"same_time"` | `same_time` hoặc `spread` |
| `times` | 6 mốc | Giờ địa phương của bạn |
| `gap_minutes` | `120` | Chỉ có tác dụng ở `spread` |
| `timezone_offset` | `7` | `7` = UTC+7, giờ Việt Nam |
| `lead_minutes` | `30` | Không xếp bài vào khung gần hơn ngần này phút |
| `distribute` | `"unique"` | `unique` hoặc `mirror` |
| `max_seconds` | `60` | Ngưỡng cảnh báo độ dài |
| `channel_options` | `{}` | Tham số riêng cho từng kênh hoặc từng nền tảng |

**`channel_options`** nhận khoá là id kênh, hoặc là tên nền tảng (`"youtube"`,
`"tiktok"`, …). Riêng kênh YouTube luôn được tự điền tiêu đề lấy từ `meta.json` —
YouTube từ chối bài không có tiêu đề.

**Nội dung bài đăng** lấy từ `description` trong `meta.json` (đã gồm cả hashtag),
cắt ở 2100 ký tự. Muốn đổi giới hạn thì thêm `"caption_limit"` vào khối `publish`.

---

## Danh sách soát trước lượt thật đầu tiên

- [ ] Nút Test khoá Planly báo đúng số kênh bạn có.
- [ ] `mode = same_time`, `distribute = unique`.
- [ ] `timezone_offset = 7`, và bảng xem trước hiện đúng giờ Việt Nam.
- [ ] Số video trong lượt đủ chia cho số kênh (không có cảnh báo "nothing left for").
- [ ] Không có cảnh báo quá 60 giây.
- [ ] Đã chạy một lượt `dry_run` và đọc hết bảng giờ.
</content>
