# Short-video factory — kênh faceless cho thị trường US (9:16)

Tool tự động ra video ngắn **tiếng Anh Mỹ** cho TikTok / Reels / Shorts.
Một lệnh → kịch bản → giọng đọc → phụ đề karaoke → ảnh minh hoạ → nhạc + SFX →
file `.mp4` 1080×1920 sẵn sàng đăng.

Đây là bản song sinh của project Mexico ở `D:\comentary`, đã localize toàn bộ:
giọng đọc en-US, prompt tiếng Anh, đơn vị đo Mỹ, niche theo thị trường Mỹ.

---

## Chạy nhanh

```bash
python main.py
```

```bash
python main.py --count 5
```

Video ra ở `output/<ngày-giờ>_<chủ-đề>/video.mp4`, kèm `meta.json` (title +
description + hashtag để copy-paste khi đăng) và `credits.txt`.

---

## 6 niche, mỗi cái một tông riêng

| Niche | Nội dung | Giọng | Nhạc | Màu |
|---|---|---|---|---|
| `mysteries` *(mặc định)* | Vụ mất tích, nơi kỳ lạ, hiện tượng chưa giải thích | Andrew, +8% | La thứ, tối | Vignette + grain |
| `truecrime` | Vụ án đã khép lại, có tư liệu công khai | Brian, +4% | Sol thứ, nặng & chậm | Tối nhất, bạc màu |
| `facts` | Sự thật phản trực giác về khoa học, đời thường | Ava, +16% | Đô trưởng, sáng | Tươi, sạch |
| `history` | Góc tối và kỳ lạ của lịch sử | Brian, +8% | Si thứ | Trầm, hơi grain |
| `money` | Tâm lý tiền bạc, thói quen chi tiêu | Andrew, +14% | Rê trưởng, đều | Sáng, sạch |
| `humor` | Hài quan sát đời sống Mỹ | Andrew, +20% | Fa trưởng, nhịp nhanh | Rực, không vignette |

```bash
python main.py --niche facts --count 3
```

Mỗi niche đổi **giọng đọc, tốc độ, khoảng nghỉ, hợp âm nhạc nền, bộ SFX,
transition và color grade** — không phải chỉ đổi chủ đề.

### Hai niche có ràng buộc cứng trong prompt

**`truecrime`** — đây là mảng lớn nhất thị trường Mỹ nhưng cũng rủi ro nhất.
Prompt chặn: chỉ vụ đã khép lại và có tư liệu chính thống, **không nêu tên nghi phạm
chưa bị kết án**, không nêu tên trẻ vị thành niên hay người thân nạn nhân, không mô tả
thương tích, không suy đoán trình bày như sự thật. Kết bằng điều vụ án đã thay đổi
(luật, phương pháp điều tra), không phải bằng lời kêu gọi suy đoán.

**Vẫn nên đọc lại kịch bản trước khi đăng.** Đây là niche duy nhất tôi khuyên như vậy.

**`money`** — chỉ giáo dục tài chính chung. Cấm nêu mã cổ phiếu / coin / quỹ / sàn cụ thể,
cấm dự đoán lợi nhuận, cấm "get rich" và income claim. Toàn bộ đều làm account bị gắn cờ.

---

## App exe — mở lên tuỳ chỉnh

```bash
python app.py
```

Đóng gói thành file exe chạy độc lập:

```bash
python build_exe.py
```

Ra `dist/VideoFactory.exe`, **17.5 MB**, một file duy nhất. Copy đi đâu cũng chạy —
lần đầu mở nó tự ghi `config.json`, `topics.json` và `assets/` ra cạnh nó để bạn sửa.
Đã test trong thư mục trắng: bootstrap + render ra video thật.

Ba tab trong app:

- **Content** — niche, số video, độ dài, số cảnh, ép chủ đề, chọn AI viết kịch bản
- **Look & sound** — giọng đọc, tốc độ, transition, camera shake, SFX, âm lượng, CRF
- **API keys** — nhập key, **nút Test gọi thật lên từng API** và báo lỗi cụ thể,
  nút Save ghi vào `.env`

Bấm Generate là chạy nền trong thread riêng, log hiện realtime bên phải, có nút Stop.

**FFmpeg**: exe không kèm sẵn (sẽ nặng thêm ~120 MB). App tự kiểm tra lúc mở và
báo nếu thiếu. Muốn nhét vào luôn:

```bash
python build_exe.py --with-ffmpeg
```

Mặc định exe **không kèm SDK Claude** cho nhẹ. Cần Claude thì:

```bash
python build_exe.py --with-claude
```

### Exe cũng chạy được không cần mở cửa sổ

```bash
VideoFactory.exe --count 3 --niche facts
```

Có tham số là chạy headless, log ghi vào `run.log` cạnh exe. Dùng cho Windows
Task Scheduler.

---

## Viết kịch bản bằng Gemini

`config.json` → `"provider"`:

| Giá trị | Nghĩa |
|---|---|
| `auto` *(mặc định)* | Có key nào dùng key đó. **Gemini trước**, rồi Claude, rồi bank offline |
| `gemini` | Ép Gemini |
| `claude` | Ép Claude |
| `bank` | Không gọi AI, chỉ `topics.json` |

Gemini là lựa chọn mặc định vì **có free tier thật** — đủ cho khối lượng này.
Key lấy ở https://aistudio.google.com/apikey

Model không hardcode. Tool gọi `models.list` và **tự chọn lại** nếu id trong config
không còn tồn tại (Google đổi tên model khá thường xuyên) — ưu tiên bản `pro`,
bản chính thức trước bản preview. Nên `"gemini_model"` sai cũng không chết.

Provider nào lỗi thì rơi xuống provider kế tiếp, không làm hỏng cả lượt chạy.

---

## API key — đều tuỳ chọn

Tạo file **`.env`** ở thư mục gốc project (copy từ `.env.example`):

```
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
PEXELS_API_KEY=...
```

Không dấu nháy, không khoảng trắng quanh dấu `=`. Dùng file thay vì `setx` vì
`setx` rất dễ sai (quên mở lại terminal, dính dấu nháy, copy nhầm placeholder).

Kiểm tra bằng:

```bash
python tools/check_keys.py
```

Nó gọi thật lên từng API và báo chính xác cái nào hỏng.

| Key | Được gì | Không có thì sao |
|---|---|---|
| `GEMINI_API_KEY` | Gemini viết kịch bản mới mỗi lần (free tier) | Dùng 9 kịch bản trong `topics.json` |
| `ANTHROPIC_API_KEY` | Claude viết kịch bản, chất hơn nhưng trả tiền | Không bắt buộc, Gemini thay được |
| `PEXELS_API_KEY` | Video stock có chuyển động, xen kẽ với ảnh Wikimedia | Chỉ ảnh Wikimedia (vẫn ổn, ảnh tĩnh có zoom) |

Pexels key miễn phí ở https://www.pexels.com/api/ — key thật dài ~56 ký tự.

Chi phí Claude: ~$0.07/video với `claude-opus-5`. Đổi `"model": "claude-sonnet-5"`
trong `config.json` thì còn ~$0.03.

---

## Không cần key nào cũng chạy được

- **Ảnh**: Wikimedia Commons — ảnh thật của đúng chủ đề, không cần key
- **Giọng đọc**: Edge TTS, miễn phí
- **Nhạc nền**: sinh bằng FFmpeg, hợp âm đổi theo niche, zero bản quyền
- **SFX**: boom / whoosh / riser (hoặc pop / ding cho humor), cũng tự sinh
- **Mix**: nhạc ducking dưới giọng đọc, chuẩn hoá −14 LUFS đúng target TikTok

Bỏ file `.mp3` vào `assets/music/` thì nhạc của bạn ghi đè nhạc tự sinh.

## Ghi công ảnh Wikimedia

Phần lớn ảnh Commons là CC BY / CC BY-SA — **bắt buộc ghi nguồn**. Mỗi video có
sẵn `credits.txt` (tác giả + license + link), dán vào mô tả bài đăng là xong.

Né hẳn thì lấy Pexels key rồi bỏ `wikimedia` khỏi `visual_priority` — Pexels
không yêu cầu ghi công.

---

## Tuỳ chọn

| Cờ | Ý nghĩa |
|---|---|
| `--count N` | Số video |
| `--topic "..."` | Ép chủ đề (hoặc id trong `topics.json` khi dùng `--bank`) |
| `--niche` | 6 niche ở bảng trên |
| `--voice` | Giọng Edge TTS, vd `en-US-AvaMultilingualNeural` |
| `--seconds` | Độ dài mong muốn (mặc định 45) |
| `--bank` | Bỏ qua AI, chỉ dùng `topics.json` |

Sâu hơn thì chỉnh `config.json`. Câu chữ của prompt nằm riêng ở
`pipeline/prompts.py` — đó là file bạn sẽ muốn sửa nhất.

---

## Thêm chủ đề

Thêm vào `topics.json`, nhớ điền `niche` và `subject`. `subject` là 2–3 chữ tiếng Anh
để tìm ảnh thật trên Commons — Commons bắt **tất cả** từ phải khớp nên càng ngắn
càng tốt (`Roanoke Colony` ra 9 ảnh, `radium clock dial` chỉ ra 3).

---

## Cấu trúc

```
app.py               App giao diện (Tkinter)
build_exe.py         Đóng gói -> dist/VideoFactory.exe
main.py              CLI
config.json          Tham số + preset giọng/ảnh theo niche
topics.json          9 kịch bản dự phòng (không cần API)
.env                 Key của bạn (gitignored)
.github/workflows/
  videos.yml         Chạy 4 lần/ngày trên cloud, video ra dạng artifact
tools/
  check_keys.py      Test key thật lên API
  preflight.py       Kiểm tra ffmpeg/filter/font trước khi render
pipeline/
  prompts.py         Niche + luật viết kịch bản  <- sửa ở đây nhiều nhất
  gemini.py          Gọi Gemini REST + tự resolve tên model
  script_gen.py      Chọn provider: gemini -> claude -> topics.json
  tts.py             Edge TTS en-US + timing từng từ
  subtitles.py       .ass karaoke, chống chồng dòng
  visuals.py         Wikimedia -> Pexels -> assets/stock -> gradient
  audio_fx.py        Nhạc nền + SFX sinh bằng FFmpeg
  render.py          9:16, blur-fill, Ken Burns, xfade, phụ đề, mix + ducking
```

---

## Ghi chú

- Mỗi video mất khoảng 90–150 giây.
- Wikimedia chặn bot bắn nhanh (429). Tool throttle 1.2 giây/ảnh và tự giãn khi bị
  chặn; ảnh cache ở `cache/media/` nên lần sau nhanh hơn nhiều.
- Kịch bản Claude sinh ra **nên liếc qua trước khi đăng**, nhất là `truecrime`.
  `script.json` và `meta.json` nằm sẵn cạnh video để sửa nhanh.

---

## Không mở máy thì video nằm ở đâu?

Đây là câu đúng phải hỏi. Có hai đường:

**1. Không nối Planly** — video nằm ở mục **Artifacts** của mỗi lần chạy Actions,
phải vào GitHub tải về tay, giữ 90 ngày. Chạy ngầm được nhưng vẫn phải đụng tay.

**2. Nối Planly** — video **không cần nằm ở đâu cả**. Runner render xong là đẩy
thẳng lên thư viện media của Planly rồi xếp lịch luôn. Bạn mở Planly ra là thấy
lịch đăng đã đầy. Đây là cái bạn muốn.

## Nối Planly

Bật trong `config.json`:

```json
"planly": {
  "enabled": true,
  "dry_run": true,
  "channels": ["all"],
  "slots": ["09:00", "13:00", "18:00"],
  "timezone_offset": 7,
  "lead_minutes": 30
}
```

Key lấy ở Planly → **Settings → Security**, bỏ vào `.env` hoặc secret
`PLANLY_API_KEY` trên GitHub.

Luồng mỗi video: `media/start-upload` → PUT thẳng lên S3 → `media/finish-upload`
→ `schedules/create` một entry cho mỗi channel.

**Giờ đăng** là giờ địa phương của bạn (`timezone_offset: 7` = Việt Nam), tool
tự đổi sang UTC khi gửi. Nó tìm slot trống gần nhất **cách hiện tại ít nhất
`lead_minutes` phút**, và nhớ slot đã dùng trong `state.json` nên chạy 3 video
một lượt thì ra 3 khung giờ khác nhau, không đè lên nhau.

**`dry_run: true` là mặc định và bạn nên để nguyên lần đầu.** Nó làm hết mọi
thứ kể cả upload, chỉ không tạo lịch. Chạy thử, xem log, thấy đúng ngày giờ và
đúng channel rồi mới tắt.

Trong app có tab **Publishing** với nút **Load channels from Planly** — bấm là in
ra id + tên + mạng xã hội của từng channel để bạn dán vào ô Channel ids.

Planly lỗi thì **không làm hỏng video** — file đã render vẫn nằm nguyên trên đĩa,
lỗi ghi vào `meta.json`.

## Chất lượng video

`config.json` → `"quality"` và `"resolution"`:

| quality | CRF | preset | trần bitrate |
|---|---|---|---|
| `fast` | 22 | veryfast | 6M |
| `high` *(mặc định)* | 19 | medium | 14M |
| `max` | 16 | slow | 24M |

`"resolution"`: `1080p` (1080×1920, mặc định), `1440p`, `4k`.

**Nên để 1080p.** Đó đúng là cái TikTok / Reels / Shorts phát ra; to hơn thì lúc
upload bị encode nhỏ lại, chỉ tốn thời gian render.

---

## Chạy ngầm trên GitHub Actions

Workflow ở `.github/workflows/videos.yml`, chạy **4 lần/ngày** (01:00, 07:00,
13:00, 19:00 UTC). Push repo lên GitHub rồi thêm secret ở
`Settings → Secrets and variables → Actions`:

| Secret | Bắt buộc? |
|---|---|
| `GEMINI_API_KEY` | Không, nhưng có thì mới ra kịch bản mới |
| `PEXELS_API_KEY` | Không |
| `ANTHROPIC_API_KEY` | Không |
| `PLANLY_API_KEY` | Không, chỉ cần nếu bật xếp lịch tự động |
| `WIKI_CONTACT` | Không, email/URL để Wikimedia biết ai gọi |

Video tải về ở mục **Artifacts** mỗi lần chạy (giữ 90 ngày), kèm `meta.json`,
`credits.txt`, `script.json`. Tab Summary hiện luôn title + hashtag để copy.

`state.json` và `cache/` được lưu qua `actions/cache` giữa các lần chạy nên
chủ đề không lặp và ảnh không phải tải lại.

**Nói thẳng về "lúc nào cũng chạy ngầm"**: GitHub Actions không có chế độ chạy
liên tục 24/7. Cron 4 lần/ngày là gần nhất có thể, và thực tế 12 video/ngày đã
nhiều hơn sức đăng của một kênh. Repo public không giới hạn phút; repo private
được 2000 phút/tháng, mỗi video tốn ~2 phút runner.
