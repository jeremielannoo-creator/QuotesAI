"""
Agent — Formate l'article pour chaque plateforme sociale.
Pas d'API externe : le texte Drive est utilisé directement.

  - Instagram / TikTok : tronqué à 2 200 caractères
  - Facebook           : texte complet + lien blog
  - Reel script        : 3 premières phrases (superposition vidéo)
"""
import re

HASHTAGS_DEFAULT = (
    "#bookstagram #lecture #livres #critique #litterature "
    "#booklover #bookreview #reading #books #bibliophile "
    "#lecturedumoment #livresfrancais #bookstagramfr "
    "#thejourneyfava #avasjourney"
)


def generate_social_posts(article: dict) -> dict:
    """Formate l'article pour chaque plateforme sans API externe."""
    body = article["body"]

    return {
        "instagram_caption": _truncate(body, 2000),
        "hashtags":          HASHTAGS_DEFAULT,
        "reel_script":       _first_sentences(body, 3),
        "tiktok_script":     _truncate(body, 2200),
        "facebook_post":     body + "\n\nL'article complet est sur le blog → [LIEN]",
    }


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _first_sentences(text: str, n: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:n])
