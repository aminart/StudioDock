import type { DockApp, DockState, PrepareState, Settings } from './types';

export class ActionError extends Error {}

async function call<T>(method: 'GET' | 'POST' | 'PUT', path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    let message = `Erreur ${response.status}`;
    try {
      message = (await response.json()).detail ?? message;
    } catch {
      /* réponse sans JSON */
    }
    throw new ActionError(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  state: () => call<DockState>('GET', '/api/apps'),
  launch: (id: string) => call<DockApp>('POST', `/api/apps/${id}/launch`),
  stop: (id: string) => call<DockApp>('POST', `/api/apps/${id}/stop`),
  open: (id: string) => call<{ ok: boolean }>('POST', `/api/apps/${id}/open`),
  dismiss: (id: string) => call<DockApp>('POST', `/api/apps/${id}/dismiss`),
  folder: (id: string) => call<{ ok: boolean }>('POST', `/api/apps/${id}/folder`),
  openFolder: (name: 'home' | 'logs' | 'shared') => call<{ ok: boolean }>('POST', `/api/open-folder/${name}`),
  install: (id: string) => call<DockApp>('POST', `/api/apps/${id}/install`),
  uninstall: (id: string) => call<DockApp>('POST', `/api/apps/${id}/uninstall`),
  seen: (ids: string[]) => call<{ ok: boolean }>('POST', '/api/seen', { ids }),
  settings: () => call<Settings>('GET', '/api/settings'),
  saveSettings: (shared_folder: string) => call<Settings>('PUT', '/api/settings', { shared_folder }),
  saveCatalogueLink: (catalogue_link: string) => call<Settings>('PUT', '/api/settings', { catalogue_link }),
  cancelDownload: (id: string) => call<DockApp>('POST', `/api/apps/${id}/cancel-download`),
  checkCatalogue: () => call<{ ok: boolean }>('POST', '/api/catalogue/check'),
  cancelCatalogue: () => call<{ ok: boolean }>('POST', '/api/catalogue/cancel'),
  prepare: (folder: string) => call<PrepareState>('POST', '/api/admin/catalogue', { folder }),
  build: (body: { folder: string; links: Record<string, string>; studiodockLink: string; catalogueLink: string }) =>
    call<PrepareState>('POST', '/api/admin/catalogue/build', body),
  showPrepare: (folder: string) => call<{ ok: boolean }>('POST', '/api/admin/catalogue/show', { folder }),
  installDock: (folder: string) => call<{ ok: boolean; restarting: boolean; folder: string; shortcut: boolean }>('PUT', '/api/settings/install', { folder }),
  chooseFolder: () => call<{ path: string | null }>('POST', '/api/settings/choose-folder'),
  updateDock: () => call<{ ok: boolean; restarting: boolean; waiting?: boolean }>('POST', '/api/dock/update'),
  openLink: (url: string) => call<{ ok: boolean }>('POST', '/api/open-link', { url }),
};
