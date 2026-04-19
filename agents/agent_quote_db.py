"""
Agent 1 (v2) — Sélection de citation depuis la base SQLite locale
Remplace agent_gemini.py — aucune API requise, 100% offline
"""
import sqlite3
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "db", "quotes.db")


def generate_quote(mood_filter: str | None = None) -> dict:
    """
    Sélectionne une citation non encore publiée dans la base.

    Args:
        mood_filter: filtre optionnel sur l'humeur
                     (calm | energetic | melancholic | triumphant | contemplative)

    Returns:
        {quote, author, original, mood, keywords, hashtags}
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "Base de données introuvable. Lance d'abord : python import_quotes.py"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # Chercher une citation non publiée
    if mood_filter:
        cur.execute(
            "SELECT * FROM quotes WHERE published = 0 AND mood = ? ORDER BY RANDOM() LIMIT 1",
            (mood_filter,),
        )
    else:
        cur.execute(
            "SELECT * FROM quotes WHERE published = 0 ORDER BY RANDOM() LIMIT 1"
        )

    row = cur.fetchone()

    # Si tout est publié → réinitialiser le cycle
    if not row:
        print("  [agent_quote_db] Cycle terminé — remise à zéro des statuts.")
        conn.execute("UPDATE quotes SET published = 0, last_used = NULL")
        conn.commit()
        cur.execute("SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1")
        row = cur.fetchone()

    if not row:
        conn.close()
        raise RuntimeError(
            "Base de données vide. Lance : python import_quotes.py"
        )

    # Marquer comme publiée
    conn.execute(
        "UPDATE quotes SET published = 1, last_used = ? WHERE id = ?",
        (date.today().isoformat(), row["id"]),
    )
    conn.commit()
    conn.close()

    keywords = [k.strip() for k in row["keywords"].split("|") if k.strip()]
    hashtags = [h.strip() for h in row["hashtags"].split("|") if h.strip()]

    result = {
        "quote":    row["quote"],
        "author":   row["author"],
        "original": row["original"],
        "mood":     row["mood"],
        "keywords": keywords,
        "hashtags": hashtags,
    }

    print(f'  [agent_quote_db] Citation : "{result["quote"][:60]}..." — {result["author"]}')
    return result


if __name__ == "__main__":
    q = generate_quote()
    print(q)
