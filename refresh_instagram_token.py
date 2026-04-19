"""
refresh_instagram_token.py — Rafraîchit le token Instagram (valable 60 jours)
À lancer localement dès que le token expire.

Usage :
    python refresh_instagram_token.py
"""
import requests
from dotenv import load_dotenv, set_key
import os

load_dotenv()

TOKEN  = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
ENVFILE = os.path.join(os.path.dirname(__file__), ".env")

if not TOKEN:
    print("❌  INSTAGRAM_ACCESS_TOKEN absent du .env")
    exit(1)

print("🔄  Rafraîchissement du token Instagram...")
resp = requests.get(
    "https://graph.facebook.com/v21.0/oauth/access_token",
    params={
        "grant_type":        "fb_exchange_token",
        "client_id":         os.getenv("INSTAGRAM_APP_ID", ""),
        "client_secret":     os.getenv("INSTAGRAM_APP_SECRET", ""),
        "fb_exchange_token": TOKEN,
    },
    timeout=15,
)

if not resp.ok:
    print(f"❌  Erreur : {resp.json()}")
    exit(1)

new_token = resp.json().get("access_token", "")
if not new_token:
    print(f"❌  Réponse inattendue : {resp.json()}")
    exit(1)

# Sauvegarder dans .env
set_key(ENVFILE, "INSTAGRAM_ACCESS_TOKEN", new_token)
print(f"✅  Nouveau token sauvegardé dans .env")
print(f"\n⚠️  N'oubliez pas de mettre à jour le secret GitHub :")
print(f"   INSTAGRAM_ACCESS_TOKEN = {new_token[:30]}...")
print(f"\n   → https://github.com/jeremielannoo-creator/QuotesAI/settings/secrets/actions")
