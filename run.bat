@echo off
call venv\Scripts\activate.bat

echo Que souhaitez-vous faire ?
echo  1. Lancer le pipeline maintenant (Instagram + TikTok)
echo  2. Lancer le pipeline maintenant (Instagram seulement)
echo  3. Lancer le pipeline maintenant (TikTok seulement)
echo  4. Dry-run (générer la vidéo sans publier)
echo  5. Ajouter des créneaux de publication automatique
echo  6. Voir les tâches planifiées
echo  7. Lancer le planificateur automatique
echo  8. Quitter

set /p choice="Votre choix (1-8) : "

if "%choice%"=="1" python pipeline.py --platform both
if "%choice%"=="2" python pipeline.py --platform instagram
if "%choice%"=="3" python pipeline.py --platform tiktok
if "%choice%"=="4" python pipeline.py --dry-run
if "%choice%"=="5" (
    set /p times="Heures (ex: 09:00 18:00) : "
    python scheduler.py add --time %times% --platform both
)
if "%choice%"=="6" python scheduler.py list
if "%choice%"=="7" python scheduler.py start
if "%choice%"=="8" exit

pause
