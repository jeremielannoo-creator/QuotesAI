"""
config.py — Paramètres globaux chargés depuis .env
"""
import os
import platform
from dotenv import load_dotenv

load_dotenv()

# ── APIs ───────────────────────────────────────────────
ANTHROPIC_API_KEY       = os.getenv("ANTHROPIC_API_KEY", "")
PEXELS_API_KEY          = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY         = os.getenv("PIXABAY_API_KEY", "")

CLOUDINARY_CLOUD_NAME   = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY      = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET   = os.getenv("CLOUDINARY_API_SECRET", "")

INSTAGRAM_ACCESS_TOKEN  = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID       = os.getenv("INSTAGRAM_USER_ID", "")

TIKTOK_ACCESS_TOKEN     = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_OPEN_ID          = os.getenv("TIKTOK_OPEN_ID", "")

# ── Vidéo ──────────────────────────────────────────────
VIDEO_WIDTH    = 1080          # Format portrait Instagram/TikTok
VIDEO_HEIGHT   = 1920
VIDEO_DURATION = 30            # Durée en secondes (max 60 pour TikTok)

# ── Dossiers ───────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
TEMP_DIR    = os.path.join(BASE_DIR, "temp")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MUSIC_DIR   = os.path.join(ASSETS_DIR, "music")
FONTS_DIR   = os.path.join(ASSETS_DIR, "fonts")

# ── Polices ────────────────────────────────────────────
# Fallback sur Arial Bold Windows si les fichiers ne sont pas présents
FONT_BOLD   = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")
FONT_LIGHT  = os.path.join(FONTS_DIR, "Montserrat-Light.ttf")
FONT_ITALIC = os.path.join(FONTS_DIR, "Montserrat-Italic.ttf")

# Polices de secours selon le système (utilisées si les TTF du projet sont absents)
if platform.system() == "Windows":
    SYSTEM_FONT_BOLD  = r"C:\Windows\Fonts\arialbd.ttf"
    SYSTEM_FONT_LIGHT = r"C:\Windows\Fonts\arial.ttf"
else:
    # Linux (GitHub Actions, Ubuntu…)
    SYSTEM_FONT_BOLD  = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    SYSTEM_FONT_LIGHT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
