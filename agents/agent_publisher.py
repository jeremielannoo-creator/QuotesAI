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
)

_IG_BASE   = "https://graph.facebook.com/v21.0"
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
            "media_type":    "REELS",
            "video_url":     video_url,
            "caption":       full_caption,
            "share_to_feed": "true",
            "access_token":  INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Instagram {resp.status_code} — {resp.json()}"
        )
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

def publish_tiktok(video_path: str, caption: str, hashtags: list[str]) -> str:
    """
    Publie une vidéo sur TikTok via Content Posting API v2.

    Utilise FILE_UPLOAD : upload direct du fichier local (pas de vérification
    de domaine requise, contrairement à PULL_FROM_URL).

    Args:
        video_path: Chemin local vers le fichier MP4
        caption:    Texte de la publication
        hashtags:   Liste de hashtags

    Returns:
        publish_id TikTok
    """
    full_caption = f"{caption}\n{' '.join(hashtags)}"
    file_size    = os.path.getsize(video_path)

    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type":  "application/json; charset=utf-8",
    }

    # ── Étape 1 : initier l'upload ────────────────────────────────────────────
    print("  [tiktok] Initiation de l'upload...")
    body = {
        "post_info": {
            "title":                    full_caption[:150],
            "privacy_level":            "SELF_ONLY",  # sandbox : SELF_ONLY requis ; prod : PUBLIC_TO_EVERYONE
            "disable_duet":             False,
            "disable_stitch":           False,
            "disable_comment":          False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source":            "FILE_UPLOAD",
            "video_size":        file_size,
            "chunk_size":        file_size,   # fichier entier en 1 chunk
            "total_chunk_count": 1,
        },
    }
    resp = requests.post(
        f"{_TIKTOK_BASE}/post/publish/video/init/",
        json=body,
        headers=headers,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"TikTok {resp.status_code} — {resp.json()}")

    result     = resp.json()
    publish_id = result["data"]["publish_id"]
    upload_url = result["data"]["upload_url"]
    print(f"  [tiktok] Publication initiée : {publish_id}")

    # ── Étape 2 : uploader le fichier ─────────────────────────────────────────
    print("  [tiktok] Upload de la vidéo...")
    with open(video_path, "rb") as fh:
        video_data = fh.read()

    up_resp = requests.put(
        upload_url,
        data=video_data,
        headers={
            "Content-Type":   "video/mp4",
            "Content-Range":  f"bytes 0-{file_size - 1}/{file_size}",
            "Content-Length": str(file_size),
        },
        timeout=180,
    )
    if not up_resp.ok:
        raise RuntimeError(
            f"TikTok upload {up_resp.status_code} — {up_resp.text[:300]}"
        )
    print("  [tiktok] ✓ Fichier uploadé")

    # ── Étape 3 : vérifier le statut ──────────────────────────────────────────
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
