import React from 'react';
import { api } from './api';
import { InstallFolderForm } from './install';
import type { DockApp, DockState, Settings } from './types';
import {
  Actions, AppActions, AppIcon, AppNotice, IconAlert, IconBack, IconChevron, IconDownload, IconExternal, IconFolder, IconRefresh, IconSpinner,
  PlatformContext, ProgressBar, StatusChip, StatusLine, TeamContext, UpdateBanner, UpdateButton, WaitingActions, where,
} from './ui';

/** Mes applications : installées sur ce poste, ou imposées à l'équipe (installation en cours ou en attente). */
export const isMine = (app: DockApp, team: boolean) => !team || app.installed || app.mode === 'auto';

/* ---------- Menu « ⋯ » d'une carte ---------- */

const CardMenu: React.FC<{ app: DockApp; actions: Actions }> = ({ app, actions }) => {
  const team = React.useContext(TeamContext);
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  const item = 'flex min-h-10 w-full items-center gap-2.5 rounded-sm border-0 bg-transparent px-3 text-left text-sm text-ink-body hover:bg-surface-3';
  const removable = team && app.installed;
  return (
    <div ref={ref} className="relative -mr-2 -mt-1.5">
      <button type="button" onClick={() => setOpen(!open)} aria-label={`Plus d'actions pour ${app.name}`} aria-haspopup="menu" aria-expanded={open}
        className="flex h-9 w-9 items-center justify-center rounded border-0 bg-transparent text-ink-subtle hover:bg-surface-3 hover:text-ink">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="5" r="1.8" /><circle cx="12" cy="12" r="1.8" /><circle cx="12" cy="19" r="1.8" /></svg>
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-10 z-10 flex min-w-[250px] flex-col rounded-md border border-line-strong bg-surface p-1.5 shadow-lg">
          <a role="menuitem" href={`#/app/${app.id}`} className={`${item} no-underline`}>Fiche et prise en main</a>
          {app.folder && (app.location || !team) && (
            <button type="button" role="menuitem" className={item} onClick={() => { setOpen(false); actions.folder(app); }}>
              Afficher le dossier de l'app
            </button>
          )}
          {removable && (app.mode === 'auto' ? (
            <span role="menuitem" aria-disabled="true" className="px-3 py-2 text-[13px] text-ink-subtle">
              Installée pour toute l'équipe : ne peut pas être retirée
            </span>
          ) : app.kind === 'web' ? (
            <button type="button" role="menuitem" className={item} onClick={() => { setOpen(false); actions.uninstall(app); }}>
              Retirer de ce poste
            </button>
          ) : (
            <span role="menuitem" aria-disabled="true" className="px-3 py-2 text-[13px] text-ink-subtle">
              Se désinstalle depuis les réglages du système
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

/* ---------- Accueil ---------- */

const AppCard: React.FC<{ app: DockApp; actions: Actions; pending: boolean }> = ({ app, actions, pending }) => {
  const on = app.state === 'on';
  return (
    <article className={`flex min-h-[268px] flex-col gap-4 rounded-lg p-[22px] ${on
      ? 'border-[1.5px] border-accent bg-gradient-to-b from-accent-softer to-surface'
      : 'border border-line bg-surface hover:border-line-strong'}`}>
      <div className="flex items-start justify-between">
        <a href={`#/app/${app.id}`} aria-label={`Fiche de ${app.name}`} className="rounded-[13px] shadow-[0_6px_14px_-6px_rgba(27,29,42,0.35)]">
          <AppIcon app={app} size={56} />
        </a>
        <CardMenu app={app} actions={actions} />
      </div>
      <div className="flex flex-grow flex-col gap-1.5">
        <h2 className="clamp-1 m-0 text-[19px] font-bold leading-snug text-ink">
          <a href={`#/app/${app.id}`} className="text-inherit no-underline hover:underline">{app.name}</a>
        </h2>
        {app.tagline && <p className="clamp-2 m-0 text-sm leading-[1.45] text-ink-muted">{app.tagline}</p>}
      </div>
      <AppNotice app={app} actions={actions} compact />
      <div className="flex flex-col gap-3">
        <StatusLine app={app} />
        <ProgressBar app={app} />
        <div className="flex gap-2">
          <AppActions app={app} actions={actions} pending={pending} />
          <UpdateButton app={app} actions={actions} />
        </div>
      </div>
    </article>
  );
};

/** Carte compacte d'une app proposée par l'équipe, pas encore installée sur ce poste. */
const AvailableCard: React.FC<{ app: DockApp; actions: Actions }> = ({ app, actions }) => (
  <article className="flex flex-col gap-3 rounded-lg border border-dashed border-line-strong bg-surface px-[18px] py-4">
    <div className="flex items-center gap-3.5">
      <AppIcon app={app} size={40} />
      <div className="flex min-w-0 flex-grow flex-col">
        <div className="flex min-w-0 items-center gap-2">
          <h3 className="clamp-1 m-0 min-w-0 text-base font-bold text-ink">
            <a href={`#/app/${app.id}`} className="text-inherit no-underline hover:underline">{app.name}</a>
          </h3>
          {app.isNew && (
            <span className="shrink-0 rounded-full bg-primary px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-primary-on">Nouveau</span>
          )}
        </div>
        {app.tagline && <p className="clamp-1 m-0 text-sm text-ink-muted">{app.tagline}</p>}
      </div>
    </div>
    <AppNotice app={app} actions={actions} />
    {app.waiting && app.progress === null ? (
      <WaitingActions app={app} actions={actions} wide />
    ) : app.progress !== null ? (
      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between text-[13px] text-ink-subtle"><span>Installation…</span><span className="font-mono">{app.progress} %</span></div>
        <ProgressBar app={app} />
      </div>
    ) : (
      <div className="flex items-center gap-3">
        <span className="clamp-1 flex-grow font-mono text-[13px] text-ink-subtle">
          {app.availableVersion ? `v${app.availableVersion} · ` : ''}{app.kind === 'web' ? 'app web' : 'app de bureau'}
        </span>
        {app.availableVersion ? (
          <button type="button" onClick={() => actions.install(app)}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-4 font-medium text-accent hover:bg-surface-3">
            <IconDownload /> Installer
          </button>
        ) : (
          <span className="text-[13px] text-ink-subtle">Indisponible</span>
        )}
      </div>
    )}
  </article>
);

const grid = { gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' };
const gridAvailable = { gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))' };

/** Pastilles de résumé : apps ouvertes, mises à jour disponibles. */
const Summary: React.FC<{ apps: DockApp[] }> = ({ apps }) => {
  const on = apps.filter((a) => a.state === 'on').length;
  const updates = apps.filter((a) => a.update).length;
  if (!on && !updates) return null;
  return (
    <div className="flex gap-2">
      {on > 0 && (
        <span className="flex h-8 items-center gap-2 rounded-full bg-success-soft px-3 text-[13px] font-medium text-success-text">
          <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" />{on} {on > 1 ? 'apps ouvertes' : 'app ouverte'}
        </span>
      )}
      {updates > 0 && (
        <span className="flex h-8 items-center gap-2 rounded-full bg-accent-soft px-3 text-[13px] font-medium text-accent-ink">
          <IconRefresh size={14} />{updates} {updates > 1 ? 'mises à jour' : 'mise à jour'}
        </span>
      )}
    </div>
  );
};

/** Catalogue en ligne : date du catalogue, vérification des mises à jour, import du premier catalogue. */
export type CatalogueActions = { check: () => void; cancel: () => void };

const formatDate = (iso: string | null) => {
  if (!iso) return null;
  const d = new Date(iso.replace(' ', 'T'));
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
};

const OnlineBar: React.FC<{ state: DockState; catalogue: CatalogueActions }> = ({ state, catalogue }) => {
  const { online } = state;
  const btn = 'flex h-9 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3';
  const waiting = online.waiting && (
    <div role="status" className="flex flex-wrap items-center gap-3 rounded-md bg-accent-soft px-4 py-3 text-sm text-accent-ink">
      <IconSpinner />
      <span className="flex-grow">Téléchargez <span className="font-mono">studio-dock-catalogue.zip</span> dans la page qui s'est ouverte : Studio Dock l'importe dès qu'il arrive dans vos Téléchargements.</span>
      <button type="button" onClick={catalogue.check} className="border-0 bg-transparent p-0 font-medium text-accent-ink underline">Rouvrir la page</button>
      <button type="button" onClick={catalogue.cancel} className="border-0 bg-transparent p-0 font-medium text-accent-ink underline">Annuler</button>
    </div>
  );
  const erreur = online.error && (
    <div role="alert" className="flex items-start gap-2 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
      <IconAlert className="mt-0.5 shrink-0" />
      <span>{online.error}</span>
    </div>
  );
  if (state.source === 'online') {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
          <span>Catalogue de l'équipe{online.published ? ` du ${formatDate(online.published)}` : ''}</span>
          {!online.waiting && (
            <button type="button" onClick={catalogue.check} className={btn}><IconRefresh /> Vérifier les mises à jour</button>
          )}
        </div>
        {waiting}
        {erreur}
      </div>
    );
  }
  if (state.source !== 'local' || state.sharedFolder) return null;
  return (
    <div className="flex flex-col gap-3">
      {!online.waiting && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface px-4 py-3 text-sm text-ink-muted">
          <IconDownload className="shrink-0" />
          <span className="min-w-0 flex-[1_1_360px]">
            Votre équipe partage ses applications en ligne ? Téléchargez son catalogue
            (<span className="font-mono text-[13px]">studio-dock-catalogue.zip</span>) : Studio Dock l'importe dès qu'il arrive dans vos Téléchargements.
          </span>
          {online.link ? (
            <button type="button" onClick={catalogue.check} className={btn}><IconExternal /> Ouvrir le catalogue</button>
          ) : (
            <a href="#/reglages" className="text-accent">Indiquer son lien</a>
          )}
        </div>
      )}
      {waiting}
      {erreur}
    </div>
  );
};

export const Home: React.FC<{ state: DockState; actions: Actions; pending: Set<string>; catalogue: CatalogueActions }> = ({ state, actions, pending, catalogue }) => {
  const team = state.source !== 'local';
  const mine = state.apps.filter((a) => isMine(a, team));
  const available = state.apps.filter((a) => !isMine(a, team));
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div className="flex flex-[1_1_360px] flex-col gap-2">
          <h1 className="m-0 text-[32px] font-bold leading-tight text-ink">Mes applications</h1>
          <p className="m-0 max-w-[680px] text-[15px] text-ink-muted">Vos outils de design, lancés et mis à jour depuis un seul endroit.</p>
        </div>
        <Summary apps={mine} />
      </div>
      <OnlineBar state={state} catalogue={catalogue} />
      {mine.length === 0 ? (
        <div className="rounded-lg border border-dashed border-line-dashed bg-surface p-8 text-center text-ink-muted">
          {team ? 'Aucune application installée pour le moment : choisissez-en dans « Disponibles pour vous ».'
            : <>Aucune application dans <span className="font-mono">{state.catalogue}</span>.</>}
        </div>
      ) : (
        <div className="grid gap-5" style={grid}>
          {mine.map((app) => <AppCard key={app.id} app={app} actions={actions} pending={pending.has(app.id)} />)}
        </div>
      )}
      {available.length > 0 && (
        <section aria-labelledby="dispo" className="mt-4 flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 id="dispo" className="m-0 flex items-center gap-2.5 text-[21px] font-bold leading-snug text-ink">
              Disponibles pour vous
              <span className="rounded-full bg-accent-soft px-2.5 text-[13px] font-medium text-accent-ink">{available.length}</span>
            </h2>
            <p className="m-0 text-sm text-ink-muted">Proposées par votre équipe. Installez celles qui vous servent ; vous pourrez les retirer à tout moment.</p>
          </div>
          <div className="grid gap-5" style={gridAvailable}>
            {available.map((app) => <AvailableCard key={app.id} app={app} actions={actions} />)}
          </div>
        </section>
      )}
    </div>
  );
};

/* ---------- Fiche d'une app ---------- */

const Info: React.FC<{ label: string; children: React.ReactNode; mono?: boolean }> = ({ label, children, mono }) => (
  <>
    <dt className="text-ink-subtle">{label}</dt>
    <dd className={`m-0 min-w-0 break-words ${mono ? 'font-mono text-[13px]' : ''}`}>{children}</dd>
  </>
);

const versionText = (app: DockApp) => {
  if (!app.version) return app.availableVersion ? `${app.availableVersion} disponible` : '—';
  if (app.update) return `${app.version} · ${app.availableVersion} disponible`;
  return app.availableVersion ? `${app.version} · à jour` : app.version;
};

export const AppPage: React.FC<{ app: DockApp; actions: Actions; pending: boolean }> = ({ app, actions, pending }) => {
  const team = React.useContext(TeamContext);
  React.useEffect(() => {
    if (app.isNew) api.seen([app.id]).catch(() => undefined);
  }, [app.id, app.isNew]);
  return (
    <div className="flex flex-col gap-6">
      <a href="#/" className="flex min-h-8 items-center gap-1.5 self-start text-sm text-ink-muted no-underline hover:text-ink">
        <IconBack /> Mes applications
      </a>

      <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface px-8 py-7">
        <div className="flex flex-wrap items-center gap-x-7 gap-y-5">
          <span className="rounded-[22px] shadow-[0_10px_22px_-10px_rgba(27,29,42,0.4)]"><AppIcon app={app} size={96} /></span>
          <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="m-0 text-[34px] font-bold leading-tight text-ink">{app.name}</h1>
              <StatusChip app={app} />
            </div>
            {app.tagline && <p className="m-0 text-[17px] text-ink-muted">{app.tagline}</p>}
          </div>
          <AppActions app={app} actions={actions} pending={pending} wide />
        </div>
        <ProgressBar app={app} />
        <UpdateBanner app={app} actions={actions} />
        <AppNotice app={app} actions={actions} />
      </section>

      <div className="flex flex-wrap items-start gap-7">
        <div className="flex min-w-0 flex-[999_1_560px] flex-col gap-7">
          {(app.description || app.points.length > 0) && (
            <section className="flex flex-col gap-3">
              <h2 className="m-0 text-[21px] font-bold text-ink">À quoi sert {app.name}</h2>
              {app.description && <p className="m-0 max-w-[720px] text-[15px] leading-relaxed text-ink-body">{app.description}</p>}
              {app.points.length > 0 && (
                <ul className="m-0 grid list-none gap-2.5 p-0" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>
                  {app.points.map((pt) => (
                    <li key={pt} className="flex gap-2.5 rounded-md border border-line bg-surface px-3.5 py-3 text-sm leading-[1.45] text-ink-body">
                      <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />{pt}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {app.tutorial.length > 0 && (
            <section className="flex flex-col gap-3">
              <h2 className="m-0 text-[21px] font-bold text-ink">Prise en main</h2>
              <ol className="m-0 flex list-none flex-col gap-2.5 p-0">
                {app.tutorial.map((step, i) => (
                  <li key={step.title} className="flex gap-3.5 rounded-md border border-line bg-surface px-4 py-3.5">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-bold text-accent-ink" aria-hidden="true">{i + 1}</span>
                    <div className="flex min-w-0 flex-col gap-0.5">
                      <span className="text-[15px] font-medium text-ink">{step.title}</span>
                      {step.text && <span className="text-sm text-ink-muted">{step.text}</span>}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>

        <aside className="flex min-w-0 flex-[1_1_300px] flex-col gap-4">
          <section className="rounded-lg border border-line bg-surface p-5">
            <h2 className="m-0 mb-3.5 text-[17px] font-bold text-ink">En bref</h2>
            <dl className="m-0 grid gap-x-4 gap-y-3 text-sm" style={{ gridTemplateColumns: '130px minmax(0, 1fr)' }}>
              <Info label="Version">{versionText(app)}</Info>
              <Info label="Intelligence artificielle">{app.ai ? 'Utilise votre connexion au modèle' : 'Aucune'}</Info>
              <Info label="Hors ligne">{app.ai ? 'Non, a besoin du modèle' : 'Oui, entièrement'}</Info>
              <Info label="S'ouvre dans">{app.kind === 'web' ? 'Votre navigateur' : 'Sa propre fenêtre'}</Info>
              {team && <Info label="Installation">{app.mode === 'auto' ? "Pour toute l'équipe" : 'Choisie par vous'}</Info>}
            </dl>
          </section>

          <details className="group rounded-lg border border-line bg-surface-2 px-5 py-3.5">
            <summary className="flex min-h-8 cursor-pointer list-none items-center justify-between gap-2 text-[15px] font-medium text-ink-body [&::-webkit-details-marker]:hidden">
              Détails techniques
              <IconChevron className="rotate-90 transition-transform group-open:-rotate-90" />
            </summary>
            <dl className="m-0 mt-3 grid gap-x-4 gap-y-2 text-sm" style={{ gridTemplateColumns: 'auto minmax(0, 1fr)' }}>
              <Info label="Type">{app.kind === 'web' ? 'App web locale' : 'App de bureau'}</Info>
              {app.kind === 'web' && <Info label="Adresse" mono>{where(app)}</Info>}
              {team && <Info label="Sur le partage" mono>{app.availableVersion ?? '—'}</Info>}
              <Info label="Emplacement" mono>{app.location ?? 'non installée'}</Info>
            </dl>
            <div className="mt-3.5 flex flex-wrap gap-2">
              {app.folder && (app.location || !team) && (
                <button type="button" onClick={() => actions.folder(app)}
                  className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
                  <IconFolder /> Afficher le dossier
                </button>
              )}
              <button type="button" onClick={() => actions.logs()}
                className="flex h-10 items-center rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
                Journaux
              </button>
              {team && app.installed && app.mode !== 'auto' && app.kind === 'web' && (
                <button type="button" onClick={() => actions.uninstall(app)}
                  className="flex h-10 items-center rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
                  Retirer de ce poste
                </button>
              )}
            </div>
          </details>

          {app.links.length > 0 && (
            <section className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-5 text-sm">
              <h2 className="m-0 mb-0.5 text-[17px] font-bold text-ink">Liens</h2>
              {app.links.map((l) => (
                <button key={l.url} type="button" onClick={() => actions.link(l.url)}
                  className="self-start border-0 bg-transparent p-0 text-left text-accent underline">{l.label}</button>
              ))}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
};

/* ---------- Réglages ---------- */

export const SettingsPage: React.FC<{ onSaved: () => void; openFolder: (name: 'home' | 'shared') => void; onRestart: (folder: string) => void }> = ({ onSaved, openFolder, onRestart }) => {
  const platform = React.useContext(PlatformContext);
  const [settings, setSettings] = React.useState<Settings | null>(null);
  const [value, setValue] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.settings().then((s) => { setSettings(s); setValue(s.shared_folder); }).catch(() => setMessage('Réglages illisibles.'));
  }, []);

  const save = async (folder: string) => {
    setBusy(true);
    setMessage(null);
    try {
      const s = await api.saveSettings(folder);
      setSettings(s);
      setValue(s.shared_folder);
      setMessage(!folder ? 'Dossier partagé retiré : Studio Dock utilise la liste locale.'
        : s.hasCatalogue ? 'Dossier partagé enregistré.' : 'Enregistré, mais le catalogue de l\'équipe est introuvable à cet endroit.');
      onSaved();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Enregistrement impossible.');
    } finally {
      setBusy(false);
    }
  };

  const choose = async () => {
    const { path } = await api.chooseFolder();
    if (path) {
      setValue(path);
      await save(path);
    }
  };

  const status = settings && settings.shared_folder
    ? settings.hasCatalogue ? { ok: true, text: 'Accessible, catalogue de l\'équipe trouvé.' }
      : settings.reachable ? { ok: false, text: 'Dossier accessible, mais sans catalogue.json.' }
        : { ok: false, text: 'Dossier inaccessible depuis ce poste (réseau, VPN, droits).' }
    : null;

  return (
    <div className="flex flex-col gap-7">
      <a href="#/" className="flex min-h-8 items-center gap-1.5 self-start text-sm text-ink-muted no-underline hover:text-ink">
        <IconBack /> Mes applications
      </a>
      <div className="flex flex-col gap-1.5">
        <h1 className="m-0 text-[30px] font-bold leading-tight text-ink">Réglages</h1>
        <p className="m-0 max-w-[680px] text-ink-muted">Où Studio Dock trouve les applications de l'équipe (dossier partagé), et où il les installe sur ce poste (votre dossier).</p>
      </div>

      <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
        <div className="flex flex-col gap-1">
          <h2 className="m-0 text-[19px] font-bold text-ink">Dossier partagé de l'équipe</h2>
          <p className="m-0 text-sm text-ink-muted">
            Contient <span className="font-mono">catalogue.json</span> et un sous-dossier par application, où sont déposées les nouvelles versions.
            Les apps n'y sont jamais lancées : elles sont copiées sur ce poste.
          </p>
        </div>
        <form className="flex flex-wrap gap-2.5" onSubmit={(e) => { e.preventDefault(); save(value.trim()); }}>
          <label htmlFor="partage" className="sr-only">Chemin du dossier partagé</label>
          <input id="partage" value={value} onChange={(e) => setValue(e.target.value)} placeholder={platform === 'mac' ? '/Volumes/Equipe UX' : '\\\\serveur\\Equipe UX  ou  Z:\\Equipe UX'}
            className="h-11 min-w-0 flex-[1_1_320px] rounded border border-line-strong bg-surface-2 px-3.5 font-mono text-sm text-ink focus:outline focus:outline-2 focus:outline-focus" />
          {settings?.canChooseFolder && (
            <button type="button" onClick={choose} disabled={busy}
              className="flex h-11 items-center gap-2 rounded border border-line-strong bg-surface px-4 font-medium text-ink-body hover:bg-surface-3">
              <IconFolder /> Choisir…
            </button>
          )}
          <button type="submit" disabled={busy || value.trim() === (settings?.shared_folder ?? '')}
            className="flex h-11 items-center gap-2 rounded border-0 bg-primary px-5 font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:bg-primary-disabled disabled:text-primary-on-disabled">
            {busy && <IconSpinner />} Enregistrer
          </button>
        </form>
        {status && (
          <p className={`m-0 flex items-center gap-2 text-sm ${status.ok ? 'text-success-text' : 'text-warning-text'}`}>
            {status.ok ? <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" /> : <IconAlert />} {status.text}
            {settings?.reachable && (
              <button type="button" onClick={() => openFolder('shared')} className="ml-1 border-0 bg-transparent p-0 text-accent underline">Ouvrir</button>
            )}
          </p>
        )}
        {message && <p role="status" className="m-0 text-sm text-ink-muted">{message}</p>}
        {settings?.shared_folder && (
          <button type="button" onClick={() => save('')} className="self-start border-0 bg-transparent p-0 text-sm text-ink-subtle underline">
            Ne plus utiliser de dossier partagé
          </button>
        )}
      </section>

      <OnlineSection settings={settings} onSaved={(s) => { setSettings(s); onSaved(); }} />

      <InstallSection settings={settings} platform={platform} openHome={() => openFolder('home')} onRestart={onRestart} />

      <section className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-line-strong bg-surface px-6 py-4">
        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-0.5">
          <h2 className="m-0 text-[17px] font-bold text-ink">Vous préparez le catalogue de l'équipe ?</h2>
          <p className="m-0 text-sm text-ink-muted">Versions, liens des dossiers en ligne et fichier <span className="font-mono">studio-dock-catalogue.zip</span> à mettre en ligne.</p>
        </div>
        <a href="#/catalogue" className="flex h-10 items-center rounded border border-line-strong bg-surface px-4 text-sm font-medium text-ink-body no-underline hover:bg-surface-3">
          Préparer le catalogue
        </a>
      </section>
    </div>
  );
};

/* ---------- Catalogue en ligne ---------- */

const OnlineSection: React.FC<{ settings: Settings | null; onSaved: (s: Settings) => void }> = ({ settings, onSaved }) => {
  const [value, setValue] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  React.useEffect(() => { if (settings) setValue(settings.catalogue_link); }, [settings?.catalogue_link]);
  const save = async () => {
    setBusy(true);
    setMessage(null);
    try {
      onSaved(await api.saveCatalogueLink(value.trim()));
      setMessage(value.trim() ? 'Lien enregistré.' : 'Lien retiré.');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Enregistrement impossible.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
      <div className="flex flex-col gap-1">
        <h2 className="m-0 text-[19px] font-bold text-ink">Catalogue en ligne de l'équipe</h2>
        <p className="m-0 text-sm text-ink-muted">
          Quand l'équipe n'a qu'un dossier en ligne (SharePoint, Teams), sans dossier partagé : le navigateur télécharge
          le catalogue et les applications, Studio Dock les récupère dans vos Téléchargements et les installe.
          Le lien est repris du catalogue dès le premier import.
        </p>
      </div>
      <form className="flex flex-wrap gap-2.5" onSubmit={(e) => { e.preventDefault(); save(); }}>
        <label htmlFor="lien-catalogue" className="sr-only">Lien du catalogue en ligne</label>
        <input id="lien-catalogue" value={value} onChange={(e) => setValue(e.target.value)} placeholder="https://entreprise.sharepoint.com/…"
          className="h-11 min-w-0 flex-[1_1_320px] rounded border border-line-strong bg-surface-2 px-3.5 font-mono text-sm text-ink focus:outline focus:outline-2 focus:outline-focus" />
        <button type="submit" disabled={busy || value.trim() === (settings?.catalogue_link ?? '')}
          className="flex h-11 items-center gap-2 rounded border-0 bg-primary px-5 font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:bg-primary-disabled disabled:text-primary-on-disabled">
          {busy && <IconSpinner />} Enregistrer
        </button>
      </form>
      {message && <p role="status" className="m-0 text-sm text-ink-muted">{message}</p>}
      {settings && (
        <p className="m-0 text-[13px] text-ink-subtle">Téléchargements surveillés : <span className="font-mono">{settings.downloads}</span></p>
      )}
    </section>
  );
};

/* ---------- Dossier d'installation ---------- */

const InstallSection: React.FC<{
  settings: Settings | null;
  platform: 'windows' | 'mac' | 'linux';
  openHome: () => void;
  onRestart: (folder: string) => void;
}> = ({ settings, platform, openHome, onRestart }) => {
  const [editing, setEditing] = React.useState(false);
  const install = settings?.install;
  const show = platform === 'mac' ? 'Afficher dans le Finder' : 'Afficher dans l\'Explorateur';

  if (!install?.available) {
    // Mac (ou développement) : emplacement fixe, affiché pour information
    return (
      <section className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-6">
        <div className="flex flex-col gap-1">
          <h2 className="m-0 text-[19px] font-bold text-ink">Emplacement des applications</h2>
          <p className="m-0 text-sm text-ink-muted">Les applications installées depuis le dossier partagé sont copiées ici, une par dossier, et lancées depuis cet endroit.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="min-w-0 flex-grow break-all rounded bg-surface-2 px-3.5 py-2.5 font-mono text-sm">{settings?.home ?? '…'}</span>
          <button type="button" onClick={openHome}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
            <IconFolder /> {show}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
      <div className="flex flex-col gap-1">
        <h2 className="m-0 text-[19px] font-bold text-ink">Votre dossier d'installation</h2>
        <p className="m-0 text-sm text-ink-muted">
          Le dossier de ce poste où sont installés Studio Dock et vos applications (une par dossier), et d'où elles sont lancées.
          Propre à chaque membre de l'équipe, distinct du dossier partagé.
        </p>
      </div>
      {!editing ? (
        <div className="flex flex-wrap items-center gap-3">
          <span className="min-w-0 flex-grow break-all rounded bg-surface-2 px-3.5 py-2.5 font-mono text-sm">{install.folder ?? '…'}</span>
          <button type="button" onClick={openHome}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
            <IconFolder /> {show}
          </button>
          <button type="button" onClick={() => setEditing(true)}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
            Changer de dossier
          </button>
        </div>
      ) : (
        <>
          <p className="m-0 flex items-start gap-2 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
            <IconAlert className="mt-0.5 shrink-0" />
            Studio Dock et vos applications installées seront déplacés dans le nouveau dossier, puis Studio Dock redémarrera.
            Les applications lancées seront arrêtées.
          </p>
          <InstallFolderForm initial={install.folder ?? install.suggested} canChoose={!!settings?.canChooseFolder}
            submitLabel="Déplacer ici" onRestart={onRestart} onCancel={() => setEditing(false)} current={install.folder} />
        </>
      )}
    </section>
  );
};
