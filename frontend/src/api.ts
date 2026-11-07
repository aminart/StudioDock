import type { DockApp, DockState } from './types';

export class ActionError extends Error {}

async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
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
  openFolder: (name: 'home' | 'logs') => call<{ ok: boolean }>('POST', `/api/open-folder/${name}`),
  openLink: (url: string) => call<{ ok: boolean }>('POST', '/api/open-link', { url }),
};
