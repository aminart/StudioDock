export type AppState = 'missing' | 'off' | 'starting' | 'on' | 'error';

/** Une app du catalogue (apps.json) et son état sur ce poste, tels que renvoyés par GET /api/apps. */
export interface DockApp {
  id: string;
  name: string;
  kind: 'web' | 'native' | 'external';
  port: number | null;
  ai: boolean;
  exe: string;
  /** App web externe : adresse fixe (http://localhost:5000) ; vide = port détecté au lancement. */
  address?: string | null;
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
  /** Ouverte mais trop occupée pour répondre à Studio Dock (longue génération) : elle continue de tourner. */
  busy?: boolean;
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
  /** Première connexion : le tutoriel d'accueil s'affiche. */
  welcome: boolean;
  /** Ce poste tient le catalogue de l'équipe : l'onglet « Préparer pour l'équipe » s'affiche. */
  catalogueAdmin: boolean;
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
  /** Ce poste tient le catalogue de l'équipe : l'onglet « Préparer pour l'équipe » s'affiche. */
  catalogue_admin: boolean;
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
  /** Modèle de transcription de l'équipe, s'il est déclaré dans le catalogue. */
  transcription: { name: string; source: string; found: string | null; version: string | null; link: string } | null;
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

/* ---------- Modèles d'IA communs aux apps ---------- */

export interface ConnectionTest {
  ok: boolean;
  field: 'api_base' | 'api_key' | 'certificate' | 'models' | null;
  title: string;
  message: string;
  available?: string[] | null;
  missing?: string[];
  at: string;
}

export interface AiConnection {
  id: string;
  name: string;
  provider: 'openai' | 'ollama';
  api_base: string;
  has_api_key: boolean;
  api_key_hint: string;
  certificate: { name: string; imported_at?: string; expires_at?: string | null } | null;
  models: string[];
  context_tokens: number;
  max_output_tokens: number;
  last_test: ConnectionTest | null;
}

/** Choix d'un modèle : une connexion et un de ses modèles, ou la configuration propre à l'app. */
export type AiChoice = { connection: string; model: string } | { own: true };

export interface AiApp {
  id: string;
  name: string;
  installed: boolean;
  iconUrl: string | null;
  choice: AiChoice | null;
}

export interface AiState {
  connections: AiConnection[];
  default: { connection: string; model: string } | null;
  apps: AiApp[];
  folder: string;
  created?: string;
}

export interface ConnectionForm {
  name: string;
  api_base: string;
  /** null : garder la clé enregistrée ; '' : aucune clé. */
  api_key: string | null;
  models: string[];
  context_tokens: number | null;
  last_test?: ConnectionTest;
}

export interface OllamaModel { name: string; size: string; parameters: string; quantization: string; family: string }
export interface OllamaPull { model: string; status: string; completed: number; total: number; error: string | null; finished: boolean }
export interface OllamaState {
  address: string;
  running: boolean;
  version: string | null;
  models: OllamaModel[];
  pulls: OllamaPull[];
  connection: AiConnection | null;
}

/* ---------- Préparer pour l'équipe : édition du catalogue ---------- */

export interface CatalogueApp {
  id: string;
  name: string;
  kind: 'web' | 'native' | 'external';
  port: number | null;
  ai: boolean;
  exe: string;
  address?: string | null;
  source: string;
  mode: 'auto' | 'optionnel' | 'masque';
  install_name?: string | null;
  tagline: string;
  description: string;
  points: string[];
  tutorial: { title: string; text: string }[];
  links: { label: string; url: string }[];
  icon: { file: string | null; style: 'logo' | 'symbole' };
  iconFound?: boolean;
  sourceFound?: boolean;
  /** Fiche refusée par la validation (catalogue.json modifié à la main). */
  invalid?: string;
}

/** Modèle de transcription déclaré dans le catalogue (Préparer pour l'équipe). */
export interface CatalogueTranscription {
  name: string;
  source: string;
  sourceFound?: boolean;
  found?: string | null;
  version?: string | null;
  invalid?: string;
}

/** Modèle de transcription sur ce poste (Réglages › Modèles d'IA). */
export interface TranscriptionState {
  offered: boolean;
  name: string | null;
  installed: boolean;
  version: string | null;
  path: string | null;
  available: string | null;
  update: boolean;
  size: number | null;
  online: boolean;
  canDownload: boolean;
  waiting: boolean;
  progress: number | null;
  error: string | null;
}

export interface CatalogueEdit {
  folder: string;
  exists: boolean;
  apps: CatalogueApp[];
  studiodock: { source: string };
  transcription: CatalogueTranscription | null;
  /** Le dossier édité est le dossier partagé de l'équipe : les changements y sont visibles tout de suite. */
  isShared: boolean;
  saved?: string;
}
