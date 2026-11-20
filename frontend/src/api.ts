import type { AiChoice, CatalogueApp, CatalogueEdit, AiState, ConnectionForm, ConnectionTest, DockApp, DockState, OllamaState, PrepareState, Settings } from './types';

export class ActionError extends Error {}

async function call<T>(method: 'GET' | 'POST' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T> {
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
  welcomeDone: (welcome_done: boolean) => call<Settings>('PUT', '/api/settings', { welcome_done }),
  saveCatalogueAdmin: (catalogue_admin: boolean) => call<Settings>('PUT', '/api/settings', { catalogue_admin }),
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

/** Préparer pour l'équipe : catalogue.json édité par formulaire. */
export const catalogueApi = {
  read: (folder: string) => call<CatalogueEdit>('POST', '/api/admin/catalogue/apps', { folder }),
  create: (folder: string) => call<CatalogueEdit>('POST', '/api/admin/catalogue/create', { folder }),
  save: (folder: string, id: string | null, app: CatalogueApp) =>
    call<CatalogueEdit>('PUT', '/api/admin/catalogue/apps', { folder, id: id ?? undefined, app }),
  remove: (folder: string, id: string) => call<CatalogueEdit>('POST', '/api/admin/catalogue/apps/delete', { folder, id }),
  move: (folder: string, id: string, direction: number) =>
    call<CatalogueEdit>('POST', '/api/admin/catalogue/apps/move', { folder, id, direction }),
  uploadIcon: (folder: string, id: string, name: string, data: string) =>
    call<{ file: string }>('POST', '/api/admin/catalogue/icon', { folder, id, name, data }),
};

/** Modèles d'IA communs aux apps (Réglages › Modèles d'IA). */
export const iaApi = {
  state: () => call<AiState>('GET', '/api/ia'),
  create: (form: ConnectionForm) => call<AiState>('POST', '/api/ia/connections', form),
  update: (id: string, form: ConnectionForm) => call<AiState>('PUT', `/api/ia/connections/${id}`, form),
  remove: (id: string) => call<AiState>('DELETE', `/api/ia/connections/${id}`),
  test: (body: ConnectionForm & { id?: string; certificate_b64?: string }) => call<ConnectionTest>('POST', '/api/ia/test', body),
  uploadCertificate: (id: string, name: string, data: string) =>
    call<AiState>('POST', `/api/ia/connections/${id}/certificate`, { name, data }),
  removeCertificate: (id: string) => call<AiState>('DELETE', `/api/ia/connections/${id}/certificate`),
  choose: (body: { default: AiState['default']; apps: Record<string, AiChoice> }) => call<AiState>('PUT', '/api/ia/choices', body),
  ollama: (address?: string) => call<OllamaState>('GET', `/api/ia/ollama${address ? `?address=${encodeURIComponent(address)}` : ''}`),
  pull: (model: string, address: string) => call<OllamaState>('POST', '/api/ia/ollama/pull', { model, address }),
  offerOllama: (address: string, models: string[], context_tokens: number | null) =>
    call<AiState & { ollama: OllamaState }>('PUT', '/api/ia/ollama', { address, models, context_tokens }),
};

/** Contenu d'un fichier en base64 (certificat). */
export const toBase64 = (file: File): Promise<string> => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(String(reader.result).split(',')[1] ?? '');
  reader.onerror = () => reject(reader.error);
  reader.readAsDataURL(file);
});
