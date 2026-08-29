"""Subtitulos ASS estilo TikTok: grupos de 2-4 palabras con la palabra activa resaltada."""
from pathlib import Path

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,7,4,5,90,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(seconds):
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _clean(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")").strip()


def _chunk(words, size):
    return [words[i:i + size] for i in range(0, len(words), size)]


def build_ass(timeline, cfg, out_path):
    # La misma fuente de la verdad que el render: si no, el .ass quedaria armado
    # para un lienzo distinto al del video y todos los subtitulos saldrian
    # descuadrados.
    from .render import _dims

    w, h, _fps = _dims(cfg)
    # El tamano esta pensado para 1080 de ancho, asi que escala con el lienzo.
    size = int(round(int(cfg.get("font_size", 92)) * w / 1080))
    font = cfg.get("font", "Arial Black")
    per = max(1, int(cfg.get("words_per_caption", 3)))
    hi = cfg.get("highlight_color", "&H0033E5FF&")
    # y = 58% de la altura -> algo abajo del centro, zona segura de TikTok
    pos_y = int(h * 0.58)
    pos_x = w // 2

    # Los grupos se arman DENTRO de cada escena. Si se agrupan sobre la lista
    # entera, el final de una frase se pega con el inicio de la siguiente y sale
    # un grupo sin sentido ("el canal / Dias despues" -> "el canal Dias").
    chunks = []
    for sc in timeline:
        words = [wd for wd in sc["words"] if _clean(wd["text"])]
        chunks += _chunk(words, per)

    events = []
    for chunk in chunks:
        for i, word in enumerate(chunk):
            start = word["start"]
            end = (min(chunk[i + 1]["start"], word["end"] + 0.6)
                   if i + 1 < len(chunk) else word["end"] + 0.28)
            rendered = []
            for j, other in enumerate(chunk):
                txt = _clean(other["text"])
                if j == i:
                    rendered.append(
                        f"{{\\c{hi}\\fscx112\\fscy112}}{txt}"
                        f"{{\\c&H00FFFFFF&\\fscx100\\fscy100}}"
                    )
                else:
                    rendered.append(txt)
            events.append([start, end, " ".join(rendered)])

    # Dos lineas encimadas en la misma posicion se ven como texto borroso ilegible.
    # Recorto cada linea justo antes de que empiece la siguiente.
    events.sort(key=lambda e: e[0])
    for cur, nxt in zip(events, events[1:]):
        cur[1] = min(cur[1], nxt[0])
    events = [e for e in events if e[1] - e[0] >= 0.04]

    tags = f"{{\\an5\\pos({pos_x},{pos_y})\\bord7\\shad4}}"
    lines = [HEADER.format(w=w, h=h, font=font, size=size)]
    lines += [f"Dialogue: 0,{_ts(s)},{_ts(e)},Main,,0,0,0,,{tags}{body}"
              for s, e, body in events]

    out_path = Path(out_path)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
