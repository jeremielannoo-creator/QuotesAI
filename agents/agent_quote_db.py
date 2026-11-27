"""
Agent 1 (v2) — Sélection de citation depuis la base SQLite locale
Remplace agent_gemini.py — aucune API requise, 100% offline
"""
import sqlite3
import os
import json
import random
from datetime import date

from agents import agent_dedup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "db", "quotes.db")
WEIGHTS_PATH = os.path.join(BASE_DIR, "db", "mood_weights.json")

# Les hashtags renvoyés ici sont ceux de la citation elle-même (auteur, thème).
# Le jeu réellement publié est assemblé par agents/agent_hashtags.py, qui les
# mélange à des paliers tournants — l'ancien bloc « boost » systématique
# revenait à signer chaque post avec les cinq mêmes tags.


def _load_mood_weights() -> dict[str, float]:
    """Poids de performance par mood (écrits par agent_analytics). {} si absent."""
    if not os.path.exists(WEIGHTS_PATH):
        return {}
    try:
        with open(WEIGHTS_PATH, encoding="utf-8") as f:
            return json.load(f).get("weights", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _pick_weighted_id(rows: list, weights: dict[str, float]) -> int:
    """Tire un id de citation, biaisé par le poids de performance de son mood."""
    ids = [r["id"] for r in rows]
    w   = [weights.get(r["mood"], 1.0) for r in rows]
    return random.choices(ids, weights=w, k=1)[0]


def generate_quote(mood_filter: str | None = None) -> dict:
    """
    Sélectionne une citation non encore publiée dans la base.

    Args:
        mood_filter: filtre optionnel sur l'humeur
                     (calm | energetic | melancholic | triumphant | contemplative)

    Returns:
        {id, quote, author, original, mood, keywords, hashtags}

    La citation n'est PAS marquée publiée ici : voir mark_published().
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "Base de données introuvable. Lance d'abord : python import_quotes.py"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    weights = _load_mood_weights()

    # Chercher les citations non publiées (candidates) puis tirer selon les poids
    if mood_filter:
        candidates = cur.execute(
            "SELECT id, mood FROM quotes WHERE published = 0 AND mood = ?", (mood_filter,),
        ).fetchall()
    else:
        candidates = cur.execute(
            "SELECT id, mood FROM quotes WHERE published = 0"
        ).fetchall()

    # Si tout est publié → réinitialiser le cycle
    if not candidates:
        print("  [agent_quote_db] Cycle terminé — remise à zéro des statuts.")
        conn.execute("UPDATE quotes SET published = 0, last_used = NULL")
        conn.commit()
        where = "WHERE mood = ?" if mood_filter else ""
        args  = (mood_filter,) if mood_filter else ()
        candidates = cur.execute(f"SELECT id, mood FROM quotes {where}", args).fetchall()

    if not candidates:
        conn.close()
        raise RuntimeError(
            "Base de données vide. Lance : python import_quotes.py"
        )

    # Tirage, en écartant ce qui est déjà en ligne sous une autre forme. Un
    # doublon détecté est marqué publié pour ne plus jamais être tiré.
    history = agent_dedup.load_history(conn)
    row = None
    while candidates:
        chosen_id = _pick_weighted_id(candidates, weights)
        candidates = [c for c in candidates if c["id"] != chosen_id]
        row = cur.execute("SELECT * FROM quotes WHERE id = ?", (chosen_id,)).fetchone()
        dup = agent_dedup.find_duplicate(row["quote"], history)
        if not dup:
            break
        print(f'  [agent_quote_db] Déjà publiée, écartée : "{row["quote"][:50]}…" ≈ "{dup[:50]}…"')
        conn.execute("UPDATE quotes SET published = 1 WHERE id = ?", (chosen_id,))
        conn.commit()
        row = None
    conn.close()

    if row is None:
        raise RuntimeError("Toutes les citations candidates sont déjà en ligne.")

    keywords = [k.strip() for k in row["keywords"].split("|") if k.strip()]
    hashtags = [h.strip() for h in row["hashtags"].split("|") if h.strip()]

    result = {
        "id":       row["id"],
        "quote":    row["quote"],
        "author":   row["author"],
        "original": row["original"],
        "mood":     row["mood"],
        "keywords": keywords,
        "hashtags": hashtags,
    }

    print(f'  [agent_quote_db] Citation : "{result["quote"][:60]}..." — {result["author"]}')
    return result


def mark_published(quote_id: int) -> None:
    """
    Marque la citation publiée. Appelé APRÈS la publication : avant, un échec
    d'upload ou un dry-run « brûlait » la citation sans qu'elle soit en ligne.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE quotes SET published = 1, last_used = ? WHERE id = ?",
        (date.today().isoformat(), quote_id),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    q = generate_quote()
    print(q)
