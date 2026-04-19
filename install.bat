@echo off
echo ============================================
echo  QuotesAI — Installation (Windows)
echo ============================================
echo.

REM Vérifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR : Python non trouvé. Installer depuis https://python.org
    pause
    exit /b 1
)
echo [OK] Python détecté

REM Vérifier FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ATTENTION : FFmpeg non trouvé dans le PATH.
    echo Télécharger depuis : https://www.gyan.dev/ffmpeg/builds/
    echo Choisir "ffmpeg-release-full.7z", extraire et ajouter le dossier bin au PATH.
    echo.
    echo Appuyez sur une touche pour continuer quand même...
    pause >nul
) else (
    echo [OK] FFmpeg détecté
)

REM Créer l'environnement virtuel
echo.
echo Création de l'environnement virtuel...
python -m venv venv
call venv\Scripts\activate.bat

REM Installer les dépendances
echo Installation des dépendances Python...
pip install --upgrade pip --quiet
pip install -r requirements.txt

REM Créer les dossiers nécessaires
echo.
echo Création des dossiers...
if not exist "assets\music"  mkdir "assets\music"
if not exist "assets\fonts"  mkdir "assets\fonts"
if not exist "output"        mkdir "output"
if not exist "temp"          mkdir "temp"

REM Copier le fichier .env
if not exist ".env" (
    copy ".env.example" ".env"
    echo.
    echo [IMPORTANT] Fichier .env créé. Ouvrez-le et remplissez vos clés API !
)

echo.
echo ============================================
echo  Installation terminée !
echo ============================================
echo.
echo Prochaines étapes :
echo  1. Editez le fichier .env avec vos clés API
echo  2. Placez des fichiers MP3 dans assets\music\
echo  3. (Optionnel) Téléchargez Montserrat depuis fonts.google.com
echo     et placez les .ttf dans assets\fonts\
echo  4. Lancez : run.bat
echo.
pause
