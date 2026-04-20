"""
Agent — Reformate un article de critique littéraire pour chaque plateforme
via l'API Claude (Anthropic). Respecte le style d'Ava : intime, poétique, honnête.
"""
import anthropic
from config import ANTHROPIC_API_KEY

_client = None

_STYLE = """Tu es Ava, auteure du blog littéraire "The Journey of Ava".
Ton style : intime, poétique, précis. Tu écris en français.
Tu ne fais pas de résumé de quatrième de couverture — tu partages une expérience de lecture.
Tu es honnête sur ce qui t'a moins convaincue. Tu ne sur-vendes pas.
Chaque phrase doit sonner comme toi, pas comme une publicité."""


def generate_social_posts(article: dict) -> dict:
    """Génère tous les posts à partir de l'article."""
    title  = article["title"]
    author = article["author"]
    body   = article["body"]
    ctx    = f"Livre : {title} — {author}\n\nArticle complet :\n{body}"

    posts = {}

    # ── Instagram caption ─────────────────────────────────────────────────────
    print("  [agent_social_writer] Instagram caption...")
    posts["instagram_caption"] = _call(
        system=_STYLE + """

Transforme cet article en caption Instagram.
Format :
- 3 à 5 phrases qui donnent envie de lire sans tout dévoiler
- 1 question ou phrase finale qui invite à l'engagement
- Ton personnel, pas journalistique
- Maximum 250 mots. Pas de hashtags.""",
        prompt=ctx,
    )

    # ── Hashtags ──────────────────────────────────────────────────────────────
    posts["hashtags"] = _call(
        system="""Génère 15 hashtags Instagram pour une critique littéraire en français.
Mix : hashtags généraux (#bookstagram #lecture #livres) + spécifiques au livre et aux thèmes.
Une seule ligne, séparés par des espaces.""",
        prompt=f"Livre : {title} — {author}",
    )

    # ── Reel script ───────────────────────────────────────────────────────────
    print("  [agent_social_writer] Reel script...")
    posts["reel_script"] = _call(
        system=_STYLE + """

Écris un script pour un Reel Instagram de 30 à 45 secondes.
Voix off calme, comme un journal intime lu à voix haute.
Structure :
1. Une phrase d'accroche qui arrête le scroll (5 sec)
2. De quoi parle ce livre — 2 phrases max (8 sec)
3. Ce qui t'a vraiment touchée — 1 élément précis (15 sec)
4. Une phrase finale mémorable (5 sec)
Texte uniquement, pas de didascalies ni de timecodes.""",
        prompt=ctx,
    )

    # ── TikTok script ─────────────────────────────────────────────────────────
    print("  [agent_social_writer] TikTok script...")
    posts["tiktok_script"] = _call(
        system=_STYLE + """

Écris un script TikTok BookTok de 45 à 60 secondes.
Plus direct qu'Instagram, mais toujours ton style.
Structure :
1. Hook immédiat — commence par ce qui t'a le plus frappée (5 sec)
2. Pitch ultra-court du livre (10 sec)
3. Ce qui est bien — 1 chose précise (15 sec)
4. Ce qui est moins bien — l'honnêteté crée la confiance (10 sec)
5. Verdict : pour qui ce livre ? (8 sec)
Texte uniquement.""",
        prompt=ctx,
    )

    # ── Facebook post ─────────────────────────────────────────────────────────
    print("  [agent_social_writer] Facebook post...")
    posts["facebook_post"] = _call(
        system=_STYLE + """

Écris un post Facebook pour "The Journey of Ava".
Plus développé qu'Instagram, invite à la conversation.
Structure :
- 1 paragraphe d'ouverture qui accroche
- 2 paragraphes de développement (tu peux citer des phrases de l'article)
- 1 question finale qui invite au commentaire
- Termine par : "L'article complet est sur le blog → [LIEN]"
Maximum 350 mots.""",
        prompt=ctx,
    )

    return posts


def _call(system: str, prompt: str) -> str:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = _client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"  [agent_social_writer] Erreur Claude API : {e}")
        return ""
