"""
agents/agent_video_ai.py — Génération d'un fond vidéo par IA text-to-video.

Deux usages, tous les deux optionnels (le pipeline retombe toujours sur les
banques de stock si ça échoue) :

1. **API HuggingFace Inference Providers** — activée par VIDEO_AI_ENABLED=1.
   Le modèle tourne chez un provider (fal.ai, Replicate…), pas sur le runner :
   les modèles text-to-video demandent 12–24 Go de VRAM, ce qu'un runner
   GitHub Actions (CPU seul, 7 Go de RAM) ne peut pas fournir. C'est donc un
   appel réseau facturé au clip, d'où le flag désactivé par défaut.

2. **Banque de clips pré-générés** — le mode gratuit, recommandé.
   `python -m agents.agent_video_ai --prompts 12` imprime des prompts prêts à
   coller dans Google Flow (labs.google/fx). Tu déposes les MP4 obtenus dans
   assets/backgrounds/<famille>/ et agent_video les consomme en priorité, sans
   jamais repasser deux fois sur le même clip.
"""
import argparse
import os
import time

from agents.agent_scenes import pick_family, t2v_prompt, MOOD_FAMILIES
from config import HF_TOKEN, TEMP_DIR, VIDEO_AI_ENABLED, VIDEO_AI_MODEL


def generate_background(mood: str, family: str) -> str | None:
    """
    Génère un clip de fond via l'API HuggingFace. Retourne le chemin du MP4,
    ou None si désactivé / indisponible (l'appelant se rabat sur le stock).
    """
    if not VIDEO_AI_ENABLED:
        return None
    if not HF_TOKEN:
        print("  [video_ai] VIDEO_AI_ENABLED=1 mais HF_TOKEN absent — ignoré")
        return None

    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        print("  [video_ai] huggingface_hub non installé (pip install huggingface_hub)")
        return None

    prompt = t2v_prompt(mood, family)
    print(f"  [video_ai] {VIDEO_AI_MODEL} ← {prompt[:70]}…")

    try:
        client = InferenceClient(api_key=HF_TOKEN)
        video  = client.text_to_video(prompt, model=VIDEO_AI_MODEL)
    except Exception as e:
        print(f"  [video_ai] Échec de la génération : {e}")
        return None

    os.makedirs(TEMP_DIR, exist_ok=True)
    dest = os.path.join(TEMP_DIR, f"ai_{family}_{int(time.time())}.mp4")
    with open(dest, "wb") as fh:
        fh.write(video)
    print(f"  [video_ai] ✓ Clip généré : {dest} ({len(video) / 1_048_576:.1f} Mo)")
    return dest


def print_prompt_batch(n: int) -> None:
    """Imprime n prompts variés à coller dans Google Flow / un modèle HF local."""
    moods = list(MOOD_FAMILIES)
    print("\nPrompts text-to-video — à coller dans labs.google/fx/tools/flow")
    print("Format de sortie : 9:16, ~5 s. Ranger les MP4 dans "
          "assets/backgrounds/<famille>/\n")
    for i in range(n):
        mood   = moods[i % len(moods)]
        family = pick_family(mood)
        print(f"{i + 1:2}. [{mood} / {family}]")
        print(f"    {t2v_prompt(mood, family)}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Fonds vidéo générés par IA")
    p.add_argument("--prompts", type=int, metavar="N",
                   help="Imprime N prompts pour Google Flow au lieu d'appeler l'API")
    p.add_argument("--mood", default="calm", help="Humeur pour un test d'appel API")
    args = p.parse_args()

    if args.prompts:
        print_prompt_batch(args.prompts)
    else:
        print(generate_background(args.mood, pick_family(args.mood)))
