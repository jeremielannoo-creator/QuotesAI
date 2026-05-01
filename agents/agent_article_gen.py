"""
agents/agent_article_gen.py — Génération d'article de critique littéraire via Gemini API.

Fallback utilisé par pipeline_book.py quand Google Drive ne contient pas d'article.
Utilise google-genai (nouveau SDK officiel Google — aistudio.google.com pour la clé).
"""
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

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

_PROMPT = """Choisis un livre parmi : classiques français ou anglo-saxons, grands romans populaires adaptés au cinéma ou à la télévision, romans contemporains à succès bien écrits.

Rédige directement le retour de lecture dans la voix d'Ava, sans préambule ni explication de méthode. 600 à 900 mots.

Format strict de ta réponse — respecte exactement ces deux premières lignes :
Titre du livre — Prénom Nom de l'auteur

[corps de la critique, commence directement]"""


def generate_article() -> dict | None:
    """
    Génère un article de critique littéraire avec Gemini API (gratuit).

    Returns:
        dict avec keys : title, author, body, raw, slug, file_path
        None en cas d'erreur
    """
    if not GEMINI_API_KEY:
        print("  [agent_article_gen] GEMINI_API_KEY non configuré")
        print("  [agent_article_gen] → Clé gratuite sur aistudio.google.com")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        print("  [agent_article_gen] Génération d'article via Gemini API...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=_PROMPT,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                max_output_tokens=1500,
                temperature=0.9,
            ),
        )

        text = response.text.strip()
        print(f"  [agent_article_gen] ✓ Article généré ({len(text)} caractères)")

        from agents.agent_article import parse_article_from_text
        article = parse_article_from_text(text, source_name="gemini-generated")
        print(f"  [agent_article_gen] ✓ « {article['title']} » — {article['author']}")
        return article

    except Exception as e:
        print(f"  [agent_article_gen] Erreur : {e}")
        return None
