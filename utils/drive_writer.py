"""
utils/drive_writer.py — Création d'un article dans Drive/Littérature via le GAS.

Utilisé par la skill `ava-blog-hebdo` (et peut être appelé en CLI).

Exemple :
    python -m utils.drive_writer --slot B1 --date 2026-05-13 --file critique_b1.md
"""
import argparse
import sys
import requests
from config import DRIVE_GAS_URL


def create_article(slot: str, date: str, content: str) -> dict:
    """POST {action:"create", slot, date, content} vers le GAS."""
    if not DRIVE_GAS_URL:
        raise RuntimeError("DRIVE_GAS_URL non configuré dans .env")
    if slot not in ("B1", "B2"):
        raise ValueError(f"slot invalide : {slot!r} (attendu B1 ou B2)")

    resp = requests.post(
        DRIVE_GAS_URL,
        json={"action": "create", "slot": slot, "date": date, "content": content},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"GAS : {data['error']}")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Créer un article B1/B2 dans Drive/Littérature")
    ap.add_argument("--slot", required=True, choices=["B1", "B2"])
    ap.add_argument("--date", required=True, help="AAAA-MM-JJ (date du mercredi)")
    ap.add_argument("--file", required=True, help="Chemin du fichier .md à uploader")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as f:
        content = f.read()

    result = create_article(args.slot, args.date, content)
    print(f"✓ {result['name']} créé (id: {result['id']})")
