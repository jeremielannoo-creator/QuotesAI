"""
agents/agent_carousel.py — Génération des slides carousel Instagram.

Crée une série d'images JPEG 1080×1350 (portrait 4:5) :
  Slide 1   : couverture du livre + titre + auteur
  Slides 2…N: texte de la critique découpé en chunks
  Slide N+1 : hashtags (fond sombre)

Max 10 slides (limite Instagram).
"""
import os
import re
import textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from config import VIDEO_WIDTH, FONTS_DIR, TEMP_DIR, SYSTEM_FONT_BOLD, SYSTEM_FONT_LIGHT

# ── Dimensions carousel (portrait 4:5) ────────────────────────────────────────
W, H = 1080, 1350

# ── Couleurs ──────────────────────────────────────────────────────────────────
BG_DARK   = (18, 18, 24)       # fond quasi-noir légèrement bleuté
GOLD      = (210, 170, 100)    # or chaud
WHITE     = (245, 240, 230)    # blanc cassé chaud
WHITE_DIM = (180, 170, 155)    # blanc atténué pour le secondaire
SHADOW    = (0, 0, 0, 140)

# ── Polices ───────────────────────────────────────────────────────────────────
F = lambda name: os.path.join(FONTS_DIR, name)

def _load(path: str, fallback: str, size: int) -> ImageFont.FreeTypeFont:
    for p in (path, fallback):
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()

def _fonts():
    title  = _load(F("PlayfairDisplay-Italic.ttf"),  SYSTEM_FONT_BOLD,  58)
    body   = _load(F("PlayfairDisplay-Regular.ttf"), SYSTEM_FONT_BOLD,  46)
    small  = _load(F("Montserrat-Light.ttf"),         SYSTEM_FONT_LIGHT, 32)
    tiny   = _load(F("Montserrat-Light.ttf"),         SYSTEM_FONT_LIGHT, 26)
    return title, body, small, tiny


# ── Découpage du texte ────────────────────────────────────────────────────────

def _split_chunks(text: str, max_chars: int = 280) -> list[str]:
    """Découpe le texte en chunks à la frontière de phrase."""
    sentences = re.split(r'(?<=[.!?…])\s+', text.strip())
    chunks, buf = [], ""
    for s in sentences:
        candidate = (buf + " " + s).strip() if buf else s
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            buf = s[:max_chars]  # force-coupe si phrase trop longue
    if buf:
        chunks.append(buf)
    return chunks


# ── Helpers de dessin ─────────────────────────────────────────────────────────

def _draw_text_centered(draw, text, font, y_center, color=WHITE, max_w=820):
    """Dessine du texte wrappé centré horizontalement et verticalement à y_center."""
    avg_char = font.getlength("m")
    chars_per_line = max(10, int(max_w / avg_char))
    lines = textwrap.wrap(text, width=chars_per_line)

    bbox = font.getbbox("Ag")
    line_h = int((bbox[3] - bbox[1]) * 1.5)
    total_h = len(lines) * line_h
    y = y_center - total_h // 2
    cx = W // 2

    for line in lines:
        # Ombre
        draw.text((cx + 2, y + 2), line, font=font, fill=(0, 0, 0, 100), anchor="mt")
        draw.text((cx, y), line, font=font, fill=color, anchor="mt")
        y += line_h

    return y   # retourne la position après le dernier ligne


def _draw_divider(draw, y, width=80):
    """Ligne décorative dorée centrée."""
    cx = W // 2
    draw.line([(cx - width, y), (cx + width, y)], fill=GOLD, width=1)


# ── Création des slides ───────────────────────────────────────────────────────

def _slide_cover(cover_path: str, title: str, author: str) -> Image.Image:
    """Slide 1 : couverture floue en fond + titre + auteur."""
    _, body_font, small_font, _ = _fonts()

    # Fond : couverture étirée + flou + assombrissement
    try:
        bg = Image.open(cover_path).convert("RGB")
    except Exception:
        bg = Image.new("RGB", (W, H), BG_DARK)

    bg = bg.resize((W, H), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=18))

    # Voile sombre pour lisibilité
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 165))
    img = bg.convert("RGBA")
    img.alpha_composite(veil)

    # Couverture originale centrée et visible (pas floue)
    try:
        cover = Image.open(cover_path).convert("RGBA")
        cw, ch = cover.size
        scale = min(400 / cw, 500 / ch)
        cover = cover.resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)
        cx = (W - cover.width) // 2
        img.paste(cover, (cx, 180), cover)
    except Exception:
        pass

    draw = ImageDraw.Draw(img)

    # Titre
    y_after = _draw_text_centered(draw, title, body_font, y_center=820, color=WHITE)
    _draw_divider(draw, y_after + 20)
    # Auteur
    _draw_text_centered(draw, author, small_font, y_center=y_after + 70, color=GOLD)

    return img.convert("RGB")


def _slide_text(chunk: str, title: str, page: int, total: int) -> Image.Image:
    """Slides de texte : fond sombre + texte de la critique."""
    _, body_font, small_font, tiny_font = _fonts()

    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Bordure décorative intérieure subtile
    draw.rectangle([30, 30, W - 30, H - 30], outline=(*GOLD, 60), width=1)

    # Titre du livre en haut (petit)
    draw.text((W // 2, 90), title.upper(), font=tiny_font, fill=GOLD, anchor="mm")
    _draw_divider(draw, 125, width=50)

    # Texte principal centré verticalement
    _draw_text_centered(draw, f'« {chunk} »', body_font, y_center=680, color=WHITE)

    # Numéro de page en bas
    draw.text((W // 2, H - 80), f"{page} / {total}", font=tiny_font, fill=WHITE_DIM, anchor="mm")

    return img


def _slide_hashtags(hashtags: str, title: str) -> Image.Image:
    """Slide finale : hashtags sur fond sombre."""
    _, _, small_font, tiny_font = _fonts()

    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    draw.rectangle([30, 30, W - 30, H - 30], outline=(*GOLD, 60), width=1)

    draw.text((W // 2, 200), "The Journey of Ava", font=small_font, fill=GOLD, anchor="mm")
    _draw_divider(draw, 250, width=60)
    draw.text((W // 2, 310), title, font=tiny_font, fill=WHITE_DIM, anchor="mm")

    # Hashtags wrappés
    tags = hashtags.replace("#", "\n#").strip()
    y = 430
    for tag in tags.split("\n"):
        tag = tag.strip()
        if tag:
            draw.text((W // 2, y), tag, font=tiny_font, fill=WHITE_DIM, anchor="mm")
            y += 38

    return img


# ── Point d'entrée ────────────────────────────────────────────────────────────

def create_carousel(article: dict, cover_path: str | None, hashtags: str) -> list[str]:
    """
    Crée toutes les slides du carousel et retourne leurs chemins JPEG.

    Args:
        article:    dict avec title, author, body
        cover_path: chemin de la couverture (peut être None)
        hashtags:   chaîne de hashtags

    Returns:
        Liste de chemins JPEG (max 10)
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

    title  = article["title"]
    author = article["author"]
    body   = article["body"]

    chunks = _split_chunks(body, max_chars=280)
    # Max 8 slides de texte (+ 1 cover + 1 hashtags = 10 max)
    chunks = chunks[:8]
    total_text = len(chunks)

    paths = []

    # Slide 1 : couverture
    if cover_path and os.path.exists(cover_path):
        img = _slide_cover(cover_path, title, author)
    else:
        img = _slide_text(f"{title}\n{author}", title, 1, total_text + 2)
    p = os.path.join(TEMP_DIR, "carousel_00.jpg")
    img.save(p, "JPEG", quality=92)
    paths.append(p)
    print(f"  [carousel] Slide 1/cover créée")

    # Slides texte
    for i, chunk in enumerate(chunks, start=1):
        img = _slide_text(chunk, title, i, total_text)
        p   = os.path.join(TEMP_DIR, f"carousel_{i:02d}.jpg")
        img.save(p, "JPEG", quality=92)
        paths.append(p)
        print(f"  [carousel] Slide {i + 1}/{len(chunks) + 2}")

    # Slide hashtags
    img = _slide_hashtags(hashtags, title)
    p   = os.path.join(TEMP_DIR, "carousel_99.jpg")
    img.save(p, "JPEG", quality=92)
    paths.append(p)
    print(f"  [carousel] Slide hashtags créée — total : {len(paths)} slides")

    return paths
