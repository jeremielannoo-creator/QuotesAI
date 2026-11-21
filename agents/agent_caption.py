"""
agents/agent_caption.py — Légendes des Reels citations.

Avant, la légende publiée était… la citation, seule. Aucune accroche, aucun
appel à commenter, aucun pont vers un livre.

Structure produite maintenant :
    ligne 1  ACCROCHE      → les 125 premiers caractères sont les seuls
                             visibles avant « …plus » : c'est là que tout se joue
    bloc 2   LA CITATION   → avec son auteur
    bloc 3   RÉFLEXION     → 1–2 phrases dans la voix d'Ava, qui rendent la
                             citation concrète
    bloc 4   CTA LIVRE     → pont explicite vers un titre du catalogue
    bloc 5   QUESTION      → un vrai appel à commenter, pas un « et toi ? »

Accroche, réflexion et question sont écrites par Gemini si GEMINI_API_KEY est
présent, sinon tirées de réserves rédigées à l'avance : la publication n'échoue
jamais à cause d'une API.
"""
import json
import os
import random

from config import BASE_DIR
from utils import state
from utils.gemini import json_completion

BOOKS_PATH = os.path.join(BASE_DIR, "db", "books.json")

# ── Réserves de secours (si Gemini indisponible) ──────────────────────────────
HOOKS: dict[str, list[str]] = {
    "calm": [
        "Personne ne t'a appris à ne rien faire.",
        "Il y a une différence entre se reposer et fuir.",
        "Le calme n'est pas l'absence de bruit.",
        "Tu confonds patience et résignation.",
    ],
    "warm": [
        "On sous-estime ce que fait une seule phrase gentille.",
        "Ce que tu donnes revient rarement d'où tu l'attends.",
        "La tendresse n'est pas une faiblesse tactique.",
        "Tu as le droit d'être content sans le justifier.",
    ],
    "melancholic": [
        "Certaines phrases, on les comprend trop tard.",
        "Il y a des tristesses qui sont justes.",
        "On ne guérit pas de tout. On devient lucide.",
        "Ce n'est pas le manque qui fait mal, c'est l'habitude.",
    ],
    "contemplative": [
        "Relis-la. La deuxième fois fait plus mal.",
        "Une question qui dérange vaut mieux qu'une réponse qui rassure.",
        "On passe sa vie à répondre à des questions qu'on n'a pas posées.",
        "Ce que tu crois savoir de toi date de quand, exactement ?",
    ],
    "energetic": [
        "Tu attends d'avoir envie. Ça n'arrivera pas.",
        "Le courage, c'est ennuyeux. C'est pour ça que ça marche.",
        "Personne ne viendra te chercher.",
        "Tu n'as pas un problème de motivation.",
    ],
    "triumphant": [
        "Ce que tu as traversé ne se voit pas. Tant mieux.",
        "On ne se relève pas grandi. On se relève, c'est déjà ça.",
        "La force, ça ressemble rarement à de la force.",
        "Tu as survécu à 100 % de tes pires journées.",
    ],
}

REFLECTIONS: dict[str, list[str]] = {
    "calm": ["On croit qu'il faut ajouter. Presque toujours, il faut retirer."],
    "warm": ["Ce qui reste d'une journée, ce sont deux ou trois minutes qu'on n'avait pas prévues."],
    "melancholic": ["Il n'y a rien à réparer là-dedans. Juste à regarder en face."],
    "contemplative": ["Les phrases comme celle-là ne donnent pas de réponse. Elles déplacent la question."],
    "energetic": ["L'élan ne précède pas l'action. Il arrive après, et seulement si on a commencé."],
    "triumphant": ["Ce n'est pas héroïque. C'est répété, obstiné, et ça finit par tenir."],
}

QUESTIONS = [
    "Tu es d'accord, ou tu trouves ça trop facile à dire ?",
    "À qui tu penses en lisant ça ?",
    "Vrai pour toi, ou seulement sur le papier ?",
    "Tu l'aurais compris à 20 ans, cette phrase ?",
    "Dis-moi en commentaire ce que tu en retiens.",
    "Ça te parle, ou ça t'agace ?",
    "Quelle phrase tu mettrais à la place ?",
]

CTA_FORMATS = [
    "Si cette ligne t'a fait quelque chose : « {title} » de {author} — {pitch}. {link}",
    "Le roman qui dit ça mieux que moi : « {title} », {author}. {pitch.capitalize}. {link}",
    "J'en ai reparlé longuement à propos de « {title} » ({author}) : {pitch}. {link}",
    "À lire dans la foulée : « {title} », {author} — {pitch}. {link}",
]

AI_NOTE = ""   # laissé vide pour les citations : aucune image de personne


def caption_for_quote(quote: str, author: str, mood: str,
                      keywords: list[str] | None = None) -> str:
    """Construit la légende complète d'un Reel citation."""
    parts = _write_parts(quote, author, mood, keywords or [])
    book  = pick_book(mood)

    blocks = [
        parts["hook"],
        f"« {quote} »\n— {author}" if author else f"« {quote} »",
        parts["reflection"],
    ]
    if book:
        blocks.append(_format_cta(book))
    blocks.append(parts["question"])

    return "\n\n".join(b for b in blocks if b)


# ── Catalogue de livres ───────────────────────────────────────────────────────

def _load_catalogue() -> dict:
    try:
        with open(BOOKS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"books": [], "default_cta": ""}


def pick_book(mood: str) -> dict | None:
    """
    Choisit un livre du catalogue accordé à l'humeur, en évitant ceux poussés
    dans les 4 dernières publications.
    """
    cat   = _load_catalogue()
    books = cat.get("books", [])
    if not books:
        return None

    recent  = set(state.load().get("recent_cta_books", []))
    matched = [b for b in books if mood in b.get("moods", [])]

    for pool in (matched, books):
        fresh = [b for b in pool if state.book_key(b["title"], b["author"]) not in recent]
        if fresh:
            chosen = random.choice(fresh)
            _remember_cta(chosen)
            chosen = dict(chosen)
            chosen["_default_cta"] = cat.get("default_cta", "")
            return chosen

    chosen = dict(random.choice(books))
    _remember_cta(chosen)
    chosen["_default_cta"] = cat.get("default_cta", "")
    return chosen


def _remember_cta(book: dict, keep: int = 4) -> None:
    st  = state.load()
    key = state.book_key(book["title"], book["author"])
    st["recent_cta_books"] = ([key] + [k for k in st.get("recent_cta_books", []) if k != key])[:keep]
    state.save(st)


def _format_cta(book: dict) -> str:
    link = book.get("url") or book.get("_default_cta", "")
    tpl  = random.choice(CTA_FORMATS)
    pitch = book.get("pitch", "")
    return (tpl
            .replace("{pitch.capitalize}", pitch[:1].upper() + pitch[1:])
            .replace("{title}", book["title"])
            .replace("{author}", book["author"])
            .replace("{pitch}", pitch)
            .replace("{link}", link)
            .strip())


# ── Rédaction ─────────────────────────────────────────────────────────────────

def _write_parts(quote: str, author: str, mood: str, keywords: list[str]) -> dict:
    return _gemini_parts(quote, author, mood) or _fallback_parts(mood)


def _fallback_parts(mood: str) -> dict:
    return {
        "hook":       random.choice(HOOKS.get(mood, HOOKS["contemplative"])),
        "reflection": random.choice(REFLECTIONS.get(mood, REFLECTIONS["contemplative"])),
        "question":   random.choice(QUESTIONS),
    }


# Voix partagée par toutes les rédactions du compte (citations et lifestyle).
AVA_VOICE = """Tu es Ava : 25 ans, éditrice junior dans une maison indépendante parisienne, tu tiens le compte « The Journey of Ava ». Tu lis beaucoup, tu voyages, tu as une dévotion pour l'Italie.
Ton : personnel, direct, parfois tranchant, jamais condescendant, jamais coach en développement personnel. Phrases courtes. Aucun emoji. Aucun mot creux du type « bouleversant », « incontournable », « puissant », « pépite ».
Tu ne décris pas : tu dis ce que ça fait."""

_TEMPLATE = """Citation : « {quote} » — {author}
Humeur : {mood}

Écris trois éléments pour la légende Instagram.

- hook : UNE phrase de 6 à 12 mots. C'est la seule ligne visible avant « …plus ». Elle doit accrocher sans annoncer la citation, et ne jamais la répéter.
- reflection : UNE ou DEUX phrases qui rendent la citation concrète, vécue.
- question : UNE question ouverte, précise, qui donne envie de répondre en commentaire. Pas « et toi ? », pas « qu'en penses-tu ? ».

Réponds uniquement en JSON valide, sans balises markdown :
{{"hook": "...", "reflection": "...", "question": "..."}}"""


def _gemini_parts(quote: str, author: str, mood: str) -> dict | None:
    """Rédige accroche/réflexion/question via Gemini. None si indisponible."""
    return json_completion(
        AVA_VOICE,
        _TEMPLATE.format(quote=quote, author=author or "anonyme", mood=mood),
        required=("hook", "reflection", "question"),
        max_tokens=400,
    )


if __name__ == "__main__":
    print(caption_for_quote(
        "Tu as du pouvoir sur ton esprit, pas sur les événements extérieurs.",
        "Marc Aurèle", "calm",
    ))
