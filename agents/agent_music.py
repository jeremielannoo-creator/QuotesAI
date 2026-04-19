"""
Agent 3 — Sélection et téléchargement de musique via Pixabay API
Télécharge automatiquement une piste libre de droits selon l'humeur.
Fallback sur les fichiers locaux dans assets/music/ si l'API échoue.

Pixabay music : gratuit, pas d'attribution requise, autorisé sur Instagram/TikTok.
"""
import os
import random
import requests
from config import MUSIC_DIR, TEMP_DIR, PIXABAY_API_KEY

_PIXABAY_URL = "https://pixabay.com/api/"

# ── Termes de recherche par humeur ────────────────────────────────────────────
_MOOD_TERMS: dict[str, list[str]] = {
    "calm":          ["calm piano", "peaceful ambient", "soft instrumental", "relaxing"],
    "energetic":     ["upbeat cinematic", "motivational", "epic instrumental", "powerful"],
    "melancholic":   ["sad piano", "emotional ambient", "melancholic", "nostalgic"],
    "triumphant":    ["epic orchestral", "cinematic triumph", "inspiring", "victory"],
    "contemplative": ["meditation ambient", "deep atmospheric", "zen", "mindful"],
    "warm":          ["warm acoustic", "gentle piano", "cozy ambient", "romantic"],
}


def select_music(mood: str) -> str | None:
    """
    Retourne le chemin d'un fichier audio pour l'humeur donnée.
    1. Essaie de télécharger depuis Pixabay API
    2. Fallback sur les fichiers locaux dans assets/music/
    3. Retourne None si rien de disponible (vidéo sans son)
    """
    os.makedirs(MUSIC_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR,  exist_ok=True)

    # ── Tentative Pixabay ─────────────────────────────────────────────────────
    if PIXABAY_API_KEY:
        path = _fetch_pixabay(mood)
        if path:
            return path
        print("  [agent_music] Pixabay indisponible — fallback local")

    # ── Fallback : fichiers locaux ────────────────────────────────────────────
    return _select_local(mood)


# ── Pixabay ───────────────────────────────────────────────────────────────────

def _fetch_pixabay(mood: str) -> str | None:
    """Cherche et télécharge une piste Pixabay correspondant à l'humeur."""
    terms = _MOOD_TERMS.get(mood.lower(), ["ambient instrumental"])

    for term in terms:
        try:
            resp = requests.get(
                _PIXABAY_URL,
                params={
                    "key":        PIXABAY_API_KEY,
                    "media_type": "music",
                    "q":          term,
                    "per_page":   10,
                },
                timeout=15,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            if not hits:
                continue

            # Choisir aléatoirement parmi les 5 premiers résultats
            track = random.choice(hits[:5])
            audio_url = track.get("previewURL") or track.get("audioURL", "")
            if not audio_url:
                continue

            dest = os.path.join(TEMP_DIR, f"music_{mood}.mp3")
            if _download(audio_url, dest):
                title = track.get("tags", term)[:40]
                print(f"  [agent_music] ♪ Pixabay ({mood}) : {title}")
                return dest

        except requests.RequestException as e:
            print(f"  [agent_music] Erreur Pixabay pour '{term}': {e}")
            continue

    return None


def _download(url: str, dest: str) -> bool:
    """Télécharge un fichier audio. Retourne True si succès."""
    try:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 32):
                fh.write(chunk)
        return True
    except Exception as e:
        print(f"  [agent_music] Échec téléchargement audio : {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False


# ── Fichiers locaux ───────────────────────────────────────────────────────────

_MOOD_ALIASES: dict[str, list[str]] = {
    "calm":          ["calm", "peaceful", "relax", "zen", "soft"],
    "energetic":     ["energetic", "upbeat", "power", "drive", "epic"],
    "melancholic":   ["melancholic", "sad", "melancholy", "nostalgic", "emotional"],
    "triumphant":    ["triumphant", "victory", "hero", "strong", "bold"],
    "contemplative": ["contemplative", "ambient", "meditative", "deep", "mind"],
    "warm":          ["warm", "acoustic", "gentle", "romantic", "cozy"],
}


def _select_local(mood: str) -> str | None:
    """Sélectionne un fichier audio local selon l'humeur."""
    all_files = _list_audio_files()
    if not all_files:
        print("  [agent_music] Aucun fichier audio trouvé dans assets/music/")
        return None

    aliases  = _MOOD_ALIASES.get(mood.lower(), [mood.lower()])
    matched  = [
        f for f in all_files
        if any(alias in os.path.basename(f).lower() for alias in aliases)
    ]
    chosen = random.choice(matched) if matched else random.choice(all_files)
    print(f"  [agent_music] ♪ Local ({mood}) : {os.path.basename(chosen)}")
    return chosen


def _list_audio_files() -> list[str]:
    extensions = {".mp3", ".m4a", ".aac", ".wav", ".ogg"}
    return [
        os.path.join(MUSIC_DIR, f)
        for f in os.listdir(MUSIC_DIR)
        if os.path.splitext(f)[1].lower() in extensions
    ]


if __name__ == "__main__":
    for mood in ["calm", "energetic", "melancholic", "triumphant", "contemplative"]:
        print(f"{mood}: {select_music(mood)}")
