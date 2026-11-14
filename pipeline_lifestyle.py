"""
pipeline_lifestyle.py — Publication des posts « vie d'Ava ».

Trois types :
    outfit — tenue du jour, une marque du catalogue db/brands.json
    place  — café / bar / restaurant de db/places.json
    travel — carnet de voyage : photo de la photothèque + trois conseils

Source de l'image :
    travel → Photos/Travel/ si une photo correspond à la destination,
             sinon génération Gemini
    autres → génération Gemini à partir des portraits de référence

Publication : Instagram (image) puis Facebook (photo), avec la même légende.

Usage :
    python pipeline_lifestyle.py --type outfit
    python pipeline_lifestyle.py --type place --city Lille
    python pipeline_lifestyle.py --type travel --dry-run
    python pipeline_lifestyle.py                 # type tiré au sort
"""
import argparse
import os
import random
import unicodedata

from rich.console import Console

from agents import agent_hashtags
from agents.agent_ava_photo import (
    generate, prompt_outfit, prompt_place, prompt_travel, to_portrait_file,
)
from agents.agent_lifestyle import (
    caption_outfit, caption_place, caption_travel,
    pick_brand, pick_place, pick_travel,
)
from config import TRAVEL_DIRS

console = Console()
TYPES = ("outfit", "place", "travel")
# "mix" = tenue ou adresse. Le voyage a son propre créneau dans la semaine,
# on ne veut pas qu'il sorte deux fois.
CHOICES = TYPES + ("mix",)


def run(post_type: str | None = None, city: str | None = None,
        dry_run: bool = False) -> dict:
    if post_type == "mix":
        post_type = random.choice(("outfit", "place"))
    post_type = post_type or random.choice(TYPES)
    console.print(f"\n[bold cyan]Pipeline lifestyle — type : {post_type}[/bold cyan]\n")

    built = _build(post_type, city)
    if not built:
        console.print("[yellow]Rien à publier — catalogue vide.[/yellow]")
        return {}

    caption, hashtags, image_path, label = built
    full_caption = f"{caption}\n\n{' '.join(hashtags)}"

    console.print(f"  ✓ Sujet : [bold]{label}[/bold]")

    if dry_run:
        console.print(f"\n[yellow]── DRY RUN ──[/yellow]\n{full_caption}\n")
        console.print(f"Image : {image_path or '[red]aucune[/red]'}")
        return {"caption": full_caption, "image": image_path}

    if not image_path:
        console.print("[red]Pas d'image — publication annulée.[/red]")
        console.print("[dim]GEMINI_API_KEY manquant, ou génération refusée.[/dim]")
        return {}

    from utils.video_host import upload_video
    image_url = upload_video(image_path)
    console.print(f"  ✓ Cloudinary : [dim]{image_url}[/dim]")

    results = {"instagram": None, "facebook": None}

    from agents.agent_publisher import publish_facebook, publish_instagram_image
    try:
        results["instagram"] = publish_instagram_image(image_url, full_caption)
        console.print(f"  ✓ [green]Instagram[/green] — {results['instagram']}")
    except Exception as e:
        console.print(f"  ✗ [red]Instagram : {e}[/red]")

    try:
        results["facebook"] = publish_facebook(image_url, full_caption)
        console.print(f"  ✓ [green]Facebook[/green] — {results['facebook']}")
    except Exception as e:
        console.print(f"  ✗ [red]Facebook : {e}[/red]")

    return results


# ── Construction du post ──────────────────────────────────────────────────────

def _build(post_type: str, city: str | None) -> tuple | None:
    if post_type == "outfit":
        brand = pick_brand()
        if not brand:
            return None
        target = city or "Paris"
        return (
            caption_outfit(brand, target),
            agent_hashtags.for_outfit(brand, target),
            generate(prompt_outfit(brand, target), label="outfit"),
            f"{brand['name']} — {target}",
        )

    if post_type == "place":
        place = pick_place(city)
        if not place:
            return None
        return (
            caption_place(place),
            agent_hashtags.for_place(place["city"], place["kind"], place.get("area", "")),
            generate(prompt_place(place), label="place"),
            f"{place['name']} — {place['city']}",
        )

    entry = pick_travel()
    if not entry:
        return None
    destination = entry["destination"]
    image = _local_travel_photo(destination) or generate(
        prompt_travel(destination, entry.get("detail", "")), label="travel",
    )
    return (
        caption_travel(entry),
        agent_hashtags.for_travel(destination),
        image,
        destination,
    )


def _local_travel_photo(destination: str) -> str | None:
    """Cherche une photo de la destination dans la photothèque, et la normalise."""
    needle  = _fold(destination)
    matches = []
    for folder in TRAVEL_DIRS:
        if not os.path.isdir(folder):
            continue
        matches = [
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg")) and needle in _fold(f)
        ]
        if matches:
            break
    if not matches:
        return None
    chosen = random.choice(matches)
    print(f"  [lifestyle] Photothèque : {os.path.basename(chosen)}")
    # Instagram refuse les images plus hautes que 4:5 → recadrage systématique.
    return to_portrait_file(chosen)


def _fold(text: str) -> str:
    """Minuscule sans accents — 'Toscane' doit matcher 'Toscane_1.png'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="QuotesAI — Pipeline lifestyle")
    p.add_argument("--type", choices=CHOICES, default=None,
                   help="Type de post. 'mix' = tenue ou adresse. Défaut : tiré au sort.")
    p.add_argument("--city", default=None,
                   help="Ville à privilégier (Paris, Lille, Londres, Bruxelles, Anvers, Amsterdam)")
    p.add_argument("--dry-run", action="store_true",
                   help="Affiche la légende sans publier")
    args = p.parse_args()
    run(post_type=args.type, city=args.city, dry_run=args.dry_run)
