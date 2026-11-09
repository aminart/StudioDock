import React from 'react';
import { ActionError, api } from './api';
import { InstallScreen, Restarting } from './install';
import { PreparePage } from './prepare';
import { AppPage, Home, SettingsPage } from './screens';
import type { DockApp, DockState } from './types';
import { Actions, Header, IconAlert, IconDownload, PlatformContext, TeamContext } from './ui';

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

  // Suivi des états : plus rapproché pendant un démarrage ou une installation
  const busy = !!state?.apps.some((a) => a.state === 'starting' || a.progress !== null) || pending.size > 0;
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
    install: (app) => run(null, async () => { await api.install(app.id); if (app.isNew) await api.seen([app.id]); }),
    uninstall: (app) => run(app, () => api.uninstall(app.id)),
    cancelDownload: (app) => run(null, () => api.cancelDownload(app.id)),
  };
  const catalogue = {
    check: () => run(null, () => api.checkCatalogue()),
    cancel: () => run(null, () => api.cancelCatalogue()),
  };

  const [restarting, setRestarting] = React.useState(false);
  const [moving, setMoving] = React.useState<string | null>(null);
  const updateDock = () => run(null, async () => {
    const r = await api.updateDock();
    if (r.restarting) setRestarting(true);
  });

  const appId = route.startsWith('#/app/') ? decodeURIComponent(route.slice(6)) : null;
  const settingsRoute = route === '#/reglages';
  const prepareRoute = route === '#/catalogue';
  const team = !!state && state.source !== 'local';
  const current = appId ? state?.apps.find((a) => a.id === appId) : undefined;

  return (
    <PlatformContext.Provider value={state?.platform ?? 'windows'}>
    <TeamContext.Provider value={team}>
    <div className="flex min-h-screen flex-col bg-bg font-sans text-[15px] leading-normal text-ink-body">
      <Header />
      <main className="mx-auto box-border flex w-full max-w-[1200px] flex-grow flex-col gap-6 px-6 pb-8 pt-10">
        {offline && (
          <div role="alert" className="flex items-center gap-2 rounded-md bg-danger-soft px-4 py-3 text-sm text-danger-text">
            <IconAlert /> Studio Dock ne répond plus. Relancez-le.
          </div>
        )}
        {restarting && (
          <div role="status" className="flex items-center gap-2 rounded-md bg-accent-soft px-4 py-3 text-sm text-accent-ink">
            Studio Dock redémarre avec la nouvelle version…
          </div>
        )}
        {moving && !state?.needsInstall && <Restarting folder={moving} />}
        {state?.dock.update && !restarting && !state.needsInstall && (
          <div className="flex flex-wrap items-center gap-3 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
            <IconDownload className="shrink-0" />
            {state.source === 'online' ? (
              state.dock.waiting ? (
                <span className="flex-grow">Téléchargez Studio Dock {state.dock.update} dans la page qui s'est ouverte : il se mettra à jour et redémarrera tout seul.</span>
              ) : (
                <>
                  <span className="flex-grow">Studio Dock {state.dock.update} est disponible.</span>
                  <button type="button" onClick={updateDock} className="border-0 bg-transparent p-0 font-medium text-warning-text underline">
                    {state.dock.canUpdate ? 'Télécharger la mise à jour' : 'Ouvrir la page de téléchargement'}
                  </button>
                </>
              )
            ) : (
              <>
                <span className="flex-grow">Studio Dock {state.dock.update} est disponible dans le dossier partagé.</span>
                <button type="button" onClick={updateDock} className="border-0 bg-transparent p-0 font-medium text-warning-text underline">
                  {state.dock.canUpdate ? 'Mettre à jour et redémarrer' : 'Ouvrir le dossier'}
                </button>
              </>
            )}
          </div>
        )}
        {state && state.source === 'cache' && (
          <div role="status" className="flex items-start gap-2 rounded-md border border-line bg-surface px-4 py-3 text-sm text-ink-muted">
            <IconAlert className="mt-0.5 shrink-0" />
            <span>Le dossier partagé de l'équipe est inaccessible. Vos applications installées restent utilisables ; installations et mises à jour reprendront dès qu'il sera de nouveau accessible.</span>
          </div>
        )}
        {state?.error && (
          <div role="alert" className="flex items-start gap-2 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
            <IconAlert className="mt-0.5 shrink-0" />
            <span>
              {state.source === 'local' ? 'La liste des apps contient une erreur' : 'Le catalogue de l\'équipe est illisible'} ; la dernière version valide reste affichée.
              <br /><span className="font-mono text-[13px]">{state.error}</span>
            </span>
          </div>
        )}
        {state?.needsInstall && !settingsRoute ? (
          <InstallScreen onRestart={setMoving} restartingIn={moving} />
        ) : prepareRoute ? (
          <PreparePage canChoose={!!state?.canChooseFolder} />
        ) : settingsRoute ? (
          <SettingsPage onSaved={refresh} openFolder={(name) => run(null, () => api.openFolder(name))} onRestart={setMoving} />
        ) : !state ? (
          <p className="text-ink-muted">Chargement…</p>
        ) : appId ? (
          current ? (
            <AppPage app={current} actions={actions} pending={pending.has(current.id)} />
          ) : (
            <p>Application inconnue. <a href="#/" className="text-accent">Retour à mes applications</a></p>
          )
        ) : (
          <Home state={state} actions={actions} pending={pending} catalogue={catalogue} />
        )}
      </main>
      <footer className="mx-auto box-border w-full max-w-[1200px] px-6 pb-6">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-line pt-4 text-[13px] text-ink-subtle">
          <span>Studio Dock {state ? `v${state.version}` : ''}</span>
          <span>Les apps web s'arrêtent quand vous fermez Studio Dock.</span>
          <span className="ml-auto flex gap-4">
            <button type="button" onClick={() => run(null, () => api.openFolder('home'))} className="border-0 bg-transparent p-0 text-accent hover:underline">Dossier d'installation</button>
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
    </TeamContext.Provider>
    </PlatformContext.Provider>
  );
};
