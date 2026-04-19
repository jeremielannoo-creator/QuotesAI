"""
Agent 4 — Montage vidéo avec FFmpeg
  1. Redimensionne / recadre la vidéo en 9:16 (1080×1920)
  2. Superpose l'overlay (citation) via Pillow → PNG transparent
  3. Mélange la musique avec un fade in/out
  4. Exporte un MP4 H.264 prêt pour Instagram/TikTok
"""
import os
import time
import random
import subprocess
import ffmpeg
from utils.text_overlay import create_overlay
from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_DURATION,
    OUTPUT_DIR, TEMP_DIR,
)


def render_video(
    video_path: str,
    quote: str,
    author: str,
    music_path: str | None = None,
    mood: str = "calm",
    color_grade: bool = True,
) -> str:
    """
    Produit la vidéo finale.

    Args:
        video_path:   Chemin du fichier MP4 de fond
        quote:        Texte de la citation
        author:       Nom de l'auteur
        music_path:   Chemin MP3/AAC (optionnel)
        color_grade:  Applique un grade colorimétrique cinématique (défaut: True)

    Returns:
        Chemin du fichier MP4 final dans OUTPUT_DIR
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # ── Étape 1 : overlay texte ────────────────────────────────────────────────
    print("  [agent_render] Génération de l'overlay texte...")
    overlay_path = create_overlay(quote, author, mood=mood)

    # ── Étape 2 : construire le filtre FFmpeg ──────────────────────────────────
    output_path = os.path.join(OUTPUT_DIR, f"quote_{int(time.time())}.mp4")
    print(f"  [agent_render] Montage FFmpeg → {output_path}")

    _run_ffmpeg(video_path, overlay_path, music_path, output_path,
               mood=mood, color_grade=color_grade)

    print(f"  [agent_render] ✓ Vidéo prête : {output_path}")
    return output_path


# ── Fonctions internes ─────────────────────────────────────────────────────────

def _run_ffmpeg(
    video_path: str,
    overlay_path: str,
    music_path: str | None,
    output_path: str,
    mood: str = "calm",
    color_grade: bool = True,
):
    """
    Construit et exécute la commande FFmpeg via le module ffmpeg-python.

    Filtres :
      - scale+crop      → 1080×1920 (recadrage centre)
      - trim            → durée max VIDEO_DURATION secondes
      - eq / colorbalance → grade cinématique selon le mood
      - overlay         → superpose le PNG transparent
      - (optionnel) amix → mélange audio musique + son original
    """
    dur = VIDEO_DURATION

    # Entrée vidéo
    v_in = ffmpeg.input(video_path)

    # Traitement vidéo : redimensionner, recadrer, tronquer
    v = (
        v_in.video
        .filter("scale",
                w=f"{VIDEO_WIDTH}",
                h=f"{VIDEO_HEIGHT}",
                force_original_aspect_ratio="increase")
        .filter("crop", w=VIDEO_WIDTH, h=VIDEO_HEIGHT)
        .trim(duration=dur)
        .filter("setpts", "PTS-STARTPTS")
    )

    # ── Grade colorimétrique cinématique ──────────────────────────────────────
    if color_grade:
        if mood in ("triumphant", "energetic"):
            # Tons chauds dorés — style golden hour Tyler Glass
            v = (v
                 .filter("eq", saturation=1.18, brightness=0.03, contrast=1.06)
                 .filter("colorbalance",
                         rs=0.03, gs=0.0,  bs=-0.04,   # ombres : chaud
                         rm=0.02, gm=0.0,  bm=-0.03,   # mi-tons
                         rh=0.01, gh=0.0,  bh=-0.01))  # hautes lumières
        elif mood == "melancholic":
            # Tons froids désaturés — mélancolie poétique
            v = (v
                 .filter("eq", saturation=0.88, brightness=0.0, contrast=1.04)
                 .filter("colorbalance",
                         rs=-0.02, gs=0.0, bs=0.04,
                         rm=-0.01, gm=0.0, bm=0.03,
                         rh=0.0,   gh=0.0, bh=0.01))
        elif mood == "contemplative":
            # Légèrement désaturé, neutre, cinématique
            v = v.filter("eq", saturation=0.92, brightness=0.01, contrast=1.05)
        else:
            # calm + défaut : légère chaleur douce
            v = (v
                 .filter("eq", saturation=1.08, brightness=0.02, contrast=1.04)
                 .filter("colorbalance",
                         rs=0.02, gs=0.0, bs=-0.02,
                         rm=0.01, gm=0.0, bm=-0.01,
                         rh=0.0,  gh=0.0, bh=0.0))

    # Overlay texte
    overlay_in = ffmpeg.input(overlay_path)
    v_final    = ffmpeg.overlay(v, overlay_in, x=0, y=0)

    # ── Cas 1 : avec musique ───────────────────────────────────────────────────
    if music_path and os.path.exists(music_path):
        # Choisir un point de départ aléatoire dans la piste
        start_time = _random_music_start(music_path, dur)
        print(f"  [agent_render] Musique : départ à {start_time:.1f}s")

        a_music = (
            ffmpeg.input(music_path, ss=start_time).audio
            .filter("volume", 0.35)
            .filter("afade", t="in",  st=0,      d=2)
            .filter("afade", t="out", st=dur - 3, d=3)
            .filter("atrim", duration=dur)
            .filter("asetpts", "PTS-STARTPTS")
        )

        # Vérifier si la vidéo source a un flux audio
        try:
            probe     = ffmpeg.probe(video_path)
            has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
        except Exception:
            has_audio = False

        if has_audio:
            a_video = (
                v_in.audio
                .filter("volume", 0.15)
                .filter("atrim", duration=dur)
                .filter("asetpts", "PTS-STARTPTS")
            )
            a_final = ffmpeg.filter([a_video, a_music], "amix", inputs=2, duration="first")
        else:
            a_final = a_music

        out = ffmpeg.output(
            v_final, a_final, output_path,
            vcodec="libx264", acodec="aac",
            video_bitrate="4M", audio_bitrate="192k",
            r=30, pix_fmt="yuv420p", t=dur,
        )

    # ── Cas 2 : sans musique ───────────────────────────────────────────────────
    else:
        out = ffmpeg.output(
            v_final, output_path,
            vcodec="libx264",
            video_bitrate="4M",
            r=30, pix_fmt="yuv420p", t=dur,
            an=None,
        )

    ffmpeg.run(out, overwrite_output=True, quiet=False)


def _random_music_start(music_path: str, video_dur: float) -> float:
    """
    Retourne un point de départ aléatoire dans la piste musicale,
    en s'assurant qu'il reste assez de contenu pour couvrir la vidéo.
    """
    try:
        probe      = ffmpeg.probe(music_path)
        audio_info = next(
            s for s in probe["streams"] if s["codec_type"] == "audio"
        )
        music_dur  = float(audio_info.get("duration", 0))
        margin     = video_dur + 3   # garde 3s de marge pour le fade out
        max_start  = max(0.0, music_dur - margin)
        return round(random.uniform(0, max_start), 1)
    except Exception:
        return 0.0


def check_ffmpeg() -> bool:
    """Vérifie que ffmpeg est installé et accessible."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


if __name__ == "__main__":
    if not check_ffmpeg():
        print("ERREUR : FFmpeg n'est pas installé ou non trouvé dans le PATH.")
        print("Télécharger sur : https://ffmpeg.org/download.html")
    else:
        # Test rapide
        import sys
        if len(sys.argv) == 2:
            out = render_video(
                sys.argv[1],
                "Ce qui ne me tue pas me rend plus fort.",
                "Friedrich Nietzsche",
            )
            print("Rendu :", out)
