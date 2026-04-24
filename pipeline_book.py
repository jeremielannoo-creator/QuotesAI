"""
pipeline_book.py — Pipeline de publication de critiques littéraires.

Source des articles : Google Drive
  Mon Drive/AI/The Journey of Ava/Littérature/
  Convention : AAAA-MM-JJ-B1 (mercredi 19h00) | AAAA-MM-JJ-B2 (dimanche 10h30)
  Après publication : fichier déplacé dans 'Publiés/'

Flux :
  1. Lecture de l'article depuis Drive (selon le jour ou --drive-file)
  2. Couverture du livre (Open Library → Pexels fallback)
  3. Upload Cloudinary
  4. Publication Hashnode (blog)
  5. Formatage des posts sociaux (texte Drive, pas d'API externe)
  6. Publication Instagram
  7. Publication TikTok
  8. Publication Facebook
  9. Archivage Drive

Usage :
  python pipeline_book.py                          # auto selon jour (mer/dim)
  python pipeline_book.py --drive-file 2026-04-22-B1
  python pipeline_book.py --article chemin/local.md
  python pipeline_book.py --platform instagram
  python pipeline_book.py --dry-run
"""
import argparse
import os
import time
from rich.console import Console

from agents.agent_article       import parse_article
from agents.agent_book_cover    import get_book_cover
from agents.agent_social_writer import generate_social_posts
from agents.agent_blog          import publish_to_hashnode
from utils.video_host           import upload_video

console = Console()

# Créer le dossier logs si absent
os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)


def _get_article(article_path: str | None, drive_file: str | None) -> dict | None:
    """Résout la source de l'article."""

    # 1. Fichier local explicite
    if article_path:
        return parse_article(article_path)

    # 2. Fichier Drive explicite  (ex: "2026-04-29-B1" ou juste "B1")
    if drive_file:
        # Extrait le slot (dernier segment après le dernier '-')
        slot = drive_file.rsplit("-", 1)[-1].upper()
        if slot not in ("B1", "B2"):
            console.print(f"[red]Format --drive-file invalide : {drive_file!r}. Attendu : AAAA-MM-JJ-B1 ou B1[/red]")
            return None
        date_str = drive_file.rsplit("-", 1)[0] if "-" in drive_file[:-3] else None
        from utils.drive_reader import get_article_by_slot
        return get_article_by_slot(slot, date_str or None)

    # 3. Auto selon le jour courant (mercredi → B1, dimanche → B2)
    from utils.drive_reader import get_article_for_today
    return get_article_for_today()


def run(
    article_path: str | None = None,
    drive_file:   str | None = None,
    platform:     str        = "all",
    dry_run:      bool       = False,
):
    started_at = time.time()
    results    = {"blog": None, "instagram": None, "tiktok": None, "facebook": None}

    console.print(
        f"\n[bold cyan]╭──────────────────────────────────╮\n"
        f"│ QuotesAI — Pipeline Livre        │\n"
        f"│ Plateforme : {platform:<8} Dry-run : {'Oui' if dry_run else 'Non'} │\n"
        f"╰──────────────────────────────────╯[/bold cyan]\n"
    )

    # ── 1. Lire l'article ─────────────────────────────────────────────────────
    with console.status("[bold]Lecture de l'article..."):
        article = _get_article(article_path, drive_file)

    if not article:
        console.print("[yellow]Aucun article à publier aujourd'hui.[/yellow]")
        return results

    console.print(f"  ✓ Article : [bold]{article['title']}[/bold] — {article['author']}")

    # ── 2. Couverture du livre ────────────────────────────────────────────────
    with console.status("[bold]Recherche de la couverture..."):
        cover_path = get_book_cover(article["title"], article["author"])

    if cover_path:
        console.print(f"  ✓ Couverture : [dim]{cover_path}[/dim]")
    else:
        console.print("  ⚠ Pas de couverture — publication sans image")

    # ── 3. Upload Cloudinary ──────────────────────────────────────────────────
    cover_url = None
    if cover_path and not dry_run:
        with console.status("[bold]Upload couverture..."):
            try:
                cover_url = upload_video(cover_path)
                console.print(f"  ✓ Cloudinary : [dim]{cover_url}[/dim]")
            except Exception as e:
                console.print(f"  ⚠ Cloudinary : {e}")

    # ── 4. Blog Hashnode ──────────────────────────────────────────────────────
    if platform in ("all", "blog") and not dry_run:
        with console.status("[bold]Publication Hashnode..."):
            try:
                blog_url = publish_to_hashnode(article, cover_url=cover_url)
                results["blog"] = blog_url
                console.print(f"  ✓ [bold green]Blog publié[/bold green] → {blog_url}")
            except Exception as e:
                console.print(f"  ✗ [red]Hashnode : {e}[/red]")

    # ── 5. Formatage des posts sociaux ────────────────────────────────────────
    with console.status("[bold]Formatage des posts..."):
        posts = generate_social_posts(article)

    console.print("  ✓ Posts formatés")

    if dry_run:
        console.print("\n[yellow]── DRY RUN — Aperçu ──[/yellow]")
        console.print(f"\n[bold]Instagram caption :[/bold]\n{posts.get('instagram_caption','')[:300]}…")
        console.print(f"\n[bold]Hashtags :[/bold]\n{posts.get('hashtags','')}")
        console.print(f"\n[bold]Reel script :[/bold]\n{posts.get('reel_script','')}")
        console.print(f"\n[bold]Facebook :[/bold]\n{posts.get('facebook_post','')[:300]}…")
        _print_summary(results, started_at)
        return results

    # ── 6. Instagram carousel ────────────────────────────────────────────────
    if platform in ("all", "instagram"):
        with console.status("[bold]Génération carousel Instagram..."):
            try:
                from agents.agent_carousel  import create_carousel
                from agents.agent_publisher import publish_instagram_carousel

                slides     = create_carousel(article, cover_path, posts.get("hashtags", ""))
                slide_urls = [upload_video(p) for p in slides]

                caption  = posts.get("instagram_caption", article["title"])
                hashtags = posts.get("hashtags", "")
                full_cap = f"{caption}\n\n{hashtags}"

                media_id = publish_instagram_carousel(slide_urls, full_cap)
                results["instagram"] = media_id
                console.print(f"  ✓ [bold green]Instagram carousel publié[/bold green] — ID : {media_id}")
            except Exception as e:
                console.print(f"  ✗ [red]Instagram : {e}[/red]")

    # ── 7. TikTok ─────────────────────────────────────────────────────────────
    if platform in ("all", "tiktok") and cover_path:
        with console.status("[bold]Publication TikTok..."):
            try:
                from agents.agent_publisher import publish_tiktok
                from agents.agent_render    import render_video
                from agents.agent_music     import select_music

                music_path = select_music("contemplative")
                video_path = render_video(
                    cover_path,
                    posts.get("reel_script", article["title"])[:120],
                    article["author"],
                    music_path=music_path,
                    mood="contemplative",
                )
                caption  = f"{article['title']} — {article['author']}"
                hashtags = posts.get("hashtags", "").split()
                pub_id   = publish_tiktok(video_path, caption, hashtags)
                results["tiktok"] = pub_id
                console.print(f"  ✓ [bold green]TikTok publié[/bold green] — ID : {pub_id}")
            except Exception as e:
                console.print(f"  ✗ [red]TikTok : {e}[/red]")

    # ── 8. Facebook ───────────────────────────────────────────────────────────
    if platform in ("all", "facebook") and cover_url:
        with console.status("[bold]Publication Facebook..."):
            try:
                from agents.agent_publisher import publish_facebook
                fb_post = posts.get("facebook_post", "")
                if results.get("blog"):
                    fb_post = fb_post.replace("[LIEN]", results["blog"])
                post_id = publish_facebook(cover_url, fb_post)
                results["facebook"] = post_id
                console.print(f"  ✓ [bold green]Facebook publié[/bold green] — ID : {post_id}")
            except Exception as e:
                console.print(f"  ✗ [red]Facebook : {e}[/red]")

    # ── 9. Archivage Drive ────────────────────────────────────────────────────
    published_count = sum(1 for v in results.values() if v)
    if published_count > 0 and article.get("_drive_file_id"):
        with console.status("[bold]Archivage Drive..."):
            try:
                from utils.drive_reader import mark_as_published
                mark_as_published(article)
            except Exception as e:
                console.print(f"  ⚠ Archivage Drive : {e}")

    _print_summary(results, started_at)
    return results


def _print_summary(results: dict, started_at: float):
    elapsed = int(time.time() - started_at)
    console.print(
        f"\n[bold cyan]╭─────────────────────────────────────────╮\n"
        f"│ Pipeline terminé en {elapsed}s{' ' * (20 - len(str(elapsed)))}│\n"
        f"│ Blog      : {str(results.get('blog') or '—')[:40]:<40}│\n"
        f"│ Instagram : {str(results.get('instagram') or '—'):<40}│\n"
        f"│ TikTok    : {str(results.get('tiktok') or '—'):<40}│\n"
        f"│ Facebook  : {str(results.get('facebook') or '—'):<40}│\n"
        f"╰─────────────────────────────────────────╯[/bold cyan]\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QuotesAI — Pipeline Livre")
    parser.add_argument("--drive-file", type=str, default=None,
                        help="Forcer un fichier Drive (ex: 2026-04-22-B1)")
    parser.add_argument("--article",   type=str, default=None,
                        help="Utiliser un fichier local à la place de Drive")
    parser.add_argument("--platform",  choices=["all", "blog", "instagram", "tiktok", "facebook"],
                        default="all")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Affiche les posts sans publier")
    args = parser.parse_args()
    run(
        article_path=args.article,
        drive_file=args.drive_file,
        platform=args.platform,
        dry_run=args.dry_run,
    )
