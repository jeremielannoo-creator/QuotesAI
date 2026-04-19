"""
utils/text_overlay.py — Génère une image RGBA avec la citation superposée
Style inspiré de @tylerwayneglass : fond cinématique visible, texte centré haut,
gradient léger en vignette (pas un écran noir), typographie épurée.

Sélection de police :
  - Bebas Neue       → Nietzsche, Marc Aurèle (puissance, urgence)
  - Playfair Display → Platon, Socrate, Schopenhauer (élégance, mélancolie)
  - Montserrat       → Épictète, Sénèque et autres (clarté, modernité)
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, FONTS_DIR, TEMP_DIR,
    SYSTEM_FONT_BOLD, SYSTEM_FONT_LIGHT,
)

# ── Chemins des polices ────────────────────────────────────────────────────────
F = lambda name: os.path.join(FONTS_DIR, name)

MONTSERRAT_BOLD  = F("Montserrat-ExtraBold.ttf")
MONTSERRAT_LIGHT = F("Montserrat-Light.ttf")
PLAYFAIR_ITALIC  = F("PlayfairDisplay-Italic.ttf")
PLAYFAIR_REGULAR = F("PlayfairDisplay-Regular.ttf")
BEBAS            = F("BebasNeue-Regular.ttf")

# ── Règles de sélection de police ─────────────────────────────────────────────
WARRIOR_AUTHORS = {"Friedrich Nietzsche", "Marc Aurèle", "Épictète"}
POETIC_AUTHORS  = {
    "Socrate", "Platon", "Arthur Schopenhauer",
    "Søren Kierkegaard", "Ralph Waldo Emerson",
    "Johann Wolfgang von Goethe", "John Lennon",
}

# ── Auteurs affichés comme "anonymes" ─────────────────────────────────────────
ANONYMOUS_AUTHORS = {"", "anonyme", "anonymous", "inconnu", "unknown", "none"}

# ── Palette ───────────────────────────────────────────────────────────────────
COLOR_WHITE      = (255, 255, 255, 250)
COLOR_WHITE_DIM  = (220, 215, 205, 200)   # légèrement chaud
COLOR_SHADOW     = (0,   0,   0,   120)   # ombre plus douce
COLOR_ACCENT     = (255, 210, 120, 200)   # or chaud
COLOR_TRANSPARENT= (0,   0,   0,   0)


def create_overlay(quote: str, author: str, mood: str = "calm") -> str:
    """
    Crée une image PNG transparente (1080×1920) avec la citation.

    Args:
        quote:  Texte de la citation (sans guillemets)
        author: Nom de l'auteur (vide ou "anonyme" → non affiché)
        mood:   calm | energetic | melancholic | triumphant | contemplative

    Returns:
        Chemin du fichier PNG généré dans TEMP_DIR
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

    img  = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), COLOR_TRANSPARENT)
    _draw_gradient(img, mood)
    draw = ImageDraw.Draw(img)

    # ── Sélection du style de police ──────────────────────────────────────────
    style          = _get_style(author, mood)
    f_main, f_auth = _load_fonts(style, len(quote))

    # Bebas Neue s'écrit en majuscules
    display_quote = quote.upper() if style == "bebas" else f'« {quote} »'

    # ── Layout centré-haut (style cinématique Tyler Glass) ────────────────────
    # Zone de texte : 15 % – 78 % de la hauteur → texte visible sur la vidéo
    area_top    = int(VIDEO_HEIGHT * 0.15)
    area_bottom = int(VIDEO_HEIGHT * 0.78)
    area_height = area_bottom - area_top
    cx          = VIDEO_WIDTH // 2

    margin      = 140                      # marges latérales généreuses
    chars       = _chars_per_line(f_main, VIDEO_WIDTH - margin * 2)
    lines       = textwrap.wrap(display_quote, width=chars)
    line_h      = _line_height(f_main)
    show_author = author.strip().lower() not in ANONYMOUS_AUTHORS
    deco_gap    = 24

    total_h = len(lines) * line_h
    if show_author:
        total_h += deco_gap * 2 + _line_height(f_auth)

    # Centrage vertical dans la zone, légèrement décalé vers le haut
    start_y = area_top + (area_height - total_h) // 2 - int(area_height * 0.05)

    # ── Citation ──────────────────────────────────────────────────────────────
    for i, line in enumerate(lines):
        _draw_shadowed(draw, (cx, start_y + i * line_h), line, f_main)

    # ── Ligne déco + auteur ───────────────────────────────────────────────────
    if show_author:
        deco_y = start_y + len(lines) * line_h + deco_gap
        # Ligne décorative fine, couleur or chaud
        draw.line(
            [(cx - 70, deco_y), (cx + 70, deco_y)],
            fill=COLOR_ACCENT, width=1,
        )
        _draw_shadowed(
            draw,
            (cx, deco_y + deco_gap),
            f"— {author} —",
            f_auth,
            color=COLOR_WHITE_DIM,
        )

    out = os.path.join(TEMP_DIR, "overlay.png")
    img.save(out, "PNG")
    return out


# ── Fonctions internes ────────────────────────────────────────────────────────

def _get_style(author: str, mood: str) -> str:
    if author in WARRIOR_AUTHORS or mood in ("triumphant", "energetic"):
        return "bebas"
    if author in POETIC_AUTHORS or mood in ("melancholic", "contemplative"):
        return "playfair"
    return "montserrat"


def _load_fonts(style: str, qlen: int):
    # Taille principale selon longueur de la citation
    if qlen < 60:
        sq = 80
    elif qlen < 120:
        sq = 66
    elif qlen < 200:
        sq = 54
    else:
        sq = 44

    sa = max(sq - 22, 28)

    if style == "bebas":
        sq = int(sq * 1.18)   # Bebas Neue bénéficie d'une taille plus grande
        return _load(BEBAS, SYSTEM_FONT_BOLD, sq), _load(MONTSERRAT_LIGHT, SYSTEM_FONT_LIGHT, sa)
    elif style == "playfair":
        return _load(PLAYFAIR_ITALIC, SYSTEM_FONT_BOLD, sq), _load(PLAYFAIR_REGULAR, SYSTEM_FONT_LIGHT, sa)
    else:
        return _load(MONTSERRAT_BOLD, SYSTEM_FONT_BOLD, sq), _load(MONTSERRAT_LIGHT, SYSTEM_FONT_LIGHT, sa)


def _load(path: str, fallback: str, size: int) -> ImageFont.FreeTypeFont:
    for p in (path, fallback):
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_gradient(img: Image.Image, mood: str = "calm"):
    """
    Vignette cinématique légère (style Tyler Glass) :
    - Bas de l'image : assombri progressivement (lisibilité du texte)
    - Haut de l'image : léger voile pour l'auteur si nécessaire
    - Centre : vidéo pleinement visible
    La teinte varie légèrement selon le mood.
    """
    ov = Image.new("RGBA", img.size, COLOR_TRANSPARENT)
    d  = ImageDraw.Draw(ov)

    w, h = img.size

    # Couleur de base du voile selon le mood
    if mood in ("triumphant", "energetic"):
        tint = (10, 5, 0)     # très légèrement chaud
    elif mood in ("melancholic",):
        tint = (0, 2, 8)      # très légèrement froid
    else:
        tint = (0, 0, 0)      # neutre

    # ── Vignette bas (55 % → bas) ────────────────────────────────────────────
    start_bottom = int(h * 0.50)
    for y in range(start_bottom, h):
        progress = (y - start_bottom) / (h - start_bottom)
        alpha    = int(175 * min(progress ** 0.9, 1.0))
        d.line([(0, y), (w, y)], fill=(*tint, alpha))

    # ── Vignette haut (0 → 20 %) ─────────────────────────────────────────────
    end_top = int(h * 0.20)
    for y in range(0, end_top):
        progress = 1.0 - (y / end_top)
        alpha    = int(90 * min(progress ** 1.2, 1.0))
        d.line([(0, y), (w, y)], fill=(*tint, alpha))

    img.alpha_composite(ov)


def _draw_shadowed(draw, xy, text, font, color=COLOR_WHITE, offset=2):
    """Texte avec ombre portée douce (offset réduit pour un look plus fin)."""
    x, y = xy
    # Ombre légèrement diffuse (2 passes décalées)
    draw.text((x + offset + 1, y + offset + 1), text, font=font, fill=(0, 0, 0, 80), anchor="mm")
    draw.text((x + offset,     y + offset),     text, font=font, fill=COLOR_SHADOW,  anchor="mm")
    draw.text(xy,                                text, font=font, fill=color,          anchor="mm")


def _line_height(font) -> int:
    bbox = font.getbbox("Ag")
    return int((bbox[3] - bbox[1]) * 1.45)


def _chars_per_line(font, max_w: int) -> int:
    avg = font.getlength("abcdefghijklmnopqrstuvwxyz ") / 27
    return max(10, int(max_w / avg))
