"""
Agent 4 — Montage vidéo avec FFmpeg.

Ce que fait le montage, dans l'ordre :
  1. Recadre le fond en 9:16 avec une marge pour le mouvement caméra
  2. Applique un grade colorimétrique selon l'humeur
  3. Simule un travelling lent (zoompan) — plus de plan totalement figé
  4. Incruste la séquence d'overlays : la citation se révèle ligne par ligne
  5. Mixe la musique avec fondus d'entrée et de sortie
  6. Exporte un MP4 H.264 prêt pour Instagram / TikTok / Facebook

La durée n'est plus fixe : elle est calculée sur le temps de lecture réel de
la citation (≈ 8–14 s au lieu de 30 s figées, où 20 s de vidéo ne montraient
plus rien de neuf).
"""
import os
import random
import subprocess
import time

import ffmpeg

from agents.agent_scenes import camera_move
from config import OUTPUT_DIR, TEMP_DIR, VIDEO_DURATION, VIDEO_HEIGHT, VIDEO_WIDTH
from utils import state
from utils.text_overlay import TEMPLATES, create_overlay_sequence

# ── Rythme de lecture ─────────────────────────────────────────────────────────
LEAD_IN     = 0.6    # la vidéo respire avant la première ligne
PER_LINE    = 1.05   # temps d'affichage d'une ligne supplémentaire
HOLD_OUT    = 3.5    # citation complète + auteur à l'écran
MIN_DURATION = 8.0

# Marge de recadrage : on travaille 20 % plus grand que la cible pour que le
# zoom ne dégrade jamais l'image (on ne fait que descendre vers 1080×1920).
_OVERSCAN = 1.20
_ZOOM_MAX = 1.12


def render_video(
    video_path: str,
    quote: str,
    author: str,
    music_path: str | None = None,
    mood: str = "calm",
    color_grade: bool = True,
) -> str:
    """
    Produit la vidéo finale et retourne son chemin dans OUTPUT_DIR.

    Args:
        video_path:  MP4 de fond
        quote:       Texte de la citation
        author:      Nom de l'auteur (vide → non affiché)
        music_path:  MP3/AAC optionnel
        mood:        humeur — pilote le grade, le gabarit et le mouvement
        color_grade: applique le grade cinématique
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # ── 1. Séquence d'overlays ────────────────────────────────────────────────
    template = _pick_template()
    seq      = create_overlay_sequence(quote, author, mood=mood, template=template)
    state.remember_template(template)
    print(f"  [agent_render] Gabarit : {template} — {seq['lines']} ligne(s)")

    # ── 2. Timeline ───────────────────────────────────────────────────────────
    durations, total = _timeline(seq["lines"])
    concat_path = _write_concat_list(seq["frames"], durations)
    print(f"  [agent_render] Durée calculée : {total:.1f}s")

    # ── 3. Montage ────────────────────────────────────────────────────────────
    output_path = os.path.join(OUTPUT_DIR, f"quote_{int(time.time())}.mp4")
    _run_ffmpeg(video_path, concat_path, music_path, output_path,
                duration=total, mood=mood, color_grade=color_grade)

    print(f"  [agent_render] ✓ Vidéo prête : {output_path}")
    return output_path


# ── Timeline ──────────────────────────────────────────────────────────────────

def _timeline(n_lines: int) -> tuple[list[float], float]:
    """
    Durée d'affichage de chaque overlay cumulatif.
    frames[0] = fond seul, frames[i] = i lignes, frames[n] = tout + auteur.
    """
    n = max(n_lines, 1)
    per_line = PER_LINE
    total    = LEAD_IN + n * per_line + HOLD_OUT

    if total > VIDEO_DURATION:                    # citation très longue
        per_line = max(0.5, (VIDEO_DURATION - LEAD_IN - HOLD_OUT) / n)
        total    = LEAD_IN + n * per_line + HOLD_OUT
    total = max(total, MIN_DURATION)

    hold = total - LEAD_IN - n * per_line
    return [LEAD_IN] + [per_line] * (n - 1) + [per_line + hold], total


def _write_concat_list(frames: list[str], durations: list[float]) -> str:
    """
    Écrit la playlist du démultiplexeur concat. On passe par ce format plutôt
    que par des filtres `enable=` : les expressions temporelles contiennent des
    virgules, que ffmpeg-python n'échappe pas dans un filtergraph.
    """
    path = os.path.join(TEMP_DIR, "overlay_seq.txt")
    with open(path, "w", encoding="utf-8") as f:
        for frame, dur in zip(frames, durations):
            f.write(f"file '{frame.replace(os.sep, '/')}'\n")
            f.write(f"duration {dur:.3f}\n")
        # Le démultiplexeur concat ignore la durée du dernier élément :
        # on le répète pour que la séquence aille bien jusqu'au bout.
        f.write(f"file '{frames[-1].replace(os.sep, '/')}'\n")
    return path


def _pick_template() -> str:
    """Gabarit différent de la publication précédente."""
    pool = [t for t in TEMPLATES if t != state.last_template()] or list(TEMPLATES)
    return random.choice(pool)


# ── FFmpeg ────────────────────────────────────────────────────────────────────

def _run_ffmpeg(
    video_path: str,
    concat_path: str,
    music_path: str | None,
    output_path: str,
    duration: float,
    mood: str = "calm",
    color_grade: bool = True,
):
    fps = 30
    # -stream_loop : les clips IA font souvent 5–8 s, plus court que la vidéo
    v_in = ffmpeg.input(video_path, stream_loop=-1, t=duration)

    work_w = int(VIDEO_WIDTH * _OVERSCAN) // 2 * 2
    work_h = int(VIDEO_HEIGHT * _OVERSCAN) // 2 * 2

    v = (
        v_in.video
        # zoompan consomme une frame d'entrée par frame de sortie : sans
        # normalisation préalable, un fond en 24 fps donnerait une vidéo
        # raccourcie d'un cinquième.
        .filter("fps", fps=fps)
        .filter("scale", w=work_w, h=work_h, force_original_aspect_ratio="increase")
        .filter("crop", w=work_w, h=work_h)
        .filter("setpts", "PTS-STARTPTS")
    )

    v = _grade(v, mood) if color_grade else v
    v = _camera(v, mood, duration, fps)

    # Séquence d'overlays (PNG RGBA enchaînés par le démultiplexeur concat)
    overlay_in = ffmpeg.input(concat_path, format="concat", safe=0)
    v_final    = ffmpeg.overlay(v, overlay_in, x=0, y=0, eof_action="repeat")

    common = dict(vcodec="libx264", video_bitrate="4M", r=fps,
                  pix_fmt="yuv420p", t=duration)

    if music_path and os.path.exists(music_path):
        a_final = _audio(v_in, video_path, music_path, duration)
        out = ffmpeg.output(v_final, a_final, output_path,
                            acodec="aac", audio_bitrate="192k", **common)
    else:
        out = ffmpeg.output(v_final, output_path, an=None, **common)

    ffmpeg.run(out, overwrite_output=True, quiet=False)


def _grade(v, mood: str):
    """Grade colorimétrique cinématique selon l'humeur."""
    if mood in ("triumphant", "energetic"):
        return (v.filter("eq", saturation=1.18, brightness=0.03, contrast=1.06)
                 .filter("colorbalance", rs=0.03, gs=0.0, bs=-0.04,
                         rm=0.02, gm=0.0, bm=-0.03, rh=0.01, gh=0.0, bh=-0.01))
    if mood == "melancholic":
        return (v.filter("eq", saturation=0.88, contrast=1.04)
                 .filter("colorbalance", rs=-0.02, gs=0.0, bs=0.04,
                         rm=-0.01, gm=0.0, bm=0.03, rh=0.0, gh=0.0, bh=0.01))
    if mood == "contemplative":
        return v.filter("eq", saturation=0.92, brightness=0.01, contrast=1.05)
    return (v.filter("eq", saturation=1.08, brightness=0.02, contrast=1.04)
             .filter("colorbalance", rs=0.02, gs=0.0, bs=-0.02,
                     rm=0.01, gm=0.0, bm=-0.01))


def _camera(v, mood: str, duration: float, fps: int):
    """
    Travelling lent simulé. On part d'une image 20 % plus grande que la cible :
    même au zoom maximum, on ne remonte jamais au-dessus de la résolution
    native, donc aucune perte de netteté.
    """
    move = camera_move(mood)
    if move == "still":
        return v.filter("scale", w=VIDEO_WIDTH, h=VIDEO_HEIGHT)

    frames = max(int(duration * fps), 1)
    step   = (_ZOOM_MAX - 1.0) / frames
    if move == "in":
        z = f"min(1.0+{step:.6f}*on,{_ZOOM_MAX})"
    else:
        z = f"max({_ZOOM_MAX}-{step:.6f}*on,1.0)"

    return v.filter(
        "zoompan", z=z, d=1, fps=fps,
        x="iw/2-(iw/zoom/2)", y="ih/2-(ih/zoom/2)",
        s=f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
    )


def _audio(v_in, video_path: str, music_path: str, duration: float):
    """Musique en fondu + son d'ambiance de la source si elle en a un."""
    start = _random_music_start(music_path, duration)
    print(f"  [agent_render] Musique : départ à {start:.1f}s")

    fade_out = max(duration - 2.5, 0.1)
    a_music = (
        ffmpeg.input(music_path, ss=start).audio
        .filter("volume", 0.35)
        .filter("afade", t="in", st=0, d=1.5)
        .filter("afade", t="out", st=fade_out, d=2.5)
        .filter("atrim", duration=duration)
        .filter("asetpts", "PTS-STARTPTS")
    )

    try:
        probe     = ffmpeg.probe(video_path)
        has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
    except Exception:
        has_audio = False

    if not has_audio:
        return a_music

    a_video = (
        v_in.audio
        .filter("volume", 0.15)
        .filter("atrim", duration=duration)
        .filter("asetpts", "PTS-STARTPTS")
    )
    return ffmpeg.filter([a_video, a_music], "amix", inputs=2, duration="first")


def _random_music_start(music_path: str, video_dur: float) -> float:
    """Point de départ aléatoire dans la piste, en gardant de quoi couvrir."""
    try:
        probe = ffmpeg.probe(music_path)
        info  = next(s for s in probe["streams"] if s["codec_type"] == "audio")
        max_start = max(0.0, float(info.get("duration", 0)) - (video_dur + 3))
        return round(random.uniform(0, max_start), 1)
    except Exception:
        return 0.0


def check_ffmpeg() -> bool:
    """Vérifie que ffmpeg est installé et accessible."""
    try:
        return subprocess.run(["ffmpeg", "-version"], capture_output=True,
                              text=True, timeout=5).returncode == 0
    except FileNotFoundError:
        return False


if __name__ == "__main__":
    import sys
    if not check_ffmpeg():
        print("ERREUR : FFmpeg introuvable dans le PATH.")
    elif len(sys.argv) == 2:
        print("Rendu :", render_video(
            sys.argv[1],
            "Ce qui ne me tue pas me rend plus fort.",
            "Friedrich Nietzsche",
            mood="energetic",
        ))
