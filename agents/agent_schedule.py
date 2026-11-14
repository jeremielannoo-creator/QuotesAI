"""
agents/agent_schedule.py — Créneaux de publication en heure de Paris.

Problème : les crons GitHub Actions sont en UTC. Calés sur l'heure d'été, tous
les créneaux glissent d'une heure le dernier dimanche d'octobre (08h Paris
devient 07h) et reviennent fin mars.

Solution : chaque créneau Paris reçoit DEUX crons (son heure UTC d'été et son
heure UTC d'hiver) et ce module sert de portier. Il regarde l'heure PRÉVUE du
cron déclencheur (github.event.schedule), pas l'heure réelle d'exécution —
GitHub démarre souvent les crons 15 à 60 min en retard — et ne laisse passer
que celui qui tombe pile sur un créneau Paris ce jour-là.

Les créneaux sont définis ici, une seule fois. Les heures retenues viennent
du rapport de agents/agent_analytics.py (« Meilleurs créneaux »).

Usage :
    python -m agents.agent_schedule gate reels "0 6 * * 1"   # portier (workflow)
    python -m agents.agent_schedule crons reels              # lignes cron à coller

Bibliothèque standard uniquement : le portier tourne avant `pip install`.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Créneaux par workflow, en heure de Paris (jour, "HH:MM").
SLOTS: dict[str, list[tuple[str, str]]] = {
    "reels": [            # .github/workflows/daily_post.yml
        ("mon", "08:00"),
        ("tue", "19:00"),
        ("sat", "16:00"),
        ("sat", "21:00"),
        ("sun", "23:00"),
    ],
    "book": [             # .github/workflows/book_post.yml
        ("wed", "19:00"),
        ("sun", "10:30"),
    ],
    "lifestyle": [        # .github/workflows/lifestyle_post.yml
        ("thu", "15:00"),
        ("fri", "19:00"),
    ],
}


def scheduled_at(cron: str, now: datetime) -> datetime:
    """
    Instant UTC prévu du cron « M H * * J » le plus récent avant `now`.
    Seule cette forme est gérée : c'est celle que produit crons().
    """
    minute, hour, _, _, dow = cron.split()
    py_dow = (int(dow) - 1) % 7                  # cron : 0 = dimanche
    t = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
    while t.weekday() != py_dow or t > now:
        t -= timedelta(days=1)
    return t


def is_slot(workflow: str, cron: str, now: datetime | None = None) -> bool:
    """True si le cron tombe sur un créneau Paris du workflow, à sa date prévue."""
    now   = now or datetime.now(timezone.utc)
    local = scheduled_at(cron, now).astimezone(PARIS)
    return (_DAYS[local.weekday()], local.strftime("%H:%M")) in SLOTS[workflow]


def crons(workflow: str) -> list[str]:
    """Lignes cron UTC (été + hiver) couvrant les créneaux Paris du workflow."""
    lines = []
    for day, hhmm in SLOTS[workflow]:
        for ref, season in ((datetime(2026, 7, 6), "été"), (datetime(2026, 1, 5), "hiver")):
            local = (ref + timedelta(days=_DAYS.index(day))).replace(
                hour=int(hhmm[:2]), minute=int(hhmm[3:]), tzinfo=PARIS)
            utc = local.astimezone(timezone.utc)
            cron = f"{utc.minute} {utc.hour} * * {(utc.weekday() + 1) % 7}"
            lines.append(f"    - cron: '{cron}'   # {day} {hhmm} Paris ({season})")
    return lines


def _gate(workflow: str, cron: str) -> None:
    # Déclenchement manuel (workflow_dispatch) : pas de cron, on publie.
    go = not cron or is_slot(workflow, cron)
    print(f"[agent_schedule] {workflow} — cron '{cron or 'manuel'}' → "
          f"{'publication' if go else 'hors créneau Paris, rien à faire'}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"go={'true' if go else 'false'}\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    cmd, wf = sys.argv[1], sys.argv[2]
    if cmd == "gate":
        _gate(wf, sys.argv[3] if len(sys.argv) > 3 else "")
    elif cmd == "crons":
        print("\n".join(crons(wf)))
