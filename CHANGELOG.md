# Historique des versions de Studio Dock

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; numéros : [versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

## [0.6.2] — 2026-11-21

### Modifié

- Cases à cocher et boutons radio aux couleurs de Night Navy, en clair comme en sombre : contour gris foncé,
  coché en bleu marine (coche blanche, point central pour les radios), survol en bleu, anneau de focus du design
  system au clavier. Ils remplacent les contrôles par défaut de Windows, partout dans Studio Dock (Mon espace,
  tutoriel, Modèles d'IA, fiches du catalogue).

## [0.6.1] — 2026-11-20

### Modifié

- Réglages › Mon espace en deux parties : « 1 · Mes applications » (votre dossier sur ce poste, avec le dossier
  de chaque app) et « 2 · Les applications de l'équipe », avec le choix dossier réseau Windows (par défaut) ou
  dossier en ligne ; la source utilisée est signalée, et choisir le dossier en ligne retire le dossier réseau.
- L'onglet « Préparer pour l'équipe » n'apparaît que pour la personne qui tient le catalogue : case « Je gère le
  catalogue de l'équipe » dans Réglages › Mon espace (cochée d'office si un dossier de préparation a déjà servi).
  Les autres membres ne voient que Mon espace et Modèles d'IA.
- Le lien « Dossier d'installation » quitte le pied de page : votre dossier se présente et s'ouvre dans
  Réglages › Mon espace › Mes applications.
- Mise à jour d'une app : un seul bouton « Mettre à jour · 1.4.0 », en couleur d'accent, sous les boutons de la
  carte et à côté de « Lancer » sur la fiche (fini le bouton « ↻ 1.4.0 » sans verbe et le bandeau jaune). La ligne
  d'état garde l'état de l'app (« Prête », « Ouverte ») au lieu d'afficher « Mise à jour disponible ».
- Le bouton ■ des cartes porte son libellé « Arrêter ».
- « Journaux » devient « Signaler un problème » : le dossier des journaux s'ouvre et Studio Dock dit quels
  fichiers envoyer (studiodock.log et celui de l'app).
- Mots plus courants : « s'ouvre dans le navigateur » et « application Windows » au lieu de « app web » et
  « app de bureau », « Pas encore publiée » au lieu de « Indisponible », « Installée à votre demande »,
  « Version 1.3.0 (1.4.0 disponible) ». Les chemins longs sont abrégés à leurs deux derniers dossiers
  (chemin complet au survol).
- Fiches par défaut : l'étape « Vérifiez la connexion au modèle » de SpecGen, AuditErgo et DocAnalyser renvoie à
  Réglages › Modèles d'IA de Studio Dock. « En bref » indique le modèle utilisé par l'app, avec un lien
  « Changer ».
- Le bouton « Réglages » de l'en-tête montre qu'on est dans les réglages.
- « Ouvrir » et « Afficher » prennent le même style que « Lancer » : un seul bouton principal par carte.
- Accueil : les pastilles de résumé passent sous le titre ; « 1 mise à jour : SpecGen » mène à la carte et à son
  bouton « Mettre à jour ». Les apps de l'équipe sans version publiée ne prennent plus une carte : une ligne
  « Bientôt dans l'équipe : Mapline » les regroupe.
- Modèles d'IA : sections numérotées dans l'ordre où on les règle (1 · Services d'IA, 2 · Ollama, 3 · Modèle
  utilisé par les apps) ; le choix des modèles n'apparaît qu'une fois un service ou Ollama réglé.
- Préparer pour l'équipe : avec le dossier réseau, l'étape « Catalogue en ligne » est repliée derrière
  « Publier aussi un catalogue en ligne… » ; elle reste ouverte pour un catalogue en ligne.
- Mon espace : les liens vers la visite et le tutoriel sont regroupés dans un bloc « Aide » en bas de page, et la
  case « Je gère le catalogue de l'équipe » est présentée comme option avancée.
- Les exemples de saisie (chemins, liens) sont écrits sous les champs, et le texte indicatif des champs passe
  au contraste AA.

### Corrigé

- Une app web occupée (longue génération, gros document) était arrêtée par Studio Dock avec « … ne répond pas
  après 120 secondes » : le délai de 120 s, prévu pour le démarrage, s'appliquait aussi après, dès qu'un contrôle
  de /health tardait. Une app démarrée n'est plus jamais arrêtée parce qu'elle tarde à répondre : sa carte
  indique « Ouverte · occupée ». Le contrôle attend aussi plus longtemps (2 s au lieu de 0,6 s).

### Ajouté

- Fermer Studio Dock alors que des apps web sont ouvertes demande d'abord : « Réduire Studio Dock » (proposé
  d'office, les apps continuent) ou « Tout fermer ». Sans app ouverte, la fenêtre se ferme comme avant.
- Tutoriel en cinq étapes : le dossier de vos applications est rappelé dans « Bienvenue ». Le formulaire de
  connexion à l'IA y est réduit à l'adresse, la clé, le certificat de l'entreprise (.crt) et les modèles ; nom et
  fenêtre de contexte sont dans « Plus d'options ». Sans nom, le service prend celui de son serveur.
- Confirmation avant d'arrêter une app, de la mettre à jour pendant qu'elle est ouverte, ou de la retirer de ce
  poste. Pour le retrait, la boîte dit ce qui part (le programme) et ce qui reste (documents, historique,
  réglages).
- Menu ⋮ des cartes au clavier : focus sur le premier choix à l'ouverture, flèches haut et bas, Début, Fin,
  Échap rend le focus au bouton.
- Tutoriel de première connexion, qui fait toute la configuration : ce qu'est Studio Dock, où sont vos
  applications (votre dossier), où sont celles de l'équipe (dossier réseau Windows, dossier en ligne ou plus tard),
  la connexion aux modèles d'IA (service de l'entreprise avec test, ou modèles Ollama du poste), les premières
  apps à installer (cochées, installées à la fin du tutoriel), et comment se servir des cartes. Il s'affiche tant qu'aucune app n'est installée et qu'il n'a pas été vu ; il se
  revoit depuis le pied de page (« Revoir le tutoriel ») ou Réglages › Mon espace.
- Visite guidée de l'accueil, sans rien régler : un projecteur passe sur les vrais éléments (carte d'une app, sa
  fiche, ses boutons, le menu ⋮, les apps disponibles, Réglages, le pied de page) avec une bulle d'explication ;
  les éléments absents sont sautés ; clavier ← → et Échap. Elle se relance à tout moment (« Visite guidée » en
  bas de page, Réglages › Mon espace) et se propose à la fin du tutoriel, qui reste celui de la première connexion.
- Journal de session (logs\studiodock.log) : démarrages et arrêts de Studio Dock, lancement de chaque app, arrêt
  imprévu d'une app avec la fin de son journal, erreurs non rattrapées ; plantages brutaux dans plantages.log.
  Le journal d'une app est gardé au lancement suivant (<app>.precedent.log).

## [0.6.0] — 2026-11-19

### Ajouté

- Préparer pour l'équipe › Applications : le catalogue de l'équipe s'édite par formulaire, sans écrire de JSON.
  « Créer le catalogue » le crée avec les apps de la suite (fiches, icônes, un sous-dossier par app) ; chaque app
  se modifie (nom, type, IA, mode pour l'équipe, icône importée, accroche, description, points forts, prise en
  main, liens), s'ajoute, se déplace ou se retire. Identifiant, programme, sous-dossier et port libre sont déduits
  du nom. Chaque enregistrement est validé avant d'écrire catalogue.json (copie de la version précédente en
  catalogue.json.bak). Fonctionne pour le dossier partagé Windows (changements visibles tout de suite) comme
  pour la copie locale du catalogue en ligne.

### Modifié

- Le dossier partagé Windows de l'équipe (lecteur réseau, par exemple Q:) se règle à nouveau dans Réglages ›
  Mon espace. Quand il est réglé, il passe avant le catalogue en ligne.

## [0.5.0] — 2026-11-17

### Ajouté

- Réglages › Modèles d'IA : connexions aux modèles réglées une fois et reprises par toutes les apps de la suite
  (SpecGen, AuditErgo, DocAnalyser). Même modèle que DocAnalyser : services compatibles OpenAI avec clé chiffrée,
  certificat de l'entreprise, modèles et test de connexion. Modèles locaux avec Ollama : détection, modèles
  installés, téléchargement d'un modèle, choix des modèles proposés. Modèle par défaut, modèle propre à une app,
  ou configuration propre à l'app. Les apps lisent ces réglages avec `contrat/studiodock_ia.py`.

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
