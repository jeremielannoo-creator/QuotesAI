"""
get_tiktok_token.py — OAuth TikTok initial
À lancer UNE SEULE FOIS pour obtenir access_token + refresh_token.
Ensuite le pipeline se renouvelle automatiquement via le refresh_token.

Usage :
    python get_tiktok_token.py
"""
import webbrowser
import requests
import urllib.parse
from dotenv import set_key
import os

# ── Credentials Sandbox TikTok ─────────────────────────────────────────────
CLIENT_KEY    = "sbawqz0csa468gz8j1"
CLIENT_SECRET = "KDQYGJOLnkyOq3zrMZDk3dq8EYsLMQ4u"
REDIRECT_URI  = "https://example.com"
SCOPE         = "user.info.basic,video.publish"
ENVFILE       = os.path.join(os.path.dirname(__file__), ".env")

# ── Étape 1 : Ouvrir le navigateur ─────────────────────────────────────────
auth_url = (
    "https://www.tiktok.com/v2/auth/authorize?"
    + urllib.parse.urlencode({
        "client_key":    CLIENT_KEY,
        "scope":         SCOPE,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "state":         "quotesai",
    })
)

print("\n=== ÉTAPE 1 ===")
print("Ouverture du navigateur pour autoriser TikTok...")
webbrowser.open(auth_url)

print("\n=== ÉTAPE 2 ===")
print("Après avoir autorisé, tu seras redirigé vers example.com")
print("L'URL ressemblera à : https://example.com?code=XXXX&state=quotesai")

raw = input("\nColle ici l'URL complète de redirection : ").strip()

# Extraire le code de l'URL complète
if "code=" in raw:
    from urllib.parse import urlparse, parse_qs, unquote
    parsed = urlparse(raw if raw.startswith("http") else "https://example.com?" + raw.split("?")[-1])
    code   = unquote(parse_qs(parsed.query)["code"][0])
    print(f"  → Code extrait : {code[:30]}...")
else:
    from urllib.parse import unquote
    code = unquote(raw)

# ── Étape 3 : Échanger le code contre les tokens ───────────────────────────
print("\n=== ÉTAPE 3 : Échange du code... ===")
resp = requests.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "client_key":    CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code":          code,
        "grant_type":    "authorization_code",
        "redirect_uri":  REDIRECT_URI,
    },
)

data = resp.json()

if "access_token" not in data:
    print(f"\n❌  Erreur : {data}")
    exit(1)

access_token   = data["access_token"]
refresh_token  = data.get("refresh_token", "")
open_id        = data.get("open_id", "")
expires_in     = data.get("expires_in", 86400)
refresh_exp    = data.get("refresh_expires_in", 31536000)

print("\n=== ✅ SUCCÈS ===")
print(f"access_token         : {access_token[:30]}...")
print(f"refresh_token        : {refresh_token[:30] if refresh_token else 'absent'}...")
print(f"open_id              : {open_id}")
print(f"Expiration token     : {expires_in // 3600}h")
print(f"Expiration refresh   : {refresh_exp // 86400} jours")

# ── Sauvegarder dans .env ──────────────────────────────────────────────────
set_key(ENVFILE, "TIKTOK_ACCESS_TOKEN",  access_token)
set_key(ENVFILE, "TIKTOK_OPEN_ID",       open_id)
if refresh_token:
    set_key(ENVFILE, "TIKTOK_REFRESH_TOKEN", refresh_token)

print("\n✅  Tokens sauvegardés dans .env")
print("\n⚠️  Ajoutez ces secrets dans GitHub :")
print("   TIKTOK_ACCESS_TOKEN  → (valeur ci-dessus)")
print("   TIKTOK_OPEN_ID       → (valeur ci-dessus)")
if refresh_token:
    print("   TIKTOK_REFRESH_TOKEN → (valeur ci-dessus)  ← LE PLUS IMPORTANT")
print(f"\n   → https://github.com/jeremielannoo-creator/QuotesAI/settings/secrets/actions")
