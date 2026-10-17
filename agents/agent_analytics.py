"""
Agent Analytics — Boucle d'apprentissage QuotesAI
Tire les statistiques Instagram (Graph API), relie chaque post au mood de la
citation (via le texte de la légende) et calcule des poids de performance par
mood. Ces poids sont ensuite utilisés par agent_quote_db pour biaiser la
sélection vers les thèmes qui marchent.

Sortie : db/mood_weights.json

Usage :
    python -m agents.agent_analytics          # rapport + écriture des poids
    python -m agents.agent_analytics --report # rapport seulement (pas d'écriture)

Signal d'engagement : on ne compte plus les likes bruts. La portée d'un post
varie d'un facteur 40 d'une publication à l'autre (mesuré : 3 à 124 comptes
touchés) — comparer des totaux revenait à comparer des loteries. On mesure
maintenant un TAUX rapporté à la portée :

    interactions = likes + 2×commentaires + 3×enregistrements + 3×partages
    taux         = interactions / portée

Enregistrements et partages pèsent le plus : ce sont les signaux que l'algorithme
Instagram valorise le plus, et ceux que visent les formats voyage et lifestyle.

Nécessite la permission `instagram_manage_insights` sur le token. Sans elle, on
se rabat automatiquement sur likes + commentaires.
"""
import os
import re
import json
import math
import sqlite3
import statistics
import unicodedata
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

load_dotenv()

# Console Windows (cp1252) → force l'UTF-8 pour les accents et emojis des rapports
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH    = os.path.join(BASE_DIR, "db", "quotes.db")
WEIGHTS_PATH = os.path.join(BASE_DIR, "db", "mood_weights.json")

_IG_BASE = "https://graph.facebook.com/v21.0"
PARIS    = ZoneInfo("Europe/Paris")

# Poids plancher / plafond pour éviter d'exclure totalement un mood ou de trop
# concentrer la sélection sur un seul.
WEIGHT_FLOOR = 0.3
WEIGHT_CAP   = 3.0
MIN_SAMPLE   = 3   # nombre mini de posts pour faire confiance à un mood

# Pondération des interactions. Un enregistrement vaut trois likes : c'est
# l'intention de revenir, pas le réflexe de pouce.
W_LIKE, W_COMMENT, W_SAVED, W_SHARE = 1, 2, 3, 3

# Lissage des créneaux horaires : nombre de posts fictifs à portée médiane
# ajoutés à chaque créneau avant d'en faire la moyenne.
SLOT_PRIOR = 3

# Les insights coûtent un appel par média. On se limite aux publications
# récentes : au-delà, le contenu ne ressemble plus à ce qu'on produit.
INSIGHTS_LIMIT = 80


def _norm(s: str) -> str:
    """Minuscule, sans accents, alphanumérique — pour matcher légende ↔ citation."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _fetch_media() -> list[dict]:
    """Récupère tous les médias Instagram (pagination complète)."""
    tok = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    uid = os.getenv("INSTAGRAM_USER_ID")
    if not tok or not uid:
        raise RuntimeError("INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_USER_ID manquants dans .env")

    media, url = [], f"{_IG_BASE}/{uid}/media"
    params = {
        "fields": "id,caption,media_type,timestamp,like_count,comments_count",
        "limit": 50, "access_token": tok,
    }
    while url:
        d = requests.get(url, params=params, timeout=30).json()
        if "error" in d:
            raise RuntimeError(f"Instagram API : {d['error']}")
        media.extend(d.get("data", []))
        url = d.get("paging", {}).get("next")
        params = None  # l'URL "next" contient déjà le token
    return media


def _fetch_insights(media_id: str, tok: str) -> dict:
    """
    Portée, enregistrements et partages d'un média.
    Retourne {} si la permission manque ou si la métrique n'existe pas pour ce
    type de média — l'appelant se rabat alors sur likes + commentaires.
    """
    try:
        r = requests.get(
            f"{_IG_BASE}/{media_id}/insights",
            params={"metric": "reach,saved,shares", "access_token": tok},
            timeout=20,
        )
        if not r.ok:
            return {}
        return {d["name"]: d["values"][0]["value"] for d in r.json().get("data", [])}
    except requests.RequestException:
        return {}


def _engagement(m: dict) -> tuple[float, dict]:
    """
    Taux d'engagement d'un média, et le détail des compteurs.

    Sans portée disponible, on retombe sur le total brut likes + commentaires
    (l'ancien signal) plutôt que de fausser la moyenne avec un zéro.
    """
    likes    = m.get("like_count", 0) or 0
    comments = m.get("comments_count", 0) or 0
    ins      = m.get("_insights", {})
    reach    = ins.get("reach", 0) or 0
    saved    = ins.get("saved", 0) or 0
    shares   = ins.get("shares", 0) or 0

    interactions = (W_LIKE * likes + W_COMMENT * comments
                    + W_SAVED * saved + W_SHARE * shares)
    detail = {"likes": likes, "comments": comments, "reach": reach,
              "saved": saved, "shares": shares}

    if reach <= 0:
        return float(likes + comments), detail
    return interactions / reach, detail


def _best_slots(media: list[dict]) -> dict:
    """
    Heures et jours de publication qui maximisent la PORTÉE, en heure de Paris.

    L'heure joue sur la diffusion du post, pas sur son taux d'engagement (qui
    dépend du contenu) : on compare donc la portée. Chaque portée est rapportée
    à la médiane de ses voisines chronologiques, pour neutraliser la croissance
    du compte, puis la moyenne par créneau est tirée vers 1.0 (SLOT_PRIOR posts
    fictifs) : un créneau à deux posts chanceux ne passe pas devant un créneau
    régulier. Les posts de moins de 3 jours, dont la portée grimpe encore, sont
    ignorés.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    rows = sorted(
        (datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z"), m["_insights"]["reach"])
        for m in media
        if m.get("_insights", {}).get("reach") and m.get("timestamp")
    )
    rows = [(t.astimezone(PARIS), r) for t, r in rows if t < cutoff]

    by_hour: dict[int, list[float]] = defaultdict(list)
    by_day:  dict[int, list[float]] = defaultdict(list)
    for i, (t, reach) in enumerate(rows):
        neighbours = [r for _, r in rows[max(0, i - 5): i + 6]]
        # En log : un post viral (×20) ne doit pas écraser tout son créneau
        rel = math.log(reach / (statistics.median(neighbours) or 1))
        by_hour[t.hour].append(rel)
        by_day[t.weekday()].append(rel)

    def ranked(groups: dict[int, list[float]]) -> list[tuple[int, float, int]]:
        # Moyenne géométrique lissée vers 1.0 (log 0)
        scored = [(k, math.exp(sum(v) / (len(v) + SLOT_PRIOR)), len(v))
                  for k, v in groups.items() if len(v) >= MIN_SAMPLE]
        return sorted(scored, key=lambda s: -s[1])

    days = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
    return {
        "hours": [{"heure": h, "portee_rel": round(s, 2), "n": n}
                  for h, s, n in ranked(by_hour)[:6]],
        "days":  [{"jour": days[d], "portee_rel": round(s, 2), "n": n}
                  for d, s, n in ranked(by_day)],
    }


def _load_quotes() -> list[tuple[str, str]]:
    """Retourne [(citation_normalisée[:60], mood), ...] depuis la base."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT quote, mood FROM quotes").fetchall()
    conn.close()
    return [(_norm(r["quote"])[:60], r["mood"]) for r in rows]


def compute(write: bool = True) -> dict:
    """Calcule les poids par mood et (optionnellement) les écrit sur disque."""
    media  = _fetch_media()
    quotes = _load_quotes()
    tok    = os.getenv("INSTAGRAM_ACCESS_TOKEN")

    # Insights sur les publications récentes uniquement (1 appel par média)
    print(f"  Récupération des insights ({min(len(media), INSIGHTS_LIMIT)} médias)…")
    for m in media[:INSIGHTS_LIMIT]:
        m["_insights"] = _fetch_insights(m["id"], tok)
    with_reach = sum(1 for m in media if m.get("_insights", {}).get("reach"))

    by_mood_eng: dict[str, list[float]] = defaultdict(list)
    totals  = defaultdict(int)
    matched = 0

    for m in media:
        eng, detail = _engagement(m)
        for k, v in detail.items():
            totals[k] += v

        cap = _norm(m.get("caption", ""))
        for qn, mood in quotes:
            if len(qn) > 15 and qn in cap:
                by_mood_eng[mood].append(eng)
                matched += 1
                break

    if matched == 0:
        raise RuntimeError("Aucun post relié à une citation — impossible de calculer les poids.")

    all_eng     = [e for es in by_mood_eng.values() for e in es]
    global_mean = statistics.mean(all_eng) or 1.0

    mood_engagement, weights = {}, {}
    for mood, es in by_mood_eng.items():
        mean = round(statistics.mean(es), 4)
        mood_engagement[mood] = {"n": len(es), "eng_moy": mean}
        if len(es) >= MIN_SAMPLE:
            w = mean / global_mean
            weights[mood] = round(min(WEIGHT_CAP, max(WEIGHT_FLOOR, w)), 3)
        else:
            weights[mood] = 1.0  # échantillon trop faible → neutre

    slots = _best_slots(media)

    result = {
        "n_posts":         len(media),
        "n_matched":       matched,
        "n_avec_portee":   with_reach,
        "signal":          "taux/portée" if with_reach else "likes+commentaires",
        "global_eng_moy":  round(global_mean, 4),
        "totaux":          dict(totals),
        "mood_engagement": mood_engagement,
        "weights":         weights,
        "best_hours_paris": slots["hours"],
        "best_days_paris":  slots["days"],
    }

    _print_report(result)

    if write:
        os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
        with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Poids écrits → {WEIGHTS_PATH}")

    return result


def _print_report(r: dict):
    print(f"\n📊 QuotesAI Analytics — {r['n_matched']}/{r['n_posts']} posts reliés à un mood")
    print(f"   Signal : {r['signal']} ({r.get('n_avec_portee', 0)} posts avec portée)")
    t = r.get("totaux", {})
    if t.get("reach"):
        print(f"   Cumul  : {t['reach']} portée · {t['likes']} likes · "
              f"{t['comments']} commentaires · {t['saved']} enregistrements · "
              f"{t['shares']} partages")
    print(f"   Engagement moyen global : {r['global_eng_moy']}\n")
    print(f"   {'mood':16} {'n':>4} {'eng_moy':>10} {'poids':>7}")
    for mood, w in sorted(r["weights"].items(), key=lambda x: -x[1]):
        st = r["mood_engagement"].get(mood, {})
        print(f"   {mood:16} {st.get('n', 0):>4} {st.get('eng_moy', 0):>10} {w:>7}")
    print("\n   Meilleurs créneaux (heure de Paris, portée relative ; 1.0 = médiane) :")
    print("   " + " · ".join(f"{s['heure']}h {s['portee_rel']} (n={s['n']})"
                             for s in r["best_hours_paris"]))
    print("   " + " · ".join(f"{s['jour']} {s['portee_rel']} (n={s['n']})"
                             for s in r["best_days_paris"]))


if __name__ == "__main__":
    compute(write="--report" not in sys.argv)
