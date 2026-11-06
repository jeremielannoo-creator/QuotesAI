"""
utils/gemini.py — Appel Gemini renvoyant du JSON, avec échec silencieux.

Toutes les rédactions du bot (accroches, légendes, conseils) passent par ici.
La règle est la même partout : si l'API manque, échoue ou renvoie un JSON
incomplet, on retourne None et l'appelant se rabat sur ses réserves écrites à
l'avance. Une publication ne doit jamais sauter à cause d'un quota.
"""
import json
import re

from config import GEMINI_API_KEY

MODEL = "gemini-2.0-flash-lite"


def json_completion(
    system: str,
    prompt: str,
    required: tuple[str, ...],
    max_tokens: int = 700,
    temperature: float = 1.0,
) -> dict | None:
    """Retourne le JSON produit par Gemini, ou None si quoi que ce soit cloche."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        raw  = re.sub(r"^```(?:json)?|```$", "", resp.text.strip(), flags=re.MULTILINE)
        data = json.loads(raw.strip())
    except Exception as e:
        print(f"  [gemini] Indisponible ({e}) — réserve utilisée")
        return None

    if all(data.get(k) for k in required):
        return data
    print("  [gemini] Réponse incomplète — réserve utilisée")
    return None
