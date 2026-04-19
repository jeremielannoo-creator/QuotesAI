"""
setup_fonts.py — Télécharge automatiquement les polices depuis GitHub
Montserrat (ExtraBold + Light), Playfair Display (Italic + Regular), Bebas Neue

Usage :
    python setup_fonts.py
"""
import os
import requests
from rich.console import Console

console   = Console()
FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")

# URLs directes GitHub vérifiées (200 OK)
FONTS = {
    # Montserrat — repo source googlefonts/Montserrat (les fichiers statiques ont
    # été retirés du repo google/fonts au profit des variable fonts)
    "Montserrat-ExtraBold.ttf": (
        "https://raw.githubusercontent.com/googlefonts/Montserrat/"
        "master/fonts/ttf/Montserrat-ExtraBold.ttf"
    ),
    "Montserrat-Light.ttf": (
        "https://raw.githubusercontent.com/googlefonts/Montserrat/"
        "master/fonts/ttf/Montserrat-Light.ttf"
    ),
    # Playfair Display — dernier commit avant migration variable font
    "PlayfairDisplay-Italic.ttf": (
        "https://raw.githubusercontent.com/google/fonts/"
        "a6909e3332b2/ofl/playfairdisplay/PlayfairDisplay-Italic.ttf"
    ),
    "PlayfairDisplay-Regular.ttf": (
        "https://raw.githubusercontent.com/google/fonts/"
        "a6909e3332b2/ofl/playfairdisplay/PlayfairDisplay-Regular.ttf"
    ),
    # Bebas Neue — repo google/fonts main
    "BebasNeue-Regular.ttf": (
        "https://raw.githubusercontent.com/google/fonts/"
        "main/ofl/bebasneue/BebasNeue-Regular.ttf"
    ),
}


def download_font(name: str, url: str) -> bool:
    dest = os.path.join(FONTS_DIR, name)
    if os.path.exists(dest):
        console.print(f"  [dim]⏭  {name} déjà présent[/dim]")
        return True
    try:
        console.print(f"  ⬇  Téléchargement de [cyan]{name}[/cyan]...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        size_ko = len(resp.content) // 1024
        console.print(f"  ✓  {name} ({size_ko} Ko)")
        return True
    except Exception as e:
        console.print(f"  [red]✗  {name} : {e}[/red]")
        return False


if __name__ == "__main__":
    os.makedirs(FONTS_DIR, exist_ok=True)
    console.print("\n[bold cyan]Téléchargement des polices...[/bold cyan]\n")
    ok    = sum(download_font(n, u) for n, u in FONTS.items())
    total = len(FONTS)
    color = "green" if ok == total else "yellow"
    console.print(
        f"\n[{color}]{ok}/{total}[/{color}] polices installées dans [dim]{FONTS_DIR}[/dim]\n"
    )
