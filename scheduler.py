"""
scheduler.py — Planification des publications QuotesAI
Permet de programmer des publications automatiques à des heures précises.

Usage :
    # Ajouter une tâche quotidienne à 9h et 18h
    python scheduler.py add --time 09:00 --time 18:00 --platform both

    # Afficher les tâches planifiées
    python scheduler.py list

    # Supprimer une tâche
    python scheduler.py remove --id <job_id>

    # Lancer le planificateur (tourne en continu)
    python scheduler.py start
"""
import argparse
import json
import os
import sys
from datetime import datetime
from rich.console import Console
from rich.table   import Table
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron      import CronTrigger

from pipeline import run as run_pipeline

console = Console()

JOBS_FILE = os.path.join(os.path.dirname(__file__), "scheduled_jobs.json")


# ── Gestion des tâches ────────────────────────────────────────────────────────

def load_jobs() -> list[dict]:
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_jobs(jobs: list[dict]):
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


def add_job(times: list[str], platform: str):
    """
    Ajoute des créneaux horaires de publication.
    times : liste de chaînes "HH:MM"
    """
    jobs  = load_jobs()
    added = []

    for t in times:
        try:
            h, m = t.split(":")
            job  = {
                "id":       f"job_{len(jobs) + len(added) + 1}",
                "hour":     int(h),
                "minute":   int(m),
                "platform": platform,
                "created":  datetime.now().isoformat(),
                "active":   True,
            }
            jobs.append(job)
            added.append(job)
        except ValueError:
            console.print(f"[red]Format invalide : '{t}' (attendu HH:MM)[/red]")

    save_jobs(jobs)
    for j in added:
        console.print(
            f"  ✓ Tâche ajoutée : [cyan]{j['id']}[/cyan] — "
            f"{j['hour']:02d}:{j['minute']:02d} sur {j['platform']}"
        )


def remove_job(job_id: str):
    jobs = [j for j in load_jobs() if j["id"] != job_id]
    save_jobs(jobs)
    console.print(f"  ✓ Tâche supprimée : {job_id}")


def list_jobs():
    jobs = load_jobs()
    if not jobs:
        console.print("[yellow]Aucune tâche planifiée.[/yellow]")
        return

    t = Table(title="Tâches planifiées", border_style="cyan")
    t.add_column("ID",        style="cyan")
    t.add_column("Heure",     style="bold white")
    t.add_column("Plateforme")
    t.add_column("Actif")
    t.add_column("Créé le")

    for j in jobs:
        t.add_row(
            j["id"],
            f"{j['hour']:02d}:{j['minute']:02d}",
            j["platform"],
            "✓" if j.get("active", True) else "✗",
            j.get("created", "—")[:16],
        )

    console.print(t)


# ── Planificateur APScheduler ─────────────────────────────────────────────────

def start_scheduler():
    """Lance le planificateur en mode bloquant (tourne jusqu'à Ctrl+C)."""
    jobs = load_jobs()
    if not jobs:
        console.print("[yellow]Aucune tâche à planifier. Utilisez 'add' d'abord.[/yellow]")
        sys.exit(0)

    scheduler = BlockingScheduler(timezone="Europe/Paris")

    for job in jobs:
        if not job.get("active", True):
            continue

        scheduler.add_job(
            func     = _run_job,
            trigger  = CronTrigger(
                hour   = job["hour"],
                minute = job["minute"],
                timezone="Europe/Paris",
            ),
            kwargs   = {"platform": job["platform"]},
            id       = job["id"],
            name     = f"{job['hour']:02d}:{job['minute']:02d} — {job['platform']}",
            misfire_grace_time=300,   # tolérance 5 min si le PC était en veille
        )

    console.print(Panel.fit(
        f"[bold green]Planificateur démarré[/bold green]\n"
        f"{len(scheduler.get_jobs())} tâche(s) chargée(s)\n"
        "Appuyez sur [bold]Ctrl+C[/bold] pour arrêter.",
        border_style="green",
    ))

    list_jobs()

    try:
        scheduler.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Planificateur arrêté.[/yellow]")
        scheduler.shutdown()


def _run_job(platform: str):
    """Callback exécuté par APScheduler à chaque déclenchement."""
    console.print(
        f"\n[bold cyan]⏰ Déclenchement automatique[/bold cyan] — "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')} — {platform}"
    )
    try:
        run_pipeline(platform=platform)
    except Exception as e:
        console.print(f"[red]Erreur dans la tâche planifiée : {e}[/red]")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QuotesAI Scheduler")
    sub    = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Ajouter des créneaux de publication")
    p_add.add_argument(
        "--time", action="append", required=True, dest="times",
        metavar="HH:MM", help="Heure de publication (répétable)",
    )
    p_add.add_argument(
        "--platform", choices=["instagram", "tiktok", "both"],
        default="both",
    )

    # list
    sub.add_parser("list", help="Afficher les tâches planifiées")

    # remove
    p_rm = sub.add_parser("remove", help="Supprimer une tâche")
    p_rm.add_argument("--id", required=True, dest="job_id")

    # start
    sub.add_parser("start", help="Lancer le planificateur")

    args = parser.parse_args()

    if args.command == "add":
        add_job(args.times, args.platform)
    elif args.command == "list":
        list_jobs()
    elif args.command == "remove":
        remove_job(args.job_id)
    elif args.command == "start":
        start_scheduler()


if __name__ == "__main__":
    main()
