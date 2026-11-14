"""
agents/agent_scenes.py — Vocabulaire visuel partagé.

Un seul endroit décrit à quoi ressemble une vidéo « The Journey of Ava ».
Consommé par :
  - agent_video    → requêtes Pexels / Pixabay
  - agent_video_ai → prompts text-to-video (HuggingFace, ou copier-coller Flow)
  - agent_render   → mouvement caméra

Le but est la VARIÉTÉ : 8 familles visuelles au lieu des 5 listes de mots-clés
qui tournaient en boucle, et une famille différente de la publication précédente.
"""
import random

# ── Familles visuelles ────────────────────────────────────────────────────────
# "stock" : requêtes pour banques d'images (anglais, termes qui donnent des
#           résultats réels sur Pexels/Pixabay)
# "t2v"   : descriptions de scène pour un modèle text-to-video
SCENE_FAMILIES: dict[str, dict[str, list[str]]] = {
    "water": {
        "stock": ["ocean waves slow motion", "calm lake morning", "rain on window",
                  "river stones water", "sea foam beach", "underwater light rays"],
        "t2v":   ["slow ocean swell breaking over dark rocks",
                  "raindrops sliding down a window pane, blurred city behind",
                  "still lake surface with mist drifting across it",
                  "sunlight refracting through shallow moving water"],
    },
    "mountain": {
        "stock": ["mountain peak clouds", "foggy valley sunrise", "desert dunes wind",
                  "cliff edge sea", "snow ridge light", "alpine lake reflection"],
        "t2v":   ["clouds pouring over a mountain ridge at dawn",
                  "wind combing ripples across desert dunes",
                  "a lone cliff edge above a grey sea, fog moving through"],
    },
    "forest": {
        "stock": ["forest light rays", "autumn leaves falling", "moss stones woods",
                  "tall trees wind", "pine forest fog", "wildflowers meadow wind"],
        "t2v":   ["shafts of light cutting through mist between tall pines",
                  "autumn leaves drifting down through still forest air",
                  "tall grass bending in slow wind, late afternoon light"],
    },
    "urban": {
        "stock": ["rainy street night reflections", "cafe terrace people", "neon city night",
                  "empty subway station", "rooftop city dusk", "old european street morning"],
        "t2v":   ["wet asphalt reflecting neon signs, cars passing slowly",
                  "an empty café terrace at blue hour, chairs stacked",
                  "narrow old european street, morning light on stone walls"],
    },
    "intimate": {
        "stock": ["open book pages turning", "coffee cup steam", "candle flame close up",
                  "hands writing notebook", "linen curtain window light", "vinyl record playing"],
        "t2v":   ["steam curling off a coffee cup beside an open book",
                  "a candle flame trembling in a dark room",
                  "a hand turning the page of a worn paperback, window light",
                  "linen curtains breathing in front of an open window"],
    },
    "sky": {
        "stock": ["clouds timelapse sky", "starry night sky", "sunrise horizon",
                  "northern lights", "birds flying sky", "storm clouds moving"],
        "t2v":   ["stars wheeling slowly over a black horizon",
                  "heavy clouds moving across a wide empty sky",
                  "the first band of light appearing on a flat horizon"],
    },
    "texture": {
        "stock": ["ink in water", "smoke slow motion black", "dust particles light",
                  "silk fabric moving", "fire embers close up", "paper texture macro"],
        "t2v":   ["black ink blooming into clear water",
                  "dust motes drifting through a single beam of light",
                  "embers rising slowly from a dying fire",
                  "silk folding and unfolding in slow motion"],
    },
    "human": {
        "stock": ["silhouette walking sunset", "person back looking horizon", "crowd blurred motion",
                  "dancer slow motion", "person reading window", "couple walking away"],
        "t2v":   ["a lone silhouette walking away down a long road at dusk",
                  "a figure seen from behind, standing still before a wide horizon",
                  "a blurred crowd moving past a motionless person"],
    },
}

# ── Familles privilégiées par humeur (les 2 premières pèsent le plus) ─────────
MOOD_FAMILIES: dict[str, list[str]] = {
    "calm":          ["water", "sky", "forest", "intimate"],
    "warm":          ["intimate", "human", "urban", "forest"],
    "melancholic":   ["urban", "water", "texture", "human"],
    "contemplative": ["texture", "sky", "intimate", "mountain"],
    "energetic":     ["mountain", "urban", "human", "sky"],
    "triumphant":    ["mountain", "sky", "water", "human"],
}

# ── Mots-clés des citations → famille visuelle ───────────────────────────────
# Les mots-clés de la base sont surtout abstraits (love, self, truth, freedom…).
# Chacun est relié à la famille qui l'illustre ; quand le mot est filmable, on
# donne en plus la requête de stock qui le montre littéralement. Avant, la
# famille ne dépendait que de l'humeur : une citation sur l'océan pouvait
# tomber sur une rue de nuit.
KEYWORD_SCENES: dict[str, tuple[str, str]] = {
    # water — calme, lâcher-prise
    "ocean": ("water", "ocean waves"), "sea": ("water", "sea waves"),
    "water": ("water", "water surface"), "calm water": ("water", "calm lake"),
    "river": ("water", "river flowing"), "rain": ("water", "rain drops window"),
    "reflection": ("water", "water reflection"), "flow": ("water", ""),
    "peace": ("water", ""), "silence": ("water", ""), "stillness": ("water", ""),
    "calm": ("water", ""), "peaceful": ("water", ""), "patience": ("water", ""),
    "letting go": ("water", ""), "acceptance": ("water", ""), "accept": ("water", ""),
    # mountain — effort, force
    "mountain": ("mountain", "mountain peak"), "climbing": ("mountain", "rock climbing"),
    "desert": ("mountain", "desert dunes"), "obstacle": ("mountain", "steep mountain trail"),
    "strength": ("mountain", ""), "courage": ("mountain", ""), "effort": ("mountain", ""),
    "will": ("mountain", ""), "discipline": ("mountain", ""), "overcome": ("mountain", ""),
    "endure": ("mountain", ""), "résilience": ("mountain", ""), "dépassement": ("mountain", ""),
    "force": ("mountain", ""), "power": ("mountain", ""), "success": ("mountain", ""),
    # forest — nature, croissance
    "nature": ("forest", ""), "forest": ("forest", "forest light rays"),
    "growth": ("forest", "plant growing"), "flowers": ("forest", "flowers wind"),
    "garden": ("forest", "garden morning"), "spring": ("forest", "spring blossom"),
    "rose": ("forest", "rose petals"), "bees": ("forest", "bees flowers"),
    "fog": ("forest", "pine forest fog"), "harmony": ("forest", ""),
    "healing": ("forest", ""), "simplicity": ("forest", ""),
    # urban — le monde, les autres
    "world": ("urban", ""), "monde": ("urban", ""), "others": ("urban", ""),
    "other": ("urban", ""), "work": ("urban", ""), "night": ("urban", "city night lights"),
    # intimate — amour, savoir, intériorité douce
    "love": ("intimate", ""), "amour": ("intimate", ""), "heart": ("intimate", ""),
    "cœur": ("intimate", ""), "books": ("intimate", "open book pages turning"),
    "library": ("intimate", "library books"), "candle": ("intimate", "candle flame close up"),
    "music": ("intimate", "vinyl record playing"), "art": ("intimate", "painter brush canvas"),
    "warmth": ("intimate", "fireplace"), "knowledge": ("intimate", ""),
    "connaissance": ("intimate", ""), "wisdom": ("intimate", ""), "sagesse": ("intimate", ""),
    "learning": ("intimate", ""), "education": ("intimate", ""), "memory": ("intimate", ""),
    "creation": ("intimate", ""), "creativity": ("intimate", ""), "gratitude": ("intimate", ""),
    "kindness": ("intimate", ""), "compassion": ("intimate", ""), "giving": ("intimate", ""),
    "generosity": ("intimate", ""), "générosité": ("intimate", ""),
    # sky — lumière, espoir, infini
    "light": ("sky", ""), "lumière": ("sky", ""), "sunrise": ("sky", "sunrise horizon"),
    "sunset": ("sky", "sunset sky"), "morning": ("sky", "morning sunrise"),
    "sun": ("sky", "sun rays clouds"), "stars": ("sky", "starry night sky"),
    "universe": ("sky", "galaxy stars"), "cosmos": ("sky", "galaxy stars"),
    "sky": ("sky", "clouds sky"), "horizon": ("sky", "horizon"),
    "eagle": ("sky", "eagle flying"), "storm": ("sky", "storm clouds"),
    "freedom": ("sky", "birds flying sky"), "liberté": ("sky", "birds flying sky"),
    "hope": ("sky", ""), "dream": ("sky", ""), "future": ("sky", ""), "beyond": ("sky", ""),
    "eternity": ("sky", ""), "eternal": ("sky", ""), "divine": ("sky", ""),
    "god": ("sky", ""), "faith": ("sky", ""),
    # texture — introspection, temps, impermanence
    "self": ("texture", ""), "soi": ("texture", ""), "inner": ("texture", ""),
    "intérieur": ("texture", ""), "soul": ("texture", ""), "âme": ("texture", ""),
    "mind": ("texture", ""), "mirror": ("texture", "mirror reflection"),
    "truth": ("texture", ""), "vérité": ("texture", ""), "illusion": ("texture", ""),
    "perception": ("texture", ""), "thought": ("texture", ""), "conscience": ("texture", ""),
    "time": ("texture", "hourglass sand"), "temps": ("texture", "hourglass sand"),
    "fire": ("texture", "fire flames"), "shadow": ("texture", "shadow light"),
    "dark": ("texture", ""), "meditation": ("texture", "incense smoke"),
    "impermanence": ("texture", "smoke slow motion"), "death": ("texture", ""),
    "mortality": ("texture", ""), "past": ("texture", ""), "change": ("texture", ""),
    "transformation": ("texture", ""), "transform": ("texture", ""),
    # human — chemin, action, solitude
    "path": ("human", "path walking"), "chemin": ("human", "path walking"),
    "journey": ("human", "person walking road"), "road": ("human", "empty road"),
    "travel": ("human", "traveler backpack"), "voyage": ("human", "traveler backpack"),
    "running": ("human", "running sunrise"), "dance": ("human", "dancer slow motion"),
    "warrior": ("human", ""), "solitude": ("human", "person alone"),
    "alone": ("human", "person alone"), "adventure": ("human", ""), "action": ("human", ""),
    "life": ("human", ""), "vie": ("human", ""), "live": ("human", ""), "joy": ("human", ""),
    "happiness": ("human", ""), "bonheur": ("human", ""), "together": ("human", ""),
    "humanity": ("human", ""), "community": ("human", ""), "direction": ("human", ""),
    "forward": ("human", ""), "begin": ("human", ""), "start": ("human", ""),
}

# Poids d'un mot-clé reconnu face aux familles de l'humeur (2 et 1) : un
# mot-clé suffit à rendre sa famille favorite sans la rendre systématique.
_KEYWORD_WEIGHT = 3.0


# ── Grammaire cinématographique ──────────────────────────────────────────────
CAMERA_MOVES = [
    "slow push in", "slow dolly out", "gentle handheld drift",
    "locked-off static shot", "slow tilt up", "slow lateral pan",
]

LIGHTING = [
    "golden hour backlight", "soft overcast light", "blue hour",
    "hard side light with deep shadows", "candlelight glow",
    "moonlight", "diffused window light",
]

LOOKS = [
    "35mm film grain", "shallow depth of field, heavy bokeh",
    "anamorphic lens flare", "muted desaturated palette",
    "warm amber tones", "high contrast chiaroscuro",
]


# ── API ───────────────────────────────────────────────────────────────────────

def _keyword_hits(keywords: list[str]) -> list[tuple[str, str]]:
    """(famille, requête) des mots-clés reconnus, dans l'ordre de la citation."""
    return [KEYWORD_SCENES[k.lower().strip()] for k in keywords
            if k.lower().strip() in KEYWORD_SCENES]


def pick_family(mood: str, avoid: str = "", keywords: list[str] | None = None) -> str:
    """
    Choisit une famille visuelle d'après l'humeur ET les mots-clés de la
    citation, en évitant celle du post précédent. Les 2 premières familles de
    l'humeur pèsent 2, les suivantes 1, chaque mot-clé reconnu ajoute 3 à sa
    famille.
    """
    families = MOOD_FAMILIES.get(mood, MOOD_FAMILIES["calm"])
    scores   = {f: 2.0 if f in families[:2] else 1.0 for f in families}
    for fam, _query in _keyword_hits(keywords or []):
        scores[fam] = scores.get(fam, 0.0) + _KEYWORD_WEIGHT

    pool = {f: s for f, s in scores.items() if f != avoid} or scores
    return random.choices(list(pool), weights=list(pool.values()), k=1)[0]


def stock_queries(mood: str, keywords: list[str], family: str, n: int = 10) -> list[str]:
    """
    Ordre de recherche pour les banques de stock :
      requêtes littérales des mots-clés de la famille choisie (ocean → "ocean
      waves") → famille choisie → autres familles de l'humeur → familles
      restantes (garde-fou, pour ne jamais échouer).

    Les mots-clés bruts ne sont plus envoyés tels quels : « self » ou « truth »
    ramenaient des selfies et des images sans rapport.
    """
    literal = [q for fam, q in _keyword_hits(keywords) if fam == family and q]

    fam_terms = SCENE_FAMILIES[family]["stock"][:]
    random.shuffle(fam_terms)

    others: list[str] = []
    for f in MOOD_FAMILIES.get(mood, MOOD_FAMILIES["calm"]):
        if f != family:
            others += random.sample(SCENE_FAMILIES[f]["stock"], k=2)

    safety = [SCENE_FAMILIES[f]["stock"][0] for f in SCENE_FAMILIES if f != family]

    queries = literal + fam_terms[:3] + others + fam_terms[3:] + safety
    # dédoublonne en conservant l'ordre
    seen, out = set(), []
    for q in queries:
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:n] if n else out


def t2v_prompt(mood: str, family: str) -> str:
    """
    Prompt text-to-video. Utilisable tel quel par agent_video_ai (HuggingFace)
    ou copié-collé dans Google Flow pour produire la banque de clips.
    """
    scene = random.choice(SCENE_FAMILIES[family]["t2v"])
    return (
        f"{scene}. {random.choice(CAMERA_MOVES)}, {random.choice(LIGHTING)}, "
        f"{random.choice(LOOKS)}. Cinematic, vertical 9:16 framing, "
        f"no text, no logos, no faces to camera, calm continuous motion."
    )


def camera_move(mood: str) -> str:
    """Mouvement caméra à simuler au montage : 'in', 'out' ou 'still'."""
    if mood in ("energetic", "triumphant"):
        return random.choice(["in", "in", "out"])
    if mood in ("melancholic", "contemplative"):
        return random.choice(["out", "still", "in"])
    return random.choice(["in", "out"])


if __name__ == "__main__":
    for m in MOOD_FAMILIES:
        fam = pick_family(m, keywords=["solitude", "ocean"])
        print(f"\n{m:14} → {fam}")
        print("  stock :", stock_queries(m, ["solitude", "ocean"], fam, n=4))
        print("  t2v   :", t2v_prompt(m, fam))
