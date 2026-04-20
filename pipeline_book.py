"""
pipeline_book.py — Pipeline de publication de critiques littéraires.

Flux :
  1. Lecture de l'article (.md dans content/articles/)
  2. Couverture du livre (Open Library → Pexels fallback)
  3. Upload Cloudinary (URL publique pour Hashnode + Instagram)
  4. Publication Hashnode (blog)
  5. Génération des posts sociaux (Claude API)
  6. Publication Instagram (photo + caption)
  7. Publication TikTok (vidéo avec couverture)
  8. Publication Facebook (photo + texte)

Usage :
  python pipeline_book.py
  python pipeline_book.py --article content/articles/mon-article.md
  python pipeline_book.py --platform instagram
  python pipeline_book.py --dry-run
"""
import argparse
import time
from rich.console import Console

from agents.agent_article       import get_latest_article, parse_article
from agents.agent_book_cover    import get_book_cover
from agents.agent_social_writer import generate_social_posts
from agents.agent_blog          import publish_to_hashnode
from utils.video_host           import upload_video

console = Console()


def run(
    article_path: str | None = None,
    platform: str = "all",
    dry_run: bool = False,
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
        article = parse_article(article_path) if article_path else get_latest_article()
        if not article:
            console.print("[red]Aucun article trouvé. Dépose un .md dans content/articles/[/red]")
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
                cover_url = upload_video(cover_path)   # réutilise l'uploader Cloudinary
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

    # ── 5. Génération posts sociaux ───────────────────────────────────────────
    with console.status("[bold]Génération des posts (Claude API)..."):
        posts = generate_social_posts(article)

    console.print("  ✓ Posts générés")

    if dry_run:
        console.print("\n[yellow]── DRY RUN — Aperçu des posts ──[/yellow]")
        console.print(f"\n[bold]Instagram caption :[/bold]\n{posts.get('instagram_caption','')}")
        console.print(f"\n[bold]Hashtags :[/bold]\n{posts.get('hashtags','')}")
        console.print(f"\n[bold]Reel script :[/bold]\n{posts.get('reel_script','')}")
        console.print(f"\n[bold]TikTok script :[/bold]\n{posts.get('tiktok_script','')}")
        console.print(f"\n[bold]Facebook :[/bold]\n{posts.get('facebook_post','')}")
        _print_summary(results, started_at)
        return results

    # ── 6. Instagram ──────────────────────────────────────────────────────────
    if platform in ("all", "instagram") and cover_url:
        with console.status("[bold]Publication Instagram..."):
            try:
                from agents.agent_publisher import publish_instagram
                caption   = posts.get("instagram_caption", article["title"])
                hashtags  = posts.get("hashtags", "").split()
                media_id  = publish_instagram(cover_url, caption, hashtags)
                results["instagram"] = media_id
                console.print(f"  ✓ [bold green]Instagram publié[/bold green] — ID : {media_id}")
            except Exception as e:
                console.print(f"  ✗ [red]Instagram : {e}[/red]")

    # ── 7. TikTok (vidéo couverture + script) ─────────────────────────────────
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
    parser.add_argument("--article",  type=str, default=None,
                        help="Chemin vers l'article .md (sinon : dernier article)")
    parser.add_argument("--platform", choices=["all", "blog", "instagram", "tiktok", "facebook"],
                        default="all")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Génère les posts sans publier")
    args = parser.parse_args()
    run(article_path=args.article, platform=args.platform, dry_run=args.dry_run)
