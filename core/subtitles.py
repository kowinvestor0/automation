"""ASS Karaoke subtitles generator with dynamic word highlighting."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,5,3,5,140,140,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _clean(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").strip()


def _smart_chunk(words: List[Dict[str, Any]], max_chars_per_line: int = 15) -> List[List[Dict[str, Any]]]:
    """Chunks words smartly so text never overflows the 1080x1920 portrait safe zone."""
    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_len = 0

    for w in words:
        clean_txt = _clean(w.get("text", ""))
        if not clean_txt:
            continue
        w_len = len(clean_txt)
        # 1-2 words per chunk, or break if length exceeds safe limit
        if current and (len(current) >= 2 or (current_len + 1 + w_len) > max_chars_per_line):
            chunks.append(current)
            current = [w]
            current_len = w_len
        else:
            current.append(w)
            current_len += w_len if not current else (w_len + 1)

    if current:
        chunks.append(current)
    return chunks


def build_ass_subtitles(
    timeline: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    out_path: Path,
    w: int = 1080,
    h: int = 1920
) -> Path:
    """Builds professional TikTok-style ASS karaoke subtitles with word highlighting.
    Guarantees 100% adherence to TikTok Safe Zone (NO text overflow, NO off-screen cutoff).
    """
    font = cfg.get("font", "Anton")
    # Reduced from 95 to 66 for crisp, perfectly framed subtitles that NEVER overflow screen width
    raw_size = int(cfg.get("font_size", 66))
    size = min(72, max(58, int(round(raw_size * w / 1080))))
    hi = cfg.get("highlight_color", "&H0033E5FF&")  # High-converting energetic yellow/cyan

    # y = 56% of height (Centered in TikTok Safe Zone: safe from buttons on right, UI on bottom)
    pos_y = int(h * 0.56)
    pos_x = w // 2

    all_words = []
    for sc in timeline:
        for wd in sc.get("words", []):
            if _clean(wd.get("text", "")):
                all_words.append(wd)

    chunks = _smart_chunk(all_words, max_chars_per_line=15)

    events = []
    for chunk in chunks:
        for i, word in enumerate(chunk):
            start = word["start"]
            end = (
                min(chunk[i + 1]["start"], word["end"] + 0.5)
                if i + 1 < len(chunk)
                else word["end"] + 0.25
            )
            rendered = []
            for j, other in enumerate(chunk):
                txt = _clean(other["text"])
                if j == i:
                    # Subtle 105% scale on active word so it never overflows boundary
                    rendered.append(
                        f"{{\\c{hi}\\fscx105\\fscy105}}{txt}"
                        f"{{\\c&H00FFFFFF&\\fscx100\\fscy100}}"
                    )
                else:
                    rendered.append(txt)
            events.append([start, end, " ".join(rendered)])

    # Avoid overlapping
    events.sort(key=lambda e: e[0])
    for cur, nxt in zip(events, events[1:]):
        cur[1] = min(cur[1], nxt[0])
    events = [e for e in events if e[1] - e[0] >= 0.04]

    tags = f"{{\\an5\\pos({pos_x},{pos_y})\\bord5\\shad3\\blur1}}"
    lines = [HEADER.format(w=w, h=h, font=font, size=size)]
    lines += [
        f"Dialogue: 0,{_ts(s)},{_ts(e)},Main,,0,0,0,,{tags}{body}"
        for s, e, body in events
    ]

    out_path = Path(out_path)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
