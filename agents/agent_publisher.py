"""
Agent 5 — Publication sur Instagram (Reels) et TikTok
Instagram : Meta Graph API v19.0 — nécessite une URL vidéo publique (Cloudinary)
TikTok    : Content Posting API v2 — upload direct par URL publique
"""
import time
import requests
from config import (
    INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID,
    TIKTOK_ACCESS_TOKEN, TIKTOK_OPEN_ID,
)

_IG_BASE   = "https://graph.facebook.com/v19.0"
_TIKTOK_BASE = "https://open.tiktokapis.com/v2"


# ══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM
# ══════════════════════════════════════════════════════════════════════════════

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

    # ── Étape 1 : créer le conteneur ──────────────────────────────────────────
    print("  [instagram] Création du conteneur Reels...")
    resp = requests.post(
        f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media",
        data={
            "media_type":   "REELS",
            "video_url":    video_url,
            "caption":      full_caption,
            "share_to_feed": "true",
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]
    print(f"  [instagram] Conteneur créé : {container_id}")

    # ── Étape 2 : attendre FINISHED ───────────────────────────────────────────
    _wait_ig_container(container_id)

    # ── Étape 3 : publier ─────────────────────────────────────────────────────
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

def publish_tiktok(video_url: str, caption: str, hashtags: list[str]) -> str:
    """
    Publie une vidéo sur TikTok via Content Posting API v2.

    Utilise la source PULL_FROM_URL (TikTok télécharge depuis l'URL).

    Args:
        video_url: URL publique HTTPS de la vidéo
        caption:   Texte de la publication
        hashtags:  Liste de hashtags

    Returns:
        publish_id TikTok
    """
    full_caption = f"{caption}\n{' '.join(hashtags)}"

    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type":  "application/json; charset=utf-8",
    }

    # ── Étape 1 : initier la publication ──────────────────────────────────────
    print("  [tiktok] Initiation de la publication...")
    body = {
        "post_info": {
            "title":            full_caption[:150],  # max 150 chars
            "privacy_level":    "PUBLIC_TO_EVERYONE",
            "disable_duet":     False,
            "disable_stitch":   False,
            "disable_comment":  False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source":    "PULL_FROM_URL",
            "video_url": video_url,
        },
    }
    resp = requests.post(
        f"{_TIKTOK_BASE}/post/publish/video/init/",
        json=body,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    result     = resp.json()
    publish_id = result["data"]["publish_id"]
    print(f"  [tiktok] Publication initiée : {publish_id}")

    # ── Étape 2 : vérifier le statut ──────────────────────────────────────────
    _wait_tiktok_publish(publish_id, headers)

    print(f"  [tiktok] ✓ Vidéo publiée sur TikTok ! publish_id : {publish_id}")
    return publish_id


def _wait_tiktok_publish(
    publish_id: str,
    headers: dict,
    max_attempts: int = 20,
    interval: int = 15,
):
    """Vérifie périodiquement le statut de publication TikTok."""
    for attempt in range(max_attempts):
        resp = requests.post(
            f"{_TIKTOK_BASE}/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data   = resp.json().get("data", {})
        status = data.get("status", "PROCESSING_UPLOAD")
        print(f"  [tiktok] Statut ({attempt + 1}/{max_attempts}) : {status}")

        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            return
        if "FAILED" in status or "ERROR" in status:
            raise RuntimeError(f"Erreur TikTok lors de la publication : {data}")

        time.sleep(interval)

    raise TimeoutError(
        f"Publication TikTok non terminée après {max_attempts * interval}s"
    )
