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


def publish_instagram_image(image_url: str, caption: str) -> str:
    """
    Publie une image simple (post carré/portrait) sur Instagram.

    Args:
        image_url: URL publique HTTPS (Cloudinary)
        caption:   texte complet, hashtags compris

    Returns:
        ID du média publié
    """
    print("  [instagram] Création du conteneur image…")
    resp = requests.post(
        f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media",
        data={
            "image_url":    image_url,
            "caption":      caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Instagram image {resp.status_code} — {resp.json()}")
    container_id = resp.json()["id"]

    print("  [instagram] Publication de l'image…")
    resp = requests.post(
        f"{_IG_BASE}/{INSTAGRAM_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": INSTAGRAM_ACCESS_TOKEN},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Instagram publish {resp.status_code} — {resp.json()}")
    media_id = resp.json()["id"]
    print(f"  [instagram] ✓ Image publiée ! ID : {media_id}")
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
    Publie une vidéo sur TikTok via la Content Posting API v2 (upload direct du
    fichier, aucune URL publique requise).

    Deux modes selon config.TIKTOK_AUDITED :
      • False (défaut, app non auditée) → BROUILLON : la vidéo arrive dans
        l'inbox TikTok, l'utilisateur ajoute la légende et publie en 1 tap.
      • True  (app auditée)            → publication PUBLIQUE directe et 100% auto.

    Args:
        video_path: Chemin local vers le fichier MP4
        caption:    Texte de la publication
        hashtags:   Liste de hashtags

    Returns:
        Le publish_id retourné par TikTok
    """
    from config import TIKTOK_ACCESS_TOKEN, TIKTOK_AUDITED
    from utils.tiktok_refresh import refresh_tiktok_token

    # Renouvelle l'access_token (valable 24h) via le refresh_token si dispo
    token = refresh_tiktok_token() or TIKTOK_ACCESS_TOKEN
    if not token:
        raise RuntimeError(
            "Aucun token TikTok. Lance : python get_tiktok_token.py"
        )

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Vidéo introuvable : {video_path}")

    if TIKTOK_AUDITED:
        full_caption = f"{caption}\n{' '.join(hashtags)}"[:2200]
        return _tiktok_direct_post(token, video_path, full_caption)
    return _tiktok_inbox_upload(token, video_path)


def _tiktok_init(token: str, endpoint: str, body: dict) -> dict:
    """Appelle un endpoint /init/ TikTok et retourne le champ `data`."""
    resp = requests.post(
        f"{_TIKTOK_BASE}{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json; charset=UTF-8",
        },
        json=body,
        timeout=30,
    )
    data = resp.json()
    if not resp.ok or data.get("error", {}).get("code", "ok") not in ("ok", None):
        raise RuntimeError(f"TikTok init {resp.status_code} — {data}")
    return data["data"]


def _tiktok_put_file(upload_url: str, video_path: str, size: int):
    """Envoie le fichier vidéo en un seul chunk vers l'upload_url TikTok."""
    with open(video_path, "rb") as f:
        data = f.read()
    resp = requests.put(
        upload_url,
        headers={
            "Content-Type":  "video/mp4",
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
        data=data,
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"TikTok upload {resp.status_code} — {resp.text[:200]}")


def _tiktok_inbox_upload(token: str, video_path: str) -> str:
    """Envoie la vidéo dans l'inbox TikTok (brouillon) — sans audit requis."""
    size = os.path.getsize(video_path)
    print("  [tiktok] Init upload brouillon (inbox)...")
    data = _tiktok_init(token, "/post/publish/inbox/video/init/", {
        "source_info": {
            "source":            "FILE_UPLOAD",
            "video_size":        size,
            "chunk_size":        size,
            "total_chunk_count": 1,
        },
    })
    print("  [tiktok] Upload du fichier...")
    _tiktok_put_file(data["upload_url"], video_path, size)
    publish_id = data.get("publish_id", "")
    print(f"  [tiktok] ✓ Vidéo en brouillon TikTok (à publier depuis l'app) — {publish_id}")
    return publish_id


def _tiktok_direct_post(token: str, video_path: str, caption: str) -> str:
    """Publication publique directe — nécessite une app auditée (video.publish)."""
    size = os.path.getsize(video_path)
    print("  [tiktok] Init publication publique directe...")
    data = _tiktok_init(token, "/post/publish/video/init/", {
        "post_info": {
            "title":                 caption,
            "privacy_level":         "PUBLIC_TO_EVERYONE",
            "disable_comment":       False,
            "disable_duet":          False,
            "disable_stitch":        False,
        },
        "source_info": {
            "source":            "FILE_UPLOAD",
            "video_size":        size,
            "chunk_size":        size,
            "total_chunk_count": 1,
        },
    })
    print("  [tiktok] Upload du fichier...")
    _tiktok_put_file(data["upload_url"], video_path, size)
    publish_id = data.get("publish_id", "")
    print(f"  [tiktok] ✓ Publication TikTok lancée — {publish_id}")
    return publish_id


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


def publish_facebook_video(video_url: str, description: str) -> str:
    """
    Publie une vidéo sur la Page Facebook depuis une URL publique (Cloudinary).

    C'est le pendant automatique du « partage sur Facebook » d'Instagram : le
    Reel publié sur Instagram est aussi posté sur la Page, avec la même légende.
    Le crosspost natif d'Instagram (Paramètres → Partage sur d'autres apps) est
    un réglage d'interface qu'aucune API n'expose — cette fonction fait le
    travail côté serveur, sans dépendre de ce réglage.

    Args:
        video_url:   URL publique HTTPS du MP4
        description: Texte du post (légende + hashtags)

    Returns:
        ID de la vidéo publiée
    """
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_TOKEN:
        raise RuntimeError("FACEBOOK_PAGE_ID / FACEBOOK_PAGE_TOKEN manquants")

    print("  [facebook] Publication de la vidéo sur la Page...")
    resp = requests.post(
        f"https://graph.facebook.com/v21.0/{FACEBOOK_PAGE_ID}/videos",
        data={
            "file_url":     video_url,
            "description":  description,
            "access_token": FACEBOOK_PAGE_TOKEN,
        },
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"Facebook vidéo {resp.status_code} — {resp.json()}")
    video_id = resp.json().get("id", "")
    print(f"  [facebook] ✓ Vidéo publiée ! ID : {video_id}")
    return video_id
