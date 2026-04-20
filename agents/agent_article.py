"""
Agent — Lecture et parsing d'un article de critique littéraire.
Format attendu :
  Ligne 1 : "Titre — Auteur"
  Ligne 2 : vide
  Reste   : corps de l'article
"""
import os
import re
from pathlib import Path
from config import BASE_DIR

ARTICLES_DIR = os.path.join(BASE_DIR, "content", "articles")


def get_latest_article() -> dict | None:
    """Retourne le dernier article non traité (le plus récent .md ou .txt)."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    files = sorted(
        list(Path(ARTICLES_DIR).glob("*.md")) +
        list(Path(ARTICLES_DIR).glob("*.txt")),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not files:
        print("  [agent_article] Aucun article trouvé dans content/articles/")
        return None
    article = parse_article(str(files[0]))
    print(f"  [agent_article] Article : « {article['title']} » — {article['author']}")
    return article


def parse_article(file_path: str) -> dict:
    """Parse un fichier article et retourne un dict structuré."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    lines = content.split("\n")
    first_line = lines[0].strip()

    # Titre — Auteur (tiret long ou court)
    if " — " in first_line:
        title, author = first_line.split(" — ", 1)
    elif " - " in first_line:
        title, author = first_line.split(" - ", 1)
    else:
        title, author = first_line, ""

    # Corps : tout après la première ligne (et la ligne vide éventuelle)
    body_lines = lines[1:]
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    body = "\n".join(body_lines).strip()

    return {
        "file_path": file_path,
        "title":     title.strip(),
        "author":    author.strip(),
        "body":      body,
        "raw":       content,
        "slug":      _slugify(title.strip()),
    }


def _slugify(text: str) -> str:
    text = text.lower()
    for src, dst in [("àâä","a"),("éèêë","e"),("îï","i"),("ôö","o"),("ùûü","u"),("ç","c")]:
        for c in src:
            text = text.replace(c, dst)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
