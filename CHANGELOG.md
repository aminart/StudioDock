# Historique des versions de Studio Dock

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; numéros : [versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté

- Fenêtre Windows Studio Dock (pywebview) : accueil « Mes applications » et fiche de chaque app avec sa prise en main.
- Apps web (contrat commun : `--port`, `--no-browser`, `/health`) : Lancer, Ouvrir, Arrêter ; arrêt de toutes les apps
  lancées à la fermeture de Studio Dock, même en cas de plantage.
- Apps natives (ex. Mapline) : détection de l'installation Windows, lancement, mise au premier plan.
- Liste des apps dans `apps.json` à côté de l'exe (créé au premier lancement) ; exe rangés dans `apps\<id>\`,
  plusieurs versions côte à côte acceptées (la plus récente est lancée).
- Messages : app introuvable (avec le dossier où déposer l'exe), port occupé, arrêt inattendu avec la fin du journal.
- Design system Night Navy, mode clair et sombre.
