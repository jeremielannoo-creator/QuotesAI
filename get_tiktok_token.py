import webbrowser
import requests
import urllib.parse

# ── Credentials Sandbox TikTok ─────────────────────────
CLIENT_KEY    = "sbawqz0csa468gz8j1"     # <- Client key (Sandbox)
CLIENT_SECRET = "KDQYGJOLnkyOq3zrMZDk3dq8EYsLMQ4u"  # <- Client secret (Sandbox)
REDIRECT_URI  = "https://example.com"
SCOPE         = "user.info.basic,video.upload"

# ── Étape 1 : Ouvrir le navigateur pour autoriser ──────
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
print(f"URL : {auth_url}\n")
webbrowser.open(auth_url)

print("=== ÉTAPE 2 ===")
print("Après avoir autorisé, tu seras redirigé vers example.com")
print("L'URL ressemblera à : https://example.com?code=XXXX&state=quotesai")
print("Copie la valeur du paramètre 'code=' dans l'URL\n")

raw = input("Colle ici l'URL complète de redirection (ou juste le code) : ").strip()

# Extraire automatiquement le code si l'URL complète est collée
if "code=" in raw:
    from urllib.parse import urlparse, parse_qs, unquote
    parsed = urlparse(raw if raw.startswith("http") else "https://example.com?" + raw.split("?")[-1])
    code = unquote(parse_qs(parsed.query)["code"][0])
    print(f"  → Code extrait : {code[:30]}...")
else:
    from urllib.parse import unquote
    code = unquote(raw)

# ── Étape 3 : Échanger le code contre un token ─────────
print("\n=== ÉTAPE 3 : Échange du code contre le token... ===")
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
print("\nRésultat :", data)

if "access_token" in data:
    print("\n=== SUCCÈS ===")
    print(f"TIKTOK_ACCESS_TOKEN = {data['access_token']}")
    print(f"TIKTOK_OPEN_ID      = {data['open_id']}")
    print("\nCopie ces deux valeurs dans ton fichier .env !")
else:
    print("\nErreur — vérifie tes credentials et réessaie.")
