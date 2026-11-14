"""
agents/agent_ava_photo.py — Photos du personnage Ava, générées par Gemini.

Ava est un personnage de fiction. La cohérence du visage et de la silhouette
d'une photo à l'autre vient des portraits de référence : on envoie 2 images de
Photos/Portraits/ au modèle avec la description de la nouvelle scène, plutôt
que de repartir d'un prompt nu à chaque fois.

Trois types de scènes :
    outfit  — essayage / tenue du jour, une marque mise en avant
    place   — café, bar ou restaurant d'une ville du circuit
    travel  — carnet de voyage

Sortie : JPEG 1080×1350 (4:5, le format qui occupe le plus de hauteur dans le
feed Instagram).

⚠️ Toute publication issue d'ici doit porter config.AI_DISCLOSURE.
"""
import io
import os
import random
import time

from PIL import Image

from config import AVA_REF_DIRS, GEMINI_API_KEY, GEMINI_IMAGE_MODEL, TEMP_DIR

OUT_W, OUT_H = 1080, 1350

# ── Constantes de personnage ──────────────────────────────────────────────────
# Reprises de la fiche d'Ava (agent_article_gen) pour que l'image et la plume
# décrivent la même personne.
AVA_IDENTITY = (
    "Ava, a 25-year-old woman with long wavy chestnut-brown hair, fair skin, "
    "slim build, natural makeup, understated elegance"
)

FRAMINGS = [
    "candid shot from behind, she is looking away",
    "three-quarter view, she is not looking at the camera",
    "wide editorial shot, she occupies a third of the frame",
    "over-the-shoulder shot, face partly hidden",
    "seated, seen from across the table",
]

LIGHTING = [
    "soft morning window light", "golden hour backlight", "grey overcast daylight",
    "warm interior lamplight", "blue hour street light",
]

FILM_LOOK = (
    "shot on 35mm film, shallow depth of field, natural grain, muted warm palette, "
    "editorial lifestyle photography, no text, no watermark, no logo overlay, "
    "photorealistic, vertical 4:5 framing"
)


def generate(scene_prompt: str, label: str = "ava") -> str | None:
    """
    Génère une photo d'Ava à partir d'une description de scène.

    Args:
        scene_prompt: la scène en anglais (voir prompt_outfit / prompt_place / …)
        label:        préfixe du fichier de sortie

    Returns:
        Chemin du JPEG 1080×1350, ou None si la génération échoue.
    """
    if not GEMINI_API_KEY:
        print("  [ava_photo] GEMINI_API_KEY absent — génération impossible")
        return None

    refs = _reference_images(2)
    if not refs:
        print(f"  [ava_photo] Aucun portrait de référence dans {AVA_REF_DIRS}")
        return None

    prompt = (
        f"Using the attached reference photos of the same woman, keep her face, "
        f"hair and body type strictly identical. Generate a new photograph.\n\n"
        f"Subject: {AVA_IDENTITY}.\n"
        f"Scene: {scene_prompt}\n"
        f"Framing: {random.choice(FRAMINGS)}.\n"
        f"Light: {random.choice(LIGHTING)}.\n"
        f"Style: {FILM_LOOK}."
    )

    raw = _call_gemini(prompt, refs)
    if not raw:
        return None

    os.makedirs(TEMP_DIR, exist_ok=True)
    dest = os.path.join(TEMP_DIR, f"{label}_{int(time.time())}.jpg")
    _to_portrait(raw).save(dest, "JPEG", quality=92)
    print(f"  [ava_photo] ✓ Photo générée : {dest}")
    return dest


# ── Prompts de scène ──────────────────────────────────────────────────────────

def prompt_outfit(brand: dict, city: str) -> str:
    piece = random.choice(brand.get("pieces", ["an outfit"]))
    return (
        f"She is wearing {piece} in the style of the French label {brand['name']}, "
        f"trying it on in a {city} apartment with herringbone parquet and tall windows, "
        f"or in front of a full-length mirror. The clothes are the subject of the photo."
    )


def prompt_place(place: dict) -> str:
    return (
        f"She is at {place['name']}, a {place['kind']} in {place['city']} "
        f"({place['vibe']}). She is having {random.choice(place.get('order', ['a coffee']))}, "
        f"a book on the table. Real interior atmosphere, other customers blurred in the background."
    )


def prompt_travel(destination: str, detail: str) -> str:
    return (
        f"She is travelling in {destination}. {detail} "
        f"Travel diary atmosphere, nothing posed, the place matters more than her."
    )


# ── Interne ───────────────────────────────────────────────────────────────────

def _reference_images(n: int) -> list[Image.Image]:
    """Charge n portraits de référence au hasard (redimensionnés, pour la latence)."""
    files = []
    for folder in AVA_REF_DIRS:
        if os.path.isdir(folder):
            files = [os.path.join(folder, f) for f in os.listdir(folder)
                     if f.lower().endswith((".png", ".jpg", ".jpeg"))]
            if files:
                break
    out = []
    for path in random.sample(files, k=min(n, len(files))):
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((1024, 1024))
            out.append(img)
        except Exception as e:
            print(f"  [ava_photo] Référence illisible {os.path.basename(path)} : {e}")
    return out


def _call_gemini(prompt: str, refs: list[Image.Image]) -> bytes | None:
    """Appelle le modèle d'image et retourne les octets de la première image."""
    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"  [ava_photo] {GEMINI_IMAGE_MODEL} ← {prompt[:70]}…")
        resp = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=[prompt, *refs],
        )
        for part in resp.candidates[0].content.parts:
            data = getattr(part, "inline_data", None)
            if data and data.data:
                return data.data
        print("  [ava_photo] Réponse sans image (prompt probablement refusé)")
    except Exception as e:
        print(f"  [ava_photo] Échec Gemini : {e}")
    return None


def to_portrait_file(path: str) -> str:
    """
    Normalise une photo locale en 1080×1350 et retourne le nouveau chemin.

    Instagram refuse les images plus hautes que 4:5 : les photos de la
    photothèque doivent passer par ici avant d'être envoyées.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    with open(path, "rb") as f:
        img = _to_portrait(f.read())
    dest = os.path.join(TEMP_DIR, f"photo_{int(time.time())}.jpg")
    img.save(dest, "JPEG", quality=92)
    return dest


def _to_portrait(raw: bytes) -> Image.Image:
    """Recadre au centre en 4:5 et met à l'échelle 1080×1350."""
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    target = OUT_W / OUT_H
    w, h = img.size
    if w / h > target:                       # trop large → rogne les côtés
        new_w = int(h * target)
        img = img.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    else:                                    # trop haute → rogne haut et bas
        new_h = int(w / target)
        img = img.crop((0, (h - new_h) // 2, w, (h - new_h) // 2 + new_h))
    return img.resize((OUT_W, OUT_H), Image.LANCZOS)


if __name__ == "__main__":
    print(generate(
        "She is sitting on a café terrace in Paris in early autumn, "
        "a espresso and a paperback in front of her.",
        label="ava_test",
    ))
