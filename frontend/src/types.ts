export type AppState = 'missing' | 'off' | 'starting' | 'on' | 'error';

/** Une app du catalogue (apps.json) et son état sur ce poste, tels que renvoyés par GET /api/apps. */
export interface DockApp {
  id: string;
  name: string;
  kind: 'web' | 'native';
  port: number | null;
  ai: boolean;
  exe: string;
  tagline: string;
  description: string;
  points: string[];
  tutorial: { title: string; text: string }[];
  links: { label: string; url: string }[];
  icon: { file: string | null; style: 'symbole' | 'logo' };
  iconUrl: string | null;
  state: AppState;
  version: string | null;
  location: string | null;
  folder: string | null;
  url: string | null;
  external: boolean;
  error: { code: string; message: string } | null;
  /** Catalogue d'équipe : mode, installation sur ce poste, version disponible sur le partage. */
  mode: 'auto' | 'optionnel' | 'masque';
  installed: boolean;
  availableVersion: string | null;
  update: boolean;
  progress: number | null;
  installError: string | null;
  isNew: boolean;
  /** Catalogue en ligne : lien du dossier en ligne de l'app, téléchargement demandé et attendu. */
  link: string | null;
  waiting: boolean;
}

export interface OnlineState {
  /** Date de fabrication du catalogue en ligne importé. */
  published: string | null;
  /** Date du dernier import sur ce poste. */
  imported: string | null;
  link: string | null;
  waiting: boolean;
  error: string | null;
  downloads: string;
}

export interface DockState {
  version: string;
  platform: 'windows' | 'mac' | 'linux';
  home: string;
  catalogue: string;
  /** shared : catalogue du dossier partagé ; cache : sa copie (partage inaccessible) ;
   *  online : catalogue en ligne téléchargé ; local : apps.json. */
  source: 'shared' | 'cache' | 'online' | 'local';
  sharedFolder: string | null;
  sharedOk: boolean;
  error: string | null;
  dock: { update: string | null; canUpdate: boolean; waiting: boolean };
  online: OnlineState;
  canChooseFolder: boolean;
  /** Exe Windows lancé hors de son dossier d'installation : l'écran d'installation s'affiche. */
  needsInstall: boolean;
  apps: DockApp[];
}

export interface Settings {
  shared_folder: string;
  resolved: string | null;
  reachable: boolean;
  hasCatalogue: boolean;
  home: string;
  canChooseFolder: boolean;
  install: InstallState;
  catalogue_link: string;
  prepare_folder: string;
  downloads: string;
}

export interface PrepareApp {
  id: string;
  name: string;
  source: string;
  mode: string;
  found: string | null;
  version: string | null;
  link: string;
  icon: boolean;
}

export interface PrepareState {
  folder: string;
  apps: PrepareApp[];
  studiodock: { source: string; found: string | null; version: string | null; link: string };
  link: string;
  published: string | null;
  zip?: string;
}

export interface InstallState {
  /** Choix du dossier d'installation possible (exe Windows). */
  available: boolean;
  /** Studio Dock tourne depuis le dossier choisi. */
  installed: boolean;
  folder: string | null;
  suggested: string;
  running: string | null;
}
