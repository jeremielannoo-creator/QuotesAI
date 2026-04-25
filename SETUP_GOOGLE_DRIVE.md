# Connexion Google Drive — via Google Apps Script (gratuit)

Aucun Google Cloud. Aucune clé API. Aucun compte de facturation.
Le script tourne dans ton compte Google, accessible via une URL HTTPS.

---

## Étape 1 — Créer le script Apps Script (5 min)

1. Va sur **https://script.google.com/home**
2. Clique **"Nouveau projet"**
3. Renomme le projet : `QuotesAI Drive Reader`
4. Dans l'éditeur, **remplace tout le contenu** par le script ci-dessous
5. Clique **Enregistrer** (icône disquette)

```javascript
/**
 * QuotesAI — Drive Reader & Video Uploader
 *
 * GET  ?slot=B1&date=2026-04-23          →  retourne le contenu de l'article
 * POST {fileId: "..."}                   →  archive l'article dans Publiés/
 * POST {action:"video", video_url, ...}  →  sauvegarde vidéo + rappel Calendar
 */

var FOLDER_NAME    = "Littérature";
var PUBLISHED_NAME = "Publiés";

// ── GET : lecture article ─────────────────────────────────────────────────────

function doGet(e) {
  try {
    var slot = e.parameter.slot;
    var date = e.parameter.date;
    if (!slot) return err("Paramètre 'slot' manquant");

    var folder = findFolder(FOLDER_NAME);
    if (!folder) return err('Dossier "' + FOLDER_NAME + '" introuvable dans Drive');

    var file = null;

    // 1. Si une date est fournie, chercher d'abord le fichier exact AAAA-MM-JJ-slot
    if (date) {
      var exact = folder.searchFiles('title contains "' + date + '-' + slot + '" and trashed = false');
      if (exact.hasNext()) file = exact.next();
    }

    // 2. Fallback : premier fichier dont le nom contient '-slot' (tri alphabétique = FIFO)
    if (!file) {
      var any = folder.searchFiles('title contains "-' + slot + '" and trashed = false');
      if (any.hasNext()) file = any.next();
    }

    if (!file) return err('Aucun fichier "-' + slot + '" trouvé dans ' + FOLDER_NAME);

    var content;
    if (file.getMimeType() === 'application/vnd.google-apps.document') {
      var token    = ScriptApp.getOAuthToken();
      var response = UrlFetchApp.fetch(
        'https://www.googleapis.com/drive/v3/files/' + file.getId() + '/export?mimeType=text/plain',
        { headers: { 'Authorization': 'Bearer ' + token } }
      );
      content = response.getContentText('UTF-8');
    } else {
      content = file.getBlob().getDataAsString('UTF-8');
    }

    return json({ name: file.getName(), id: file.getId(), content: content });

  } catch (e) { return err(e.toString()); }
}

// ── POST : archive article OU sauvegarde vidéo ────────────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // Sauvegarde vidéo + rappel Calendar
    if (data.action === "video") {
      return handleVideoUpload(data);
    }

    // Archive article dans Publiés/
    var fileId = data.fileId;
    if (!fileId) return err("fileId manquant");

    var file      = DriveApp.getFileById(fileId);
    var published = findOrCreateFolder(PUBLISHED_NAME);
    var parents   = file.getParents();

    if (parents.hasNext()) parents.next().removeFile(file);
    published.addFile(file);

    return json({ status: "archived", name: file.getName() });

  } catch (e) { return err(e.toString()); }
}

// ── Sauvegarde vidéo + rappel Calendar ───────────────────────────────────────

function handleVideoUpload(data) {
  var videoUrl = data.video_url;
  var filename = data.filename || ("quote_" + new Date().toISOString().slice(0, 10) + ".mp4");
  var caption  = data.caption  || "";

  // 1. Télécharger depuis Cloudinary
  var response = UrlFetchApp.fetch(videoUrl, { muteHttpExceptions: true });
  if (response.getResponseCode() !== 200) {
    return err("Téléchargement vidéo échoué : HTTP " + response.getResponseCode());
  }
  var blob = response.getBlob().setName(filename);

  // 2. Déposer dans AI/Quotes AI/Video/
  var folder = findOrCreatePath(["AI", "Quotes AI", "Video"]);
  var file   = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  var driveUrl = "https://drive.google.com/uc?export=download&id=" + file.getId();

  // 3. Créer événement Calendar dans 10 min, notification 5 min avant
  var now       = new Date();
  var startTime = new Date(now.getTime() + 10 * 60 * 1000);
  var endTime   = new Date(startTime.getTime() + 15 * 60 * 1000);

  var description = "📥 Télécharger la vidéo :\n" + driveUrl
                  + "\n\n📝 Caption prête à coller :\n" + caption;

  var cal   = CalendarApp.getDefaultCalendar();
  var event = cal.createEvent("📱 Poster sur TikTok", startTime, endTime, {
    description: description,
  });
  event.addPopupReminder(5);  // notification 5 min avant l'événement

  return json({ status: "ok", drive_url: driveUrl, event_id: event.getId() });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function findFolder(name) {
  var folders = DriveApp.getFoldersByName(name);
  return folders.hasNext() ? folders.next() : null;
}

function findOrCreateFolder(name) {
  var folder = findFolder(name);
  if (folder) return folder;
  var lit    = findFolder(FOLDER_NAME);
  var parent = lit ? lit.getParents().next() : DriveApp.getRootFolder();
  return parent.createFolder(name);
}

function findOrCreatePath(names) {
  var folder = DriveApp.getRootFolder();
  for (var i = 0; i < names.length; i++) {
    var subs = folder.getFoldersByName(names[i]);
    folder = subs.hasNext() ? subs.next() : folder.createFolder(names[i]);
  }
  return folder;
}

function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function err(msg) {
  return json({ error: msg });
}
```

---

## Étape 2 — Déployer comme Web App

1. Dans l'éditeur GAS : menu **"Déployer"** → **"Nouveau déploiement"**
2. Clique l'icône ⚙ à côté de "Sélectionnez un type" → **"Application Web"**
3. Paramètres :
   - Description : `v1`
   - Exécuter en tant que : **Moi**
   - Accès : **Tout le monde**
4. Clique **"Déployer"** → **Autoriser l'accès** (fenêtre Google)
5. **Copie l'URL** qui ressemble à :
   ```
   https://script.google.com/macros/s/AKfycb.../exec
   ```

---

## Étape 3 — Configurer le projet

Colle l'URL dans deux endroits :

**`.env`** (local) :
```
DRIVE_GAS_URL=https://script.google.com/macros/s/AKfycb.../exec
```

**GitHub → Settings → Secrets → Actions → New repository secret** :
- Nom : `DRIVE_GAS_URL`
- Valeur : l'URL du script

---

## Étape 4 — Créer la structure Drive

Dans **Mon Drive**, crée ces dossiers :
```
Mon Drive/
└── AI/
    └── The Journey of Ava/
        └── Littérature/      ← dépose tes articles ici
```
Le dossier `Publiés/` est créé automatiquement après la première publication.

---

## Convention de nommage des fichiers

| Fichier                 | Publié le                              |
|-------------------------|----------------------------------------|
| `2026-04-22-B1.md`      | Mercredi 22 avril à 19h00             |
| `2026-04-22-B2.md`      | Dimanche 26 avril à 10h30             |

→ Pour le dimanche : le nom utilise **la date du mercredi précédent**.

Format du contenu :
```
Titre du livre — Prénom Nom

Corps de la critique (texte libre, style Ava)...
```

---

## Format des fichiers acceptés

- Google Docs (`.gdoc`) — recommandé
- Texte brut (`.txt`)
- Markdown (`.md`)

---

## Test

Pour tester sans attendre mercredi/dimanche :

```bash
# Depuis GitHub Actions → Actions → "Pipeline Livre" → Run workflow
# Champ "drive_file" : entrer "2026-04-22-B1"

# Ou en local avec un fichier test :
python pipeline_book.py --drive-file 2026-04-22-B1 --dry-run
```

---

## Mise à jour du script (si changements)

Après modification du code GAS :
1. **"Déployer"** → **"Gérer les déploiements"**
2. Clique l'icône ✏️ → change la version → **"Déployer"**
L'URL reste la même.
