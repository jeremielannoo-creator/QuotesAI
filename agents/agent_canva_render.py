"""
agents/agent_canva_render.py — Génération de Reels via Canva Connect API.

Flux :
  1. Échange le refresh token contre un access token
  2. Appelle generate-design (POST /v1/designs/generate)
  3. Attend la fin de la génération (polling)
  4. Exporte en MP4
  5. Télécharge le MP4 localement

Secrets requis :
  CANVA_CLIENT_ID
  CANVA_CLIENT_SECRET
  CANVA_REFRESH_TOKEN
"""
import os
import time
import requests
from config import BASE_DIR

CANVA_API   = "https://api.canva.com/rest/v1"
CANVA_AUTH  = "https://api.canva.com/rest/v1/oauth/token"

CLIENT_ID      = os.getenv("CANVA_CLIENT_ID", "")
CLIENT_SECRET  = os.getenv("CANVA_CLIENT_SECRET", "")
REFRESH_TOKEN  = os.getenv("CANVA_REFRESH_TOKEN", "")


def _get_access_token() -> str:
    """Échange le refresh token contre un access token."""
    resp = requests.post(
        CANVA_AUTH,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=15,
    )
    if not resp.ok:
        raise RuntimeError(f"Canva auth : {resp.status_code} — {resp.text}")
    return resp.json()["access_token"]


def _generate_design(token: str, title: str, author: str, excerpt: str) -> str:
    """Lance la génération du design Story et retourne le design_id."""
    query = (
        f'Instagram Story / Reel literary book review. Dark elegant aesthetic. '
        f'Book title: "{title}". Author: "{author}". '
        f'Quote: "{excerpt[:120]}". '
        f'Vertical 9:16. Moody atmospheric, dark background, warm tones. '
        f'Sophisticated bookstagram style.'
    )
    resp = requests.post(
        f"{CANVA_API}/designs/generate",
        json={"query": query, "design_type": "your_story"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Canva generate : {resp.status_code} — {resp.text}")

    data = resp.json()
    job_id     = data["job"]["id"]
    candidates = data["job"]["result"]["generated_designs"]
    candidate  = candidates[0]["candidate_id"]  # premier résultat
    print(f"  [canva] Design généré — job {job_id}, candidat {candidate}")
    return job_id, candidate


def _create_design(token: str, job_id: str, candidate_id: str) -> str:
    """Convertit le candidat en design éditable, retourne le design_id."""
    resp = requests.post(
        f"{CANVA_API}/designs/from-candidate",
        json={"job_id": job_id, "candidate_id": candidate_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Canva create : {resp.status_code} — {resp.text}")
    design_id = resp.json()["design_summary"]["id"]
    print(f"  [canva] Design créé : {design_id}")
    return design_id


def _export_mp4(token: str, design_id: str) -> str:
    """Lance l'export MP4 et retourne l'URL de téléchargement."""
    resp = requests.post(
        f"{CANVA_API}/exports",
        json={
            "design_id": design_id,
            "format": {"type": "mp4", "quality": "horizontal_1080p"},
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Canva export : {resp.status_code} — {resp.text}")

    job = resp.json()["job"]
    job_id = job["id"]

    # Polling jusqu'à success
    for _ in range(30):
        time.sleep(5)
        r = requests.get(
            f"{CANVA_API}/exports/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        status = r.json()["job"]["status"]
        if status == "success":
            url = r.json()["job"]["urls"][0]
            print(f"  [canva] ✓ Export MP4 prêt")
            return url
        if status == "failed":
            raise RuntimeError("Canva export échoué")
        print(f"  [canva] Export en cours ({status})…")

    raise RuntimeError("Canva export timeout")


def _download(url: str, dest: str) -> str:
    """Télécharge le MP4 et retourne le chemin local."""
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  [canva] ✓ Vidéo téléchargée : {dest}")
    return dest


def render_canva_reel(title: str, author: str, excerpt: str) -> str:
    """
    Génère un Reel Canva pour le livre et retourne le chemin local du MP4.

    Args:
        title:   Titre du livre
        author:  Auteur
        excerpt: Extrait du corps de l'article (120 chars max utilisés)

    Returns:
        Chemin absolu du fichier MP4 local
    """
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        raise RuntimeError(
            "CANVA_CLIENT_ID / CANVA_CLIENT_SECRET / CANVA_REFRESH_TOKEN manquants"
        )

    print(f"  [canva] Génération Reel pour : {title} — {author}")
    token = _get_access_token()

    job_id, candidate_id = _generate_design(token, title, author, excerpt)
    design_id = _create_design(token, job_id, candidate_id)
    mp4_url   = _export_mp4(token, design_id)

    dest = os.path.join(BASE_DIR, "output", f"canva_{int(time.time())}.mp4")
    return _download(mp4_url, dest)
