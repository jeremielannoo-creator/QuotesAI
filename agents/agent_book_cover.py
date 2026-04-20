"""
Agent — Récupère la couverture du livre via Open Library API.
Fallback : image Pexels thématique.
"""
import os
import random
import requests
from config import TEMP_DIR, PEXELS_API_KEY

_OL_SEARCH = "https://openlibrary.org/search.json"
_OL_COVERS = "https://covers.openlibrary.org/b"


def get_book_cover(title: str, author: str) -> str | None:
    """
    Retourne le chemin local d'une image de couverture.
    1. Open Library (couverture officielle)
    2. Pexels (image "book reading" générique)
    3. None
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    dest = os.path.join(TEMP_DIR, "book_cover.jpg")

    # ── Open Library ──────────────────────────────────────────────────────────
    url = _fetch_ol_cover(title, author)
    if url and _download(url, dest):
        print(f"  [agent_book_cover] ✓ Open Library : {title}")
        return dest

    # ── Pexels fallback ───────────────────────────────────────────────────────
    if PEXELS_API_KEY:
        url = _fetch_pexels("open book reading")
        if url and _download(url, dest):
            print(f"  [agent_book_cover] ✓ Pexels (fallback)")
            return dest

    print(f"  [agent_book_cover] Aucune couverture trouvée pour : {title}")
    return None


def _fetch_ol_cover(title: str, author: str) -> str | None:
    try:
        resp = requests.get(
            _OL_SEARCH,
            params={"title": title, "author": author, "limit": 1, "fields": "isbn,cover_i"},
            timeout=10,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        if not docs:
            return None
        doc      = docs[0]
        cover_id = doc.get("cover_i")
        if cover_id:
            return f"{_OL_COVERS}/id/{cover_id}-L.jpg"
        isbns = doc.get("isbn", [])
        if isbns:
            return f"{_OL_COVERS}/isbn/{isbns[0]}-L.jpg"
    except Exception as e:
        print(f"  [agent_book_cover] Erreur Open Library : {e}")
    return None


def _fetch_pexels(query: str) -> str | None:
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 5, "orientation": "portrait"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return random.choice(photos[:3])["src"]["large"]
    except Exception as e:
        print(f"  [agent_book_cover] Erreur Pexels : {e}")
    return None


def _download(url: str, dest: str) -> bool:
    try:
        resp = requests.get(url, timeout=15, stream=True)
        if not resp.ok:
            return False
        ct = resp.headers.get("Content-Type", "")
        if "image" not in ct:
            return False
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=32768):
                fh.write(chunk)
        return os.path.getsize(dest) > 1000
    except Exception:
        return False
