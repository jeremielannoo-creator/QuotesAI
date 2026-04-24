"""
utils/drive_reader.py — Lecture des articles depuis Google Drive.

Fonctionne via un Google Apps Script (GAS) déployé comme Web App.
  • Zéro Google Cloud, zéro credential
  • Simple requête HTTP GET / POST
  • Gratuit (GAS = inclus dans tout compte Google)

Setup : voir SETUP_GOOGLE_DRIVE.md
"""
import requests
from datetime import date, timedelta
from config import DRIVE_GAS_URL


def _today_slot() -> str | None:
    """
    Retourne le slot selon le jour courant.
      Mercredi → 'B1'
      Dimanche → 'B2'
      Autre    → None
    """
    wd = date.today().weekday()  # 0=lundi … 6=dimanche
    if wd == 2:
        return "B1"
    if wd == 6:
        return "B2"
    return None


def get_article_for_today() -> dict | None:
    """
    Récupère l'article à publier aujourd'hui (B1 le mercredi, B2 le dimanche).
    Cherche par slot uniquement — peu importe la date dans le nom de fichier.
    """
    slot = _today_slot()
    if not slot:
        print("  [drive_reader] Pas un jour de publication (mer/dim uniquement)")
        return None
    return get_article_by_slot(slot)


def get_article_by_slot(slot: str, date_str: str | None = None) -> dict | None:
    """
    Récupère le premier article Drive dont le nom contient '-B1' ou '-B2'.

    slot     : 'B1' ou 'B2'
    date_str : optionnel — si fourni, cherche d'abord AAAA-MM-JJ-slot,
               puis replie sur slot seul si introuvable.
    """
    if not DRIVE_GAS_URL:
        print("  [drive_reader] DRIVE_GAS_URL non configuré dans .env")
        return None

    params = {"slot": slot}
    if date_str:
        params["date"] = date_str   # GAS tente l'exact en premier

    try:
        resp = requests.get(DRIVE_GAS_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [drive_reader] Erreur HTTP : {e}")
        return None

    if "error" in data:
        print(f"  [drive_reader] {data['error']}")
        return None

    print(f"  [drive_reader] Fichier : {data['name']}")

    from agents.agent_article import parse_article_from_text
    article = parse_article_from_text(data["content"], source_name=data["name"])
    article["_drive_file_id"] = data.get("id")
    return article


def mark_as_published(article: dict):
    """
    Déplace l'article dans 'Publiés/' via le GAS (HTTP POST).
    """
    file_id = article.get("_drive_file_id")
    if not file_id or not DRIVE_GAS_URL:
        return
    try:
        resp = requests.post(
            DRIVE_GAS_URL,
            json={"fileId": file_id},
            timeout=30,
        )
        if resp.ok:
            data = resp.json()
            if "error" in data:
                print(f"  [drive_reader] Archivage : {data['error']}")
            else:
                print(f"  [drive_reader] Archivé dans 'Publiés/'")
    except Exception as e:
        print(f"  [drive_reader] Archivage impossible : {e}")
