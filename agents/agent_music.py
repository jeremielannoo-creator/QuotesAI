"""
Agent 3 — Sélection de la musique dans la bibliothèque locale (assets/music/).

La recherche « Pixabay music » a été retirée : l'API Pixabay ne sert que des
images et des vidéos (le paramètre media_type=music est ignoré). Elle renvoyait
des JPEG, rejetés un à un avant de retomber de toute façon sur les fichiers
locaux.

Diversité :
  • chaque humeur accepte une catégorie principale et des catégories voisines.
    Avant, contemplative (30 % des citations) et triumphant n'avaient aucun
    fichier correspondant et tiraient au hasard dans toute la banque — épique
    compris ;
  • les dernières pistes jouées sont écartées (mémoire dans db/state.json) ;
  • agent_render démarre la piste à un point aléatoire.

Catégorie d'un fichier : son sous-dossier (assets/music/contemplative/x.mp3)
ou, à défaut, le préfixe de son nom (calm_piano_2.mp3 → calm). Pour enrichir
la banque, il suffit de déposer des fichiers selon l'une de ces conventions.
"""
import os
import random

from config import MUSIC_DIR
from utils import state

_AUDIO_EXT = {".mp3", ".m4a", ".aac", ".wav", ".ogg"}

# Humeur → catégories acceptées. La première est privilégiée (poids 3).
MOOD_CATEGORIES: dict[str, list[str]] = {
    "calm":          ["calm", "warm"],
    "warm":          ["warm", "calm"],
    "contemplative": ["contemplative", "calm", "melancholic"],
    "melancholic":   ["melancholic", "contemplative", "calm"],
    "energetic":     ["energetic", "triumphant"],
    "triumphant":    ["triumphant", "energetic"],
}

# Nombre de pistes récentes à ne pas rejouer (si la catégorie en a assez)
_RECENT = 8


def select_music(mood: str) -> str | None:
    """
    Retourne le chemin d'une piste adaptée à l'humeur, en évitant les
    dernières jouées. None si la bibliothèque est vide (vidéo sans son).
    """
    library = _library()
    if not library:
        print("  [agent_music] Aucun fichier audio trouvé dans assets/music/")
        return None

    cats = MOOD_CATEGORIES.get(mood.lower(), [mood.lower()])
    pool = [(p, c) for p, c in library if c in cats] or library

    recent = state.recent_picks("music", n=_RECENT)
    fresh  = [(p, c) for p, c in pool if os.path.basename(p) not in recent]
    if not fresh:
        # Toute la catégorie a tourné récemment : la plus anciennement jouée
        fresh = [max(pool, key=lambda pc: recent.index(os.path.basename(pc[0])))]

    weights = [3.0 if c == cats[0] else 1.0 for _, c in fresh]
    path, cat = random.choices(fresh, weights=weights, k=1)[0]
    state.remember_pick("music", os.path.basename(path), keep=_RECENT)
    print(f"  [agent_music] ♪ {cat} ({mood}) : {os.path.basename(path)}")
    return path


def _library() -> list[tuple[str, str]]:
    """[(chemin, catégorie)] de tous les fichiers audio de assets/music/."""
    out = []
    for root, _dirs, files in os.walk(MUSIC_DIR):
        sub = os.path.relpath(root, MUSIC_DIR)
        for f in files:
            if os.path.splitext(f)[1].lower() not in _AUDIO_EXT:
                continue
            cat = sub.split(os.sep)[0] if sub != "." else f.split("_")[0]
            out.append((os.path.join(root, f), cat.lower()))
    return out


if __name__ == "__main__":
    for mood in MOOD_CATEGORIES:
        print(f"{mood}: {select_music(mood)}")
