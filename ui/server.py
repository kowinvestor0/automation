"""Asynchronous Web Server and REST API for Auto Make Money Dashboard."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import re
import subprocess
import traceback
from pathlib import Path
from typing import Any, Dict, List
from aiohttp import web

from core.paths import CACHE_DIR, DATA_DIR, OUTPUT_DIR, ROOT_DIR, UI_DIR
from core.config_manager import load_config, save_config
from core.account_manager import AccountManager
from core.planly_client import PlanlyClient
from core.scraper import VideoScraper
from core.gemini_script import generate_script
from core.video_engine import render_monetizable_video
from core.scheduler import get_available_videos, schedule_channel_quota

account_mgr = AccountManager()
scraper = VideoScraper()

# Background task logs
job_logs: List[str] = []
current_job: Dict[str, Any] = {"status": "idle", "message": "Ready"}


def append_log(msg: str) -> None:
    stamp = dt.datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line)
    job_logs.append(line)
    if len(job_logs) > 300:
        job_logs.pop(0)


async def handle_index(request: web.Request) -> web.Response:
    index_file = UI_DIR / "templates" / "index.html"
    if not index_file.exists():
        return web.Response(text="Dashboard index.html not found.", status=404)
    return web.Response(text=index_file.read_text(encoding="utf-8"), content_type="text/html")


async def handle_get_status(request: web.Request) -> web.Response:
    accounts = account_mgr.load_all()
    total_channels = sum(len(a.get("channels", [])) for a in accounts)
    videos = get_available_videos()
    monetizable_count = sum(1 for v in videos if v.get("duration", 0) >= 60.0)

    return web.json_response({
        "status": current_job["status"],
        "job_message": current_job["message"],
        "accounts_count": len(accounts),
        "total_channels": total_channels,
        "videos_count": len(videos),
        "monetizable_count": monetizable_count,
        "logs": job_logs[-50:],
    })


async def handle_get_config(request: web.Request) -> web.Response:
    return web.json_response(load_config())


async def handle_save_config(request: web.Request) -> web.Response:
    data = await request.json()
    cfg = load_config()
    if "api_keys" in data and isinstance(data["api_keys"], dict):
        cfg.setdefault("api_keys", {}).update(data["api_keys"])
    if "gemini_api_key" in data:
        cfg.setdefault("api_keys", {})["gemini_api_key"] = str(data["gemini_api_key"]).strip()
    if "pexels_api_key" in data:
        cfg.setdefault("api_keys", {})["pexels_api_key"] = str(data["pexels_api_key"]).strip()
    if "publishing" in data and isinstance(data["publishing"], dict):
        cfg.setdefault("publishing", {}).update(data["publishing"])
    if "videos_per_channel_per_day" in data:
        cfg.setdefault("publishing", {})["videos_per_channel_per_day"] = int(data["videos_per_channel_per_day"])
    if "lookahead_days" in data:
        cfg.setdefault("publishing", {})["lookahead_days"] = int(data["lookahead_days"])
    save_config(cfg)
    append_log("Configuration saved successfully.")
    return web.json_response({"status": "success", "config": load_config()})


async def handle_get_accounts(request: web.Request) -> web.Response:
    return web.json_response({"accounts": account_mgr.load_all()})


async def handle_save_account(request: web.Request) -> web.Response:
    data = await request.json()
    acc = account_mgr.add_or_update(
        name=data.get("name", ""),
        token=data.get("token", ""),
        team_id=data.get("team_id", ""),
        account_id=data.get("id"),
    )
    append_log(f"Saved Planly account: {acc['name']}")
    return web.json_response({"status": "success", "account": acc})


async def handle_delete_account(request: web.Request) -> web.Response:
    data = await request.json()
    account_id = data.get("id", "")
    ok = account_mgr.delete_account(account_id)
    if ok:
        append_log(f"Deleted account {account_id}")
    return web.json_response({"status": "success" if ok else "not_found"})


async def handle_test_account(request: web.Request) -> web.Response:
    data = await request.json()
    token = data.get("token", "").strip()
    team_id = data.get("team_id", "").strip()

    client = PlanlyClient(token, team_id)
    ok, msg, channels = client.test_connection()
    return web.json_response({
        "ok": ok,
        "message": msg,
        "channels": channels,
    })


async def handle_sync_channels(request: web.Request) -> web.Response:
    data = await request.json()
    account_id = data.get("id", "")
    acc = account_mgr.get_account(account_id)
    if not acc:
        return web.json_response({"ok": False, "message": "Account not found"}, status=404)

    client = PlanlyClient(acc["token"], acc["team_id"])
    ok, msg, channels = client.test_connection()
    if ok:
        account_mgr.update_channels(account_id, channels)
        append_log(f"Synced {len(channels)} channels for {acc['name']}.")
        return web.json_response({"ok": True, "message": msg, "channels": channels})
    return web.json_response({"ok": False, "message": msg}, status=400)


async def handle_get_videos(request: web.Request) -> web.Response:
    videos = get_available_videos()
    return web.json_response({"videos": [
        {
            "filename": v["filename"],
            "title": v["title"],
            "description": v["description"],
            "duration": round(v["duration"], 1),
            "monetizable": v["monetizable"],
            "hashtags": v["hashtags"],
        }
        for v in videos
    ]})


async def handle_stream_video(request: web.Request) -> web.FileResponse:
    filename = request.match_info.get("filename", "")
    target = OUTPUT_DIR / filename
    if not target.exists():
        raise web.HTTPNotFound(text="Video file not found.")
    return web.FileResponse(target)


async def handle_open_output_folder(request: web.Request) -> web.Response:
    """Opens local D:\auto make money\output folder in Windows File Explorer."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(OUTPUT_DIR))
        return web.json_response({"ok": True, "path": str(OUTPUT_DIR)})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


def _run_generation_task(count: int, query: str, direct_url: str):
    global current_job
    current_job = {"status": "generating", "message": f"Starting generation of {count} video(s)..."}
    cfg = load_config()

    try:
        append_log(f"=== BẮT ĐẦU TẠO {count} VIDEO (>60s) ===")
        clips = []
        if direct_url:
            append_log(f"Downloading clip from URL: {direct_url}")
            meta = scraper.download_clip(direct_url)
            if meta:
                clips.append(meta)
        else:
            append_log(f"Searching and downloading clips for query: '{query}'...")
            clips = scraper.fetch_batch_for_generation(count=count, query=query)

        if not clips:
            append_log("❌ Không tìm thấy clip nào hoặc tải về thất bại.")
            current_job = {"status": "error", "message": "Failed to fetch clips."}
            return

        rendered_count = 0
        for i, clip in enumerate(clips, 1):
            append_log(f"[{i}/{len(clips)}] Đang viết kịch bản phân tích (>60s) cho: {clip['title'][:50]}...")
            script = generate_script(clip, language=cfg.get("generation", {}).get("language", "en"))
            append_log(f"  -> Hook Banner: '{script.get('hook_banner')}'")
            append_log(f"  -> Scenes: {len(script.get('scenes', []))} phân cảnh kịch tính")

            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_id = clip.get("id") or f"clip_{i}"
            out_file = OUTPUT_DIR / f"viral_{stamp}_{clean_id}.mp4"

            append_log(f"  -> Bắt đầu Render video 9:16 (Tách giọng, giữ SFX, ghép kịch bản, phụ đề Karaoke)...")
            render_monetizable_video(
                source_clips=[clip],
                script=script,
                out_file=out_file,
                cfg=cfg.get("generation", {}),
                session_used_ids=session_used_clips,
                log=append_log
            )
            rendered_count += 1
            append_log(f"  ✅ ĐÃ XONG: {out_file.name}")

        append_log(f"🎉 HOÀN THÀNH TẤT CẢ: Đã tạo {rendered_count}/{len(clips)} video chất lượng cao!")
        current_job = {"status": "idle", "message": f"Successfully generated {rendered_count} video(s)."}
    except Exception as e:
        traceback.print_exc()
        append_log(f"❌ LỖI TRONG QUÁ TRÌNH TẠO VIDEO: {e}")
        current_job = {"status": "error", "message": str(e)}


async def handle_generate(request: web.Request) -> web.Response:
    if current_job["status"] == "generating":
        return web.json_response({"ok": False, "message": "A generation job is already running."}, status=409)

    data = await request.json()
    count = int(data.get("count", 1))
    query = data.get("query", "").strip() or None
    direct_url = data.get("url", "").strip()

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_generation_task, count, query, direct_url)
    return web.json_response({"ok": True, "message": "Video generation started in background."})


def _run_publishing_task(
    account_id: str,
    channel_ids: List[str],
    videos_per_channel: int,
    mode: str,
    dry_run: bool
):
    global current_job
    current_job = {"status": "publishing", "message": "Publishing videos to Planly..."}
    try:
        acc = account_mgr.get_account(account_id)
        if not acc:
            append_log(f"❌ Không tìm thấy tài khoản Planly ID {account_id}")
            current_job = {"status": "error", "message": "Account not found."}
            return

        client = PlanlyClient(acc["token"], acc["team_id"])
        channels = [c for c in acc.get("channels", []) if (not channel_ids or c["id"] in channel_ids)]
        if not channels:
            append_log("❌ Không có kênh nào được chọn.")
            current_job = {"status": "error", "message": "No channels found."}
            return

        videos = get_available_videos()
        if not videos:
            append_log("❌ Không có video nào trong thư mục output để đăng.")
            current_job = {"status": "error", "message": "No videos found."}
            return

        cfg = load_config()
        tz_offset = cfg.get("publishing", {}).get("timezone_offset", 7)

        append_log(f"=== BẮT ĐẦU ĐĂNG/LÊN LỊCH: {videos_per_channel} VIDEO/KÊNH/NGÀY ===")
        append_log(f"Tài khoản: {acc['name']} | Số kênh: {len(channels)} | Chế độ: {mode.upper()} | Mô phỏng: {dry_run}")

        res = schedule_channel_quota(
            client=client,
            channels=channels,
            videos=videos,
            videos_per_channel=videos_per_channel,
            mode=mode,
            tz_offset=tz_offset,
            dry_run=dry_run,
            log=append_log
        )
        append_log(f"🎉 Hoàn thành đặt lịch cho {res.get('count', 0)} bài đăng!")
        current_job = {"status": "idle", "message": f"Published {res.get('count', 0)} posts successfully."}
    except Exception as e:
        traceback.print_exc()
        append_log(f"❌ LỖI KHI ĐĂNG BÀI: {e}")
        current_job = {"status": "error", "message": str(e)}


async def handle_publish(request: web.Request) -> web.Response:
    if current_job["status"] == "publishing":
        return web.json_response({"ok": False, "message": "A publishing job is already in progress."}, status=409)

    data = await request.json()
    account_id = data.get("account_id", "")
    channel_ids = data.get("channel_ids", [])
    videos_per_channel = int(data.get("videos_per_channel", 3))
    mode = data.get("mode", "same_time")
    dry_run = bool(data.get("dry_run", False))

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_publishing_task, account_id, channel_ids, videos_per_channel, mode, dry_run)
    return web.json_response({"ok": True, "message": "Publishing process started in background."})


def _run_multi_angle_news_task(topic_data: Dict[str, Any], count: int, target_mode: str):
    global current_job
    current_job = {"status": "generating", "message": f"Creating {count} completely distinct viral videos..."}
    cfg = load_config()
    try:
        from core.trending_news import (
            fetch_diverse_viral_stories,
            generate_distinct_story_script,
            mark_topic_used
        )
        append_log(f"=== BẮT ĐẦU TẠO {count} VIDEO CHỦ ĐỀ HOÀN TOÀN KHÁC NHAU ===")
        append_log(f"Chế độ mục tiêu: {target_mode.upper()} ({'>60s kiếm tiền' if target_mode == 'monetized' else '<45s viral loop'})")

        stories = fetch_diverse_viral_stories(count=count)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        rendered = 0
        session_used_clips = set()

        for i, story in enumerate(stories, 1):
            append_log(f"[{i}/{len(stories)}] Chuẩn bị video #{i} [{story.get('category')}]: '{story.get('title')}'...")
            script = generate_distinct_story_script(story, target_mode=target_mode)
            append_log(f"  -> Giọng thoại: {script['voice_q']} & {script['voice_a']} (Tốc độ: {script['speed_factor']}x)")
            append_log(f"  -> Hook Banner: {script['hook_banner']}")

            clean_name = re.sub(r"[^\w]+", "_", script["topic"][:25]).strip("_")
            out_file = OUTPUT_DIR / f"news_{stamp}_story{i}_{clean_name}.mp4"

            render_monetizable_video(
                source_clips=[],
                script=script,
                out_file=out_file,
                cfg=cfg.get("generation", {}),
                session_used_ids=session_used_clips,
                log=append_log
            )
            mark_topic_used(story.get("title", ""))
            rendered += 1
            append_log(f"  ✅ ĐÃ XONG VIDEO #{i}: {out_file.name}")

        append_log(f"🎉 HOÀN THÀNH TẤT CẢ: Đã tạo {rendered} video hoàn toàn khác biệt từ 6 lĩnh vực!")
        current_job = {"status": "idle", "message": f"Generated {rendered} distinct stories successfully."}
    except Exception as e:
        traceback.print_exc()
        append_log(f"❌ LỖI KHI TẠO CÁC GÓC TIN TỨC: {e}")
        current_job = {"status": "error", "message": str(e)}


async def handle_get_trends(request: web.Request) -> web.Response:
    from core.trending_news import fetch_diverse_viral_stories
    stories = fetch_diverse_viral_stories(count=6)
    return web.json_response({"trends": stories, "news": stories})



async def handle_generate_news(request: web.Request) -> web.Response:
    if current_job["status"] == "generating":
        return web.json_response({"ok": False, "message": "A generation job is already running."}, status=409)

    data = await request.json()
    topic = data.get("topic") or {"title": "US Breaking Alert Today"}
    count = int(data.get("count", 3))
    target_mode = data.get("target_mode", "monetized")

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_multi_angle_news_task, topic, count, target_mode)
    return web.json_response({"ok": True, "message": "Multi-angle news generation started in background."})

async def handle_commentary_inspect(request: web.Request) -> web.Response:
    from core.video_commentary import download_or_load_source_video
    try:
        data = await request.json()
        url = data.get("url", "").strip()
        target_tier = data.get("target_tier", "growth")
        cut_start = float(data.get("cut_start", 0.0))
        cut_duration = float(data.get("cut_duration")) if data.get("cut_duration") else None

        if not url:
            return web.json_response({"ok": False, "message": "Vui lòng nhập link video hoặc đường dẫn file!"}, status=400)

        append_log(f"Đang kiểm tra và tải thông tin video nguồn: {url}...")
        video_data = download_or_load_source_video(
            source_input=url,
            target_tier=target_tier,
            cut_start=cut_start,
            cut_duration=cut_duration,
            log=append_log
        )
        append_log(f"✅ Video: {video_data.get('title')} ({video_data.get('duration', 0):.1f}s)")
        return web.json_response({"ok": True, "video": video_data})
    except Exception as e:
        traceback.print_exc()
        append_log(f"❌ Lỗi tải video: {e}")
        return web.json_response({"ok": False, "message": str(e)}, status=500)


async def handle_commentary_generate_script(request: web.Request) -> web.Response:
    from core.video_commentary import generate_commentary_script
    try:
        data = await request.json()
        video_info = data.get("video_info") or {}
        voice_q = data.get("voice_q", "en-US-BrianNeural")
        voice_a = data.get("voice_a", "en-US-ChristopherNeural")
        language = data.get("language", "en")

        append_log(f"Đang viết lời bình bám sát video: '{video_info.get('title', '')[:40]}' ({video_info.get('duration', 0):.1f}s)...")
        script = generate_commentary_script(
            video_info=video_info,
            voice_q=voice_q,
            voice_a=voice_a,
            language=language
        )
        append_log(f"✅ Kịch bản lời bình: Hook '{script.get('hook_banner')}', {len(script.get('scenes', []))} câu thoại bám cảnh!")
        return web.json_response({"ok": True, "script": script})
    except Exception as e:
        traceback.print_exc()
        append_log(f"❌ Lỗi tạo kịch bản: {e}")
        return web.json_response({"ok": False, "message": str(e)}, status=500)


def _run_commentary_render_task(
    video_info: Dict[str, Any],
    script: Dict[str, Any],
    auto_publish: bool,
    account_id: str,
    channel_ids: List[str]
):
    global current_job
    current_job = {"status": "generating", "message": f"Rendering commentary for {video_info.get('title', '')[:30]}..."}
    cfg = load_config()
    try:
        append_log(f"=== BẮT ĐẦU SẢN XUẤT COMMENTARY VIDEO ===")
        append_log(f"Video nguồn: {video_info.get('title', '')}")
        append_log(f"Thời lượng gốc: {video_info.get('duration', 0):.1f}s | Hook: '{script.get('hook_banner')}'")
        append_log(f"Số phân cảnh thoại: {len(script.get('scenes', []))}")

        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = re.sub(r"[^\w]+", "_", video_info.get("title", "commentary")[:25]).strip("_")
        out_file = OUTPUT_DIR / f"commentary_{stamp}_{clean_name}.mp4"

        render_monetizable_video(
            source_clips=[video_info],
            script=script,
            out_file=out_file,
            cfg=cfg.get("generation", {}),
            log=append_log
        )

        append_log(f"✅ RENDER COMMENTARY THÀNH CÔNG: {out_file.name}")

        if auto_publish and account_id and channel_ids:
            append_log(f"=== BẮT ĐẦU ĐĂNG/LÊN LỊCH PLANLY CHO {len(channel_ids)} KÊNH ===")
            acc = account_mgr.get_account(account_id)
            if acc:
                client = PlanlyClient(acc["token"], acc["team_id"])
                channels = [c for c in acc.get("channels", []) if c["id"] in channel_ids]
                rendered_videos = get_available_videos()
                target_video = next((v for v in rendered_videos if v["filename"] == out_file.name), None)
                if target_video and channels:
                    tz_offset = cfg.get("publishing", {}).get("timezone_offset", 7)
                    res = schedule_channel_quota(
                        client=client,
                        channels=channels,
                        videos=[target_video],
                        videos_per_channel=1,
                        mode="same_time",
                        tz_offset=tz_offset,
                        dry_run=False,
                        log=append_log
                    )
                    append_log(f"🎉 Đã lên lịch Planly thành công: {res.get('count', 0)} bài đăng!")

        current_job = {"status": "idle", "message": f"Successfully finished commentary for {out_file.name}."}
    except Exception as e:
        traceback.print_exc()
        append_log(f"❌ LỖI KHI SẢN XUẤT COMMENTARY: {e}")
        current_job = {"status": "error", "message": str(e)}


async def handle_commentary_render(request: web.Request) -> web.Response:
    if current_job["status"] in ("generating", "publishing"):
        return web.json_response({"ok": False, "message": "Một tiến trình khác đang chạy, vui lòng đợi!"}, status=409)

    data = await request.json()
    video_info = data.get("video_info") or {}
    script = data.get("script") or {}
    auto_publish = bool(data.get("auto_publish", False))
    account_id = data.get("account_id", "")
    channel_ids = data.get("channel_ids", [])

    if not video_info or not video_info.get("video_path"):
        return web.json_response({"ok": False, "message": "Thông tin video không hợp lệ!"}, status=400)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_commentary_render_task, video_info, script, auto_publish, account_id, channel_ids)
    return web.json_response({"ok": True, "message": "Bắt đầu render video commentary trong background."})


def _run_sample_story_task():
    global current_job
    current_job = {"status": "generating", "message": "Dang san xuat video ky an mau (>60s)..."}
    try:
        from core.crime_story_database import get_next_crime_story
        from core.story_engine import render_crime_story_video
        story = get_next_crime_story()
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_id = re.sub(r"[^\w]+", "_", story.get("id", "crime_story"))
        out_file = OUTPUT_DIR / f"sample_{stamp}_{clean_id}.mp4"
        append_log(f"🎬 Bat dau dung video mau ky an: '{story.get('case_name')}' (>60s)...")
        render_crime_story_video(story, out_file, log=append_log)
        append_log(f"✅ DA XONG VIDEO MAU: {out_file.name}")
        current_job = {"status": "idle", "message": f"Rendered sample: {out_file.name}", "sample_video": out_file.name}
    except Exception as e:
        traceback.print_exc()
        append_log(f"❌ Loi dung video mau: {e}")
        current_job = {"status": "error", "message": str(e)}


async def handle_render_sample_story(request: web.Request) -> web.Response:
    if current_job["status"] == "generating":
        return web.json_response({"ok": False, "message": "Dang co tien trinh render video chay."}, status=409)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_sample_story_task)
    return web.json_response({"ok": True, "message": "Bat dau san xuat video ky an mau trong nen."})


async def handle_toggle_channel_tier(request: web.Request) -> web.Response:
    """Toggle a channel between 'monetized' (>60s) and 'growth' (<45s)."""
    data = await request.json()
    channel_id = data.get("channel_id", "")
    new_tier = data.get("tier")
    tier = account_mgr.toggle_channel_tier(channel_id, new_tier)
    append_log(f"Toggled channel {channel_id} to tier: {tier}")
    return web.json_response({"ok": True, "tier": tier})


# ==================== WORKER CONTROL ====================

WORKER_LOCK_FILE = DATA_DIR / "worker.lock"
WORKER_STOP_FILE = DATA_DIR / "worker.stop"
WORKER_LOG_FILE = ROOT_DIR / "logs" / "background_worker.log"


def _get_worker_pid() -> int | None:
    """Read PID from worker lock file and verify it is alive."""
    if not WORKER_LOCK_FILE.exists():
        return None
    try:
        pid = int(WORKER_LOCK_FILE.read_text().strip())
        if pid <= 0:
            return None
        # Check if process is alive on Windows
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        if str(pid) in result.stdout:
            return pid
    except Exception:
        pass
    return None


async def handle_worker_status(request: web.Request) -> web.Response:
    """Get background worker status."""
    pid = _get_worker_pid()
    running = pid is not None

    # Read last N lines from worker log
    last_lines = []
    if WORKER_LOG_FILE.exists():
        try:
            lines = WORKER_LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            last_lines = lines[-30:]
        except Exception:
            pass

    return web.json_response({
        "running": running,
        "pid": pid,
        "stop_requested": WORKER_STOP_FILE.exists(),
        "last_logs": last_lines,
    })


async def handle_worker_start(request: web.Request) -> web.Response:
    """Start background worker as a detached subprocess."""
    pid = _get_worker_pid()
    if pid:
        return web.json_response({"ok": False, "message": f"Worker đã đang chạy (PID {pid})"})

    # Clear stop signal if present
    if WORKER_STOP_FILE.exists():
        try:
            WORKER_STOP_FILE.unlink()
        except Exception:
            pass

    worker_script = ROOT_DIR / "core" / "background_worker.py"
    python_exe = Path(os.sys.executable)

    try:
        proc = subprocess.Popen(
            [str(python_exe), str(worker_script)],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        )
        append_log(f"Worker started with PID {proc.pid}")
        return web.json_response({"ok": True, "pid": proc.pid, "message": f"Worker đã khởi động (PID {proc.pid})"})
    except Exception as e:
        append_log(f"Failed to start worker: {e}")
        return web.json_response({"ok": False, "message": f"Không thể khởi động worker: {e}"}, status=500)


async def handle_worker_stop(request: web.Request) -> web.Response:
    """Stop background worker by writing stop signal file."""
    pid = _get_worker_pid()
    if not pid:
        return web.json_response({"ok": False, "message": "Worker không đang chạy."})

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        WORKER_STOP_FILE.write_text("stop", encoding="utf-8")
        append_log(f"Stop signal sent to worker PID {pid}")
        return web.json_response({"ok": True, "message": f"Đã gửi tín hiệu dừng cho worker (PID {pid}). Worker sẽ dừng sau khi hoàn thành video hiện tại."})
    except Exception as e:
        return web.json_response({"ok": False, "message": str(e)}, status=500)


# ==================== PLANLY CALENDAR ====================

async def handle_planly_calendar(request: web.Request) -> web.Response:
    """Get Planly calendar: video count per channel per date."""
    accounts = account_mgr.load_all()
    if not accounts:
        return web.json_response({"ok": False, "calendar": {}, "channels": [], "message": "Không có tài khoản Planly."})

    acc = accounts[0]
    channels = acc.get("channels", [])
    try:
        client = PlanlyClient(acc["token"], acc["team_id"])
        groups = client.list_scheduled_groups()
    except Exception as e:
        return web.json_response({"ok": False, "message": str(e), "calendar": {}, "channels": []}, status=500)

    tz_vn = dt.timezone(dt.timedelta(hours=7))
    # Build calendar: {channel_id: {date_str: count}}
    calendar: Dict[str, Dict[str, int]] = {}
    total_posts = 0
    all_dates = set()

    for g in groups:
        publish_on = g.get("publishOn")
        if not publish_on:
            continue
        try:
            clean_iso = publish_on.replace("Z", "+00:00")
            dt_utc = dt.datetime.fromisoformat(clean_iso)
            dt_local = dt_utc.astimezone(tz_vn)
            date_str = dt_local.strftime("%Y-%m-%d")
        except Exception:
            date_str = publish_on[:10]
        all_dates.add(date_str)

        for s in (g.get("schedules") or []):
            ch_id = s.get("channelId") or (s.get("channel") or {}).get("id")
            if not ch_id:
                continue
            if ch_id not in calendar:
                calendar[ch_id] = {}
            calendar[ch_id][date_str] = calendar[ch_id].get(date_str, 0) + 1
            total_posts += 1

    channel_info = [{"id": c["id"], "name": c.get("name", c["id"])} for c in channels]
    sorted_dates = sorted(all_dates)

    return web.json_response({
        "ok": True,
        "calendar": calendar,
        "channels": channel_info,
        "dates": sorted_dates,
        "total_posts": total_posts,
    })


async def handle_planly_purge(request: web.Request) -> web.Response:
    """Purge all scheduled posts from Planly."""
    accounts = account_mgr.load_all()
    if not accounts:
        return web.json_response({"ok": False, "message": "Không có tài khoản Planly."})

    acc = accounts[0]
    try:
        client = PlanlyClient(acc["token"], acc["team_id"])
        deleted = client.clear_all_scheduled_posts(log=append_log)
        append_log(f"Purged {deleted} scheduled posts from Planly calendar.")
        return web.json_response({"ok": True, "deleted": deleted, "message": f"Đã xóa {deleted} bài đăng đã xếp lịch."})
    except Exception as e:
        return web.json_response({"ok": False, "message": str(e)}, status=500)


# ==================== WORKER LOG TAIL ====================

async def handle_worker_logs(request: web.Request) -> web.Response:
    """Return last N lines of background_worker.log."""
    n = int(request.query.get("n", 80))
    lines = []
    if WORKER_LOG_FILE.exists():
        try:
            all_lines = WORKER_LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            lines = all_lines[-n:]
        except Exception:
            pass
    return web.json_response({"lines": lines})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/status", handle_get_status)
    app.router.add_get("/api/config", handle_get_config)
    app.router.add_post("/api/config", handle_save_config)
    app.router.add_get("/api/accounts", handle_get_accounts)
    app.router.add_post("/api/accounts/save", handle_save_account)
    app.router.add_post("/api/accounts/delete", handle_delete_account)
    app.router.add_post("/api/accounts/test", handle_test_account)
    app.router.add_post("/api/accounts/sync", handle_sync_channels)
    app.router.add_post("/api/channels/toggle_tier", handle_toggle_channel_tier)
    app.router.add_get("/api/news/trends", handle_get_trends)
    app.router.add_post("/api/news/generate", handle_generate_news)
    app.router.add_get("/api/videos", handle_get_videos)
    app.router.add_get("/api/video/{filename}", handle_stream_video)
    app.router.add_post("/api/open-output-folder", handle_open_output_folder)
    app.router.add_post("/api/generate", handle_generate)
    app.router.add_post("/api/publish", handle_publish)
    app.router.add_post("/api/commentary/inspect", handle_commentary_inspect)
    app.router.add_post("/api/commentary/generate_script", handle_commentary_generate_script)
    app.router.add_post("/api/commentary/render", handle_commentary_render)
    app.router.add_post("/api/story/render_sample", handle_render_sample_story)
    # Worker Control
    app.router.add_get("/api/worker/status", handle_worker_status)
    app.router.add_post("/api/worker/start", handle_worker_start)
    app.router.add_post("/api/worker/stop", handle_worker_stop)
    app.router.add_get("/api/worker/logs", handle_worker_logs)
    # Planly Calendar
    app.router.add_get("/api/planly/calendar", handle_planly_calendar)
    app.router.add_post("/api/planly/purge", handle_planly_purge)
    return app


def run_server(host: str = "127.0.0.1", port: int = 8888) -> None:
    app = create_app()
    print(f"============================================================")
    print(f"🚀 AUTO MAKE MONEY DASHBOARD RUNNING AT: http://{host}:{port}")
    print(f"============================================================")
    web.run_app(app, host=host, port=port)
