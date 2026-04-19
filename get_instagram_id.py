"""
get_instagram_id.py — Trouve l'ID Instagram Business Account correct
Le INSTAGRAM_USER_ID doit être l'ID du compte Instagram, pas celui de Facebook.

Usage :
    python get_instagram_id.py
"""
import requests
from dotenv import load_dotenv, set_key
import os

load_dotenv()

TOKEN   = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
ENVFILE = os.path.join(os.path.dirname(__file__), ".env")

if not TOKEN:
    print("❌  INSTAGRAM_ACCESS_TOKEN absent du .env")
    exit(1)

# ── Étape 1 : lister les Pages Facebook liées au compte ───────────────────
print("🔍  Recherche des Pages Facebook liées au token...")
resp = requests.get(
    "https://graph.facebook.com/v21.0/me/accounts",
    params={"access_token": TOKEN},
    timeout=15,
)

if not resp.ok:
    print(f"❌  Erreur : {resp.json()}")
    exit(1)

pages = resp.json().get("data", [])
if not pages:
    print("❌  Aucune Page Facebook trouvée.")
    print("    Assurez-vous que votre compte Instagram Business est lié à une Page Facebook.")
    exit(1)

print(f"\n✓  {len(pages)} Page(s) trouvée(s) :\n")

# ── Étape 2 : trouver l'ID Instagram Business de chaque Page ──────────────
found = []
for page in pages:
    page_id    = page["id"]
    page_name  = page["name"]
    page_token = page["access_token"]

    resp2 = requests.get(
        f"https://graph.facebook.com/v21.0/{page_id}",
        params={
            "fields":       "instagram_business_account",
            "access_token": page_token,
        },
        timeout=15,
    )
    data = resp2.json()
    ig   = data.get("instagram_business_account", {})
    ig_id = ig.get("id", "")

    if ig_id:
        print(f"  📄 Page : {page_name} (ID: {page_id})")
        print(f"  📸 Instagram Business Account ID : {ig_id}  ← C'EST CETTE VALEUR")
        found.append((page_name, ig_id, page_token))
    else:
        print(f"  📄 Page : {page_name} — pas de compte Instagram Business lié")

if not found:
    print("\n❌  Aucun compte Instagram Business trouvé.")
    print("    Vérifiez que votre Instagram est en mode Professionnel (Business/Créateur)")
    print("    et lié à une Page Facebook.")
    exit(1)

if len(found) == 1:
    _, ig_id, page_token = found[0]
else:
    print(f"\nPlusieurs comptes trouvés, lequel utiliser ? (1-{len(found)})")
    for i, (name, ig_id, _) in enumerate(found, 1):
        print(f"  {i}. {name} — {ig_id}")
    choice = int(input("Choix : ")) - 1
    _, ig_id, page_token = found[choice]

# ── Sauvegarder dans .env ─────────────────────────────────────────────────
set_key(ENVFILE, "INSTAGRAM_USER_ID", ig_id)
print(f"\n✅  INSTAGRAM_USER_ID = {ig_id} sauvegardé dans .env")
print(f"\n⚠️  Mettez à jour le secret GitHub :")
print(f"   INSTAGRAM_USER_ID = {ig_id}")
print(f"\n   → https://github.com/jeremielannoo-creator/QuotesAI/settings/secrets/actions")
