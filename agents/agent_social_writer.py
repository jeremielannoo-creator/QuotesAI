"""
Agent — Mise en forme d'une chronique pour chaque plateforme.

Avant, la légende Instagram était le corps de l'article coupé à 2 000
caractères, suivi du même bloc de 15 hashtags à chaque publication. Deux
problèmes : la première ligne (la seule visible avant « …plus ») était une
phrase d'ouverture d'article, pas une accroche ; et rien n'invitait à réagir.

Structure produite maintenant :
    accroche → extrait de la chronique → livre + CTA blog → question

Les hashtags sont désormais assemblés par agent_hashtags : un mélange tournant
qui inclut toujours #titre et #auteur, les tags les plus qualifiés.
"""
import random
import re

from agents import agent_hashtags
from agents.agent_caption import AVA_VOICE
from utils.gemini import json_completion

MAX_IG = 1800   # on laisse de la place aux hashtags dans les 2 200 caractères

QUESTIONS = [
    "Tu l'as lu ? Tu en as pensé quoi ?",
    "Quel livre t'a fait cet effet-là, à toi ?",
    "Je le conseille à qui, d'après toi ?",
    "Tu le mettrais dans ta pile, ou pas du tout ?",
    "Dis-moi le dernier livre que tu n'as pas réussi à lâcher.",
]

# Deux jeux de CTA : avec un lien qui existe vraiment, ou sans lien du tout.
# Aucun gabarit ne contient de marqueur à remplacer — un « [LIEN] » oublié
# finit publié tel quel, ce qui est arrivé sur la Page Facebook.
CTA_WITH_LINK = [
    "La chronique entière est ici → {url}",
    "J'en dis beaucoup plus là → {url}",
    "Le texte complet, sans les coupes → {url}",
]
CTA_NO_LINK = [
    "La chronique entière est en bio.",
    "Le texte complet, sans les coupes : lien en bio.",
    "J'en dis beaucoup plus sur le blog — lien en bio.",
]


def generate_social_posts(article: dict, blog_url: str | None = None) -> dict:
    """
    Formate la chronique pour Instagram, TikTok et Facebook.

    Args:
        article:  dict title / author / body
        blog_url: URL de l'article publié. Absente → le CTA renvoie vers la bio
                  plutôt que vers un lien mort.
    """
    body   = article["body"]
    title  = article["title"]
    author = article["author"]

    parts = json_completion(AVA_VOICE, _PROMPT.format(
        title=title, author=author, extract=body[:1200],
    ), required=("hook", "question"), max_tokens=300) or {
        "hook":     _first_sentences(body, 1),
        "question": random.choice(QUESTIONS),
    }

    # En mode réserve, l'accroche EST la première phrase de la chronique :
    # on la retire de l'extrait pour ne pas la lire deux fois.
    rest    = body[len(parts["hook"]):].lstrip() if body.startswith(parts["hook"]) else body
    excerpt = _truncate(rest, MAX_IG - len(parts["hook"]) - 220)
    cta     = (random.choice(CTA_WITH_LINK).format(url=blog_url)
               if blog_url else random.choice(CTA_NO_LINK))

    caption = "\n\n".join([
        parts["hook"],
        excerpt,
        f"« {title} » — {author}",
        cta,
        parts["question"],
    ])

    return {
        "instagram_caption": caption,
        "hashtags":          " ".join(agent_hashtags.for_book(title, author)),
        "reel_script":       _first_sentences(body, 3),
        "tiktok_script":     _truncate(body, 2200),
        "facebook_post":     f"{parts['hook']}\n\n{body}\n\n{cta}\n\n{parts['question']}",
    }


_PROMPT = """Chronique littéraire à publier sur Instagram.
Livre : « {title} » — {author}

Début de la chronique :
{extract}

- hook : UNE phrase de 6 à 14 mots. C'est la seule ligne visible avant « …plus ». Elle doit donner envie d'ouvrir, sans dire « ce livre est magnifique » ni résumer l'intrigue.
- question : UNE question ouverte qui donne envie de répondre en commentaire. Pas « et vous ? ».

JSON uniquement : {{"hook": "...", "question": "..."}}"""


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _first_sentences(text: str, n: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:n])
