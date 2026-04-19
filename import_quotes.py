"""
import_quotes.py — Synchronise quotes.csv vers la base SQLite

Usage :
    python import_quotes.py          # Import normal (ignore les doublons)
    python import_quotes.py --reset  # Remet tous les statuts publiés à 0
    python import_quotes.py --stats  # Affiche les statistiques
"""
import csv
import sqlite3
import os
import sys
from rich.console import Console
from rich.table   import Table

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_DIR    = os.path.join(BASE_DIR, "db")
DB_PATH   = os.path.join(DB_DIR, "quotes.db")
CSV_PATH  = os.path.join(BASE_DIR, "quotes.csv")

console = Console()


def create_db() -> sqlite3.Connection:
    """Crée la base de données et la table si elles n'existent pas."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            quote      TEXT    NOT NULL,
            author     TEXT    NOT NULL,
            original   TEXT,
            mood       TEXT    DEFAULT 'calm',
            keywords   TEXT,
            hashtags   TEXT,
            published  INTEGER DEFAULT 0,
            last_used  TEXT
        )
    """)
    conn.commit()
    return conn


def import_csv():
    """Importe le CSV dans la base SQLite (ignore les doublons)."""
    if not os.path.exists(CSV_PATH):
        console.print(f"[red]Fichier introuvable : {CSV_PATH}[/red]")
        return

    conn     = create_db()
    imported = 0
    skipped  = 0

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            quote = row.get("quote", "").strip()
            if not quote:
                continue

            # Vérifier si la citation existe déjà
            cur = conn.cursor()
            cur.execute("SELECT id FROM quotes WHERE quote = ?", (quote,))
            if cur.fetchone():
                skipped += 1
                continue

            conn.execute("""
                INSERT INTO quotes (quote, author, original, mood, keywords, hashtags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                quote,
                row.get("author", "").strip(),
                row.get("original", "").strip() or None,
                row.get("mood", "calm").strip(),
                row.get("keywords", "").strip(),
                row.get("hashtags", "").strip(),
            ))
            imported += 1

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    conn.close()

    console.print(f"\n✓ [green]{imported}[/green] citation(s) importée(s)")
    if skipped:
        console.print(f"  [yellow]{skipped}[/yellow] doublon(s) ignoré(s)")
    console.print(f"  [cyan]{total}[/cyan] citations au total dans la base")
    console.print(f"  Base de données : [dim]{DB_PATH}[/dim]\n")


def reset_published():
    """Remet toutes les citations en non-publié (pour recommencer le cycle)."""
    conn = create_db()
    conn.execute("UPDATE quotes SET published = 0, last_used = NULL")
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    conn.close()
    console.print(f"✓ [green]{count}[/green] citations remises à zéro.")


def show_stats():
    """Affiche les statistiques de la base."""
    conn = create_db()

    total     = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    published = conn.execute("SELECT COUNT(*) FROM quotes WHERE published = 1").fetchone()[0]
    remaining = total - published

    # Par auteur
    by_author = conn.execute("""
        SELECT author, COUNT(*) as total,
               SUM(published) as done
        FROM quotes
        GROUP BY author
        ORDER BY total DESC
    """).fetchall()

    # Dernières publiées
    recent = conn.execute("""
        SELECT quote, author, last_used
        FROM quotes
        WHERE published = 1
        ORDER BY last_used DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    # Affichage
    console.print(f"\n[bold cyan]📊 Statistiques QuotesAI[/bold cyan]")
    console.print(f"  Total       : [white]{total}[/white]")
    console.print(f"  Publiées    : [green]{published}[/green]")
    console.print(f"  Restantes   : [yellow]{remaining}[/yellow]\n")

    t = Table(title="Par auteur", border_style="cyan")
    t.add_column("Auteur",    style="white")
    t.add_column("Total",     justify="right")
    t.add_column("Publiées",  justify="right", style="green")
    t.add_column("Restantes", justify="right", style="yellow")
    for author, tot, done in by_author:
        t.add_row(author, str(tot), str(done or 0), str(tot - (done or 0)))
    console.print(t)

    if recent:
        console.print("\n[bold]5 dernières publiées :[/bold]")
        for q, a, d in recent:
            console.print(f"  [{d}] [italic]{q[:60]}...[/italic] — {a}")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_published()
    elif "--stats" in sys.argv:
        show_stats()
    else:
        import_csv()
        show_stats()
