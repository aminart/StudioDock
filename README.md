# Studio Dock

Fenêtre Windows et Mac qui lance les applications UX installées sur le poste (SpecGen, AuditErgo, DocAnalyser, Mapline…),
affiche leur état et les arrête quand on la ferme. Aucune app n'est écrite dans son code : la liste, les textes,
les icônes et les tutoriels viennent du fichier `apps.json`.

## Pour une équipe : dossier partagé

Studio Dock lit la liste des apps dans un **dossier partagé** que vous gérez, y trouve leurs dernières versions et
les **copie sur le poste** de chacun : les apps ne sont jamais lancées depuis le partage.

```
<dossier partagé>\                      vous seule y écrivez
  catalogue.json                        apps proposées, textes, icônes, sous-dossier et mode de chacune
  icons\                                icônes référencées par le catalogue
  StudioDock\    StudioDock-0.2.0.exe   nouvelles versions de Studio Dock
  SpecGen\       SpecGenerator-1.1.0.exe  SpecGenerator-1.2.0.exe
  Audit\         AuditErgo-1.1.0.exe
  DocAnalyser\   DocAnalyser-2.0.0.exe
  Mapline\       Mapline_1.3.1_x64-setup.exe
```

- **Publier une version** : déposer le nouvel exe dans le sous-dossier de l'app (les anciennes versions peuvent rester ;
  la plus récente est proposée). Chez chacun, la carte affiche « Version X disponible » ; les apps imposées à l'équipe
  (`"mode": "auto"`) sont mises à jour d'office quand elles ne sont pas lancées.
- **Ajouter une app** : sa fiche dans `catalogue.json` (avec `"source"` : son sous-dossier) et son exe dans ce
  sous-dossier ; elle apparaît chez chacun dans « Disponibles pour vous », avec le badge « Nouveau ».
- **Retirer une app de la liste** : `"mode": "masque"`.
- **Mettre à jour Studio Dock** : déposer `StudioDock-X.Y.Z.exe` dans `StudioDock\` ; chacun voit « Studio Dock X.Y.Z
  est disponible » et le remplace d'un clic (redémarrage automatique). Sur Mac, le bandeau ouvre le dossier.
- **Partage inaccessible** (réseau, VPN) : les apps installées restent utilisables, les cartes s'affichent depuis une copie
  locale du catalogue ; installations et mises à jour reprennent quand le partage revient.

`catalogue.json` a le même format que `apps.json` (voir plus bas), avec trois champs en plus :

| Champ | Rôle |
|---|---|
| `source` | Sous-dossier du partage où sont déposées les versions de l'app (défaut : son `id`). |
| `mode` | `auto` : installée d'office chez tout le monde, ne peut pas être retirée ; `optionnel` (défaut) : chacun l'installe s'il veut ; `masque` : retirée de la liste. |
| `studiodock.source` *(à la racine)* | Sous-dossier des versions de Studio Dock (défaut : `StudioDock`). |

**Réglage du dossier partagé** : écran Réglages de Studio Dock (bouton « Choisir… » ou chemin saisi). Pour éviter ce
réglage à chacun, posez à côté de `StudioDock.exe` un fichier `studiodock.config.json` :

```json
{ "shared_folder": "\\\\serveur\\Equipe UX" }
```

Le chemin accepte les variables (`%USERNAME%`, `$HOME`). Sans dossier partagé, Studio Dock utilise la liste locale
`apps.json` (ci-dessous).

**Installation sur le poste** : chacun copie `StudioDock.exe` (avec `studiodock.config.json`) une fois dans le dossier
local autorisé par l'entreprise et le lance. Les apps sont installées dans `apps\<id>\` à côté de lui.

## Installation sans dossier partagé

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

## Installation sur Mac

Studio Dock existe pour Mac Intel et Mac à puce Apple, macOS 12 (Monterey) ou plus récent. Pour savoir lequel
prendre : menu Pomme > « À propos de ce Mac », ligne « Processeur » (Intel) ou « Puce » (Apple M1, M2…).

1. Télécharger `StudioDock-X.Y.Z-mac-intel.zip` ou `StudioDock-X.Y.Z-mac-apple.zip` depuis la dernière release.
2. Double-cliquer sur le zip, puis glisser « Studio Dock » dans le dossier Applications.
3. Premier lancement : l'application n'est pas signée par Apple.
   - macOS 12 à 14 : clic droit (ou Ctrl + clic) sur Studio Dock > Ouvrir > Ouvrir.
   - macOS 15 et plus : l'ouvrir une fois, puis Réglages Système > Confidentialité et sécurité > « Ouvrir quand même ».
   - En dernier recours, dans le Terminal : `xattr -dr com.apple.quarantine "/Applications/Studio Dock.app"`.

Sur Mac, le dossier de Studio Dock (`apps.json`, `apps/`, `icons/`) est `~/Library/Application Support/StudioDock`
(bouton « Dossier de Studio Dock » en bas de la fenêtre) et les journaux sont dans `~/Library/Logs/StudioDock`.
Les apps web y attendent leur version Mac (`apps/specgen/SpecGenerator-1.1.0`, sans `.exe`), qui n'est pas encore
fabriquée ; les applications Mac installées (Mapline) sont retrouvées dans Applications.

## Ce que fait Studio Dock

| | App web (SpecGen, AuditErgo, DocAnalyser) | App de bureau (Mapline) |
|---|---|---|
| Lancer | `<exe> --port N --no-browser`, prête quand `GET /health` répond | Lance l'exe |
| Une fois lancée | **Ouvrir** (navigateur) et **Arrêter** | **Afficher** (fenêtre au premier plan) |
| État | `/health` sur son port | Processus présent |
| À la fermeture de Studio Dock | Arrêtée (sous Windows, même si Studio Dock plante : groupe de processus) | Continue |

Messages affichés sur la carte : exe introuvable (avec le dossier où le déposer), port pris par une autre application,
arrêt inattendu (fin du journal de l'app). Une app déjà lancée hors de Studio Dock est reconnue et peut être arrêtée.

Journaux : `%LOCALAPPDATA%\StudioDock\logs` sous Windows, `~/Library/Logs/StudioDock` sur Mac (un fichier par app,
plus `studiodock.log`).

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
   workflow « Build Windows exe » y joint `StudioDock-X.Y.Z.exe` et `StudioDock-X.Y.Z-windows.zip`, et le workflow
   « Build Mac app » `StudioDock-X.Y.Z-mac-intel.zip` et `StudioDock-X.Y.Z-mac-apple.zip`.
