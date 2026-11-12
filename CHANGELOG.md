# Historique des versions de Studio Dock

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; numéros : [versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

## [0.4.2] — 2026-11-12

### Modifié

- Réglages séparés en deux onglets : « Mon espace » (ce poste uniquement : lien du catalogue, dossier
  d'installation) et « Préparer pour l'équipe » (le catalogue publié pour tous). Chaque onglet rappelle la portée
  de ce qu'on y modifie.
- Le dossier partagé Windows est désactivé pour l'instant : l'équipe n'a pas d'emplacement réseau commun et
  utilise le catalogue en ligne. Un dossier réglé auparavant reste retirable.
- L'en-tête reste visible au défilement.

## [0.4.1] — 2026-11-09

### Corrigé

- Catalogue en ligne : une app pouvait être installée à partir d'un fichier encore en cours d'écriture (copie par
  l'Explorateur, qui garde la date d'origine), d'où « Could not load PyInstaller's embedded PKG archive » au
  lancement. Studio Dock attend désormais que plus aucun programme n'écrive dans le fichier, vérifie que la copie est
  complète, et contrôle la taille et l'empreinte (SHA-256) du fichier publié, ajoutées au catalogue par « Fabriquer
  le catalogue ». Un fichier incomplet ou différent est signalé sur la carte et n'est pas installé.

## [0.4.0] — 2026-11-09

### Ajouté

- Catalogue en ligne, pour une équipe dont le dossier n'existe qu'en ligne (SharePoint, Teams) : le navigateur
  télécharge, Studio Dock installe. Le catalogue (`studio-dock-catalogue.zip`) est importé dès qu'il arrive dans
  Téléchargements ; « Installer » et les mises à jour ouvrent le dossier en ligne de l'app, puis Studio Dock copie
  l'exe téléchargé dans le dossier d'installation et le retire des Téléchargements. « Vérifier les mises à jour »,
  mise à jour de Studio Dock lui-même par le même chemin.
- Écran « Préparer le catalogue » (Réglages) : versions lues dans une copie locale du dossier, liens des dossiers en
  ligne, fabrication de `studio-dock-catalogue.zip`.
- Premier lancement : un exe déjà posé dans un dossier de ce poste (hors Téléchargements et dossier partagé) y reste,
  sans copie ni redémarrage.

## [0.3.1] — 2026-11-09

### Corrigé

- Windows : Studio Dock pouvait planter en redémarrant juste après son installation (ou après une mise à jour),
  avec « No module named '_multiprocessing' » : la nouvelle copie réutilisait le dossier temporaire de l'ancienne,
  effacé à sa fermeture. Les programmes lancés par Studio Dock (lui-même, les apps) démarrent désormais avec un
  environnement propre.

### Modifié

- Bouton Réglages de l'en-tête : icône en roue crantée.

## [0.3.0] — 2026-11-08

### Modifié


- Refonte visuelle de l'accueil : cartes plus compactes (4 par ligne), phrase d'accroche sur deux lignes, état en
  langage courant (Ouverte, Prête, Mise à jour disponible, À installer), une seule action principale et un bouton de
  mise à jour à côté. L'app ouverte est encadrée. Pastilles de résumé en haut de page. Fiche, dossier et retrait
  dans le menu ⋮ de chaque carte.
- Fiche d'une app : bandeau avec pastille d'état, fonctionnalités en blocs, encart « En bref » en langage simple,
  détails techniques (adresse, emplacement, journaux) repliés.
- Logo de l'en-tête contouré pour rester visible sur fond blanc.

## [0.2.0] — 2026-11-07

### Ajouté

- Windows : dossier d'installation choisi par chaque membre, distinct du dossier partagé. Au premier lancement, Studio
  Dock demande où s'installer, s'y copie, ajoute un raccourci au menu Démarrer et redémarre depuis ce dossier ; les apps
  y sont installées dans `apps\<id>\`. Ouvert depuis le partage, il retient le dossier partagé. Réglages : « Changer de
  dossier » déplace Studio Dock et les apps. Dossier réseau ou dans le partage refusé. `install_folder` dans
  `studiodock.config.json` propose un dossier par défaut.
- Nouvelles icônes de la suite : Studio Dock (exe Windows, app Mac, en-tête, onglet) et icônes des apps du
  catalogue (SpecGen sarcelle, AuditErgo vert, DocAnalyser violet, Mapline bleu), en tuiles pleines (`style: logo`).
  Script `scripts/fabriquer_icones.py` pour régénérer les `.ico` et `.icns`.
- Fenêtre Windows Studio Dock (pywebview) : accueil « Mes applications » et fiche de chaque app avec sa prise en main.
- Apps web (contrat commun : `--port`, `--no-browser`, `/health`) : Lancer, Ouvrir, Arrêter ; arrêt de toutes les apps
  lancées à la fermeture de Studio Dock, même en cas de plantage.
- Apps natives (ex. Mapline) : détection de l'installation Windows, lancement, mise au premier plan.
- Liste des apps dans `apps.json` à côté de l'exe (créé au premier lancement) ; exe rangés dans `apps\<id>\`,
  plusieurs versions côte à côte acceptées (la plus récente est lancée).
- Messages : app introuvable (avec le dossier où déposer l'exe), port occupé, arrêt inattendu avec la fin du journal.
- Design system Night Navy, mode clair et sombre.
- Catalogue d'équipe : `catalogue.json` dans un dossier partagé réglé dans Studio Dock (écran Réglages, ou
  `studiodock.config.json` livré à côté de l'exe). Les apps sont copiées depuis le sous-dossier de chaque projet vers
  `apps\<id>\` sur le poste, jamais lancées depuis le partage ; installation, mise à jour (arrêt de l'app si lancée)
  et retrait ; apps `auto` installées et mises à jour d'office, `optionnel` dans « Disponibles pour vous » avec le badge
  « Nouveau », `masque` cachées ; copie locale du catalogue quand le partage est inaccessible.
- Mise à jour de Studio Dock depuis le sous-dossier `StudioDock\` du partage : remplacement de l'exe et redémarrage
  (Windows) ; sur Mac, ouverture du dossier.
- Version Mac : « Studio Dock.app » pour Mac Intel et Mac à puce Apple (macOS 12 et plus), dossier dans
  `~/Library/Application Support/StudioDock` ; applications Mac retrouvées dans Applications.

### Corrigé

- Exe Windows : lecture de la version d'un exe sans numéro dans son nom (la liste des apps renvoyait une erreur dès
  qu'un tel exe était dans le dossier partagé).
