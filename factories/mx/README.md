# Fábrica de videos — kênh faceless cho Mexico (9:16)

Tool tự động ra video ngắn **tiếng Tây Ban Nha (es-MX)** cho TikTok / Reels / Shorts.
Một lệnh → kịch bản → giọng đọc → phụ đề karaoke → b-roll → file `.mp4` 1080×1920 sẵn sàng đăng.

**Niche mặc định:** `misterios` — bí ẩn, truyền thuyết, chuyện lạ của Mexico.
Đây là mảng faceless lên follow nhanh nhất ở thị trường MX: hook mạnh, giữ chân tốt,
không dính bản quyền, và tự động hoá được 100%.

---

## Chạy nhanh

Double-click **`FabricaVideosMX.exe`** — bảng điều khiển có 3 tab: nhập khoá API,
chỉnh cấu hình, bấm tạo video. Không cần đụng file JSON nào.

Hoặc dùng dòng lệnh:

```bash
python main.py
```

Ra video ở `output/<ngày-giờ>_<chủ-đề>/video.mp4` kèm `meta.json` (title + description + hashtags để copy-paste khi đăng).

```bash
python main.py --count 5
```

Làm 5 video liên tiếp, mỗi cái một chủ đề khác nhau.

Hoặc double-click `run.bat`.

---

## Cài đặt

Đã cài sẵn trong máy bạn rồi (Python 3.12 + FFmpeg 9.0). Nếu chuyển máy khác:

```bash
pip install -r requirements.txt
```

FFmpeg phải có trong PATH (`ffmpeg -version` chạy được).

---

## Hình ảnh, nhạc và sound effect — đều tự động

Không cần cài Remotion, không cần tải file nhạc, không cần API key nào.

**Hình minh hoạ** lấy từ **Wikimedia Commons** — ảnh thật của đúng địa điểm trong
kịch bản (Isla de las Muñecas, Chichén Itzá, Popocatépetl...), không cần key.
Ảnh ngang được ghép nền blur + Ken Burns zoom chậm để lấp khung 9:16.
Thứ tự nguồn chỉnh trong `config.json` → `visual_priority`:

```
wikimedia -> pexels_video -> pexels_photo -> local -> gradient
```

**Nhạc nền** tự sinh bằng FFmpeg: hợp âm ngân + mạch trầm, đổi theo niche
(`misterios` = La thứ tối, `curiosidades` = Đô trưởng sáng hơn). Zero bản quyền.
Bỏ file `.mp3` vào `assets/music/` thì nhạc của bạn được ưu tiên.

**Sound effect** cũng tự sinh: `boom` ở câu hook, `whoosh` mỗi lần chuyển cảnh,
`riser` trước câu chốt. Tắt bằng `"sfx": false`.

**Mix**: nhạc tự động ducking (nhỏ xuống khi có giọng đọc), toàn bộ chuẩn hoá về
−14 LUFS đúng chuẩn TikTok/Reels.

**Chuyển động**: mỗi cảnh nối nhau bằng `xfade` (transition đổi theo niche —
`misterios` dùng fadeblack/dissolve, `humor` dùng slideleft/circleopen),
cảnh hook có rung máy quay tắt dần, và mỗi niche có màu riêng
(vignette + grain cho bí ẩn, tươi và sạch cho hài). Tắt bằng
`"transitions": false` / `"camera_shake": false`.

## Niche `humor` — hài bản sắc địa phương

```bash
python main.py --niche humor --count 3
```

Đây là niche riêng, không phải đổi giọng văn:

- **Kịch bản** theo cấu trúc setup → escalate → **remate** (câu chốt), không có
  "sígueme para más". Prompt ép dùng tiếng lóng Mexico thật (`no manches`, `neta`,
  `chale`, `ya valió`) nhưng **tối đa 3 từ lóng/video** — nhiều hơn là nghe như
  người nước ngoài bắt chước.
- **Chủ đề** đời thường ai cũng dính: tiệm tạp hoá đầu hẻm, kẹt xe, lương chưa về,
  nhóm WhatsApp gia đình, cái "ahorita" huyền thoại.
- **Chặn cứng** trong prompt: chính trị, tôn giáo, ma tuý, chửi thề nặng, albur tục,
  đùa về vùng miền / giai cấp / màu da / cân nặng / giới tính. Toàn bộ đều bóp
  reach và chặn kiếm tiền.
- **Âm thanh khác hẳn**: nhạc trưởng sáng, nhịp nhanh; SFX là `pop` kiểu hoạt hình
  ở mỗi cắt và `ding` ở câu chốt, thay cho boom/whoosh/riser của `misterios`.
- **Giọng đọc nhanh hơn** (+24% thay vì +12%) và khoảng nghỉ giữa cảnh ngắn lại.
- **Ảnh**: humor ưu tiên Pexels (người, đời thường) trước Wikimedia — chỉnh ở
  `niche_visuals` trong `config.json`.

Bank có sẵn 3 kịch bản humor để chạy thử không cần API key. Có
`ANTHROPIC_API_KEY` thì Claude viết mới mỗi lần.

## Khoá API (đều tùy chọn)

Cách dễ nhất: mở `FabricaVideosMX.exe` → tab **Khoá API** → dán vào → bấm
**Kiểm tra khoá**. Nó gọi thật lên từng dịch vụ và báo khoá nào sống.

| Biến môi trường | Dùng để làm gì | Không có thì sao |
|---|---|---|
| `GEMINI_API_KEY` | **Có capa miễn phí thật** — Gemini viết kịch bản mới, $0 | Thử tới Claude |
| `ANTHROPIC_API_KEY` | Claude viết kịch bản, ~$0,015/video | Lấy từ `topics.json` (27 bài viết sẵn) |
| `PEXELS_API_KEY` | Thêm **video** stock có chuyển động, xen kẽ ảnh Wikimedia | Chỉ dùng ảnh Wikimedia (vẫn đẹp, ảnh tĩnh có zoom) |

Thứ tự thử LLM đặt ở `llm_priority` trong `config.json`, mặc định
`["gemini", "claude"]`. Cái nào không có khoá thì bỏ qua; cái nào lỗi thì rớt
xuống cái sau; hết thì dùng `topics.json`.

> **Gói Gemini Pro không phải là API key.** Đó là sản phẩm chat, không cấp
> credential cho script. Nhưng cùng tài khoản Google đó bạn lấy được API key
> miễn phí ở https://aistudio.google.com/apikey — capa miễn phí riêng, không
> liên quan gói Pro.

Pexels key lấy miễn phí ở https://www.pexels.com/api/ (200 request/giờ).

```bash
setx ANTHROPIC_API_KEY "sk-ant-dan-key-that-cua-ban-vao-day"
```

```bash
setx PEXELS_API_KEY "dan-key-that-cua-ban-vao-day"
```

Mở lại terminal sau khi `setx`.

> **Đừng dán nguyên chữ mẫu.** Key Pexels thật dài khoảng 56 ký tự. Tool sẽ coi
> mọi chuỗi ngắn hơn 20 ký tự là "không có key" và bỏ qua Pexels, thay vì lỗi
> 401 rồi rơi hết xuống nền gradient. Xoá key sai bằng `setx PEXELS_API_KEY ""`.

## ⚠️ Ghi công ảnh Wikimedia

Phần lớn ảnh Commons là CC BY hoặc CC BY-SA — **bắt buộc ghi nguồn**.
Mỗi video có sẵn file `creditos.txt` liệt kê tác giả + license + link.
Dán nội dung đó vào phần mô tả bài đăng là xong.

Nếu muốn tránh hẳn chuyện này: lấy `PEXELS_API_KEY` rồi đổi `visual_priority`
thành `["pexels_video", "pexels_photo", "local", "gradient"]` — Pexels không
yêu cầu ghi công.

---

## Các tuỳ chọn

```bash
python main.py --count 3 --niche curiosidades --voice es-MX-DaliaNeural --seconds 35
```

| Cờ | Ý nghĩa |
|---|---|
| `--count N` | Số video cần làm |
| `--topic "..."` | Ép chủ đề cụ thể (vd `--topic "el chupacabras"`) |
| `--niche` | `misterios` \| `humor` \| `curiosidades` \| `historia` \| `lugares` |
| `--voice` | `es-MX-JorgeNeural` (nam, mặc định) hoặc `es-MX-DaliaNeural` (nữ) |
| `--seconds` | Độ dài mong muốn (mặc định 45) |
| `--bank` | Bỏ qua Claude, chỉ dùng `topics.json` |

Chỉnh sâu hơn (font, cỡ chữ, màu highlight, âm lượng nhạc, CRF...) trong `config.json`.

---

## Thêm chất riêng cho kênh

- **Nhạc nền:** bỏ file `.mp3` vào `assets/music/` → ghi đè nhạc tự sinh.
  Nhớ dùng nhạc free-license nếu định bật kiếm tiền.
- **B-roll riêng:** bỏ video/ảnh dọc vào `assets/stock/`.
- **Chủ đề riêng:** thêm vào `topics.json`. Nhớ điền `subject` — 2–3 chữ tiếng Tây Ban Nha,
  là từ khoá tìm ảnh thật trên Commons. Commons bắt **tất cả** từ phải khớp nên càng ngắn càng tốt
  (`Chichén Itzá` ra 12 ảnh, `cacao chocolate mexicano Theobroma` ra 0).
- **Font:** đổi `"font"` trong `config.json` sang font đã cài trong Windows
  (`Impact`, `Montserrat ExtraBold`... — nhớ cài font trước).

### Các nút chỉnh âm thanh trong `config.json`

| Key | Mặc định | Ý nghĩa |
|---|---|---|
| `music` | `"auto"` | `"off"` để tắt hẳn nhạc |
| `music_volume` | `0.20` | Âm lượng nhạc trước khi ducking |
| `music_duck` | `true` | Nhạc nhỏ xuống khi có giọng đọc |
| `sfx` / `sfx_volume` | `true` / `0.35` | Boom, whoosh, riser |
| `loudness_lufs` | `-14` | Chuẩn hoá cuối, đúng target của TikTok |
| `max_bitrate` | `"6M"` | Trần bitrate. Video 40 giây ra khoảng 5–7 MB |

**Về hạt film (grain):** mỗi niche có mức `grain` riêng trong `STYLES` của
`render.py`. Nhiễu theo thời gian tốn bitrate phi tuyến — đo ở 1080×1920/30fps:
`grain=6` ăn 5,8 Mbps còn `grain=3` chỉ 0,8 Mbps, mà nhìn trên điện thoại không
phân biệt được. Vì vậy có hằng số `GRAIN_MAX = 3` chặn trần. Muốn video nhẹ hơn
nữa thì đặt `grain: 0`.

---

## Chạy tự động mỗi ngày

### Trên cloud, không đụng máy bạn (GitHub Actions)

Đây là cách chạy hands-off. Workflow đã có sẵn ở `.github/workflows/videos.yml`.

**Bước 1** — tạo repo và push:

```bash
git init && git add . && git commit -m "Fabrica de videos MX"
```

```bash
git remote add origin https://github.com/<user>/<repo>.git && git push -u origin main
```

**Bước 2** — thêm secret ở `Settings → Secrets and variables → Actions`:

| Secret | Bắt buộc? |
|---|---|
| `ANTHROPIC_API_KEY` | Không. Có thì Claude viết kịch bản mới; không có thì dùng `topics.json` |
| `PEXELS_API_KEY` | Không. Có thì xen video stock vào giữa ảnh Wikimedia |
| `WIKI_CONTACT` | Không. Email/URL của bạn để Wikimedia biết ai đang gọi API |

**Bước 3** — xong. Workflow tự chạy **23:00 UTC = 6 giờ sáng Việt Nam**, làm 3 video.
Muốn chạy ngay thì vào tab `Actions → Generar videos → Run workflow`, chỉnh được
số lượng / niche / chủ đề.

Video tải về ở mục **Artifacts** của mỗi lần chạy (giữ 90 ngày), kèm `meta.json`,
`creditos.txt` và `script.json`. Tab Summary hiện luôn tiêu đề + hashtag để copy.

**Chi phí:** repo public thì không giới hạn phút. Repo private được 2000 phút/tháng
— mỗi video tốn ~1,5 phút runner nên thoải mái hơn 1000 video/tháng.

`state.json` và thư mục `cache/` được lưu qua `actions/cache` giữa các lần chạy,
nên chủ đề không lặp lại và ảnh Wikimedia không phải tải lại.

### Bảng điều khiển và GitHub Actions dùng chung cái gì?

| File | GUI ghi vào | Có lên GitHub không | Actions dùng được không |
|---|---|---|---|
| `config.json` | Tab Cấu hình | **Có**, được commit | **Có** — chung cấu hình với máy bạn |
| `topics.json` | (sửa tay) | **Có** | **Có** |
| `.env` | Tab Khoá API | **Không**, bị gitignore | **Không** |

Nghĩa là: chỉnh giọng đọc / độ dài / niche trong GUI rồi push lên → Actions chạy
đúng cấu hình đó. Nhưng **khoá API thì phải nhập hai lần**: một lần trong GUI (để
chạy trên máy) và một lần trong `Settings → Secrets and variables → Actions` (để
chạy trên cloud). Cố ý như vậy — file `.env` không bao giờ được lên repo.

### Trên máy bạn (Windows Task Scheduler)

Create Basic Task → Daily → Start a program:

- Program: `D:\comentary\run.bat`
- Arguments: `3`

---

## Cấu trúc

```
FabricaVideosMX.exe  Bảng điều khiển. Cũng chính là CLI khi chạy với --run
gui.py               Mã nguồn của bảng điều khiển (tkinter)
main.py              CLI, chạy toàn bộ pipeline
config.json          Tất cả tham số
topics.json          Ngân hàng chủ đề dự phòng (không cần API)
state.json           Nhớ chủ đề đã dùng để không lặp lại
tools/
  build_exe.py       Đóng gói lại exe sau khi sửa code (python tools/build_exe.py)
  preflight.py       Kiểm tra ffmpeg/filter/font/module trước khi render
  summary.py         Ghi tóm tắt vào Job Summary của GitHub Actions
.github/workflows/
  videos.yml         Chạy tự động trên cloud, video ra dạng artifact
assets/fonts/        Anton (OFL) — font đóng gói sẵn, chạy đâu cũng giống nhau
pipeline/
  script_gen.py      Claude API (claude-opus-5) hoặc topics.json
  tts.py             Edge TTS es-MX + timing từng từ
  subtitles.py       Sinh file .ass karaoke, chống chồng dòng
  visuals.py         Wikimedia -> Pexels -> assets/stock -> gradient
  audio_fx.py        Sinh nhạc nền + boom/whoosh/riser bằng FFmpeg
  render.py          Ghép FFmpeg: 9:16, blur-fill, Ken Burns, phụ đề, mix + ducking
assets/stock/        B-roll của bạn
assets/music/        Nhạc nền của bạn
cache/media/         Cache file đã tải (xoá thoải mái)
output/              Video thành phẩm
```

---

## Ghi chú

- Kịch bản do Claude sinh ra **cần bạn liếc qua trước khi đăng**. Chủ đề bí ẩn/lịch sử
  dễ có chi tiết sai; `meta.json` và `script.json` nằm sẵn cạnh video để sửa nhanh.
- Video từ Pexels được cấp phép dùng thương mại, nhưng vẫn nên đọc
  https://www.pexels.com/license/ trước khi bật kiếm tiền.
- Mỗi video mất khoảng 60–150 giây tuỳ nguồn ảnh.
- Wikimedia chặn bot bắn nhanh (429). Tool đã throttle 1.2 giây/ảnh và tự giãn ra
  khi bị chặn, nên lần chạy đầu hơi chậm; ảnh được cache ở `cache/media/` cho lần sau.
- Không cần Remotion. Remotion là React + headless Chrome — chậm hơn nhiều và thêm cả
  stack Node, chỉ đáng khi cần animation phức tạp. FFmpeg đủ cho định dạng này.
- Font Anton được đóng gói trong repo và nạp qua `fontsdir`, nên không phải cài font
  ở máy đích. Đây là lý do video render trên Linux giống hệt trên Windows.
- Workflow chỉ mới được kiểm tra ở phần cú pháp và script Python (máy này không có
  Docker/WSL để chạy thử Linux). Bước `Preflight` sẽ báo rõ nếu FFmpeg bản Ubuntu
  thiếu filter nào, trước khi tốn thời gian render.
- Chạy `python tools/preflight.py` bất cứ lúc nào để tự kiểm tra môi trường.
- Exe **không đóng gói FFmpeg** (nặng ~100 MB) và không đóng gói `config.json`,
  `topics.json`, `assets/` — mấy thứ đó nằm cạnh exe để sửa được và để Actions
  dùng chung. Vậy nên giữ exe **trong thư mục này**, đừng kéo đi chỗ khác.
- Sửa code xong thì build lại: `python tools/build_exe.py` (~1 phút).
- Đường dẫn Gemini chưa test được bằng khoá thật (tôi không có khoá). Nút
  **Kiểm tra khoá** trong GUI sẽ gọi thật và báo ngay nếu có gì sai.
