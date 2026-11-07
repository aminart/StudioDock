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
}

export interface DockState {
  version: string;
  platform: 'windows' | 'mac' | 'linux';
  home: string;
  catalogue: string;
  error: string | null;
  apps: DockApp[];
}
