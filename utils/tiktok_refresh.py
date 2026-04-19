"""
utils/tiktok_refresh.py — Renouvelle l'access_token TikTok via le refresh_token
Appelé automatiquement en début de pipeline si TIKTOK_REFRESH_TOKEN est défini.

Le refresh_token est valable 365 jours.
L'access_token est valable 24h — on le renouvelle à chaque run.
"""
import os
import requests
from dotenv import set_key

_ENVFILE      = os.path.join(os.path.dirname(__file__), "..", ".env")
_TOKEN_URL    = "https://open.tiktokapis.com/v2/oauth/token/"

CLIENT_KEY    = "sbawqz0csa468gz8j1"
CLIENT_SECRET = "KDQYGJOLnkyOq3zrMZDk3dq8EYsLMQ4u"


def refresh_tiktok_token() -> str | None:
    """
    Utilise le TIKTOK_REFRESH_TOKEN pour obtenir un nouvel access_token.

    - Met à jour la variable d'environnement TIKTOK_ACCESS_TOKEN en mémoire
    - Met à jour le .env local si présent
    - Retourne le nouvel access_token, ou None si le refresh_token est absent

    Le nouveau token est automatiquement pris en compte par config.py
    car os.environ est mis à jour directement.
    """
    refresh_token = os.getenv("TIKTOK_REFRESH_TOKEN", "")
    if not refresh_token:
        return None  # Pas de refresh token → rien à faire

    resp = requests.post(
        _TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key":    CLIENT_KEY,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )

    data = resp.json()
    new_token = data.get("access_token", "")

    if not new_token:
        print(f"  [tiktok_refresh] ⚠ Échec du renouvellement : {data}")
        return None

    # Mettre à jour en mémoire (lu par config.py via os.environ)
    os.environ["TIKTOK_ACCESS_TOKEN"] = new_token

    # Mettre à jour le .env local si disponible
    if os.path.exists(_ENVFILE):
        set_key(_ENVFILE, "TIKTOK_ACCESS_TOKEN", new_token)

    # Si le refresh_token a aussi été renouvelé, le sauvegarder
    new_refresh = data.get("refresh_token", "")
    if new_refresh and new_refresh != refresh_token:
        os.environ["TIKTOK_REFRESH_TOKEN"] = new_refresh
        if os.path.exists(_ENVFILE):
            set_key(_ENVFILE, "TIKTOK_REFRESH_TOKEN", new_refresh)

    expires_h = data.get("expires_in", 86400) // 3600
    print(f"  [tiktok_refresh] ✓ Token renouvelé (valide {expires_h}h)")
    return new_token
