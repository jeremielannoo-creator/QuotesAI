"""
utils/drive_uploader.py — Sauvegarde vidéo sur Drive + rappel Google Agenda.

Réutilise le même Google Apps Script que drive_reader.py (même URL).
Le GAS :
  1. Télécharge la vidéo depuis l'URL Cloudinary
  2. La dépose dans AI/Quotes AI/Video/ sur Drive
  3. Crée un événement Google Agenda 10 min plus tard
     avec notification 5 min avant et lien de téléchargement
"""
import requests
from config import DRIVE_GAS_URL


def save_video_and_remind(video_url: str, filename: str, caption: str) -> bool:
    """
    Sauvegarde la vidéo sur Drive et crée un rappel Calendar.

    Args:
        video_url: URL publique Cloudinary de la vidéo
        filename:  Nom du fichier (ex: "quote_2026-04-25_0730.mp4")
        caption:   Texte de la publication (affiché dans le rappel)

    Returns:
        True si succès, False sinon
    """
    if not DRIVE_GAS_URL:
        print("  [drive_uploader] DRIVE_GAS_URL non configuré — ignoré")
        return False

    try:
        resp = requests.post(
            DRIVE_GAS_URL,
            json={
                "action":    "video",
                "video_url": video_url,
                "filename":  filename,
                "caption":   caption[:500],
            },
            timeout=120,  # Le GAS télécharge la vidéo depuis Cloudinary
        )
        if not resp.ok:
            print(f"  [drive_uploader] Erreur HTTP {resp.status_code}")
            return False

        data = resp.json()
        if "error" in data:
            print(f"  [drive_uploader] {data['error']}")
            return False

        print(f"  [drive_uploader] ✓ Vidéo → Drive : {data.get('drive_url', '—')}")
        print(f"  [drive_uploader] ✓ Rappel Calendar créé (dans 10 min, notif 5 min avant)")
        return True

    except Exception as e:
        print(f"  [drive_uploader] Erreur : {e}")
        return False
