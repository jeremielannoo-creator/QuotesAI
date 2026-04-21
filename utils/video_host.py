"""
utils/video_host.py — Upload d'une vidéo sur Cloudinary
Nécessaire pour Instagram (qui exige une URL publique)
TikTok supporte l'upload direct donc ce module n'est pas requis pour TikTok.
"""
import cloudinary
import cloudinary.uploader
from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


def upload_video(local_path: str, public_id: str | None = None) -> str:
    """
    Upload un fichier sur Cloudinary et retourne son URL publique.
    Détecte automatiquement image ou vidéo selon l'extension.

    Args:
        local_path: chemin du fichier local (MP4, JPG, PNG…)
        public_id:  identifiant Cloudinary (optionnel, généré auto sinon)

    Returns:
        URL HTTPS du fichier hébergé
    """
    print(f"  [video_host] Upload Cloudinary : {local_path}")

    ext = local_path.rsplit(".", 1)[-1].lower()
    rtype = "image" if ext in ("jpg", "jpeg", "png", "gif", "webp") else "video"

    kwargs = {
        "resource_type": rtype,
        "folder":        "quotesai",
        "overwrite":     True,
    }
    if public_id:
        kwargs["public_id"] = public_id

    result = cloudinary.uploader.upload(local_path, **kwargs)
    url    = result["secure_url"]

    print(f"  [video_host] ✓ Vidéo hébergée : {url}")
    return url


def delete_video(public_id: str):
    """Supprime une vidéo de Cloudinary après publication (libère le quota)."""
    cloudinary.uploader.destroy(public_id, resource_type="video")
    print(f"  [video_host] Vidéo supprimée de Cloudinary : {public_id}")
