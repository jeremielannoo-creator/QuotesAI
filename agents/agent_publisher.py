"""
Agent 5 — Publication sur Instagram (Reels) et TikTok
Instagram : Meta Graph API v21.0 — nécessite une URL vidéo publique (Cloudinary)
TikTok    : Content Posting API v2 — FILE_UPLOAD (upload direct du fichier)
"""
import os
import time
import requests
from config import (
    INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID,
    TIKTOK_ACCESS_TOKEN, TIKTOK_OPEN_ID,
    FACEBOOK_PAGE_ID, FACEBOOK_PAGE_TOKEN,
)

_IG_BASE   = "https://graph.facebook.com/v21.0"
_TIKTOK_BASE = "https://open.tiktokapis.com/v2"


# ══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM
# ══════════════════════════════════════════════════════════════════════════════

def publish_instagram_carousel(image_urls: list[str], caption: str) -> str:
    """
    Publie un carousel Instagram (jusqu'à 10 images).

    Flux :
      1. Créer un conteneur par image (is_carousel_item=true)
      2. Créer le conteneur carousel (children=[...])
      3. Publier

    Args:
        image_urls: liste d'URLs publiques Cloudinary (max 10)
        caption:    texte complet de la publication

    Returns:
        ID du carousel publié
    """
    if not image_urls:
        raise ValueError("Aucune image pour le carousel")

    # ── Étape 1 : conteneur par image ────────────────────────────────────────
    child_ids = []
    for i, url in enumerate(image_urls[:10], 1):
        print(f"  [instagram] Conteneur slide {i}/{min(len(image_urls), 10)}…")
        resp = requests.post(
            f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media",
            data={
                "image_url":        url,
                "is_carousel_item": "true",
                "access_token":     INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Instagram slide {i} : {resp.status_code} — {resp.json()}")
        child_ids.append(resp.json()["id"])

    # ── Étape 2 : conteneur carousel ─────────────────────────────────────────
    print("  [instagram] Création du conteneur carousel…")
    resp = requests.post(
        f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media",
        data={
            "media_type":   "CAROUSEL",
            "children":     ",".join(child_ids),
            "caption":      caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Instagram carousel : {resp.status_code} — {resp.json()}")
    carousel_id = resp.json()["id"]

    # ── Étape 3 : publier ────────────────────────────────────────────────────
    print("  [instagram] Publication du carousel…")
    resp = requests.post(
        f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media_publish",
        data={
            "creation_id":  carousel_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    media_id = resp.json()["id"]
    print(f"  [instagram] ✓ Carousel publié ! ID : {media_id}")
    return media_id


def publish_instagram(video_url: str, caption: str, hashtags: list[str]) -> str:
    """
    Publie un Reel sur Instagram.

    Flux :
      1. Créer un conteneur média (statut PROCESSING)
      2. Attendre que le conteneur soit prêt (FINISHED)
      3. Publier avec media_publish

    Args:
        video_url: URL publique HTTPS de la vidéo (ex : Cloudinary)
        caption:   Texte de la publication
        hashtags:  Liste de hashtags (ex: ["#stoicisme", "#citation"])

    Returns:
        ID du média publié
    """
    full_caption = f"{caption}\n\n{' '.join(hashtags)}"

    # ── Étape 1 : créer le conteneur Reel ───────────────────────────────────
    print("  [instagram] Création du conteneur Reel...")
    resp = requests.post(
        f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media",
        data={
            "media_type":    "REELS",
            "video_url":     video_url,
            "caption":       full_caption,
            "share_to_feed": "true",
            "access_token":  INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Instagram {resp.status_code} — {resp.json()}")
    container_id = resp.json()["id"]
    print(f"  [instagram] Conteneur créé : {container_id}")

    # ── Étape 2 : attendre FINISHED ──────────────────────────────────────────
    _wait_ig_container(container_id)

    # ── Étape 3 : publier ────────────────────────────────────────────────────
    print("  [instagram] Publication du Reel...")
    resp = requests.post(
        f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media_publish",
        data={
            "creation_id":  container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    media_id = resp.json()["id"]
    print(f"  [instagram] ✓ Reel publié ! ID : {media_id}")
    return media_id


def _wait_ig_container(
    container_id: str,
    max_attempts: int = 20,
    interval: int = 15,
):
    """Attend que le conteneur Instagram soit prêt (statut FINISHED)."""
    for attempt in range(max_attempts):
        resp = requests.get(
            f"{_IG_BASE}/{container_id}",
            params={
                "fields":       "status_code,status",
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data   = resp.json()
        status = data.get("status_code", "")
        print(f"  [instagram] Statut conteneur ({attempt + 1}/{max_attempts}) : {status}")

        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Erreur Instagram lors du traitement vidéo : {data}")

        time.sleep(interval)

    raise TimeoutError(
        f"Le conteneur Instagram n'a pas été prêt après {max_attempts * interval}s"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TIKTOK
# ══════════════════════════════════════════════════════════════════════════════

def publish_tiktok(video_path: str, caption: str, hashtags: list[str]) -> str:
    """
    Publie une vidéo sur TikTok via un webhook Make.com.

    Make est une plateforme approuvée par TikTok — elle gère le posting.
    Le pipeline uploade la vidéo sur Cloudinary puis envoie l'URL au webhook.

    Args:
        video_path: Chemin local vers le fichier MP4
        caption:    Texte de la publication
        hashtags:   Liste de hashtags

    Returns:
        "make-triggered"
    """
    from config import MAKE_TIKTOK_WEBHOOK_URL
    from utils.video_host import upload_video

    if not MAKE_TIKTOK_WEBHOOK_URL:
        raise RuntimeError("MAKE_TIKTOK_WEBHOOK_URL non configuré dans .env / secrets GitHub")

    full_caption = f"{caption}\n{' '.join(hashtags)}"

    print("  [tiktok/make] Upload vidéo sur Cloudinary...")
    video_url = upload_video(video_path)

    print("  [tiktok/make] Envoi au webhook Make...")
    resp = requests.post(
        MAKE_TIKTOK_WEBHOOK_URL,
        json={
            "video_url": video_url,
            "caption":   full_caption[:2200],
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Make webhook {resp.status_code} — {resp.text[:200]}")

    print("  [tiktok/make] ✓ Vidéo transmise à Make pour publication TikTok")
    return "make-triggered"


# ══════════════════════════════════════════════════════════════════════════════
# FACEBOOK PAGE
# ══════════════════════════════════════════════════════════════════════════════

def publish_facebook(image_url: str, message: str) -> str:
    """
    Publie une photo + texte sur la Page Facebook.

    Args:
        image_url: URL publique de l'image (Cloudinary)
        message:   Texte du post

    Returns:
        ID du post publié
    """
    print("  [facebook] Publication sur la Page...")
    resp = requests.post(
        f"https://graph.facebook.com/v21.0/{FACEBOOK_PAGE_ID}/photos",
        data={
            "url":          image_url,
            "message":      message,
            "access_token": FACEBOOK_PAGE_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Facebook {resp.status_code} — {resp.json()}")
    post_id = resp.json().get("post_id") or resp.json().get("id", "")
    print(f"  [facebook] ✓ Post publié ! ID : {post_id}")
    return post_id
