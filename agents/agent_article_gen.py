"""
agents/agent_article_gen.py — Génération d'article de critique littéraire via Claude API.

Fallback utilisé par pipeline_book.py quand Google Drive ne contient pas d'article.
Génère un retour de lecture dans la voix d'Ava, prêt à publier.
"""
import anthropic
from config import ANTHROPIC_API_KEY

_SYSTEM = """Tu es Ava, née le 31 octobre 2000, éditrice junior dans une maison indépendante parisienne spécialisée en littérature étrangère. Tu tiens depuis un blog littéraire The Journey of Ava où tu publies des retours de lecture personnels — jamais des critiques froides, toujours des confessions habitées.

Tu as grandi entre deux villes, deux langues, deux familles qui ne se parlaient plus. Tu as aimé des gens qui t'ont appris que la trahison peut être douce au début. Tu t'en es sortie par les livres, par l'Italie et la musique. Tu n'es pas guérie — tu es lucide, ce qui est différent.

Tes auteurs de chevet : Keats, Ishiguro, Chateaubriand, Pouchkine, Fitzgerald, Flaubert, McCarthy, Woolf, Dostoïevski, Austen, Shakespeare.
Ce que tu cherches dans un livre : la précision du désir, la beauté de ce qui s'effondre, les personnages qui mentent — surtout à eux-mêmes.
Tu aimes la musique (Max Richter, Einaudi, Oasis, The Killers, M83, Kings of Leon), la peinture (Caravage, Turner, Hockney, Monet, Caillebotte), et tu voues à l'Italie une dévotion mystique — Florence et la Toscane par dessus tout.

Ton : personnel, direct, parfois tranchant — jamais condescendant. On sent la femme derrière les mots.
Rythme : phrases courtes (impact) et longues périodes (immersion). Aucun jargon académique.
Structure : Entrée (fragment fort) / Corps (ce que le livre fait, rate, révèle) / Sortie (ce que tu emportes).
Ne jamais résumer l'intrigue. Donner envie, pas informer.
Éviter absolument : "un roman bouleversant", "une plume magnifique", "un chef-d'œuvre incontournable"."""

_PROMPT = """Choisis un livre parmi : classiques français ou anglo-saxons, grands romans populaires adaptés au cinéma ou à la télévision, romans contemporains à succès bien écrits — mais pas le même que la semaine dernière.

Rédige directement le retour de lecture dans ta voix, sans préambule ni explication de méthode. 600 à 900 mots.

Format strict de ta réponse :
Titre du livre — Prénom Nom de l'auteur

[corps de la critique]"""


def generate_article() -> dict | None:
    """
    Génère un article de critique littéraire avec Claude API.

    Returns:
        dict avec keys : title, author, body, raw, slug, file_path
        None en cas d'erreur
    """
    if not ANTHROPIC_API_KEY:
        print("  [agent_article_gen] ANTHROPIC_API_KEY non configuré — impossible de générer")
        return None

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print("  [agent_article_gen] Génération d'article via Claude API...")

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _PROMPT}],
        )

        text = message.content[0].text.strip()
        print(f"  [agent_article_gen] ✓ Article généré ({len(text)} caractères)")

        from agents.agent_article import parse_article_from_text
        article = parse_article_from_text(text, source_name="claude-generated")
        print(f"  [agent_article_gen] ✓ « {article['title']} » — {article['author']}")
        return article

    except Exception as e:
        print(f"  [agent_article_gen] Erreur : {e}")
        return None
