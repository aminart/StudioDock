# Studio Dock

Fenêtre Windows qui lance les applications UX installées sur le poste (SpecGen, AuditErgo, DocAnalyser, Mapline…),
affiche leur état et les arrête quand on la ferme. Aucune app n'est écrite dans son code : la liste, les textes,
les icônes et les tutoriels viennent du fichier `apps.json`.

## Installation

1. Télécharger `StudioDock-X.Y.Z-windows.zip` depuis la dernière release (ou `StudioDock-X.Y.Z.exe` seul).
2. Le décompresser dans un dossier, par exemple `Documents\Studio Dock`.
3. Déposer l'exe de chaque app web dans `apps\<id>\` :

```
Studio Dock\
  StudioDock.exe
  apps.json                    créé au premier lancement
  apps\
    specgen\SpecGenerator-1.1.0.exe
    audit-ergo\AuditErgo-1.1.0.exe
    docanalyser\DocAnalyser-2.0.0.exe
  icons\                       (facultatif) icônes personnalisées
```

Un dossier par app : chaque app lit le `.env` posé à côté de son exe. Plusieurs versions peuvent cohabiter
(`SpecGenerator-1.1.0.exe`, `SpecGenerator-1.2.0.exe`) : la plus récente est lancée.
Les apps de bureau (Mapline) s'installent normalement : Studio Dock les retrouve dans « Applications installées ».

4. Double-cliquer sur `StudioDock.exe`.

La fenêtre utilise le moteur Edge WebView2, présent sur Windows 10 et 11. Les exe ne sont pas signés : au premier
lancement, Windows peut demander « Informations complémentaires » puis « Exécuter quand même ».

## Ce que fait Studio Dock

| | App web (SpecGen, AuditErgo, DocAnalyser) | App de bureau (Mapline) |
|---|---|---|
| Lancer | `<exe> --port N --no-browser`, prête quand `GET /health` répond | Lance l'exe |
| Une fois lancée | **Ouvrir** (navigateur) et **Arrêter** | **Afficher** (fenêtre au premier plan) |
| État | `/health` sur son port | Processus présent |
| À la fermeture de Studio Dock | Arrêtée, même si Studio Dock plante (groupe de processus Windows) | Continue |

Messages affichés sur la carte : exe introuvable (avec le dossier où le déposer), port pris par une autre application,
arrêt inattendu (fin du journal de l'app). Une app déjà lancée hors de Studio Dock est reconnue et peut être arrêtée.

Journaux : `%LOCALAPPDATA%\StudioDock\logs` (un fichier par app, plus `studiodock.log`).

## `apps.json`

Créé au premier lancement à partir de `resources/apps.default.json`. Un fichier invalide ne casse rien : la dernière
version valide reste affichée, avec l'erreur.

```json
{
  "apps": [
    {
      "id": "docanalyser",
      "name": "DocAnalyser",
      "kind": "web",
      "port": 8020,
      "ai": true,
      "exe": "DocAnalyser",
      "icon": { "file": "icons/docanalyser.svg", "style": "symbole" },
      "tagline": "Des documents aux insights.",
      "description": "Texte de la fiche…",
      "points": ["Point clé 1", "Point clé 2"],
      "tutorial": [{ "title": "Étape", "text": "Détail" }],
      "links": [{ "label": "Documentation", "url": "https://…" }]
    }
  ]
}
```

| Champ | Rôle |
|---|---|
| `id` | Identifiant ; pour une app web, celui que renvoie son `/health` (`specgen`, `audit-ergo`, `docanalyser`). Nom du dossier `apps\<id>\`. |
| `kind` | `web` (contrat commun) ou `native` (app de bureau). |
| `port` | App web : son port réservé (8010 SpecGen, 8501 AuditErgo, 8020 DocAnalyser). |
| `exe` | Nom de l'exe sans `.exe` ni version (`SpecGenerator`). |
| `path` | *(facultatif)* Emplacement imposé, fichier ou dossier, relatif au dossier de Studio Dock. |
| `install_name` | *(native, facultatif)* Nom dans « Applications installées », si différent de `name`. |
| `ai` | L'app utilise des modèles d'IA. |
| `icon` | Fichier relatif au dossier de Studio Dock (sinon icône livrée) ; `style` : `symbole` (posé sur fond Night Navy) ou `logo` (remplit la vignette, avec son propre fond). Carré, SVG ou PNG ≥ 256 px. |
| `tagline`, `description`, `points`, `tutorial`, `links` | Carte de l'accueil et fiche de l'app. |

### Rendre une app web compatible

Le contrat commun, déjà en place dans SpecGen, AuditErgo et DocAnalyser :

- `--port N` : port imposé ; s'il est pris par une autre application, l'app s'arrête avec le **code 2** ;
- `--no-browser` : ne pas ouvrir le navigateur ;
- `--version` ;
- `GET /health` → `{"status": "ok", "app": "<id>", "name": "…", "version": "X.Y.Z"}`, dès que le serveur tourne.

## Développement

```bash
cd frontend && npm ci && npm run build && cd ..
pip install -r backend/requirements-dev.txt
python backend/launcher.py --browser          # interface dans le navigateur, dossier « local/ » du dépôt
python backend/launcher.py --home C:\Essai    # autre dossier de Studio Dock
cd backend && python -m pytest -q
```

Interface en rechargement à chaud : `python backend/launcher.py --no-window` puis `cd frontend && npm run dev`
(http://localhost:5174, l'API est relayée vers le port 8040).

Structure : `backend/app/catalogue.py` (apps.json), `recherche.py` (trouver les exe et leur version),
`pilote.py` (lancer, suivre, arrêter), `winapi.py` (ce qui dépend de Windows), `main.py` (API) ;
`frontend/src/` (React, Tailwind, design system [Night Navy](https://github.com/aminart/Design-system-)).

## Versions

Le numéro de version vit dans le fichier `VERSION`, l'historique dans `CHANGELOG.md`.

1. `python scripts/bump_version.py patch|minor|major` (ou un numéro `X.Y.Z`) : met à jour `VERSION`, `frontend/package.json`
   et date la section « Non publié » du CHANGELOG.
2. Committer et fusionner sur `main`.
3. Créer la release GitHub avec le tag **`vX.Y.Z`** (exactement `v` + la version) : quelques minutes plus tard, le
   workflow « Build Windows exe » y joint `StudioDock-X.Y.Z.exe` et `StudioDock-X.Y.Z-windows.zip`.
