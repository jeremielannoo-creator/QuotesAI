"""
config.py — Paramètres globaux chargés depuis .env
"""
import os
import platform
from dotenv import load_dotenv

load_dotenv()

# ── APIs ───────────────────────────────────────────────
ANTHROPIC_API_KEY        = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY           = os.getenv("GEMINI_API_KEY", "")
DRIVE_GAS_URL            = os.getenv("DRIVE_GAS_URL", "")
HASHNODE_TOKEN           = os.getenv("HASHNODE_TOKEN", "")
HASHNODE_PUBLICATION_ID  = os.getenv("HASHNODE_PUBLICATION_ID", "")

FACEBOOK_PAGE_ID         = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_PAGE_TOKEN      = os.getenv("FACEBOOK_PAGE_TOKEN", "")
PEXELS_API_KEY          = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY         = os.getenv("PIXABAY_API_KEY", "")

CLOUDINARY_CLOUD_NAME   = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY      = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET   = os.getenv("CLOUDINARY_API_SECRET", "")

INSTAGRAM_ACCESS_TOKEN  = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID       = os.getenv("INSTAGRAM_USER_ID", "")

TIKTOK_ACCESS_TOKEN     = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_OPEN_ID          = os.getenv("TIKTOK_OPEN_ID", "")
# Passe à "1" une fois l'app TikTok auditée → publication publique directe.
# Tant que "0" : la vidéo est envoyée en BROUILLON (inbox) — 1 tap pour publier.
TIKTOK_AUDITED          = os.getenv("TIKTOK_AUDITED", "0") == "1"

MAKE_TIKTOK_WEBHOOK_URL = os.getenv("MAKE_TIKTOK_WEBHOOK_URL", "")

# ── Génération de fonds par IA (text-to-video) ─────────
# Désactivé par défaut : les modèles text-to-video ne tournent pas sur un
# runner GitHub Actions (CPU seul). À 1, on passe par l'API HuggingFace
# Inference Providers — facturée au clip. Voir agents/agent_video_ai.py.
HF_TOKEN         = os.getenv("HF_TOKEN", "")
VIDEO_AI_ENABLED = os.getenv("VIDEO_AI_ENABLED", "0") == "1"
VIDEO_AI_MODEL   = os.getenv("VIDEO_AI_MODEL", "Wan-AI/Wan2.2-T2V-A14B")

# ── Vidéo ──────────────────────────────────────────────
VIDEO_WIDTH    = 1080          # Format portrait Instagram/TikTok
VIDEO_HEIGHT   = 1920
VIDEO_DURATION = 30            # Plafond en secondes — la durée réelle est
                               # calculée par agent_render selon le texte

# ── Dossiers ───────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
TEMP_DIR    = os.path.join(BASE_DIR, "temp")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MUSIC_DIR   = os.path.join(ASSETS_DIR, "music")
FONTS_DIR   = os.path.join(ASSETS_DIR, "fonts")
# Banque de clips générés par IA (Flow / HuggingFace), rangés par famille :
#   assets/backgrounds/water/, assets/backgrounds/urban/, …
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, "backgrounds")

# Photothèque du personnage. Les versions versionnées vivent sous assets/ :
# .gitignore exclut tous les .png/.jpg SAUF assets/**, donc Photos/ n'existe pas
# sur le runner GitHub Actions. Les dossiers Photos/ restent le fallback local.
PHOTOS_DIR      = os.path.join(BASE_DIR, "Photos")
AVA_REF_DIRS    = [os.path.join(ASSETS_DIR, "ava_reference"),
                   os.path.join(PHOTOS_DIR, "Portraits")]
TRAVEL_DIRS     = [os.path.join(ASSETS_DIR, "travel"),
                   os.path.join(PHOTOS_DIR, "Travel")]

# ── Photos du personnage Ava (génération d'images) ─────
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# Mention de transparence ajoutée aux publications montrant Ava.
# Ava est un personnage de fiction : la mention protège le compte (politique
# Meta sur les contenus générés par IA) et les règles de publicité FR/BE/NL/UK
# dès qu'une marque est citée. Vider la variable la retire — à tes risques.
AI_DISCLOSURE = os.getenv(
    "AI_DISCLOSURE",
    "Ava est un personnage de fiction, ses photos sont générées par IA.",
)

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
