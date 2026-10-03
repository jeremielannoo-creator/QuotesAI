"""
agents/agent_hashtags.py — Construction des jeux de hashtags.

Ce que ça corrige :
  • le bloc de 15 hashtags rigoureusement identique à chaque post livre —
    c'est exactement la signature qu'Instagram traite comme du spam ;
  • les 5 hashtags « boost » collés systématiquement à chaque citation.

Principe : un mélange par paliers, différent à chaque publication.
    1 très large  (portée, forte concurrence)
    3–4 moyens    (là où un petit compte peut réellement ressortir)
    4–5 de niche  (thème/humeur/livre — l'audience qui commente)
    1 de marque   (#thejourneyofava, toujours présent)

Les hashtags des 2 dernières publications sont écartés (sauf la marque), pour
que deux posts consécutifs ne présentent jamais le même bloc.
"""
import random

from utils import state

BRAND = "#thejourneyofava"

# ── Citations ─────────────────────────────────────────────────────────────────
BROAD_QUOTE = [
    "#citation", "#quotes", "#motivation", "#inspiration",
    "#philosophie", "#developpementpersonnel",
]
MID_QUOTE = [
    "#citationdujour", "#penseepositive", "#sagesse", "#introspection",
    "#citationfrancaise", "#reflexion", "#mindset", "#philosophyoflife",
    "#lacherprise", "#motivationquotidienne", "#pensees", "#serenite",
]
MOOD_TAGS = {
    "calm":          ["#calme", "#paixinterieure", "#slowlife", "#respirer", "#presence"],
    "warm":          ["#bonheur", "#gratitude", "#douceur", "#amourdesoi", "#tendresse"],
    "melancholic":   ["#melancolie", "#nostalgie", "#emotions", "#solitude", "#poesie"],
    "contemplative": ["#meditation", "#pleineconscience", "#silence", "#contemplation", "#questionnement"],
    "energetic":     ["#courage", "#discipline", "#depassementdesoi", "#energie", "#action"],
    "triumphant":    ["#resilience", "#victoire", "#perseverance", "#force", "#reussite"],
}

# ── Livres ────────────────────────────────────────────────────────────────────
BROAD_BOOK = [
    "#bookstagram", "#lecture", "#livres", "#books", "#reading", "#booklover",
]
MID_BOOK = [
    "#bookstagramfr", "#litterature", "#chroniquelitteraire", "#lecturedumoment",
    "#livresfrancais", "#bookaddict", "#avisdelecture", "#bibliophile",
    "#pilealire", "#romanhistorique", "#instalivre", "#lecturedujour",
]
NICHE_BOOK = [
    "#clublecture", "#lecteurpassionne", "#booktokfr", "#litteratureetrangere",
    "#romancontemporain", "#classiquelitteraire", "#coupdecoeurlitteraire",
    "#quelivrelire", "#lireestunplaisir", "#chroniquelivre",
]


# ── Lifestyle (tenues, adresses, voyages) ─────────────────────────────────────
BROAD_FASHION = ["#ootd", "#mode", "#outfitinspo", "#style", "#lookoftheday"]
MID_FASHION = [
    "#modefrancaise", "#tenuedujour", "#lookdujour", "#styleminimaliste",
    "#garderobecapsule", "#frenchgirlstyle", "#modeethique", "#slowfashion",
    "#stylenaturel", "#inspirationmode",
]
BROAD_PLACE = ["#foodie", "#lifestyle", "#citylife", "#bonneadresse"]
# Le vocabulaire dépend du type de lieu : #cafedespecialite sous la photo d'un
# restaurant indien, c'est le genre de détail qui fait amateur.
MID_PLACE: dict[str, list[str]] = {
    "cafe": ["#coffeeshop", "#cafedespecialite", "#brunchtime", "#terrasse",
             "#coffeelover", "#patisserie", "#adresseacroquer"],
    "bar": ["#barambiance", "#apero", "#cocktailbar", "#terrasse",
            "#afterwork", "#adresseacroquer", "#barvintage"],
    "restaurant": ["#restodumoment", "#bonnetable", "#cuisinegenereuse",
                   "#adresseacroquer", "#restaurantlover", "#foodlover"],
    "bookshop": ["#librairie", "#librairieindependante", "#bookshop",
                 "#lecture", "#adresseacroquer"],
}
BROAD_TRAVEL = ["#travel", "#voyage", "#wanderlust", "#travelgram"]
MID_TRAVEL = [
    "#carnetdevoyage", "#voyageenfrance", "#slowtravel", "#conseilsvoyage",
    "#travelinspiration", "#citytrip", "#voyageuse", "#itineraire",
]
CITY_TAGS: dict[str, list[str]] = {
    "Paris":     ["#paris", "#parisienne", "#parisjetaime", "#visitparis"],
    "Lille":     ["#lille", "#vieuxlille", "#hautsdefrance", "#lillemaville"],
    "Londres":   ["#london", "#londres", "#londonlife", "#visitlondon"],
    "Bruxelles": ["#bruxelles", "#brussels", "#visitbrussels", "#belgique"],
    "Anvers":    ["#antwerp", "#anvers", "#visitantwerp", "#belgique"],
    "Amsterdam": ["#amsterdam", "#visitamsterdam", "#paysbas", "#amsterdamcity"],
}
# Tag de transparence, ajouté à toute publication montrant Ava.
AI_TAG = "#contenugenereparia"


def for_outfit(brand: dict, city: str = "Paris", n: int = 12) -> list[str]:
    """Post tenue : marque + ville sont toujours présentes."""
    must = [AI_TAG] + brand.get("hashtags", [])[:2]
    return _assemble(broad=BROAD_FASHION, mid=MID_FASHION,
                     niche=CITY_TAGS.get(city, CITY_TAGS["Paris"]), n=n, must=must)


def for_place(city: str, kind: str = "cafe", area: str = "", n: int = 12) -> list[str]:
    """
    Post adresse : la ville porte la découvrabilité locale, et le quartier est
    dérivé de l'adresse elle-même — un #jordaan en dur finissait sous une photo
    prise à De Pijp.
    """
    city_tags = CITY_TAGS.get(city, CITY_TAGS["Paris"])
    must      = [AI_TAG] + city_tags[:2] + _area_tag(area)
    return _assemble(broad=BROAD_PLACE, mid=MID_PLACE.get(kind, MID_PLACE["cafe"]),
                     niche=city_tags, n=n, must=must)


def _area_tag(area: str) -> list[str]:
    """#nomduquartier, à partir du premier segment du champ 'area'."""
    slug = state.norm(area.split(",")[0]).replace(" ", "")
    return [f"#{slug}"] if 4 <= len(slug) <= 24 else []


def for_travel(destination: str, n: int = 12) -> list[str]:
    """Post voyage : le tag de destination d'abord."""
    slug = state.norm(destination).replace(" ", "")
    must = [AI_TAG] + ([f"#{slug}"] if 3 <= len(slug) <= 28 else [])
    return _assemble(broad=BROAD_TRAVEL, mid=MID_TRAVEL,
                     niche=CITY_TAGS.get(destination, MID_TRAVEL), n=n, must=must)


def for_quote(db_hashtags: list[str], mood: str, n: int = 11) -> list[str]:
    """Jeu de hashtags d'un Reel citation. `db_hashtags` vient de la base."""
    niche = [h for h in db_hashtags if h.startswith("#")] + MOOD_TAGS.get(mood, [])
    return _assemble(broad=BROAD_QUOTE, mid=MID_QUOTE, niche=niche, n=n)


def for_book(title: str, author: str, n: int = 12) -> list[str]:
    """Jeu de hashtags d'un post livre. Titre et auteur sont toujours inclus :
    ce sont les tags les plus qualifiés, ceux que cherchent les lecteurs."""
    return _assemble(broad=BROAD_BOOK, mid=MID_BOOK, niche=NICHE_BOOK, n=n,
                     must=_entity_tags(title, author))


# ── Interne ───────────────────────────────────────────────────────────────────

def _entity_tags(title: str, author: str) -> list[str]:
    """#titredulivre et #nomdelauteur — les tags les plus qualifiés qui soient."""
    out = []
    for raw in (title, author):
        slug = state.norm(raw).replace(" ", "")
        if 3 <= len(slug) <= 28:
            out.append(f"#{slug}")
    return out


def _assemble(broad: list[str], mid: list[str], niche: list[str], n: int,
              must: list[str] | None = None) -> list[str]:
    recent = state.recent_hashtags(2)
    chosen: list[str] = [BRAND] + _dedupe(must or [])

    def take(pool: list[str], k: int):
        fresh = _dedupe([h for h in pool if h.lower() not in recent and h not in chosen])
        random.shuffle(fresh)
        picked = fresh[:k]
        if len(picked) < k:
            # Pool épuisé par l'anti-répétition : on complète avec le reste
            # plutôt que de rendre un jeu tronqué.
            rest = _dedupe([h for h in pool if h not in chosen and h not in picked])
            random.shuffle(rest)
            picked += rest[:k - len(picked)]
        chosen.extend(picked)

    take(broad, 1)
    take(niche, max(1, (n - 2) // 2))
    take(mid, n - len(chosen))

    random.shuffle(chosen)
    state.remember_hashtags(chosen)
    return chosen


def _dedupe(tags: list[str]) -> list[str]:
    seen, out = set(), []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


if __name__ == "__main__":
    for i in range(3):
        print(f"citation {i}:", " ".join(for_quote(["#stoicisme", "#marcaurele"], "calm")))
    for i in range(2):
        print(f"livre {i}   :", " ".join(for_book("Hamnet", "Maggie O'Farrell")))
