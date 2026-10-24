@echo off
REM ============================================================
REM QuotesAI - Lancement pipeline livres
REM Declenche par le Planificateur de taches Windows
REM 2x/semaine : mercredi 19h00 + dimanche 10h30
REM ============================================================

REM Encodage UTF-8 (sinon rich plante en cmd Windows par defaut)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
chcp 65001 >nul

cd /d "C:\Claude Agents\QuotesAI"

REM Creer le dossier logs si absent
if not exist "logs" mkdir logs

REM Activer le venv si present
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Lancer le pipeline (source Drive en priorite)
python pipeline_book.py >> logs\pipeline_book.log 2>&1

REM Code retour
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Pipeline termine avec le code %ERRORLEVEL% >> logs\pipeline_book.log
)
