import React from 'react';
import { ActionError, api } from './api';
import { InstallScreen, Restarting } from './install';
import { AiPage } from './ia';
import { PreparePage } from './prepare';
import { AppPage, Home, SettingsPage } from './screens';
import { Tour } from './tour';
import { useConfirm } from './dialog';
import { Welcome } from './welcome';
import type { DockApp, DockState } from './types';
import { Actions, AdminContext, Header, IconAlert, IconDownload, PlatformContext, TeamContext } from './ui';

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

  const [dialog, ask] = useConfirm();
  const interrompu = (app: DockApp) => app.busy
    ? `${app.name} est en train de travailler : la génération ou l'analyse en cours sera interrompue.`
    : `Un travail en cours dans ${app.name} (génération, analyse) serait interrompu. Pensez à enregistrer ce qui doit l'être.`;
  // Ouvre le dossier des journaux et dit quoi envoyer
  const report = (app?: DockApp) => run(null, async () => {
    await api.openFolder('logs');
    await ask({
      title: 'Signaler un problème',
      text: <>
        <p className="m-0">Le dossier des journaux vient de s'ouvrir. Joignez à votre message :</p>
        <ul className="m-0 flex flex-col gap-1 pl-5">
          <li><span className="font-mono">studiodock.log</span>, le journal de Studio Dock ;</li>
          <li>{app ? <><span className="font-mono">{app.id}.log</span>, celui de {app.name}</> : <>le fichier de l'app concernée, par exemple <span className="font-mono">specgen.log</span></>}.</li>
        </ul>
        <p className="m-0">Dites aussi ce que vous faisiez au moment du souci. Envoyez-les à la personne qui gère les apps de l'équipe.</p>
      </>,
    });
  });

  // Fermeture de la fenêtre avec des apps web ouvertes : appelée par Studio Dock, qui attend la réponse ici
  const latest = React.useRef(state);
  latest.current = state;
  React.useEffect(() => {
    const w = window as unknown as { __studioDockFermeture?: () => boolean };
    w.__studioDockFermeture = () => {
      const open = (latest.current?.apps ?? []).filter((a) => a.kind !== 'native' && a.state === 'on' && !a.external);
      const names = open.map((a) => a.name);
      const list = names.length > 1 ? `${names.slice(0, -1).join(', ')} et ${names[names.length - 1]}` : names[0] ?? 'Des apps';
      ask({
        title: 'Fermer Studio Dock ?',
        text: <>
          <p className="m-0">{list} {names.length > 1 ? 'sont ouvertes' : 'est ouverte'} : {names.length > 1 ? 'elles s\'arrêtent' : 'elle s\'arrête'} avec Studio Dock, et un travail en cours serait perdu.</p>
          <p className="m-0">Pour continuer à {names.length > 1 ? 'les' : 'l\''}utiliser, réduisez plutôt Studio Dock dans la barre des tâches.</p>
        </>,
        choices: [
          { label: 'Tout fermer', value: 'close', tone: 'danger' },
          { label: 'Réduire Studio Dock', value: 'minimize', tone: 'primary', focus: true },
        ],
      }).then((r) => {
        if (r === 'minimize') api.minimizeWindow().catch(() => undefined);
        else if (r === 'close') api.closeWindow().catch(() => undefined);
      });
      return true;
    };
    return () => { delete w.__studioDockFermeture; };
  }, [ask]);

  const actions: Actions = {
    launch: (app) => run(app, () => api.launch(app.id)),
    stop: async (app) => {
      const ok = await ask({ title: `Arrêter ${app.name} ?`, text: <p className="m-0">{interrompu(app)}</p>, confirm: 'Arrêter', danger: app.busy });
      if (ok) run(app, () => api.stop(app.id));
    },
    open: (app) => run(null, () => api.open(app.id)),
    dismiss: (app) => run(null, () => api.dismiss(app.id)),
    folder: (app) => run(null, () => api.folder(app.id)),
    logs: report,
    link: (url) => run(null, () => api.openLink(url)),
    install: async (app) => {
      if (app.installed && app.state === 'on') {
        const ok = await ask({
          title: `Mettre à jour ${app.name} ?`,
          text: <p className="m-0">{app.name} est ouverte : elle sera fermée, puis mise à jour en version {app.availableVersion}. {interrompu(app)}</p>,
          confirm: 'Fermer et mettre à jour', danger: app.busy,
        });
        if (!ok) return;
      }
      run(null, async () => { await api.install(app.id); if (app.isNew) await api.seen([app.id]); });
    },
    uninstall: async (app) => {
      const ok = await ask({
        title: `Retirer ${app.name} de ce poste ?`,
        text: <>
          <p className="m-0"><strong className="font-semibold text-ink">Supprimé :</strong> le programme, dans votre dossier d'applications.{app.state === 'on' ? ` ${app.name} sera d'abord fermée.` : ''}</p>
          <p className="m-0"><strong className="font-semibold text-ink">Conservé :</strong> vos documents, votre historique et vos réglages. Vous retrouverez tout en la réinstallant depuis « Disponibles pour vous ».</p>
        </>,
        confirm: 'Retirer', danger: true,
      });
      if (ok) run(app, () => api.uninstall(app.id));
    },
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
  const iaRoute = route === '#/ia';
  const welcomeRoute = route === '#/bienvenue';
  // Tutoriel commencé : il reste affiché jusqu'à ce qu'on le quitte, même si une app s'installe entre-temps
  // (les apps imposées à l'équipe, ou celles cochées à la fin)
  const [welcomeOpen, setWelcomeOpen] = React.useState(false);
  const showWelcome = !!state && (welcomeRoute
    || ((welcomeOpen || state.welcome) && !appId && !settingsRoute && !prepareRoute && !iaRoute));
  React.useEffect(() => { if (showWelcome && !state?.needsInstall) setWelcomeOpen(true); }, [showWelcome, state?.needsInstall]);
  const tourRoute = route === '#/visite';
  const team = !!state && state.source !== 'local';
  const current = appId ? state?.apps.find((a) => a.id === appId) : undefined;

  return (
    <PlatformContext.Provider value={state?.platform ?? 'windows'}>
    <TeamContext.Provider value={team}>
    <AdminContext.Provider value={!!state?.catalogueAdmin}>
    <div className="flex min-h-screen flex-col bg-bg font-sans text-[15px] leading-normal text-ink-body">
      <Header settings={settingsRoute || iaRoute || prepareRoute} />
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
        ) : state && showWelcome ? (
          <Welcome state={state} openHome={() => run(null, () => api.openFolder('home'))}
            onDone={(next) => { setWelcomeOpen(false); refresh(); window.location.hash = next ?? '#/'; }} />
        ) : iaRoute ? (
          <AiPage />
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
          <>
            <Home state={state} actions={actions} pending={pending} catalogue={catalogue} />
            {tourRoute && <Tour onClose={() => { window.location.hash = '#/'; }} />}
          </>
        )}
      </main>
      <footer className="mx-auto box-border w-full max-w-[1200px] px-6 pb-6">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-line pt-4 text-[13px] text-ink-subtle">
          <span>Studio Dock {state ? `v${state.version}` : ''}</span>
          <span>Les apps web s'arrêtent avec Studio Dock : il vous prévient avant.</span>
          <span data-tour="pied" className="ml-auto flex gap-4">
            <a href="#/visite" className="text-accent no-underline hover:underline">Visite guidée</a>
            <a href="#/bienvenue" className="text-accent no-underline hover:underline">Revoir le tutoriel</a>
            <button type="button" onClick={() => actions.logs()} className="border-0 bg-transparent p-0 text-accent hover:underline">Signaler un problème</button>
          </span>
        </div>
      </footer>
      {dialog}
      {toast && (
        <div role="status" className="fixed bottom-6 left-1/2 z-10 flex max-w-[560px] -translate-x-1/2 items-start gap-2 rounded-md bg-ink px-4 py-3 text-sm text-surface shadow-lg">
          <IconAlert className="mt-0.5 shrink-0" /> <span className="whitespace-pre-line">{toast}</span>
        </div>
      )}
    </div>
    </AdminContext.Provider>
    </TeamContext.Provider>
    </PlatformContext.Provider>
  );
};
