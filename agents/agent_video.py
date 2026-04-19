"""
Agent 2 — Recherche et téléchargement d'une vidéo Pexels
Style : cinématique chaud inspiré de @tylerwayneglass
Stratégie : portrait en priorité, termes golden-hour/bokeh/slow-motion,
            fallback sur paysage (rognage FFmpeg ensuite)
"""
import os
import random
import requests
from config import PEXELS_API_KEY, TEMP_DIR

_PEXELS_VIDEOS_URL = "https://api.pexels.com/videos/search"


# ── Termes de recherche par humeur (valeurs sûres Pexels) ────────────────────
_MOOD_TERMS: dict[str, list[str]] = {
    "calm": [
        "sunset beach",
        "calm ocean waves",
        "mountain lake",
        "slow life italy",
        "greece island sea",
        "river valley sunset",
        "green meadow",
    ],
    "energetic": [
        "mountain sunrise",
        "waterfall",
        "ocean waves",
        "city timelapse people",
        "sunrise horizon",
        "italy street crowd",
    ],
    "melancholic": [
        "people walking rainy city",
        "lonely person bench",
        "foggy city street people",
        "couple street night",
        "autumn leaves park people",
        "empty beach sunset",
        "misty mountains",
    ],
    "triumphant": [
        "mountain peak sunset",
        "sunrise horizon sea",
        "ocean waves rocks",
        "greece sunset sea",
        "sunset sky clouds",
    ],
    "contemplative": [
        "couple walking sunset",
        "people cafe terrace",
        "starry night sky",
        "night city lights people",
        "lighthouse sea",
        "slow life village",
        "greece village street",
    ],
}

# Fallbacks universels — toujours beaux sur Pexels
_POETIC_FALLBACKS = [
    "sunset beach",
    "italy street",
    "greece sea sunset",
    "slow life",
    "mountain sunset",
    "ocean waves",
    "people walking city",
    "couple sunset",
    "travel city street",
    "sea waves",
]


def find_and_download_video(keywords: list[str], mood: str = "calm") -> str:
    """
    Cherche une vidéo Pexels cinématique correspondant à l'humeur et aux mots-clés.

    Args:
        keywords: mots-clés issus de la citation
        mood:     humeur de la citation (influence les termes de recherche)

    Returns:
        Chemin local du fichier MP4 téléchargé
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

    mood_terms   = _MOOD_TERMS.get(mood, _MOOD_TERMS["calm"])
    # Ordre : 2 meilleurs termes mood → 2 keywords → reste mood → fallbacks
    search_order = mood_terms[:2] + keywords[:2] + mood_terms[2:] + _POETIC_FALLBACKS

    # 1. Portrait en priorité
    for keyword in search_order:
        videos = _search(keyword, orientation="portrait")
        if videos:
            path = _pick_and_download(videos, keyword)
            if path:
                return path

    # 2. Fallback : toutes orientations (FFmpeg rognera)
    for keyword in search_order:
        videos = _search(keyword, orientation=None)
        if videos:
            path = _pick_and_download(videos, keyword)
            if path:
                return path

    raise RuntimeError(
        f"Aucune vidéo trouvée sur Pexels pour les mots-clés : {keywords}"
    )


# ── Fonctions internes ─────────────────────────────────────────────────────────

def _search(query: str, orientation: str | None = "portrait") -> list[dict]:
    """Appelle l'API Pexels et retourne la liste de vidéos."""
    params: dict = {
        "query":    query,
        "per_page": 15,
        "size":     "medium",
    }
    if orientation:
        params["orientation"] = orientation

    try:
        resp = requests.get(
            _PEXELS_VIDEOS_URL,
            params=params,
            headers={"Authorization": PEXELS_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("videos", [])
    except requests.RequestException as e:
        print(f"  [agent_video] Erreur Pexels pour '{query}': {e}")
        return []


def _pick_and_download(videos: list[dict], label: str) -> str | None:
    """Choisit une vidéo aléatoirement parmi les meilleures et la télécharge."""
    pool = videos[:10]
    random.shuffle(pool)

    for video in pool:
        file_info = _best_file(video)
        if file_info:
            dest = os.path.join(
                TEMP_DIR,
                f"bg_{label[:15].replace(' ', '_').lower()}.mp4",
            )
            if _download(file_info["link"], dest):
                return dest
    return None


def _best_file(video: dict) -> dict | None:
    """
    Sélectionne le meilleur fichier MP4 :
    - Résolution ≤ 1920 (évite les énormes 4K)
    - Résolution ≥ 720 (qualité minimale)
    - Priorité HD
    """
    mp4_files = [
        f for f in video.get("video_files", [])
        if f.get("file_type") == "video/mp4"
        and 720 <= f.get("width", 0) <= 1920
    ]
    if not mp4_files:
        mp4_files = [
            f for f in video.get("video_files", [])
            if f.get("file_type") == "video/mp4"
        ]
    if not mp4_files:
        return None

    mp4_files.sort(key=lambda f: f.get("width", 0), reverse=True)
    return mp4_files[0]


def _download(url: str, dest: str) -> bool:
    """Télécharge un fichier par streaming. Retourne True si succès."""
    try:
        print(f"  [agent_video] Téléchargement : {url[:60]}...")
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                fh.write(chunk)
        size_mb = os.path.getsize(dest) / 1_048_576
        print(f"  [agent_video] Vidéo sauvegardée : {dest} ({size_mb:.1f} Mo)")
        return True
    except Exception as e:
        print(f"  [agent_video] Échec du téléchargement : {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False


if __name__ == "__main__":
    path = find_and_download_video(["nature", "sky", "forest"])
    print("Vidéo :", path)
