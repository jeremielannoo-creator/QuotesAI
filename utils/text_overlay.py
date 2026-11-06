"""
utils/text_overlay.py — Génère la SÉQUENCE d'overlays d'une vidéo citation.

Au lieu d'un PNG figé affiché 30 s, on produit une suite d'images cumulatives :
    frame 0 : dégradé seul (la vidéo respire une demi-seconde)
    frame 1 : ligne 1
    frame 2 : lignes 1–2
    …
    frame N : toutes les lignes + auteur
agent_render les enchaîne en fenêtres temporelles → le texte se révèle
ligne par ligne au lieu d'apparaître d'un bloc.

Trois gabarits alternent pour casser la monotonie du feed :
    center — citation centrée, gros corps (le gabarit historique)
    lower  — tiers inférieur, aligné à gauche, lecture rapide
    banner — bloc centré haut encadré de deux filets or

Sélection de police :
  Bebas Neue       → Nietzsche, Marc Aurèle (puissance, urgence)
  Playfair Display → Platon, Socrate, Schopenhauer (élégance, mélancolie)
  Montserrat       → Épictète, Sénèque et autres (clarté, modernité)
"""
import os
import random
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import (
    FONTS_DIR, SYSTEM_FONT_BOLD, SYSTEM_FONT_LIGHT, TEMP_DIR,
    VIDEO_HEIGHT, VIDEO_WIDTH,
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

ANONYMOUS_AUTHORS = {"", "anonyme", "anonymous", "inconnu", "unknown", "none"}

# ── Palette ───────────────────────────────────────────────────────────────────
COLOR_WHITE       = (255, 255, 255, 250)
COLOR_WHITE_DIM   = (220, 215, 205, 200)
COLOR_SHADOW      = (0, 0, 0, 120)
COLOR_ACCENT      = (255, 210, 120, 200)
COLOR_TRANSPARENT = (0, 0, 0, 0)

TEMPLATES = ("center", "lower", "banner")
BRAND     = "The Journey of Ava"


def create_overlay_sequence(
    quote: str,
    author: str,
    mood: str = "calm",
    template: str | None = None,
) -> dict:
    """
    Crée la séquence de PNG (1080×1920) révélant la citation ligne par ligne.

    Returns:
        {"frames": [chemins PNG, du plus vide au plus complet],
         "template": nom du gabarit, "lines": nombre de lignes de texte}
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    template = template or random.choice(TEMPLATES)

    style          = _get_style(author, mood)
    f_main, f_auth = _load_fonts(style, len(quote), template)

    layout = _layout(template)
    chars  = _chars_per_line(f_main, layout["text_width"])

    if style == "bebas":
        lines = textwrap.wrap(quote.upper(), width=chars)
    else:
        # Les guillemets sont ajoutés APRÈS le découpage : sinon textwrap
        # renvoie régulièrement un « » » seul sur la dernière ligne.
        lines = textwrap.wrap(quote, width=chars - 2)
        lines[0]  = f"« {lines[0]}"
        lines[-1] = f"{lines[-1]} »"
    line_h      = _line_height(f_main)
    show_author = author.strip().lower() not in ANONYMOUS_AUTHORS
    deco_gap    = 24

    total_h = len(lines) * line_h
    if show_author:
        total_h += deco_gap * 2 + _line_height(f_auth)
    start_y = layout["anchor_y"](total_h)

    frames = []
    for n_visible in range(len(lines) + 1):
        with_author = show_author and n_visible == len(lines)
        img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), COLOR_TRANSPARENT)
        _draw_gradient(img, mood, template)
        # Voile constant sur toutes les frames : il ne « pope » pas à
        # l'apparition d'une ligne, et garantit le contraste même sur un
        # fond clair (ciel, brume, sable).
        _draw_scrim(img, start_y - line_h, start_y + total_h)
        draw = ImageDraw.Draw(img)

        if template == "banner" and n_visible:
            _rule(draw, start_y - 46, 200, layout["x"], layout["align"])

        for i in range(n_visible):
            _draw_shadowed(
                draw, (layout["x"], start_y + i * line_h),
                lines[i], f_main, align=layout["align"],
            )

        if with_author:
            deco_y = start_y + len(lines) * line_h + deco_gap
            _rule(draw, deco_y, 200 if template == "banner" else 70,
                  layout["x"], layout["align"])
            _draw_shadowed(
                draw, (layout["x"], deco_y + deco_gap),
                f"— {author} —", f_auth,
                color=COLOR_WHITE_DIM, align=layout["align"],
            )

        _draw_brand(draw)

        path = os.path.join(TEMP_DIR, f"overlay_{n_visible:02d}.png")
        img.save(path, "PNG")
        frames.append(path)

    return {"frames": frames, "template": template, "lines": len(lines)}


# ── Gabarits ──────────────────────────────────────────────────────────────────

def _layout(template: str) -> dict:
    """Position du bloc de texte, largeur utile et alignement selon le gabarit."""
    if template == "lower":
        margin = 110
        return {
            "x":          margin,
            "align":      "left",
            "text_width": VIDEO_WIDTH - margin - 90,
            # Bloc calé dans le tiers inférieur, au-dessus de la zone d'UI
            "anchor_y":   lambda h: int(VIDEO_HEIGHT * 0.74) - h,
        }
    if template == "banner":
        margin = 160
        return {
            "x":          VIDEO_WIDTH // 2,
            "align":      "center",
            "text_width": VIDEO_WIDTH - margin * 2,
            "anchor_y":   lambda h: int(VIDEO_HEIGHT * 0.30),
        }
    # center (défaut)
    margin = 140
    return {
        "x":          VIDEO_WIDTH // 2,
        "align":      "center",
        "text_width": VIDEO_WIDTH - margin * 2,
        "anchor_y":   lambda h: int(VIDEO_HEIGHT * 0.15)
                                + (int(VIDEO_HEIGHT * 0.63) - h) // 2
                                - int(VIDEO_HEIGHT * 0.03),
    }


# ── Fonctions internes ────────────────────────────────────────────────────────

def _get_style(author: str, mood: str) -> str:
    if author in WARRIOR_AUTHORS or mood in ("triumphant", "energetic"):
        return "bebas"
    if author in POETIC_AUTHORS or mood in ("melancholic", "contemplative"):
        return "playfair"
    return "montserrat"


def _load_fonts(style: str, qlen: int, template: str):
    if qlen < 60:
        sq = 80
    elif qlen < 120:
        sq = 66
    elif qlen < 200:
        sq = 54
    else:
        sq = 44

    if template == "lower":      # aligné à gauche : corps plus compact
        sq = int(sq * 0.86)
    sa = max(sq - 22, 28)

    if style == "bebas":
        sq = int(sq * 1.18)
        return _load(BEBAS, SYSTEM_FONT_BOLD, sq), _load(MONTSERRAT_LIGHT, SYSTEM_FONT_LIGHT, sa)
    if style == "playfair":
        return _load(PLAYFAIR_ITALIC, SYSTEM_FONT_BOLD, sq), _load(PLAYFAIR_REGULAR, SYSTEM_FONT_LIGHT, sa)
    return _load(MONTSERRAT_BOLD, SYSTEM_FONT_BOLD, sq), _load(MONTSERRAT_LIGHT, SYSTEM_FONT_LIGHT, sa)


def _load(path: str, fallback: str, size: int) -> ImageFont.FreeTypeFont:
    for p in (path, fallback):
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_gradient(img: Image.Image, mood: str = "calm", template: str = "center"):
    """
    Vignette cinématique : la vidéo reste visible, seules les zones de texte
    sont assombries. Le gabarit 'lower' assombrit plus bas et plus fort.
    """
    ov = Image.new("RGBA", img.size, COLOR_TRANSPARENT)
    d  = ImageDraw.Draw(ov)
    w, h = img.size

    if mood in ("triumphant", "energetic"):
        tint = (10, 5, 0)
    elif mood == "melancholic":
        tint = (0, 2, 8)
    else:
        tint = (0, 0, 0)

    if template == "lower":
        bottom_start, bottom_alpha, top_end, top_alpha = 0.42, 205, 0.12, 60
    elif template == "banner":
        bottom_start, bottom_alpha, top_end, top_alpha = 0.58, 150, 0.32, 130
    else:
        bottom_start, bottom_alpha, top_end, top_alpha = 0.50, 175, 0.20, 90

    start_bottom = int(h * bottom_start)
    for y in range(start_bottom, h):
        progress = (y - start_bottom) / (h - start_bottom)
        d.line([(0, y), (w, y)], fill=(*tint, int(bottom_alpha * min(progress ** 0.9, 1.0))))

    end_top = int(h * top_end)
    for y in range(0, end_top):
        progress = 1.0 - (y / end_top)
        d.line([(0, y), (w, y)], fill=(*tint, int(top_alpha * min(progress ** 1.2, 1.0))))

    img.alpha_composite(ov)


def _draw_scrim(img: Image.Image, top: int, bottom: int, strength: int = 120):
    """Bande sombre très floue derrière le bloc de texte, pour le contraste."""
    pad  = 70
    band = Image.new("RGBA", img.size, COLOR_TRANSPARENT)
    ImageDraw.Draw(band).rectangle(
        [-60, top - pad, VIDEO_WIDTH + 60, bottom + pad], fill=(0, 0, 0, strength),
    )
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(55)))


def _rule(draw, y: int, half_width: int, x: int, align: str = "center"):
    """Filet décoratif or, aligné comme le texte qu'il accompagne."""
    x0 = x if align == "left" else x - half_width
    draw.line([(x0, y), (x0 + half_width * 2, y)], fill=COLOR_ACCENT, width=2)


def _draw_brand(draw):
    """Signature discrète en pied d'image — le compte devient reconnaissable."""
    font = _load(MONTSERRAT_LIGHT, SYSTEM_FONT_LIGHT, 26)
    draw.text(
        (VIDEO_WIDTH // 2, VIDEO_HEIGHT - 120), BRAND,
        font=font, fill=(235, 228, 215, 130), anchor="mm",
    )


def _draw_shadowed(draw, xy, text, font, color=COLOR_WHITE, offset=2, align="center"):
    """Texte avec ombre portée douce."""
    x, y = xy
    anchor = "lm" if align == "left" else "mm"
    draw.text((x + offset + 1, y + offset + 1), text, font=font, fill=(0, 0, 0, 80), anchor=anchor)
    draw.text((x + offset,     y + offset),     text, font=font, fill=COLOR_SHADOW,  anchor=anchor)
    draw.text(xy,                               text, font=font, fill=color,         anchor=anchor)


def _line_height(font) -> int:
    bbox = font.getbbox("Ag")
    return int((bbox[3] - bbox[1]) * 1.45)


def _chars_per_line(font, max_w: int) -> int:
    avg = font.getlength("abcdefghijklmnopqrstuvwxyz ") / 27
    return max(10, int(max_w / avg))
