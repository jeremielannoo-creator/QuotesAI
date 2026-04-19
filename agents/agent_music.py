"""
Agent 3 (musique) — Sélectionne une piste audio locale selon l'humeur de la citation.

Convention de nommage des fichiers dans assets/music/ :
  calm_01.mp3, calm_02.mp3
  energetic_01.mp3
  melancholic_01.mp3
  triumphant_01.mp3
  contemplative_01.mp3

Si aucun fichier ne correspond à l'humeur, on prend un fichier aléatoire.
Si le dossier est vide, on retourne None (vidéo sans musique).
"""
import os
import random
from config import MUSIC_DIR

# Correspondances humeur → mots-clés dans le nom de fichier
_MOOD_ALIASES: dict[str, list[str]] = {
    "calm":          ["calm", "peaceful", "relax", "zen", "soft"],
    "energetic":     ["energetic", "upbeat", "power", "drive", "epic"],
    "melancholic":   ["melancholic", "sad", "melancholy", "nostalgic", "emotional"],
    "triumphant":    ["triumphant", "victory", "hero", "strong", "bold"],
    "contemplative": ["contemplative", "ambient", "meditative", "deep", "mind"],
}


def select_music(mood: str) -> str | None:
    """
    Retourne le chemin d'un fichier audio correspondant à l'humeur,
    ou None si aucun fichier n'est disponible.

    Args:
        mood: valeur retournée par Gemini
              (calm | energetic | melancholic | triumphant | contemplative)
    """
    os.makedirs(MUSIC_DIR, exist_ok=True)

    all_files = _list_audio_files()
    if not all_files:
        print("  [agent_music] Aucun fichier audio trouvé dans assets/music/")
        return None

    # Chercher un fichier dont le nom contient un alias de l'humeur
    aliases = _MOOD_ALIASES.get(mood.lower(), [mood.lower()])
    matched = [
        f for f in all_files
        if any(alias in os.path.basename(f).lower() for alias in aliases)
    ]

    if matched:
        chosen = random.choice(matched)
        print(f"  [agent_music] Musique sélectionnée ({mood}) : {os.path.basename(chosen)}")
        return chosen

    # Fallback : fichier aléatoire
    chosen = random.choice(all_files)
    print(f"  [agent_music] Aucune musique '{mood}' trouvée, fallback : {os.path.basename(chosen)}")
    return chosen


def _list_audio_files() -> list[str]:
    """Retourne tous les fichiers audio dans MUSIC_DIR."""
    extensions = {".mp3", ".m4a", ".aac", ".wav", ".ogg"}
    files = []
    for fname in os.listdir(MUSIC_DIR):
        ext = os.path.splitext(fname)[1].lower()
        if ext in extensions:
            files.append(os.path.join(MUSIC_DIR, fname))
    return files


if __name__ == "__main__":
    for mood in ["calm", "energetic", "melancholic", "triumphant", "contemplative"]:
        print(f"{mood}: {select_music(mood)}")
