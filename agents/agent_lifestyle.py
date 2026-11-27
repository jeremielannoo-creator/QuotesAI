"""
agents/agent_lifestyle.py — Rédaction des posts « vie d'Ava ».

Trois formats, tous dans la même voix que les chroniques littéraires :
    outfit — une tenue, une marque, un moment de la journée
    place  — un café / bar / restaurant du circuit (Paris, Lille, Londres,
             Bruxelles, Anvers, Amsterdam)
    travel — carnet de voyage : une destination et trois conseils utiles

Ce qui fait l'engagement sur ces formats, ce n'est pas la photo : c'est le
conseil concret (« le café coûte moitié moins au comptoir ») et la question
finale. Les deux sont obligatoires dans chaque légende.

Toute légende porte config.AI_DISCLOSURE : Ava est un personnage de fiction,
et les publications qui citent une marque tombent sous les règles de
transparence publicitaire en France, Belgique, Pays-Bas et au Royaume-Uni.
"""
import json
import os
import random

from agents.agent_caption import AVA_VOICE
from config import AI_DISCLOSURE, BASE_DIR
from utils import state
from utils.gemini import json_completion

PLACES_PATH = os.path.join(BASE_DIR, "db", "places.json")
BRANDS_PATH = os.path.join(BASE_DIR, "db", "brands.json")


# ── Chargement des catalogues ─────────────────────────────────────────────────

def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"  [lifestyle] Catalogue illisible {os.path.basename(path)} : {e}")
        return {}


def _pick_fresh(items: list[dict], bucket: str, key: str) -> dict | None:
    """Tire un élément en évitant ceux des dernières publications du même type."""
    if not items:
        return None
    recent = set(state.recent_picks(bucket))
    fresh  = [i for i in items if i[key] not in recent] or items
    chosen = random.choice(fresh)
    state.remember_pick(bucket, chosen[key])
    return chosen


def pick_brand() -> dict | None:
    return _pick_fresh(_load(BRANDS_PATH).get("brands", []), "brands", "name")


def pick_place(city: str | None = None) -> dict | None:
    places = _load(PLACES_PATH).get("places", [])
    if city:
        places = [p for p in places if p["city"] == city] or places
    return _pick_fresh(places, "places", "name")


def pick_travel() -> dict | None:
    return _pick_fresh(_load(PLACES_PATH).get("travel", []), "travel", "destination")


# ── Légendes ──────────────────────────────────────────────────────────────────

def caption_outfit(brand: dict, city: str = "Paris") -> str:
    piece  = random.choice(brand.get("pieces", ["cette tenue"]))
    parts  = json_completion(AVA_VOICE, _P_OUTFIT.format(
        brand=brand["name"], piece=piece, city=city,
    ), required=("hook", "body", "question"), max_tokens=450)

    parts = parts or {
        "hook":     random.choice(_HOOKS_OUTFIT),
        "body":     f"Je la garde pour les jours où je n'ai rien à prouver. "
                    f"À {city}, ça arrive plus souvent qu'on croit.",
        "question": random.choice(QUESTIONS_OUTFIT),
    }

    credit = f"La pièce : {brand['name']}"
    if brand.get("handle"):
        credit += f" ({brand['handle']})"
    if brand.get("url"):
        credit += f"\n{brand['url']}"
    # La mention de partenariat n'est ajoutée que si le lien est réellement
    # rémunéré : l'annoncer à tort serait aussi faux que de l'omettre.
    if brand.get("affiliate"):
        credit += "\nLien affilié — je touche une commission si tu achètes."

    return _join([parts["hook"], parts["body"], credit, parts["question"], AI_DISCLOSURE])


def caption_place(place: dict) -> str:
    # Tant que le lieu n'est pas vérifié, on parle du quartier, jamais du nom.
    named = place.get("verified", False)
    label = place["name"] if named else f"un {_kind_fr(place['kind'])} à {place['area']}"

    parts = json_completion(AVA_VOICE, _P_PLACE.format(
        label=label, city=place["city"], area=place["area"],
        kind=_kind_fr(place["kind"]), vibe=place["vibe"],
    ), required=("hook", "body", "tip", "question"), max_tokens=500)

    soir  = place["kind"] == "bar"
    parts = parts or {
        "hook":     random.choice(_HOOKS_PLACE_SOIR if soir else _HOOKS_PLACE),
        "body":     f"{label[:1].upper()}{label[1:]}, à {place['city']}. "
                    + ("On y arrive à deux, on en repart à huit."
                       if soir else "J'y vais pour lire, pas pour être vue."),
        "tip":      ("Y aller avant 21h : après, c'est debout sur le trottoir. "
                     if soir else
                     "Le bon créneau : entre 15h et 17h, avant que ça se remplisse. ")
                    + f"Commande {random.choice(place.get('order', ['un café']))}.",
        "question": "Tu connais une adresse comme ça dans ta ville ?",
    }

    addr = f"📍 {place['area']}, {place['city']}"
    if named and place.get("handle"):
        addr = f"📍 {place['name']} ({place['handle']}) — {place['area']}, {place['city']}"
    elif named:
        addr = f"📍 {place['name']} — {place['area']}, {place['city']}"

    return _join([parts["hook"], parts["body"], parts["tip"], addr,
                  parts["question"], AI_DISCLOSURE])


def caption_travel(entry: dict) -> str:
    tips  = entry.get("tips", [])[:3]
    parts = json_completion(AVA_VOICE, _P_TRAVEL.format(
        destination=entry["destination"], tips="\n".join(f"- {t}" for t in tips),
    ), required=("hook", "body", "question"), max_tokens=500)

    parts = parts or {
        "hook":     random.choice(_HOOKS_TRAVEL),
        "body":     f"{entry['destination']}, et surtout ce que personne ne dit "
                    f"avant d'y aller.",
        "question": "Tu y es déjà allé ? Qu'est-ce que tu ajouterais ?",
    }

    tips_block = "Ce que je retiens :\n" + "\n".join(f"→ {t}" for t in tips)
    return _join([parts["hook"], parts["body"], tips_block,
                  parts["question"], AI_DISCLOSURE])


# ── Réserves ──────────────────────────────────────────────────────────────────

_HOOKS_OUTFIT = [
    "Je mets la même chose depuis trois semaines. Assumé.",
    "S'habiller, c'est décider de quoi on a envie d'avoir l'air.",
    "Il y a des pièces qu'on achète, et des pièces qui restent.",
    "Je n'ai jamais su m'habiller pour plaire. Ça se voit.",
]
QUESTIONS_OUTFIT = [
    "Tu portes quoi quand tu veux qu'on te laisse tranquille ?",
    "Une pièce que tu gardes depuis des années : c'est laquelle ?",
    "Tu achètes par coup de cœur ou par liste ?",
]
_HOOKS_PLACE = [
    "Je choisis mes cafés comme mes livres : sur la lumière.",
    "Il y a des endroits faits pour rester deux heures.",
    "Le bon café, ce n'est pas le meilleur café.",
    "J'ai une règle : jamais deux fois la même table.",
]
_HOOKS_PLACE_SOIR = [
    "Les meilleurs bars n'ont pas de site internet.",
    "Un bon bar, ça se reconnaît au bruit qu'il fait dehors.",
    "Je n'y vais jamais avant d'avoir faim.",
    "Aucune carte, aucune réservation, aucun problème.",
]
_HOOKS_TRAVEL = [
    "On y va tous pour la même photo. Dommage.",
    "Ce voyage m'a coûté trois erreurs. Voilà lesquelles.",
    "Personne ne te dit ça avant de partir.",
    "Le meilleur moment était celui que je n'avais pas prévu.",
]


# ── Prompts ───────────────────────────────────────────────────────────────────

_P_OUTFIT = """Post Instagram — tenue du jour.
Pièce : {piece}
Marque : {brand}
Ville : {city}

- hook : UNE phrase de 6 à 12 mots. Seule ligne visible avant « …plus ». Elle ne décrit pas la tenue, elle dit une idée.
- body : 2 à 3 phrases. Où tu la portes, pourquoi celle-là, ce qu'elle change. Concret, pas de vocabulaire de fiche produit.
- question : UNE question ouverte sur le rapport aux vêtements, qui donne envie de répondre.

JSON uniquement : {{"hook": "...", "body": "...", "question": "..."}}"""

_P_PLACE = """Post Instagram — une adresse.
Lieu : {label}, {kind} à {city}, quartier {area}
Ambiance : {vibe}

- hook : UNE phrase de 6 à 12 mots, seule ligne visible avant « …plus ».
- body : 2 à 3 phrases. Ce qu'on y fait, à quel moment, pour qui c'est.
- tip : UN conseil vraiment utile et vérifiable (créneau, quoi commander, quoi éviter). Pas de généralité.
- question : UNE question ouverte qui appelle d'autres adresses en commentaire.

Ne jamais inventer d'adresse postale, de prix, ni d'horaires précis.

JSON uniquement : {{"hook": "...", "body": "...", "tip": "...", "question": "..."}}"""

_P_TRAVEL = """Post Instagram — carnet de voyage.
Destination : {destination}
Conseils déjà retenus :
{tips}

- hook : UNE phrase de 6 à 12 mots, seule ligne visible avant « …plus ».
- body : 2 à 3 phrases sur ce que l'endroit fait ressentir, sans carte postale.
- question : UNE question ouverte qui appelle les conseils des autres.

Ne reformule pas les conseils ci-dessus, ils sont publiés tels quels. N'invente ni prix, ni horaires, ni noms d'hôtels.

JSON uniquement : {{"hook": "...", "body": "...", "question": "..."}}"""


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _kind_fr(kind: str) -> str:
    return {"cafe": "café", "bar": "bar", "restaurant": "restaurant",
            "bookshop": "librairie"}.get(kind, "endroit")


def _join(blocks: list[str]) -> str:
    return "\n\n".join(b.strip() for b in blocks if b and b.strip())


if __name__ == "__main__":
    print("── TENUE ──\n",  caption_outfit(pick_brand()), "\n")
    print("── ADRESSE ──\n", caption_place(pick_place()), "\n")
    print("── VOYAGE ──\n",  caption_travel(pick_travel()))
