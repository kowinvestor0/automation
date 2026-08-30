# Hướng dẫn: từ con số không đến video tự lên lịch

Đọc theo thứ tự. Bảy bước. Lần đầu mất khoảng 45 phút, sau đó bạn không phải đụng
vào máy nữa.

Vài từ sẽ gặp liên tục:

| Từ | Nghĩa |
|---|---|
| repo | Thư mục code của bạn nằm trên GitHub |
| workflow | Một việc GitHub chạy hộ bạn, khai báo trong `.github/workflows/*.yml` |
| Actions | Tab trên trang repo, nơi xem các lần chạy |
| secret | Khoá API cất trong GitHub. Nhập vào rồi không xem lại được, chỉ ghi đè |
| artifact | File mà một lần chạy để lại cho bạn tải về, giữ 90 ngày |
| cron | Lịch chạy tự động, ví dụ "6 giờ sáng mỗi ngày" |
| dry run | Chạy thử: làm đủ mọi thứ kể cả upload, nhưng **không** tạo lịch đăng |
| slot | Một khung giờ đăng, ví dụ 09:00 ngày mai |
| channel | Một tài khoản mạng xã hội đã nối vào Planly. Tài khoản của bạn đang nối **15 kênh**, tất cả là TikTok Business |

---

## Bước 1 — Đưa thư mục này lên GitHub

Thư mục `D:\automation` **chưa phải** là repo git, chưa có lịch sử commit nào. Bạn
tạo mới từ đầu.

**1a.** Vào <https://github.com/new>. Đặt tên repo (ví dụ `automation-hub`). Chọn
**Private** cũng được — Actions vẫn chạy bình thường. **Không tích** "Add a README
file", "Add .gitignore" hay "Choose a license"; để repo trống hoàn toàn.

**1b.** Repo git ở `D:\automation` **đã tạo sẵn và đã commit rồi**. Chỉ còn
đẩy lên. Mở PowerShell:

```
cd D:\automation
python tools\push_to_github.py --repo TEN-CUA-BAN/automation
```

**Không cần token.** Lần đầu chạy, Windows sẽ mở trình duyệt cho bạn đăng nhập
GitHub — bấm đồng ý là xong, và nó nhớ luôn cho các lần push sau.

Đổi `TEN-CUA-BAN` thành tên tài khoản GitHub của bạn, và nhớ tạo repo trống ở
bước 1a trước (làm được trên điện thoại).

**Cách khác, nếu bạn có Personal Access Token** (Settings → Developer settings →
Personal access tokens, tích **repo** và **workflow**) thì khỏi cần bước 1a,
lệnh này tự tạo repo luôn:

```
$env:GITHUB_TOKEN = "dan_token_vao_day"
python tools\push_to_github.py --name automation --private
```

Token chỉ sống trong phiên PowerShell đó, không ghi vào file nào. Đổi
`--private` thành `--public` nếu muốn Actions miễn phí không giới hạn phút.

**1c.** Lúc `git push` nó sẽ hỏi đăng nhập. GitHub **không còn nhận mật khẩu tài
khoản** — chỗ "Password" bạn dán một Personal Access Token (tạo ở
Settings → Developer settings → Personal access tokens). Nếu ngại, cài
[GitHub Desktop](https://desktop.github.com) rồi đăng nhập bằng trình duyệt, nó lo
phần này hộ.

**Khoá API của bạn không bị đẩy lên.** File `.gitignore` đã chặn sẵn `.env`,
`settings.json`, `output/`, `cache/` và `state.json`.

Nếu push báo lỗi `rejected ... fetch first`, nghĩa là repo trên GitHub không trống.
Chạy `git pull --rebase origin main` rồi push lại.

---

## Bước 2 — Nhập secret

Trên trang repo: **Settings → Secrets and variables → Actions → New repository
secret**. Mỗi khoá là một secret riêng, tên phải viết **hoa và đúng từng ký tự**.

| Tên secret | Lấy ở đâu | Không có thì sao |
|---|---|---|
| `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> (miễn phí) | Rơi xuống Claude; không có Claude nữa thì lấy kịch bản có sẵn trong `topics.json`, nghĩa là nội dung sẽ lặp lại |
| `ANTHROPIC_API_KEY` | <https://console.anthropic.com> (trả tiền) | Không sao, Gemini thay được |
| `PEXELS_API_KEY` | <https://www.pexels.com/api/> (miễn phí) | Chỉ còn ảnh tĩnh Wikimedia. Video vẫn ra, chỉ ít chuyển động hơn |
| `PLANLY_API_KEY` | Planly → Settings → Security | **Không đăng được gì cả.** Video render xong nằm im trong `output/` |
| `PLANLY_TEAM_ID` | App đã điền sẵn từ app upload cũ | Cũng không đăng được. Planly không có lệnh tra team, phải cho sẵn |
| `TELEGRAM_BOT_TOKEN` | Nhắn `/newbot` cho [@BotFather](https://t.me/BotFather) | Không có tin nhắn báo kết quả về điện thoại |
| `TELEGRAM_CHAT_ID` | Xem cách lấy ở dưới | Như trên. Thiếu một trong hai là mất luôn thông báo |
| `WIKI_CONTACT` | Email của bạn | Wikimedia dễ chặn hơn khi tải nhiều ảnh liên tục |

**Lấy `TELEGRAM_CHAT_ID`:** sau khi BotFather cho bạn token, mở Telegram nhắn một
câu bất kỳ cho con bot vừa tạo, rồi mở trên trình duyệt:

```
https://api.telegram.org/bot<TOKEN-CUA-BAN>/getUpdates
```

Tìm dòng `"chat":{"id":123456789` — con số đó là chat id.

**Lưu ý:** không có secret nào tên `GITHUB_TOKEN` ở đây. GitHub cấm đặt tên secret
bắt đầu bằng `GITHUB_`, và workflow đã tự có sẵn token của nó. `GITHUB_TOKEN` chỉ
cần nhập trong app trên máy, nếu bạn muốn bấm nút Run từ trong app.

---

## Bước 3 — Chạy workflow build và cài app

**3a.** Vào tab **Actions** trên repo. Bên trái chọn workflow **build**, bấm
**Run workflow → Run workflow**. Chờ khoảng 5–10 phút. Xem được từ điện thoại bằng
app GitHub Mobile hoặc trình duyệt.

**3b.** Chạy xong, mở lần chạy đó, kéo xuống cuối phần **Summary** sẽ thấy mục
**Artifacts**. Tải file:

```
AutomationHub_Setup_1.0.0.exe
```

Nếu bạn có gắn tag (`git tag v1.0.0 && git push --tags`) thì file này còn xuất hiện
ở mục **Releases** ngoài trang chính, tải dễ hơn.

Tải trên điện thoại được, nhưng file `.exe` chỉ cài được trên máy Windows. Cách gọn
nhất: tải thẳng trên máy tính khi bạn ngồi vào, hoặc bấm tải trên điện thoại rồi
đồng bộ qua Drive.

**3c.** Chạy file cài. Windows sẽ hiện bảng xanh **"Windows protected your PC"** —
đây là chuyện bình thường với file `.exe` chưa mua chữ ký số. Bấm **More info** →
**Run anyway**.

Trình cài hỏi cài vào đâu: chọn ổ nào cũng được. Thư mục làm việc (nơi chứa video
xuất ra, có thể nặng vài GB) mặc định nằm ở `Documents\AutomationHub`, và bạn đổi
được trong app sau.

---

## Bước 4 — Mở app và cấu hình Planly

Mở **Automation Hub** từ Start Menu.

1. **Dán `PLANLY_API_KEY`** vào ô của nó, bấm nút **Test**. Phải hiện dòng dạng
   `OK - 15 channel(s): tiktok_business`. Nếu không thì xem phần Sự cố ở dưới.
   **Khoá này đã được điền sẵn** — lấy từ app upload Planly cũ của bạn, cùng với
   `PLANLY_TEAM_ID`. Planly không có lệnh tra team nên id đó bắt buộc phải có.
2. **Load channels** — app gọi lên Planly và liệt kê các kênh của bạn kèm id. Tích
   những kênh muốn dùng, hoặc để nguyên `all` (nghĩa là mọi kênh đang nối).
3. **Kiểu xếp lịch:** để `same_time`. Đây đúng là cách bạn đang xếp tay: mọi kênh
   đăng cùng một phút.
4. **Cách chia video:** để `unique`. Mỗi kênh nhận video khác nhau, không kênh nào
   đăng trùng clip với kênh khác.
5. **Giờ đăng:** 6 mốc mặc định là `09:00 12:00 15:00 18:00 21:00 23:00`. Đây là
   **giờ Việt Nam của bạn**, không phải giờ UTC — chương trình tự quy đổi.
   Ô `timezone_offset` để `7`.
6. **`lead_minutes` = 30** — không bao giờ xếp bài vào khung cách hiện tại dưới 30
   phút, để Planly kịp xử lý.
7. **`max_seconds` = 60** — cảnh báo nếu video dài hơn. Đọc lý do ở
   [PLANLY.md](PLANLY.md).
8. **Nhìn phần xem trước (preview)**: nó liệt kê video nào lên kênh nào, vào giờ
   nào. Đọc kỹ bảng này. Đây là thứ sẽ xảy ra thật.
9. **Bật `publish.enabled`. Giữ `dry_run` BẬT.** Lần đầu bắt buộc để bật.
10. Bấm **Save**.

Bạn cũng nên dán các khoá còn lại (Gemini, Pexels, Telegram) vào app luôn — app
chạy trên máy đọc `settings.json`, không đọc secret của GitHub. Hai nơi phải nhập
riêng, cố ý như vậy: khoá không bao giờ được đẩy lên repo.

---

## Bước 5 — Chạy thử một lượt dry run, rồi tắt dry run

Bấm nút chạy trong app, hoặc mở PowerShell tại thư mục cài đặt:

```
python AutomationHub.py run --factory us --count 3 --dry-run
```

Đọc kỹ những dòng này trong log:

| Dòng bạn thấy | Nghĩa |
|---|---|
| `3 video(s) -> 15 channel(s) on team ...` | Đã thấy đủ kênh |
| `uploaded video.mp4  8.2 MB  1080x1920  id 3f9a...` | File đã lên thư viện Planly thật |
| `DRY RUN - would create 3 schedule entries` | Đã dừng đúng chỗ, chưa tạo lịch |
| `2026-08-30 09:00  Video A -> outdoorboysl (tiktok_business)` | Bảng giờ, theo giờ Việt Nam |
| `warning: ... 72s is longer than 60s` | Video quá dài, xem phần Sự cố |

Trước khi tắt dry run, soát 4 điều:

- Giờ trong bảng đúng ý bạn, và là giờ Việt Nam.
- Đủ số kênh bạn muốn, không thiếu kênh nào.
- Không có video nào xuất hiện ở hai kênh khác nhau.
- Không có cảnh báo quá 60 giây.

Ổn cả thì vào app **tắt `dry_run`**, Save. Hoặc chạy một lượt thật ngay:

```
python AutomationHub.py run --factory us --count 3 --live
```

Cờ `--live` tắt dry run **chỉ cho lượt đó**, không sửa file cấu hình.

Sau lượt thật, mở lịch Planly ra kiểm tra. Muốn xoá bài đã xếp thì xem
[PLANLY.md](PLANLY.md).

### Quan trọng: cài đặt trong app phải đẩy lên GitHub thì trên mây mới dùng

Khoá API nằm trong `settings.json` — file này **không** lên GitHub, và không nên
lên. Nhưng giờ đăng, danh sách kênh, cách chia video thì phải lên, nếu không các
lần chạy trên mây vẫn dùng mặc định chứ không dùng cài đặt bạn vừa chọn.

Nên khi bấm Save, app ghi ra **hai** file:

| File | Chứa gì | Lên GitHub? |
|---|---|---|
| `settings.json` | Khoá API | **Không.** Đã chặn sẵn trong `.gitignore` |
| `settings.public.json` | Giờ đăng, kênh, chế độ chia, số video | **Có.** Phải commit và push |

Sau khi đổi lịch trong app, chạy:

```
git add settings.public.json && git commit -m "doi lich dang" && git push
```

Đây cũng là nơi bật đăng thật cho lịch tự động: đặt `publish.enabled` thành
`true` và `dry_run` thành `false` trong `settings.public.json`, rồi push. Cron
chỉ đăng thật khi file này nói vậy — nút **Run workflow** bấm tay thì vẫn luôn
dry run trừ khi bạn tích ô `live`.

---

## Bước 6 — Để lịch tự chạy, và theo dõi từ điện thoại

Workflow `videos.yml` chạy theo cron. Nó render, upload, xếp lịch, rồi commit
`STATUS.md` ngược lại repo.

Ba chỗ để nhìn, xếp theo độ tiện trên điện thoại:

1. **Telegram** — tin nhắn tự đến, một màn hình:
   `6 video(s), 48 scheduled` kèm link tới lần chạy. Không cần mở gì cả.
2. **`STATUS.md`** — nằm ngay trang đầu repo, dưới README. Mở repo là thấy chấm
   xanh / vàng / đỏ, số video, số bài đã xếp, và danh sách giờ. Không phải vào tab
   Actions.
3. **Tab Actions** — khi cần đọc log chi tiết vì có gì đó hỏng.

**Quan trọng — cấu hình trên cloud khác trên máy.** File `settings.json` bị
`.gitignore` chặn, nên trên GitHub không có nó. Lần chạy trên cloud dùng **giá trị
mặc định trong `hub/settings.py`** cộng với các cờ trong workflow. May là mặc định
đã đúng với cách bạn làm: `same_time`, `unique`, 6 mốc giờ ở trên, múi giờ +7,
giới hạn 60 giây.

Muốn đổi giờ đăng **cho các lượt chạy trên cloud**, sửa `DEFAULTS["publish"]["times"]`
trong `hub/settings.py` rồi commit và push. Sửa trong app chỉ đổi cho máy của bạn.

---

## Bước 7 — Tắt, đổi giờ, hoặc chạy thêm một lượt

**Tắt hẳn việc tự chạy:** Actions → chọn workflow `videos` → nút `...` góc phải →
**Disable workflow**. Bật lại cũng ở đó.

**Tắt riêng phần đăng, vẫn render:** trong app tắt `publish.enabled`. Hoặc chạy với
cờ `--no-publish`.

**Tắt riêng một nhà máy:** trong app, `run.mx.enabled = false` (hoặc `us`).

**Đổi giờ đăng:** trên máy thì sửa trong app rồi Save. Trên cloud thì sửa
`hub/settings.py` như nói ở Bước 6.

**Chạy thêm một lượt ngay bây giờ:**

- Trên điện thoại: Actions → `videos` → **Run workflow**.
- Trong app: nút Run (cần `GITHUB_TOKEN` có quyền `workflow` trong phần cấu hình).
- Trên máy: `python AutomationHub.py run --factory us --count 1`

Lượt thêm này **không đè lên lịch cũ**. Các khung giờ đã dùng được ghi trong
`state.json`, lượt sau tự nhảy sang khung trống tiếp theo.

---

## Sự cố hay gặp

### Không ra video nào — log ghi "the render produced no video"

Theo thứ tự nghi ngờ:

1. **FFmpeg.** Chạy `python AutomationHub.py preflight`. Nó kiểm tra `ffmpeg`,
   `ffprobe`, các filter cần thiết và font. Trên máy bạn FFmpeg đã có sẵn; lỗi này
   hay xảy ra hơn trên máy mới.
2. **Không còn kịch bản.** Không có `GEMINI_API_KEY` lẫn `ANTHROPIC_API_KEY` thì
   chương trình lấy trong `topics.json` — US có 9 bài, hết là hết. Nhập key Gemini
   (miễn phí) là xong.
3. **Mạng.** Wikimedia trả 429 khi bị gọi quá nhanh. Chương trình đã tự giãn nhịp,
   nhưng runner của GitHub đôi khi vẫn bị. Chạy lại lượt đó.

Xem log ở đâu: trên cloud là tab Actions, mở lần chạy, bung bước render — log hiện
theo thời gian thực, không phải đợi đến cuối. Trên máy là cửa sổ log bên phải trong
app. Thư mục dữ liệu của app là `%APPDATA%\AutomationHub` (chứa `settings.json`,
`state.json`, `logs\`).

### Planly từ chối khoá — "Planly rejected the API key"

- Khoá lấy ở **Planly → Settings → Security**, không phải khoá của tích hợp nào khác.
- Dán dính khoảng trắng hoặc dính dấu nháy là hỏng. Xoá ô, dán lại.
- Khoá ngắn dưới 16 ký tự bị chương trình loại ngay, chưa gọi lên mạng.
- Đổi khoá bên Planly thì phải sửa **cả hai chỗ**: trong app và trong secret của
  GitHub.
- Báo `Planly rate limit hit` là bị giới hạn tốc độ, chờ một phút rồi chạy lại.

### Video dài hơn 60 giây, Planly không hiện trên lịch

Bài **vẫn được tạo và vẫn đăng đúng giờ**, chỉ là giao diện lịch của Planly không
hiển thị nó, nên bạn tưởng mất. Log có cảnh báo:

```
warning: Ten video: 72s is longer than 60s - Planly will not show it on the calendar.
```

Cách sửa: mở `factories/us/config.json` (và `factories/mx/config.json`), giảm
`"target_seconds"` — mặc định là `45`, hạ xuống `40` là chắc chắn. Kịch bản dài quá
tay là nguyên nhân chính. Hoặc chạy với `--seconds 40`.

Nếu bạn cố ý muốn video dài hơn: tăng `publish.max_seconds` trong app, cảnh báo sẽ
tắt. Chương trình không bao giờ chặn — nó chỉ nhắc.

### Lịch tự chạy im lặng sau khoảng 2 tháng

GitHub **tự tắt cron** của một repo không có hoạt động gì trong 60 ngày. Đây là quy
định của họ, không phải lỗi. Repo này có sẵn một workflow nhịp tim (heartbeat) chạy
định kỳ để đếm ngược đó không bao giờ về 0.

Nếu vẫn im: vào Actions → chọn `videos` → nút `...` → **Enable workflow**. GitHub
cũng gửi email báo trước khi tắt, để ý hộp thư.

### Chạy đúng giờ nhưng muộn

Cron của GitHub là "không sớm hơn", không phải "đúng lúc". Vào giờ cao điểm có thể
trễ 10–60 phút. Không sửa được từ phía bạn. Vì vậy `videos.yml` nên chạy sớm hơn giờ
đăng đầu tiên vài tiếng — bài vẫn lên đúng khung 09:00 vì khung giờ do chương trình
tính, không phụ thuộc lúc runner chạy.

### Hết phút Actions

Repo private được 2000 phút/tháng miễn phí. Mỗi video tốn khoảng 1,5–2 phút runner.
6 video/ngày là khoảng 360 phút/tháng — thoải mái. Repo public thì không giới hạn.

---

## Một điều nên biết về GitHub Actions

Điều khoản của GitHub nói Actions là để build, test và deploy cho chính dự án trong
repo đó. Một workflow ngồi render video theo lịch là vùng xám: nó không bị cấm rõ
ràng, nhưng cũng không phải thứ Actions sinh ra để làm, và cron ở gói miễn phí có
thể chạy trễ. Nếu sau này bạn muốn dời đi, một VPS nhỏ luôn bật (khoảng 5 USD/tháng)
chạy đúng file `tools/run_factory.py` này qua cron là xong — code không phải sửa gì,
chỉ đổi chỗ nhập khoá từ secret sang `.env`. Bạn đã cân nhắc rồi, tôi chỉ nói một
lần cho đủ.

---

## Đọc tiếp

- [PLANLY.md](PLANLY.md) — cách chia video cho kênh, cách tính giờ, cách xoá bài đã
  xếp. Nên đọc trước lượt chạy thật đầu tiên.
- [README.md](../README.md) — bản tiếng Anh, mô tả cấu trúc code.
</content>
