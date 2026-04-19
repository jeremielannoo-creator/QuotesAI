"""
Agent 1 — Génération de citations via Claude (Anthropic)
Produit : citation, auteur, humeur, mots-clés, hashtags
"""
import json
import re
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Prompt ─────────────────────────────────────────────────────────────────────
_PROMPT = """Tu es un expert en philosophie stoïcienne et en citations virales sur les réseaux sociaux.

Génère UNE citation inspirante. Elle doit provenir d'un de ces philosophes :
Marc Aurèle, Épictète, Sénèque, Nietzsche, Socrate, Platon, Schopenhauer.

Règles :
- La citation doit être authentique ou très fidèle à l'esprit du philosophe
- Si elle est en latin/allemand/grec, fournis la traduction française
- Choisie pour son impact émotionnel sur un public moderne

Réponds UNIQUEMENT en JSON valide, sans markdown, sans commentaires :
{
  "quote": "La citation complète en français",
  "author": "Prénom Nom du philosophe",
  "original": "Citation dans la langue d'origine si différente du français, sinon null",
  "mood": "calm|energetic|melancholic|triumphant|contemplative",
  "keywords": ["mot_clé_1", "mot_clé_2", "mot_clé_3"],
  "hashtags": ["#citation", "#stoicisme", "#philosophie", "#motivation", "#sagesse", "#nietzsche", "#marcaurele", "#quotes", "#inspiration", "#mindset"]
}

Les hashtags doivent mélanger français et anglais pour maximiser la portée."""


def generate_quote(custom_prompt: str | None = None) -> dict:
    """
    Appelle Claude et retourne un dictionnaire structuré.
    """
    prompt = custom_prompt or _PROMPT

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Nettoyer le JSON si Claude ajoute des balises markdown
    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)

    data = json.loads(raw.strip())

    # Valider les champs obligatoires
    for field in ("quote", "author", "mood", "keywords", "hashtags"):
        if field not in data:
            raise ValueError(f"Champ manquant dans la réponse Claude : '{field}'")

    return data


if __name__ == "__main__":
    result = generate_quote()
    print(json.dumps(result, ensure_ascii=False, indent=2))
