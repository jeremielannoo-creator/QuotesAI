"""
pipeline.py — Orchestrateur principal QuotesAI
Équivalent Make/Zapier : enchaîne les 5 agents en séquence.

Usage :
    python pipeline.py                         # Exécution immédiate
    python pipeline.py --platform instagram    # Instagram seulement
    python pipeline.py --platform tiktok       # TikTok seulement
    python pipeline.py --dry-run               # Rendu vidéo sans publier
"""
import argparse
import os
import sys
import traceback
from datetime import datetime
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table
from rich import print as rprint

from agents.agent_quote_db  import generate_quote
from agents.agent_video     import find_and_download_video
from agents.agent_music     import select_music
from agents.agent_render    import render_video, check_ffmpeg
from agents.agent_publisher import publish_instagram, publish_tiktok
from utils.video_host       import upload_video

console = Console()


def run(
    platform: str = "both",      # "instagram" | "tiktok" | "both"
    dry_run: bool = False,       # True = render seulement, pas de publication
) -> dict:
    """
    Lance le pipeline complet et retourne un résumé des résultats.

    Returns:
        {
          "quote":       str,
          "author":      str,
          "video_path":  str,
          "published":   {"instagram": str | None, "tiktok": str | None}
        }
    """
    started_at = datetime.now()
    results    = {}

    console.print(Panel.fit(
        "[bold cyan]QuotesAI Pipeline[/bold cyan]\n"
        f"Plateforme : [yellow]{platform}[/yellow]  |  "
        f"Dry-run : [yellow]{dry_run}[/yellow]",
        border_style="cyan",
    ))

    # ══════════════════════════════════════════════════════════════════════════
    # AGENT 1 — Génération de la citation (Gemini)
    # ══════════════════════════════════════════════════════════════════════════
    with console.status("[bold green]Agent 1/5 — Génération de la citation..."):
        quote_data = generate_quote()

    _print_quote_table(quote_data)
    results["quote"]  = quote_data["quote"]
    results["author"] = quote_data["author"]

    # ══════════════════════════════════════════════════════════════════════════
    # AGENT 2 — Recherche de la vidéo (Pexels)
    # ══════════════════════════════════════════════════════════════════════════
    with console.status("[bold green]Agent 2/5 — Recherche de la vidéo background..."):
        video_path = find_and_download_video(quote_data["keywords"], mood=quote_data["mood"])

    console.print(f"  ✓ Vidéo téléchargée : [dim]{video_path}[/dim]")
    results["video_path"] = video_path

    # ══════════════════════════════════════════════════════════════════════════
    # AGENT 3 — Sélection de la musique
    # ══════════════════════════════════════════════════════════════════════════
    with console.status("[bold green]Agent 3/5 — Sélection de la musique..."):
        music_path = select_music(quote_data["mood"])

    if music_path:
        console.print(f"  ✓ Musique : [dim]{os.path.basename(music_path)}[/dim]")
    else:
        console.print("  ⚠ Aucune musique disponible — vidéo sans son")

    # ══════════════════════════════════════════════════════════════════════════
    # AGENT 4 — Montage vidéo (FFmpeg + Pillow)
    # ══════════════════════════════════════════════════════════════════════════
    with console.status("[bold green]Agent 4/5 — Montage vidéo (FFmpeg)..."):
        final_video = render_video(
            video_path  = video_path,
            quote       = quote_data["quote"],
            author      = quote_data["author"],
            music_path  = music_path,
            mood        = quote_data["mood"],
        )

    console.print(f"  ✓ Vidéo rendue : [dim]{final_video}[/dim]")
    results["final_video"] = final_video

    if dry_run:
        console.print("\n[yellow]Mode dry-run : publication ignorée.[/yellow]")
        results["published"] = {"instagram": None, "tiktok": None}
        _print_summary(results, started_at)
        return results

    # ══════════════════════════════════════════════════════════════════════════
    # AGENT 5 — Upload + Publication
    # ══════════════════════════════════════════════════════════════════════════
    caption   = quote_data["quote"]
    hashtags  = quote_data["hashtags"]
    published = {"instagram": None, "tiktok": None}

    # Upload sur Cloudinary (URL publique requise par Instagram)
    with console.status("[bold green]Agent 5/5 — Upload Cloudinary..."):
        public_url = upload_video(final_video)

    if platform in ("instagram", "both"):
        with console.status("[bold green]Agent 5/5 — Publication Instagram..."):
            try:
                media_id = publish_instagram(public_url, caption, hashtags)
                published["instagram"] = media_id
                console.print(f"  ✓ [bold green]Instagram publié[/bold green] — ID : {media_id}")
            except Exception as e:
                console.print(f"  ✗ [red]Erreur Instagram : {e}[/red]")

    if platform in ("tiktok", "both"):
        with console.status("[bold green]Agent 5/5 — Publication TikTok..."):
            try:
                pub_id = publish_tiktok(public_url, caption, hashtags)
                published["tiktok"] = pub_id
                console.print(f"  ✓ [bold green]TikTok publié[/bold green] — publish_id : {pub_id}")
            except Exception as e:
                console.print(f"  ✗ [red]Erreur TikTok : {e}[/red]")

    results["published"] = published
    _print_summary(results, started_at)
    return results


# ── Helpers d'affichage ────────────────────────────────────────────────────────

def _print_quote_table(data: dict):
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column(style="bold cyan", width=12)
    t.add_column(style="white")
    t.add_row("Citation",  f'[italic]"{data["quote"]}"[/italic]')
    t.add_row("Auteur",    data["author"])
    t.add_row("Humeur",    data["mood"])
    t.add_row("Mots-clés", ", ".join(data["keywords"]))
    t.add_row("Hashtags",  " ".join(data["hashtags"][:6]) + " …")
    console.print(t)


def _print_summary(results: dict, started_at: datetime):
    elapsed = (datetime.now() - started_at).seconds
    console.print(Panel.fit(
        f"[bold green]Pipeline terminé[/bold green] en {elapsed}s\n"
        f"Vidéo : [dim]{results.get('final_video', '—')}[/dim]\n"
        f"Instagram : {results['published'].get('instagram') or '—'}\n"
        f"TikTok    : {results['published'].get('tiktok') or '—'}",
        border_style="green",
    ))


# ── Entrée CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QuotesAI Pipeline")
    parser.add_argument(
        "--platform", choices=["instagram", "tiktok", "both"],
        default="both", help="Plateforme(s) cible(s)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Rendre la vidéo sans publier",
    )
    args = parser.parse_args()

    # Vérification FFmpeg
    if not check_ffmpeg():
        console.print("[bold red]ERREUR : FFmpeg introuvable dans le PATH.[/bold red]")
        console.print("Télécharger : https://www.gyan.dev/ffmpeg/builds/ (Windows)")
        sys.exit(1)

    try:
        run(platform=args.platform, dry_run=args.dry_run)
    except KeyboardInterrupt:
        console.print("\n[yellow]Annulé par l'utilisateur.[/yellow]")
    except Exception:
        console.print("[bold red]Erreur inattendue :[/bold red]")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
