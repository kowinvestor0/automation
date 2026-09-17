"""Vox-Style Motion Graphics & Breaking News Explainer Video Engine.
Generates high-retention 9:16 vertical videos featuring:
- Paper & newspaper clipping collage with realistic newsprint textures
- Dynamic animated canary yellow / crimson highlighter sweeps
- Hand-drawn sketchy red circles, underlines, and arrow callouts
- Technical blueprint grids & 2.5D Ken Burns push-in camera motion
- Bold kinetic typography and big data statistic cards
- Journalistic Foley sound design (paper rustle, marker squeak, whoosh transitions)
"""
from __future__ import annotations

import asyncio
import math
import os
import random
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core.paths import CACHE_DIR, FONTS_DIR, OUTPUT_DIR
from core.tts_engine import ffprobe_duration

# Style constants
VOX_YELLOW = (255, 230, 0)
VOX_YELLOW_HEX = "0xFFE600"
VOX_RED = (235, 45, 45)
VOX_SLATE = (18, 22, 28)
VOX_PAPER = (244, 240, 232)
VOX_PAPER_DARK = (226, 220, 208)
VOX_BLUEPRINT = (11, 19, 32)
VOX_GRID_LINE = (22, 38, 62)

FONT_ANTON = FONTS_DIR / "Anton-Regular.ttf"
FONT_GEORGIA = Path(r"C:\Windows\Fonts\georgia.ttf")
FONT_GEORGIA_BOLD = Path(r"C:\Windows\Fonts\georgiab.ttf")
FONT_ARIAL_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")
FONT_IMPACT = Path(r"C:\Windows\Fonts\impact.ttf")


def _get_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    except Exception:
        pass
    return ImageFont.load_default()


def create_paper_texture(width: int = 1080, height: int = 1920) -> Image.Image:
    """Procedurally generates a warm vintage newspaper background with subtle paper fibers."""
    img = Image.new("RGB", (width, height), VOX_PAPER)
    draw = ImageDraw.Draw(img)
    
    # Add subtle paper grain/noise
    random.seed(42)
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            variation = random.randint(-6, 6)
            r, g, b = VOX_PAPER
            c = (max(0, min(255, r + variation)),
                 max(0, min(255, g + variation)),
                 max(0, min(255, b + variation)))
            draw.rectangle([x, y, x + 3, y + 3], fill=c)

    # Subtle horizontal fold crease line
    fold_y = int(height * 0.45)
    draw.line([(0, fold_y), (width, fold_y)], fill=(210, 204, 192), width=3)
    draw.line([(0, fold_y + 3), (width, fold_y + 3)], fill=(255, 252, 246), width=2)
    return img


def create_blueprint_texture(width: int = 1080, height: int = 1920, grid_size: int = 48) -> Image.Image:
    """Generates a technical slate blueprint grid for schematics and data scenes."""
    img = Image.new("RGB", (width, height), VOX_BLUEPRINT)
    draw = ImageDraw.Draw(img)
    
    # Draw fine technical grid
    for x in range(0, width, grid_size):
        line_w = 2 if x % (grid_size * 4) == 0 else 1
        col = (30, 52, 85) if x % (grid_size * 4) == 0 else VOX_GRID_LINE
        draw.line([(x, 0), (x, height)], fill=col, width=line_w)
        
    for y in range(0, height, grid_size):
        line_w = 2 if y % (grid_size * 4) == 0 else 1
        col = (30, 52, 85) if y % (grid_size * 4) == 0 else VOX_GRID_LINE
        draw.line([(0, y), (width, y)], fill=col, width=line_w)

    return img


def draw_sketchy_circle(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int], color=VOX_RED, loops: int = 3):
    """Draws a multi-layered imperfect hand-drawn red circle/ellipse around key terms."""
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 + 16, (y1 - y0) / 2 + 12
    
    for l in range(loops):
        points = []
        for angle_deg in range(0, 375, 15):
            rad = math.radians(angle_deg)
            jitter_r = random.uniform(-4, 4)
            px = cx + (rx + jitter_r) * math.cos(rad)
            py = cy + (ry + jitter_r) * math.sin(rad)
            points.append((px, py))
        draw.line(points, fill=color, width=4, joint="curve")


def draw_sketchy_arrow(draw: ImageDraw.ImageDraw, start: Tuple[int, int], end: Tuple[int, int], color=VOX_RED):
    """Draws a hand-drawn marker arrow pointing to a key component."""
    sx, sy = start
    ex, ey = end
    draw.line([start, end], fill=color, width=6)
    
    # Arrowhead
    angle = math.atan2(ey - sy, ex - sx)
    head_len = 28
    a1 = angle + math.pi * 0.82
    a2 = angle - math.pi * 0.82
    p1 = (ex + head_len * math.cos(a1), ey + head_len * math.sin(a1))
    p2 = (ex + head_len * math.cos(a2), ey + head_len * math.sin(a2))
    draw.line([end, p1], fill=color, width=5)
    draw.line([end, p2], fill=color, width=5)


def render_scene_1_newspaper(
    title: str,
    source: str,
    date_str: str,
    highlight_text: str,
    out_base: Path,
    out_highlighted: Path
) -> Dict[str, Any]:
    """Renders Scene 1: Authentic Newspaper front-page collage with headline & highlight coordinates."""
    W, H = 1080, 1920
    img = create_paper_texture(W, H)
    draw = ImageDraw.Draw(img)

    margin_x = 54
    paper_top = 220
    paper_bottom = 1700
    
    # Drop shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rectangle([margin_x + 8, paper_top + 14, W - margin_x + 8, paper_bottom + 14], fill=(0, 0, 0, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    img.paste(shadow, (0, 0), shadow)

    # Newspaper clipping card
    card_bg = (252, 250, 245)
    draw.rectangle([margin_x, paper_top, W - margin_x, paper_bottom], fill=card_bg, outline=(180, 172, 160), width=2)

    # Top Masthead
    font_masthead = _get_font(FONT_GEORGIA_BOLD, 42)
    masthead_text = source.upper()
    mb_bbox = draw.textbbox((0, 0), masthead_text, font=font_masthead)
    mb_w = mb_bbox[2] - mb_bbox[0]
    draw.text(((W - mb_w) // 2, paper_top + 40), masthead_text, fill=(20, 20, 20), font=font_masthead)

    # Double rule below masthead
    y_rule = paper_top + 105
    draw.line([(margin_x + 24, y_rule), (W - margin_x - 24, y_rule)], fill=(30, 30, 30), width=3)
    draw.line([(margin_x + 24, y_rule + 6), (W - margin_x - 24, y_rule + 6)], fill=(30, 30, 30), width=1)

    # Date / Issue bar
    font_meta = _get_font(FONT_ARIAL_BOLD, 22)
    meta_text = f"{date_str.upper()}  •  EXCLUSIVE INVESTIGATION  •  VOL. XLVIII"
    draw.text((margin_x + 30, y_rule + 14), meta_text, fill=(90, 85, 80), font=font_meta)
    draw.line([(margin_x + 24, y_rule + 44), (W - margin_x - 24, y_rule + 44)], fill=(160, 155, 145), width=1)

    # Huge Main Headline
    font_head = _get_font(FONT_GEORGIA_BOLD, 68)
    words = title.upper().split()
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        tb = draw.textbbox((0, 0), test, font=font_head)
        if (tb[2] - tb[0]) <= (W - margin_x * 2 - 60):
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    y_text = y_rule + 75
    line_bboxes = []
    highlight_bbox = None

    for line in lines:
        tb = draw.textbbox((margin_x + 30, y_text), line, font=font_head)
        line_bboxes.append(tb)
        if highlight_text.upper() in line:
            w_before = line[:line.find(highlight_text.upper())]
            hb_start = margin_x + 30 + draw.textlength(w_before, font=font_head)
            hb_w = draw.textlength(highlight_text.upper(), font=font_head)
            highlight_bbox = (int(hb_start) - 8, int(y_text) - 4, int(hb_start + hb_w) + 8, int(y_text + 78))
        draw.text((margin_x + 30, y_text), line, fill=(15, 15, 15), font=font_head)
        y_text += 88

    draw.line([(margin_x + 24, y_text + 15), (W - margin_x - 24, y_text + 15)], fill=(200, 195, 185), width=2)

    # News Columns & Body layout
    y_body = y_text + 40
    col_w = (W - margin_x * 2 - 80) // 2
    # Column 1
    draw.rectangle([margin_x + 30, y_body, margin_x + 30 + col_w, y_body + 340], outline=(230, 226, 218), fill=(255, 255, 255))
    draw.text((margin_x + 45, y_body + 20), "BREAKTHROUGH REPORT", fill=(180, 50, 40), font=_get_font(FONT_ARIAL_BOLD, 22))
    
    cy = y_body + 65
    for _ in range(7):
        draw.line([(margin_x + 45, cy), (margin_x + 30 + col_w - 25, cy)], fill=(120, 115, 105), width=6)
        cy += 20
    for _ in range(5):
        draw.line([(margin_x + 45, cy), (margin_x + 30 + col_w - 60, cy)], fill=(160, 155, 145), width=4)
        cy += 18

    # Column 2: Photographic Cutout
    c2_x = margin_x + 40 + col_w
    draw.rectangle([c2_x, y_body, c2_x + col_w, y_body + 340], fill=(24, 30, 42), outline=(210, 205, 195), width=3)
    
    engine_center = (c2_x + col_w // 2, y_body + 160)
    draw.ellipse([engine_center[0] - 70, engine_center[1] - 70, engine_center[0] + 70, engine_center[1] + 70],
                 outline=(0, 230, 255), width=4)
    draw.ellipse([engine_center[0] - 40, engine_center[1] - 40, engine_center[0] + 40, engine_center[1] + 40],
                 fill=(0, 150, 255))
    draw.polygon([(engine_center[0] - 90, engine_center[1] - 35),
                  (engine_center[0] + 90, engine_center[1] - 15),
                  (engine_center[0] + 90, engine_center[1] + 15),
                  (engine_center[0] - 90, engine_center[1] + 35)],
                 fill=(40, 55, 80))
    draw.text((c2_x + 20, y_body + 295), "FIG 1.1: AIR-BREATHING THRUSTER", fill=(200, 220, 240), font=_get_font(FONT_ARIAL_BOLD, 17))

    # Masking tape on top of photo
    tape_w, tape_h = 110, 36
    draw.rectangle([c2_x + col_w // 2 - tape_w // 2, y_body - tape_h // 2,
                    c2_x + col_w // 2 + tape_w // 2, y_body + tape_h // 2],
                   fill=(235, 230, 205), outline=(205, 195, 165))

    # Big Stamp at bottom
    stamp_y = paper_bottom - 240
    draw.rectangle([margin_x + 50, stamp_y, margin_x + 460, stamp_y + 90], outline=VOX_RED, width=4)
    draw.text((margin_x + 75, stamp_y + 20), "OFFICIALLY VERIFIED", fill=VOX_RED, font=_get_font(FONT_ARIAL_BOLD, 36))

    img.save(out_base, quality=95)

    # Highlighted Image
    hl_img = img.copy()
    if highlight_bbox:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.rectangle(highlight_bbox, fill=(255, 230, 0, 180))
        hl_img.paste(Image.alpha_composite(hl_img.convert("RGBA"), overlay).convert("RGB"), (0, 0))
        
        hl_draw_red = ImageDraw.Draw(hl_img)
        draw_sketchy_circle(hl_draw_red, highlight_bbox, color=VOX_RED)

    hl_img.save(out_highlighted, quality=95)
    return {
        "highlight_bbox": highlight_bbox,
        "width": W,
        "height": H
    }


def render_scene_2_blueprint(
    stat_number: str,
    stat_label: str,
    diagram_title: str,
    arrow_label: str,
    out_path: Path
):
    """Renders Scene 2: Dark Technical Blueprint with glowing schematics and Big Vox Kinetic Data."""
    W, H = 1080, 1920
    img = create_blueprint_texture(W, H)
    draw = ImageDraw.Draw(img)

    # Top Category Tag
    font_tag = _get_font(FONT_ARIAL_BOLD, 28)
    draw.rectangle([70, 180, 560, 240], fill=VOX_YELLOW)
    draw.text((95, 192), "THE ENGINEERING BREAKTHROUGH", fill=(10, 10, 10), font=font_tag)

    # Schematic Diagram Box
    box_top = 340
    box_bot = 1120
    draw.rectangle([70, box_top, W - 70, box_bot], outline=(0, 200, 255), fill=(14, 26, 44), width=2)
    
    font_diag = _get_font(FONT_ARIAL_BOLD, 32)
    draw.text((105, box_top + 35), diagram_title.upper(), fill=(0, 235, 255), font=font_diag)
    draw.line([(105, box_top + 80), (W - 105, box_top + 80)], fill=(30, 65, 95), width=1)

    cx, cy = W // 2, (box_top + box_bot) // 2 + 30
    
    # Air intake cone (left)
    draw.polygon([(cx - 360, cy - 140), (cx - 160, cy - 80), (cx - 160, cy + 80), (cx - 360, cy + 140)],
                 fill=(22, 40, 68), outline=(0, 200, 255), width=3)
    for dy in (-70, -20, 30, 80):
        draw.line([(cx - 420, cy + dy), (cx - 240, cy + dy * 0.5)], fill=(0, 255, 220), width=3)
        draw.polygon([(cx - 230, cy + dy * 0.5), (cx - 250, cy + dy * 0.5 - 8), (cx - 250, cy + dy * 0.5 + 8)], fill=(0, 255, 220))

    # Compression Chamber (middle)
    draw.rectangle([cx - 160, cy - 90, cx + 80, cy + 90], fill=(28, 52, 88), outline=(0, 200, 255), width=3)
    for x_coil in range(cx - 140, cx + 70, 35):
        draw.ellipse([x_coil, cy - 75, x_coil + 24, cy + 75], outline=(255, 180, 0), width=3)

    # Plasma discharge nozzle (right)
    draw.polygon([(cx + 80, cy - 70), (cx + 280, cy - 130), (cx + 280, cy + 130), (cx + 80, cy + 70)],
                 fill=(22, 40, 68), outline=(0, 200, 255), width=3)
    draw.polygon([(cx + 100, cy - 50), (cx + 380, cy - 110), (cx + 420, cy), (cx + 380, cy + 110), (cx + 100, cy + 50)],
                 fill=(140, 40, 255), outline=(200, 100, 255), width=2)
    draw.ellipse([cx + 260, cy - 60, cx + 380, cy + 60], fill=(0, 240, 255))

    # Red Marker Arrow & Label
    draw_sketchy_arrow(draw, (cx - 300, box_bot - 110), (cx - 260, cy + 90), color=VOX_RED)
    draw.text((cx - 380, box_bot - 90), arrow_label.upper(), fill=VOX_RED, font=_get_font(FONT_ARIAL_BOLD, 30))

    # Big Vox Kinetic Data Card at Bottom
    card_y = 1200
    draw.rectangle([70, card_y, W - 70, card_y + 440], fill=(6, 11, 20), outline=VOX_YELLOW, width=4)
    
    font_stat = _get_font(FONT_IMPACT, 150)
    draw.text((115, card_y + 45), stat_number, fill=(255, 255, 255), font=font_stat)
    
    font_lbl = _get_font(FONT_ARIAL_BOLD, 46)
    draw.text((120, card_y + 240), stat_label.upper(), fill=VOX_YELLOW, font=font_lbl)
    
    font_sub = _get_font(FONT_ARIAL_BOLD, 26)
    draw.text((120, card_y + 320), "CONTINUOUS AIR-BREATHING ELECTRIC THRUSTER", fill=(170, 190, 215), font=font_sub)

    img.save(out_path, quality=95)


def render_scene_3_orbit(
    stat_number: str,
    stat_label: str,
    feature_text: str,
    out_path: Path
):
    """Renders Scene 3: Deep Space & Orbit Impact with High-Contrast Vox Typography."""
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), (8, 12, 18))
    draw = ImageDraw.Draw(img)

    # Earth Horizon Arc
    earth_center = (W // 2, H + 600)
    earth_r = 950
    draw.ellipse([earth_center[0] - earth_r, earth_center[1] - earth_r,
                  earth_center[0] + earth_r, earth_center[1] + earth_r],
                 fill=(16, 45, 95), outline=(0, 180, 255), width=6)
    draw.arc([earth_center[0] - earth_r - 20, earth_center[1] - earth_r - 20,
              earth_center[0] + earth_r + 20, earth_center[1] + earth_r + 20],
             start=190, end=350, fill=(0, 240, 255), width=8)

    # Low Earth Orbit Trajectory Line
    orbit_y = 1100
    for x in range(60, W - 60, 40):
        draw.line([(x, orbit_y), (x + 22, orbit_y)], fill=(255, 220, 0), width=4)
        
    sat_x = W // 2
    draw.rectangle([sat_x - 35, orbit_y - 20, sat_x + 35, orbit_y + 20], fill=(240, 240, 240))
    draw.rectangle([sat_x - 110, orbit_y - 12, sat_x - 45, orbit_y + 12], fill=(0, 120, 220), outline=(255, 255, 255), width=2)
    draw.rectangle([sat_x + 45, orbit_y - 12, sat_x + 110, orbit_y + 12], fill=(0, 120, 220), outline=(255, 255, 255), width=2)

    # Top Vox Question Banner
    draw.rectangle([70, 200, W - 70, 270], fill=VOX_RED)
    draw.text((95, 218), "WHY THIS CHANGES SPACE TRAVEL FOREVER", fill=(255, 255, 255), font=_get_font(FONT_ARIAL_BOLD, 30))

    font_main = _get_font(FONT_IMPACT, 108)
    draw.text((70, 330), "PERMANENT", fill=(255, 255, 255), font=font_main)
    draw.text((70, 440), "ORBIT", fill=VOX_YELLOW, font=font_main)

    font_sub = _get_font(FONT_ARIAL_BOLD, 42)
    draw.rectangle([70, 590, W - 70, 680], fill=(255, 230, 0))
    draw.text((95, 610), feature_text.upper(), fill=(10, 10, 10), font=font_sub)

    draw.rectangle([70, 740, 620, 850], fill=(18, 28, 44), outline=(0, 200, 255), width=3)
    draw.text((95, 760), stat_number, fill=(0, 240, 255), font=_get_font(FONT_IMPACT, 60))
    draw.text((95, 815), stat_label.upper(), fill=(200, 215, 230), font=_get_font(FONT_ARIAL_BOLD, 22))

    img.save(out_path, quality=95)


def render_scene_4_outro(
    hook_text: str,
    question_text: str,
    out_path: Path
):
    """Renders Scene 4: Punchy Vox Outro with Kinetic Question Callout."""
    W, H = 1080, 1920
    img = create_paper_texture(W, H)
    draw = ImageDraw.Draw(img)

    draw.rectangle([70, 360, W - 70, 1560], fill=(16, 20, 26), outline=(30, 35, 45), width=3)

    font_tag = _get_font(FONT_ARIAL_BOLD, 32)
    draw.rectangle([110, 440, 480, 505], fill=VOX_YELLOW)
    draw.text((130, 455), "FINAL TAKEAWAY", fill=(10, 10, 10), font=font_tag)

    font_hook = _get_font(FONT_IMPACT, 105)
    draw.text((110, 560), "THE JET ENGINE", fill=(255, 255, 255), font=font_hook)
    draw.text((110, 675), "OF OUTER", fill=(255, 255, 255), font=font_hook)
    draw.text((110, 790), "SPACE.", fill=VOX_YELLOW, font=font_hook)

    draw.line([(110, 950), (W - 110, 950)], fill=(50, 60, 75), width=2)

    font_q = _get_font(FONT_GEORGIA_BOLD, 46)
    words = question_text.split()
    lines = []
    curr = []
    for w in words:
        if len(" ".join(curr + [w])) > 22:
            lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        lines.append(" ".join(curr))

    qy = 900
    for l in lines:
        draw.text((110, qy), l, fill=(240, 240, 240), font=font_q)
        qy += 62

    draw.rectangle([110, 1340, W - 110, 1460], fill=VOX_YELLOW)
    draw.text((145, 1378), "DROP YOUR THOUGHTS BELOW 💬", fill=(10, 10, 10), font=_get_font(FONT_ARIAL_BOLD, 36))

    img.save(out_path, quality=95)


def generate_vox_news_script(news_story: Dict[str, Any]) -> Dict[str, Any]:
    """Autonomously writes a punchy, 4-scene Vox-style explainer script for a breaking news topic."""
    category = news_story.get("category", "Science & Technology")
    title = news_story.get("title", "Breaking Discovery")
    source = news_story.get("source", "Science Wire")
    desc = news_story.get("description", "")

    from core.config_manager import get_api_key, load_config
    import json
    import requests

    prompt = f"""You are an elite motion-graphics documentary writer for Vox and Johnny Harris.
Write a punchy, high-retention 4-scene Vox explainer about this breaking real-world news:
Category: {category}
Headline: {title}
Context: {desc}
Source: {source}

CRITICAL RULES:
1. Speak DIRECTLY to the viewer! Start Scene 1 immediately with the mind-blowing hook.
2. ABSOLUTELY G-RATED & SAFE: No violence, politics, or controversy.
3. Total duration: 4 scenes, 80-105 words total. Fast-paced, punchy delivery.
4. Strictly valid JSON format:
{{
  "title": "ALL CAPS 4-6 WORD PUNCHY HEADLINE",
  "source": "{source.upper()}",
  "highlight_text": "2-3 EXACT WORDS IN HEADLINE TO HIGHLIGHT",
  "stat_number": "BIG NUMBER (e.g. 75 dB, 0 LITERS, 40,000 YRS, 99.4%)",
  "stat_label": "ALL CAPS 3-4 WORD LABEL",
  "diagram_title": "ALL CAPS DIAGRAM TITLE",
  "arrow_label": "ALL CAPS 2-3 WORD ARROW POINTER",
  "feature_text": "ALL CAPS 3-4 WORD KEY FEATURE",
  "takeaway_title": "ALL CAPS 3-5 WORD PUNCHLINE",
  "discussion_question": "Engaging question for viewers to comment",
  "hashtags": ["#science", "#tech", "#news", "#vox", "#fyp"],
  "scenes": [
    {{"index": 0, "text": "Scene 1 dramatic hook opening with context..."}},
    {{"index": 1, "text": "Scene 2 mechanism or discovery explanation..."}},
    {{"index": 2, "text": "Scene 3 statistical impact and why it matters..."}},
    {{"index": 3, "text": "Scene 4 memorable conclusion with viewer question..."}}
  ]
}}"""

    key = get_api_key("gemini_api_key")
    preferred = os.environ.get("GEMINI_MODEL") or load_config().get("generation", {}).get("gemini_model", "gemini-3.1-flash-lite")
    models = list(dict.fromkeys([preferred, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]))

    if key and len(key) >= 20:
        for mod in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
                res = requests.post(url, json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }, timeout=15)
                if res.status_code == 200:
                    cand = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(cand)
                    if data.get("title") and data.get("scenes"):
                        return data
            except Exception as e:
                pass

    # OpenAI fallback
    from core.openai_fallback import generate_json as generate_openai_json
    data = generate_openai_json(prompt, purpose="vox news script")
    if data and data.get("title") and data.get("scenes"):
        return data

    # Safe fallback template
    return {
        "title": title[:40].upper(),
        "source": source.upper(),
        "highlight_text": "DISCOVERY",
        "stat_number": "100%",
        "stat_label": "OFFICIALLY CONFIRMED",
        "diagram_title": "RESEARCH & DISCOVERY DATA",
        "arrow_label": "KEY BREAKTHROUGH",
        "feature_text": "GLOBAL SCIENTIFIC IMPACT",
        "takeaway_title": "A TURNING POINT IN SCIENCE",
        "discussion_question": "What are your thoughts on this new breakthrough?",
        "hashtags": ["#news", "#science", "#discovery", "#technology", "#fyp"],
        "scenes": [
            {"index": 0, "text": f"Breaking science update from {source}. Researchers have confirmed a major breakthrough in {category}."},
            {"index": 1, "text": f"{title}. The new data completely transforms what experts previously believed was possible."},
            {"index": 2, "text": "Field teams and laboratories analyzing the measurements report unprecedented results across all key indicators."},
            {"index": 3, "text": "This discovery could reshape the entire field. What are your thoughts on this breakthrough? Let me know below."}
        ]
    }


def generate_vox_explainer_video(
    story_data: Dict[str, Any],
    out_video_path: Path,
    voice_name: str = "en-US-AndrewNeural"
) -> Path:
    """End-to-end Vox Explainer Video Synthesizer."""
    workdir = CACHE_DIR / f"vox_{int(time.time())}"
    workdir.mkdir(parents=True, exist_ok=True)

    title = story_data.get("title", "A New Scientific Discovery")
    source = story_data.get("source", "Science Review")
    scenes = story_data.get("scenes", [])

    print(f"[Vox Engine] Synthesizing speech for {len(scenes)} scenes with '{voice_name}'...")
    from core.tts_engine import synthesize_script
    voice_mp3, timeline = synthesize_script(
        scenes=scenes,
        voice_cfg={"voice": voice_name, "voice_rate": "+14%", "scene_gap": 0.12},
        workdir=workdir,
        log=print
    )

    total_duration = ffprobe_duration(voice_mp3)
    print(f"[Vox Engine] Total voice duration: {total_duration:.2f}s")

    # Extract dynamic scene fields
    highlight_text = story_data.get("highlight_text", "")
    if not highlight_text or highlight_text.upper() not in title.upper():
        words = title.split()
        highlight_text = " ".join(words[-2:]) if len(words) >= 2 else title

    stat_number = story_data.get("stat_number", "100%")
    stat_label = story_data.get("stat_label", "NEW BREAKTHROUGH")
    diagram_title = story_data.get("diagram_title", "TECHNICAL SCHEMATIC ANALYSIS")
    arrow_label = story_data.get("arrow_label", "KEY MECHANISM")
    feature_text = story_data.get("feature_text", "BREAKTHROUGH DISCOVERY")
    takeaway_title = story_data.get("takeaway_title", "THE FUTURE OF SCIENCE")
    discussion_question = story_data.get("discussion_question", "What do you think about this breakthrough? Let me know below!")

    # Render Visual Scene Assets
    sc1_base = workdir / "sc1_base.png"
    sc1_hl = workdir / "sc1_highlighted.png"
    sc1_info = render_scene_1_newspaper(
        title=title,
        source=source,
        date_str="SEP 2026",
        highlight_text=highlight_text,
        out_base=sc1_base,
        out_highlighted=sc1_hl
    )

    sc2_img = workdir / "sc2_blueprint.png"
    render_scene_2_blueprint(
        stat_number=stat_number,
        stat_label=stat_label,
        diagram_title=diagram_title,
        arrow_label=arrow_label,
        out_path=sc2_img
    )

    sc3_img = workdir / "sc3_orbit.png"
    render_scene_3_orbit(
        stat_number=stat_number,
        stat_label=stat_label,
        feature_text=feature_text,
        out_path=sc3_img
    )

    sc4_img = workdir / "sc4_outro.png"
    render_scene_4_outro(
        hook_text=takeaway_title,
        question_text=discussion_question,
        out_path=sc4_img
    )

    durs = [item.get("duration", 6.0) for item in timeline]
    while len(durs) < 4:
        durs.append(6.0)

    clip_paths = []

    # Clip 1: Newspaper with animated highlighter reveal
    c1_mp4 = workdir / "clip_01.mp4"
    d1 = durs[0]
    hl_box = sc1_info.get("highlight_bbox") or (100, 400, 500, 500)
    hx0, hy0, hx1, hy1 = hl_box
    hw = hx1 - hx0
    hh = hy1 - hy0
    
    c1_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", f"{d1}", "-i", str(sc1_base),
        "-vf", (
            f"zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)':y='ih*0.35-(ih*0.35/zoom)':d={int(d1*30)}:s=1080x1920:fps=30,"
            f"drawbox=x={hx0}:y={hy0}:w='if(lt(t,0.8),0,min({hw}, (t-0.8)/1.2*{hw}))':h={hh}:color={VOX_YELLOW_HEX}@0.65:t=fill,"
            f"drawbox=x={hx0-10}:y={hy0-8}:w='if(lt(t,2.0),0,{hw+20})':h='if(lt(t,2.0),0,{hh+16})':color=0xEB2D2D@0.9:t=4"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{d1}",
        str(c1_mp4)
    ]
    subprocess.run(c1_cmd, check=True)
    clip_paths.append(c1_mp4)

    # Clip 2: Blueprint with push-in
    c2_mp4 = workdir / "clip_02.mp4"
    d2 = durs[1]
    c2_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", f"{d2}", "-i", str(sc2_img),
        "-vf", f"zoompan=z='min(zoom+0.0010,1.18)':x='iw/2-(iw/zoom/2)':y='ih*0.5-(ih*0.5/zoom)':d={int(d2*30)}:s=1080x1920:fps=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{d2}",
        str(c2_mp4)
    ]
    subprocess.run(c2_cmd, check=True)
    clip_paths.append(c2_mp4)

    # Clip 3: Orbit with camera drift
    c3_mp4 = workdir / "clip_03.mp4"
    d3 = durs[2]
    c3_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", f"{d3}", "-i", str(sc3_img),
        "-vf", f"zoompan=z='min(zoom+0.0008,1.14)':x='iw/2-(iw/zoom/2)':y='ih*0.4-(ih*0.4/zoom)':d={int(d3*30)}:s=1080x1920:fps=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{d3}",
        str(c3_mp4)
    ]
    subprocess.run(c3_cmd, check=True)
    clip_paths.append(c3_mp4)

    # Clip 4: Outro
    c4_mp4 = workdir / "clip_04.mp4"
    d4 = durs[3]
    c4_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", f"{d4}", "-i", str(sc4_img),
        "-vf", f"zoompan=z='min(zoom+0.0006,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(d4*30)}:s=1080x1920:fps=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{d4}",
        str(c4_mp4)
    ]
    subprocess.run(c4_cmd, check=True)
    clip_paths.append(c4_mp4)

    # Concatenate clips
    concat_list = workdir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve().as_posix()}'\n")

    raw_video = workdir / "raw_montage.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        str(raw_video)
    ], check=True)

    # Foley SFX
    sfx_wav = workdir / "procedural_sfx.wav"
    foley_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "anoisesrc=d=0.5:c=pink:r=44100,bandpass=f=2400:w=1100,volume=0.35",
        "-f", "lavfi", "-i", "anoisesrc=d=1.2:c=white:r=44100,bandpass=f=4200:w=700,volume=0.22",
        "-f", "lavfi", "-i", f"sine=f=65:d={total_duration+1.0},volume=0.08",
        "-filter_complex", (
            f"[0:a]adelay=100|100[a_paper];"
            f"[1:a]adelay=800|800[a_marker];"
            f"[2:a]volume=0.12[a_drone];"
            f"[a_paper][a_marker][a_drone]amix=inputs=3:duration=first:dropout_transition=2[sfx_out]"
        ),
        "-map", "[sfx_out]",
        "-t", f"{total_duration}",
        str(sfx_wav)
    ]
    subprocess.run(foley_cmd, check=True)

    # Background Music Track
    from core.audio_processor import get_background_music
    bg_music = get_background_music(total_duration, workdir)

    # Subtitles ASS generation
    from core.subtitles import build_ass_subtitles
    ass_sub = workdir / "vox_captions.ass"
    build_ass_subtitles(
        timeline=timeline,
        cfg={"font": "Anton", "font_size": 70, "highlight_color": "&H0000E6FF&"},
        out_path=ass_sub
    )

    # Final Assembly: Video + Subtitles + Voice + Ducked Background Music + Foley SFX
    clean_ass = str(ass_sub).replace("\\", "/").replace(":", r"\:")
    final_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(raw_video),
        "-i", str(voice_mp3),
        "-i", str(bg_music),
        "-i", str(sfx_wav),
        "-filter_complex", (
            f"[0:v]ass='{clean_ass}'[v_sub];"
            "[1:a]volume=1.35,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,asplit=2[voice_sc][voice];"
            "[2:a]volume=0.32,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music];"
            "[3:a]volume=0.75,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[sfx];"
            "[music][voice_sc]sidechaincompress=threshold=0.10:ratio=4:attack=15:release=320[ducked_music];"
            "[voice][ducked_music][sfx]amix=inputs=3:duration=first:dropout_transition=2[a_final]"
        ),
        "-map", "[v_sub]",
        "-map", "[a_final]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-t", f"{total_duration}",
        str(out_video_path)
    ]
    subprocess.run(final_cmd, check=True)
    print(f"[Vox Engine] Video rendered successfully: {out_video_path}")
    return out_video_path
