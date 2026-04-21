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


def _today_slot() -> tuple[str, str] | tuple[None, None]:
    """
    Retourne (date_str, slot) selon le jour courant.
      Mercredi → (date du jour, 'B1')
      Dimanche → (date du mercredi précédent, 'B2')
      Autre    → (None, None)
    """
    today = date.today()
    wd = today.weekday()  # 0=lundi … 6=dimanche

    if wd == 2:  # mercredi
        return today.strftime("%Y-%m-%d"), "B1"
    elif wd == 6:  # dimanche
        wed = today - timedelta(days=4)
        return wed.strftime("%Y-%m-%d"), "B2"
    return None, None


def get_article_for_today() -> dict | None:
    """
    Récupère l'article à publier aujourd'hui selon la convention B1/B2.
    Retourne None si ce n'est pas un jour de publication ou fichier absent.
    """
    d, slot = _today_slot()
    if not d:
        print(f"  [drive_reader] Pas un jour de publication (mer/dim uniquement)")
        return None
    return get_article_by_slot(d, slot)


def get_article_by_slot(date_str: str, slot: str) -> dict | None:
    """
    Récupère l'article Drive correspondant à AAAA-MM-JJ-B1 ou B2.
    Appelle le GAS Web App via HTTP GET.

    date_str : '2026-04-23'
    slot     : 'B1' ou 'B2'
    """
    if not DRIVE_GAS_URL:
        print("  [drive_reader] DRIVE_GAS_URL non configuré dans .env")
        return None

    pattern = f"{date_str}-{slot}"
    try:
        resp = requests.get(
            DRIVE_GAS_URL,
            params={"slot": slot, "date": date_str},
            timeout=30,
        )
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
