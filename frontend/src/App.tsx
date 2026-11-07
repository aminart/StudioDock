import React from 'react';
import { ActionError, api } from './api';
import { AppPage, Home } from './screens';
import type { DockApp, DockState } from './types';
import { Actions, Header, IconAlert } from './ui';

const useRoute = (): string => {
  const [hash, setHash] = React.useState(window.location.hash);
  React.useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash);
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return hash;
};

export const App: React.FC = () => {
  const [state, setState] = React.useState<DockState | null>(null);
  const [offline, setOffline] = React.useState(false);
  const [pending, setPending] = React.useState<Set<string>>(new Set());
  const [toast, setToast] = React.useState<string | null>(null);
  const route = useRoute();

  const refresh = React.useCallback(async () => {
    try {
      setState(await api.state());
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, []);

  // Suivi des états : plus rapproché pendant un démarrage
  const busy = !!state?.apps.some((a) => a.state === 'starting') || pending.size > 0;
  React.useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, busy ? 700 : 2000);
    return () => window.clearInterval(timer);
  }, [refresh, busy]);

  React.useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 6000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const run = React.useCallback(async (app: DockApp | null, action: () => Promise<unknown>) => {
    if (app) setPending((p) => new Set(p).add(app.id));
    try {
      await action();
    } catch (e) {
      setToast(e instanceof ActionError ? e.message : 'Action impossible : Studio Dock ne répond pas.');
    } finally {
      if (app) setPending((p) => { const n = new Set(p); n.delete(app.id); return n; });
      refresh();
    }
  }, [refresh]);

  const actions: Actions = {
    launch: (app) => run(app, () => api.launch(app.id)),
    stop: (app) => run(app, () => api.stop(app.id)),
    open: (app) => run(null, () => api.open(app.id)),
    dismiss: (app) => run(null, () => api.dismiss(app.id)),
    folder: (app) => run(null, () => api.folder(app.id)),
    logs: () => run(null, () => api.openFolder('logs')),
    link: (url) => run(null, () => api.openLink(url)),
  };

  const appId = route.startsWith('#/app/') ? decodeURIComponent(route.slice(6)) : null;
  const current = appId ? state?.apps.find((a) => a.id === appId) : undefined;

  return (
    <div className="flex min-h-screen flex-col bg-bg font-sans text-[15px] leading-normal text-ink-body">
      <Header />
      <main className="mx-auto box-border flex w-full max-w-[1120px] flex-grow flex-col gap-6 px-6 pb-8 pt-10">
        {offline && (
          <div role="alert" className="flex items-center gap-2 rounded-md bg-danger-soft px-4 py-3 text-sm text-danger-text">
            <IconAlert /> Studio Dock ne répond plus. Relancez-le.
          </div>
        )}
        {state?.error && (
          <div role="alert" className="flex items-start gap-2 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
            <IconAlert className="mt-0.5 shrink-0" />
            <span>
              Le fichier de la liste des apps contient une erreur ; la dernière version valide reste affichée.
              <br /><span className="font-mono text-[13px]">{state.error}</span>
            </span>
          </div>
        )}
        {!state ? (
          <p className="text-ink-muted">Chargement…</p>
        ) : appId ? (
          current ? (
            <AppPage app={current} actions={actions} pending={pending.has(current.id)} />
          ) : (
            <p>Application inconnue. <a href="#/" className="text-accent">Retour à mes applications</a></p>
          )
        ) : (
          <Home state={state} actions={actions} pending={pending} />
        )}
      </main>
      <footer className="mx-auto box-border w-full max-w-[1120px] px-6 pb-6">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-line pt-4 text-[13px] text-ink-subtle">
          <span>Studio Dock {state ? `v${state.version}` : ''}</span>
          <span>Les apps web s'arrêtent quand vous fermez Studio Dock.</span>
          <span className="ml-auto flex gap-4">
            <button type="button" onClick={() => run(null, () => api.openFolder('home'))} className="border-0 bg-transparent p-0 text-accent hover:underline">Dossier de Studio Dock</button>
            <button type="button" onClick={() => actions.logs()} className="border-0 bg-transparent p-0 text-accent hover:underline">Journaux</button>
          </span>
        </div>
      </footer>
      {toast && (
        <div role="status" className="fixed bottom-6 left-1/2 z-10 flex max-w-[560px] -translate-x-1/2 items-start gap-2 rounded-md bg-ink px-4 py-3 text-sm text-surface shadow-lg">
          <IconAlert className="mt-0.5 shrink-0" /> <span className="whitespace-pre-line">{toast}</span>
        </div>
      )}
    </div>
  );
};
