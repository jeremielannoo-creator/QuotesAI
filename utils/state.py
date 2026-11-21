"""
utils/state.py — Mémoire persistante du bot (db/state.json).

Sert à ne jamais répéter : mêmes clips de fond, mêmes blocs de hashtags,
mêmes livres proposés. Le fichier est commité par les workflows GitHub Actions,
donc la mémoire survit d'un run à l'autre.
"""
import json
import os
import re
import unicodedata
from datetime import date

from config import BASE_DIR

STATE_PATH = os.path.join(BASE_DIR, "db", "state.json")

_DEFAULT: dict = {
    "used_backgrounds": [],   # clés de clips déjà utilisés (les plus récents en tête)
    "recent_hashtags":  [],   # listes de hashtags des derniers posts (récents en tête)
    "books_featured":   [],   # livres déjà CHRONIQUÉS — jamais deux fois
    "recent_cta_books": [],   # livres cités en CTA récemment — simple rotation
    "last_family":      "",   # dernière famille visuelle utilisée
    "last_template":    "",   # dernier gabarit d'habillage utilisé
}


def norm(s: str) -> str:
    """Minuscule, sans accents, alphanumérique — pour comparer titres et clés."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def load() -> dict:
    if not os.path.exists(STATE_PATH):
        return dict(_DEFAULT)
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)
    return {**_DEFAULT, **data}


def save(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── Fonds vidéo ───────────────────────────────────────────────────────────────

def is_background_used(key: str) -> bool:
    return str(key) in load()["used_backgrounds"]


def remember_background(key: str, family: str = "", keep: int = 150) -> None:
    st = load()
    used = [k for k in st["used_backgrounds"] if k != str(key)]
    st["used_backgrounds"] = ([str(key)] + used)[:keep]
    if family:
        st["last_family"] = family
    save(st)


def last_family() -> str:
    return load()["last_family"]


# ── Gabarit d'habillage ───────────────────────────────────────────────────────

def last_template() -> str:
    return load().get("last_template", "")


def remember_template(name: str) -> None:
    st = load()
    st["last_template"] = name
    save(st)


# ── Hashtags ──────────────────────────────────────────────────────────────────

def recent_hashtags(n_posts: int = 3) -> set[str]:
    """Hashtags utilisés dans les n_posts dernières publications."""
    st = load()
    out: set[str] = set()
    for tags in st["recent_hashtags"][:n_posts]:
        out.update(t.lower() for t in tags)
    return out


def remember_hashtags(tags: list[str], keep: int = 10) -> None:
    st = load()
    st["recent_hashtags"] = ([list(tags)] + st["recent_hashtags"])[:keep]
    save(st)


# ── Livres ────────────────────────────────────────────────────────────────────

# ── Rotation générique (marques, adresses, destinations…) ────────────────────

def recent_picks(bucket: str, n: int = 6) -> list[str]:
    return load().get("picks", {}).get(bucket, [])[:n]


def remember_pick(bucket: str, key: str, keep: int = 6) -> None:
    st    = load()
    picks = st.setdefault("picks", {})
    prev  = [k for k in picks.get(bucket, []) if k != key]
    picks[bucket] = ([key] + prev)[:keep]
    save(st)


# ── Livres ────────────────────────────────────────────────────────────────────

def book_key(title: str, author: str) -> str:
    return f"{norm(title)}|{norm(author)}"


def is_book_featured(title: str, author: str = "") -> bool:
    """
    True si le livre a déjà été proposé. Le titre seul suffit à matcher :
    un même roman republié sous un auteur mal orthographié reste un doublon.
    """
    key   = book_key(title, author)
    ntitle = norm(title)
    for b in load()["books_featured"]:
        if b.get("key") == key or norm(b.get("title", "")) == ntitle:
            return True
    return False


def featured_books() -> list[dict]:
    return load()["books_featured"]


def remember_book(title: str, author: str = "") -> None:
    st = load()
    if not is_book_featured(title, author):
        st["books_featured"].insert(0, {
            "key":    book_key(title, author),
            "title":  title,
            "author": author,
            "date":   date.today().isoformat(),
        })
        save(st)
