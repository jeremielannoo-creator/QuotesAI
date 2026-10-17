"""
Agent 2 — Fourniture du fond vidéo.

Chaîne de sources, dans l'ordre :
  1. Banque de clips IA locale (assets/backgrounds/) — clips Flow/HuggingFace
  2. Génération text-to-video à la volée (si VIDEO_AI_ENABLED=1)
  3. Pexels
  4. Pixabay

Deux garanties par rapport à la version précédente :
  • la famille visuelle change à chaque publication (agent_scenes)
  • un clip déjà utilisé n'est jamais repris tant qu'il reste des inédits
    (utils.state)
"""
import os
import random
import re

import requests

from agents.agent_scenes import pick_family, stock_queries
from agents.agent_video_ai import generate_background
from config import BACKGROUNDS_DIR, PEXELS_API_KEY, PIXABAY_API_KEY, TEMP_DIR
from utils import state

_PEXELS_VIDEOS_URL  = "https://api.pexels.com/videos/search"
_PIXABAY_VIDEOS_URL = "https://pixabay.com/api/videos/"


def find_and_download_video(keywords: list[str], mood: str = "calm") -> str:
    """
    Retourne le chemin local d'un MP4 de fond, inédit autant que possible.

    Args:
        keywords: mots-clés issus de la citation
        mood:     humeur de la citation
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

    family = pick_family(mood, avoid=state.last_family(), keywords=keywords)
    print(f"  [agent_video] Famille visuelle : {family} (humeur : {mood})")

    # 1. Banque locale de clips IA
    path = _from_local_library(family)
    if path:
        return path

    # 2. Génération text-to-video (désactivée par défaut)
    path = generate_background(mood, family)
    if path:
        state.remember_background(os.path.basename(path), family)
        return path

    # 3–4. Banques de stock
    queries = stock_queries(mood, keywords, family, n=0)
    for fetch in (_from_pexels, _from_pixabay):
        for query in queries:
            path = fetch(query, family, keywords)
            if path:
                return path

    raise RuntimeError(f"Aucun fond vidéo trouvé (humeur {mood}, mots-clés {keywords})")


# ── Source 1 : banque locale ──────────────────────────────────────────────────

def _from_local_library(family: str) -> str | None:
    """
    Pioche un clip inédit dans assets/backgrounds/. La sous-famille est
    privilégiée ; à défaut on prend n'importe quel clip inédit de la banque.
    """
    if not os.path.isdir(BACKGROUNDS_DIR):
        return None

    preferred, others = [], []
    for root, _dirs, files in os.walk(BACKGROUNDS_DIR):
        for f in files:
            if not f.lower().endswith((".mp4", ".mov", ".webm")):
                continue
            full = os.path.join(root, f)
            (preferred if os.path.basename(root) == family else others).append(full)

    for pool in (preferred, others):
        unused = [p for p in pool if not state.is_background_used(_key(p))]
        if unused:
            chosen = random.choice(unused)
            state.remember_background(_key(chosen), family)
            print(f"  [agent_video] Banque locale : {os.path.basename(chosen)}")
            return chosen
    return None


def _key(path: str) -> str:
    return f"local:{os.path.basename(path)}"


# ── Source 2 : Pexels ─────────────────────────────────────────────────────────

def _from_pexels(query: str, family: str, keywords: list[str]) -> str | None:
    if not PEXELS_API_KEY:
        return None
    for orientation in ("portrait", None):
        params = {"query": query, "per_page": 15, "size": "medium"}
        if orientation:
            params["orientation"] = orientation
        try:
            resp = requests.get(_PEXELS_VIDEOS_URL, params=params,
                                headers={"Authorization": PEXELS_API_KEY}, timeout=15)
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
        except requests.RequestException as e:
            print(f"  [agent_video] Pexels '{query}' : {e}")
            continue

        fresh = [v for v in videos if not state.is_background_used(f"pexels:{v['id']}")]
        # L'URL Pexels porte la description du clip (…/video/waves-crashing-on-rocks-1234/)
        _rank(fresh, lambda v: v.get("url", ""), query, keywords)
        for video in fresh[:5]:
            file_info = _best_pexels_file(video)
            if not file_info:
                continue
            dest = os.path.join(TEMP_DIR, f"bg_{_slug(query)}.mp4")
            if _download(file_info["link"], dest):
                state.remember_background(f"pexels:{video['id']}", family)
                return dest
    return None


def _best_pexels_file(video: dict) -> dict | None:
    """Meilleur MP4 : entre 720 et 1920 px de large, sinon n'importe quel MP4."""
    files = video.get("video_files", [])
    mp4 = [f for f in files
           if f.get("file_type") == "video/mp4" and 720 <= f.get("width", 0) <= 1920]
    mp4 = mp4 or [f for f in files if f.get("file_type") == "video/mp4"]
    if not mp4:
        return None
    return max(mp4, key=lambda f: f.get("width", 0))


# ── Source 3 : Pixabay ────────────────────────────────────────────────────────

def _from_pixabay(query: str, family: str, keywords: list[str]) -> str | None:
    if not PIXABAY_API_KEY:
        return None
    try:
        resp = requests.get(_PIXABAY_VIDEOS_URL, params={
            "key": PIXABAY_API_KEY, "q": query,
            "per_page": 20, "video_type": "film", "safesearch": "true",
        }, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except requests.RequestException as e:
        print(f"  [agent_video] Pixabay '{query}' : {e}")
        return None

    fresh = [h for h in hits if not state.is_background_used(f"pixabay:{h['id']}")]
    _rank(fresh, lambda h: h.get("tags", ""), query, keywords)
    for hit in fresh[:5]:
        streams = hit.get("videos", {})
        url = (streams.get("large") or streams.get("medium") or {}).get("url")
        if not url:
            continue
        dest = os.path.join(TEMP_DIR, f"bg_{_slug(query)}.mp4")
        if _download(url, dest):
            state.remember_background(f"pixabay:{hit['id']}", family)
            return dest
    return None


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _rank(items: list, describe, query: str, keywords: list[str]) -> None:
    """
    Trie sur place les résultats d'une banque par pertinence : nombre de mots
    de la requête et des mots-clés de la citation présents dans la description
    du clip. Mélange d'abord pour départager les ex-aequo au hasard.
    """
    terms = set(re.findall(r"[a-z]+", f"{query} {' '.join(keywords)}".lower()))
    random.shuffle(items)
    items.sort(key=lambda it: -len(terms & set(re.findall(r"[a-z]+", describe(it).lower()))))


def _slug(text: str) -> str:
    return text[:20].strip().replace(" ", "_").lower()


def _download(url: str, dest: str) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                fh.write(chunk)
        print(f"  [agent_video] Téléchargé : {os.path.basename(dest)} "
              f"({os.path.getsize(dest) / 1_048_576:.1f} Mo)")
        return True
    except Exception as e:
        print(f"  [agent_video] Échec du téléchargement : {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False


if __name__ == "__main__":
    print(find_and_download_video(["solitude", "night"], mood="melancholic"))
