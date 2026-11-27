"""
agents/agent_dedup.py — Garde-fou « citation déjà publiée ».

La colonne quotes.published ne suffit pas :
  • la base contient des variantes d'une même citation (« Ce qui ne me tue pas
    me rend plus fort » / « Tout ce qui ne me tue pas… ») — trois paires ont
    déjà été publiées deux fois sur le compte ;
  • des citations sont en ligne sans être marquées publiées (base écrasée par
    un commit local, publication manuelle…).

La candidate est donc comparée à deux sources : les citations déjà marquées
publiées dans la base, et les légendes réellement en ligne sur Instagram
(sur RECENT_DAYS jours, pour qu'une fois la base épuisée le cycle puisse
recommencer). La comparaison est floue : texte normalisé (casse, accents,
ponctuation) puis ratio de similarité.

Usage :
    python -m agents.agent_dedup     # audit : variantes dans la base + écarts avec Instagram
"""
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from utils.state import norm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "db", "quotes.db")

# Seuil mesuré sur la base : les vraies variantes sont toutes au-dessus de 0,84
# (« Le courage est savoir… » / « Le courage est de savoir… » = 0,97).
SIMILARITY  = 0.82
RECENT_DAYS = 365

_GUILLEMETS = re.compile(r"«\s*(.+?)\s*»", re.S)


def similar(a: str, b: str) -> bool:
    """True si a et b sont la même citation, à la formulation près."""
    na, nb = norm(a), norm(b)
    if len(na) < 15 or len(nb) < 15:
        return na == nb
    if na in nb or nb in na:
        return True
    if abs(len(na) - len(nb)) > 0.4 * max(len(na), len(nb)):
        return False
    sm = SequenceMatcher(None, na, nb, autojunk=False)
    # quick_ratio() est une borne haute bon marché : élimine l'essentiel des paires
    return sm.quick_ratio() >= SIMILARITY and sm.ratio() >= SIMILARITY


def load_history(conn: sqlite3.Connection) -> dict:
    """
    Tout ce qui compte comme « déjà publié », chargé une fois par exécution :
      quotes   — citations marquées publiées dans la base
      captions — passages de légendes Instagram susceptibles de porter la citation
    """
    quotes = [r[0] for r in conn.execute("SELECT quote FROM quotes WHERE published = 1")]
    return {"quotes": quotes, "captions": _instagram_passages()}


def find_duplicate(quote: str, history: dict) -> str | None:
    """Retourne le texte déjà publié qui correspond à `quote`, ou None."""
    for q in history["quotes"]:
        if similar(quote, q):
            return q
    for passage in history["captions"]:
        if similar(quote, passage):
            return passage
    return None


def _instagram_passages() -> list[str]:
    """
    Passages des légendes Instagram récentes où peut se trouver une citation :
    le premier paragraphe (anciennes légendes) et chaque texte entre guillemets
    (légendes actuelles, où la citation suit une phrase d'accroche).
    Sans accès à l'API, on continue avec la base seule.
    """
    try:
        from agents.agent_analytics import _fetch_media
        media = _fetch_media()
    except Exception as e:
        print(f"  [agent_dedup] Historique Instagram indisponible ({e}) — contrôle sur la base seule")
        return []

    since = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    out: list[str] = []
    for m in media:
        ts = m.get("timestamp", "")
        if ts and datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z") < since:
            continue
        cap = m.get("caption") or ""
        out.append(cap.split("\n\n")[0])
        out.extend(_GUILLEMETS.findall(cap))
    return out


def audit() -> None:
    """Rapport en lecture seule : variantes dans la base, écarts avec Instagram."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, quote, author, published FROM quotes").fetchall()

    print("── Variantes d'une même citation dans la base ──")
    pairs = 0
    for i, (id_a, qa, aa, _) in enumerate(rows):
        for id_b, qb, ab, _ in rows[i + 1:]:
            if similar(qa, qb):
                pairs += 1
                print(f"  #{id_a} {qa} ({aa})\n  #{id_b} {qb} ({ab})\n")
    print(f"  {pairs} paire(s)\n")

    print("── En ligne sur Instagram mais pas marquées publiées ──")
    history = {"quotes": [], "captions": _instagram_passages()}
    missing = [(i, q) for i, q, _, pub in rows if not pub and find_duplicate(q, history)]
    for i, q in missing:
        print(f"  #{i} {q}")
    print(f"  {len(missing)} citation(s) — elles seront écartées automatiquement au tirage.")
    conn.close()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    audit()
