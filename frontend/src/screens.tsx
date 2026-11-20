import React from 'react';
import { api, iaApi } from './api';
import { InstallFolderForm } from './install';
import type { DockApp, DockState, Settings } from './types';
import {
  Actions, AppActions, AppIcon, AppNotice, IconAlert, IconBack, IconChevron, IconDownload, IconExternal, IconFolder, IconRefresh, IconSpinner,
  PlatformContext, ProgressBar, ScopeNote, SectionTitle, SettingsTabs, StatusChip, StatusLine, TeamContext, UpdateButton, shortPath, WaitingActions, where,
} from './ui';

/** Où s'ouvre l'app, en mots courants. */
const kindText = (app: DockApp, platform: string) =>
  app.kind === 'web' ? 's\'ouvre dans le navigateur' : platform === 'mac' ? 'application Mac' : 'application Windows';

const capitalize = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** Mes applications : installées sur ce poste, ou imposées à l'équipe (installation en cours ou en attente). */
export const isMine = (app: DockApp, team: boolean) => !team || app.installed || app.mode === 'auto';

/* ---------- Menu « ⋯ » d'une carte ---------- */

const CardMenu: React.FC<{ app: DockApp; actions: Actions }> = ({ app, actions }) => {
  const team = React.useContext(TeamContext);
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  const trigger = React.useRef<HTMLButtonElement>(null);
  const menu = React.useRef<HTMLDivElement>(null);
  const items = () => Array.from(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
  // Fermer en rendant le focus au bouton ⋮ (sauf clic ailleurs : le focus suit le clic)
  const close = (refocus = true) => { setOpen(false); if (refocus) trigger.current?.focus(); };
  React.useEffect(() => {
    if (!open) return;
    items()[0]?.focus();
    const outside = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', outside);
    return () => document.removeEventListener('mousedown', outside);
  }, [open]);
  // Flèches haut et bas, Début, Fin, Échap et Tab, comme un menu
  const onKey = (e: React.KeyboardEvent) => {
    const list = items();
    const i = list.indexOf(document.activeElement as HTMLElement);
    const go = (n: number) => { e.preventDefault(); list[(n + list.length) % list.length]?.focus(); };
    if (e.key === 'ArrowDown') go(i + 1);
    else if (e.key === 'ArrowUp') go(i - 1);
    else if (e.key === 'Home') go(0);
    else if (e.key === 'End') go(list.length - 1);
    else if (e.key === 'Escape') { e.preventDefault(); close(); }
    else if (e.key === 'Tab') setOpen(false);
  };
  const openWith = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); setOpen(true); }
  };
  const item = 'flex min-h-10 w-full items-center gap-2.5 rounded-sm border-0 bg-transparent px-3 text-left text-sm text-ink-body hover:bg-surface-3';
  const removable = team && app.installed;
  return (
    <div ref={ref} data-tour="menu" className="relative -mr-2 -mt-1.5">
      <button ref={trigger} type="button" onClick={() => setOpen(!open)} onKeyDown={openWith} aria-label={`Plus d'actions pour ${app.name}`} aria-haspopup="menu" aria-expanded={open}
        className="flex h-9 w-9 items-center justify-center rounded border-0 bg-transparent text-ink-subtle hover:bg-surface-3 hover:text-ink">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="5" r="1.8" /><circle cx="12" cy="12" r="1.8" /><circle cx="12" cy="19" r="1.8" /></svg>
      </button>
      {open && (
        <div ref={menu} role="menu" aria-label={`Actions pour ${app.name}`} onKeyDown={onKey} className="absolute right-0 top-10 z-10 flex min-w-[250px] flex-col rounded-md border border-line-strong bg-surface p-1.5 shadow-lg">
          <a role="menuitem" tabIndex={-1} href={`#/app/${app.id}`} className={`${item} no-underline`}>Fiche et prise en main</a>
          {app.folder && (app.location || !team) && (
            <button type="button" role="menuitem" tabIndex={-1} className={item} onClick={() => { close(); actions.folder(app); }}>
              Afficher le dossier de l'app
            </button>
          )}
          {removable && (app.mode === 'auto' ? (
            <span role="menuitem" tabIndex={-1} aria-disabled="true" className="px-3 py-2 outline-offset-[-2px] text-[13px] text-ink-subtle">
              Installée pour toute l'équipe : ne peut pas être retirée
            </span>
          ) : app.kind === 'web' ? (
            <button type="button" role="menuitem" tabIndex={-1} className={item} onClick={() => { close(); actions.uninstall(app); }}>
              Retirer de ce poste
            </button>
          ) : (
            <span role="menuitem" tabIndex={-1} aria-disabled="true" className="px-3 py-2 outline-offset-[-2px] text-[13px] text-ink-subtle">
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
    <article data-tour="carte" className={`flex min-h-[268px] flex-col gap-4 rounded-lg p-[22px] ${on
      ? 'border-[1.5px] border-accent bg-gradient-to-b from-accent-softer to-surface'
      : 'border border-line bg-surface hover:border-line-strong'}`}>
      <div className="flex items-start justify-between">
        <a href={`#/app/${app.id}`} data-tour="fiche" aria-label={`Fiche de ${app.name}`} className="rounded-[13px] shadow-[0_6px_14px_-6px_rgba(27,29,42,0.35)]">
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
      <div data-tour="etat" className="flex flex-col gap-3">
        <StatusLine app={app} />
        <ProgressBar app={app} />
        <div className="flex gap-2">
          <AppActions app={app} actions={actions} pending={pending} />
        </div>
        <UpdateButton app={app} actions={actions} />
      </div>
    </article>
  );
};

/** Carte compacte d'une app proposée par l'équipe, pas encore installée sur ce poste. */
const AvailableCard: React.FC<{ app: DockApp; actions: Actions }> = ({ app, actions }) => {
  const platform = React.useContext(PlatformContext);
  return (
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
        <span className="min-w-0 flex-grow text-[13px] leading-snug text-ink-subtle">
          {app.availableVersion ? `Version ${app.availableVersion} · ${kindText(app, platform)}` : capitalize(kindText(app, platform))}
        </span>
        {app.availableVersion ? (
          <button type="button" onClick={() => actions.install(app)}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-4 font-medium text-accent hover:bg-surface-3">
            <IconDownload /> Installer
          </button>
        ) : (
          <span className="text-[13px] text-ink-subtle">Pas encore publiée</span>
        )}
      </div>
    )}
  </article>
  );
};

const grid = { gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' };
const gridAvailable = { gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))' };

/** Pastilles de résumé : apps ouvertes, mises à jour disponibles. */
const Summary: React.FC<{ apps: DockApp[] }> = ({ apps }) => {
  const on = apps.filter((a) => a.state === 'on').length;
  const updates = apps.filter((a) => a.update);
  if (!on && !updates.length) return null;
  // Amène à la première carte à mettre à jour, focus sur son bouton
  const goToUpdate = () => {
    const el = updates.map((a) => document.getElementById(`maj-${a.id}`)).find(Boolean);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.focus({ preventScroll: true });
  };
  return (
    <div data-tour="resume" className="flex flex-wrap gap-2">
      {on > 0 && (
        <span className="flex h-8 items-center gap-2 rounded-full bg-success-soft px-3 text-[13px] font-medium text-success-text">
          <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" />{on} {on > 1 ? 'apps ouvertes' : 'app ouverte'}
        </span>
      )}
      {updates.length > 0 && (
        <button type="button" onClick={goToUpdate}
          aria-label={`${updates.length} ${updates.length > 1 ? 'mises à jour disponibles' : 'mise à jour disponible'} : aller à ${updates.map((a) => a.name).join(', ')}`}
          className="flex h-8 items-center gap-2 rounded-full border border-transparent bg-accent-soft px-3 text-[13px] font-medium text-accent-ink hover:border-accent">
          <IconRefresh size={14} />{updates.length} {updates.length > 1 ? 'mises à jour' : 'mise à jour'} : {updates.map((a) => a.name).join(', ')}
        </button>
      )}
    </div>
  );
};

/** Apps proposées par l'équipe sans version publiée : une ligne, chaque nom mène à sa fiche. */
const Soon: React.FC<{ apps: DockApp[] }> = ({ apps }) => (
  <p className="m-0 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-ink-muted">
    <span>Bientôt dans l'équipe :</span>
    {apps.map((a, i) => (
      <span key={a.id} className="inline-flex items-center gap-1.5">
        <AppIcon app={a} size={20} />
        <a href={`#/app/${a.id}`} className="text-ink-body no-underline hover:underline">{a.name}</a>{i < apps.length - 1 ? ',' : ''}
      </span>
    ))}
  </p>
);

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
      <div data-tour="en-ligne" className="flex flex-col gap-3">
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
  const others = state.apps.filter((a) => !isMine(a, team));
  // Pas encore de version publiée : rien à faire, regroupées sur une ligne « Bientôt »
  const soon = others.filter((a) => !a.availableVersion && a.progress === null && !a.waiting);
  const available = others.filter((a) => !soon.includes(a));
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
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
        <section aria-labelledby="dispo" data-tour="dispo" className="mt-4 flex flex-col gap-4">
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
          {soon.length > 0 && <Soon apps={soon} />}
        </section>
      )}
      {available.length === 0 && soon.length > 0 && <Soon apps={soon} />}
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

/** Modèle d'IA utilisé par l'app (réglé dans Studio Dock), avec un lien pour le changer. */
const AiModel: React.FC<{ app: DockApp }> = ({ app }) => {
  const [text, setText] = React.useState<string | null>(null);
  React.useEffect(() => {
    iaApi.state().then((s) => {
      const choice = s.apps.find((a) => a.id === app.id)?.choice ?? s.default;
      if (choice && 'own' in choice) return setText('Réglé dans l\'app elle-même');
      const conn = choice && s.connections.find((c) => c.id === choice.connection);
      setText(conn && choice ? `${choice.model} (${conn.name})` : 'Aucun modèle réglé');
    }).catch(() => setText(null));
  }, [app.id]);
  return (
    <span className="flex flex-col gap-0.5">
      <span>{text ?? 'Le modèle réglé dans Studio Dock'}</span>
      <a href="#/ia" className="self-start text-accent no-underline hover:underline">Changer</a>
    </span>
  );
};

const versionText = (app: DockApp) => {
  if (!app.version) return app.availableVersion ? `${app.availableVersion} disponible` : '—';
  if (app.update) return `${app.version} (${app.availableVersion} disponible)`;
  return app.availableVersion ? `${app.version}, à jour` : app.version;
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
          <div className="flex flex-wrap gap-2">
            <AppActions app={app} actions={actions} pending={pending} wide />
            <UpdateButton app={app} actions={actions} wide />
          </div>
        </div>
        <ProgressBar app={app} />
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
              <Info label="Intelligence artificielle">{app.ai ? <AiModel app={app} /> : 'Aucune'}</Info>
              <Info label="Hors ligne">{app.ai ? 'Non, a besoin du modèle' : 'Oui, entièrement'}</Info>
              <Info label="S'ouvre dans">{app.kind === 'web' ? 'Votre navigateur' : 'Sa propre fenêtre'}</Info>
              {team && <Info label="Installation">{app.mode === 'auto' ? "Installée pour toute l'équipe" : 'Installée à votre demande'}</Info>}
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
              <button type="button" onClick={() => actions.logs(app)}
                className="flex h-10 items-center rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
                Signaler un problème
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
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.settings().then(setSettings).catch(() => setError('Réglages illisibles.'));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <a href="#/" className="flex min-h-8 items-center gap-1.5 self-start text-sm text-ink-muted no-underline hover:text-ink">
        <IconBack /> Mes applications
      </a>
      <h1 className="m-0 text-[30px] font-bold leading-tight text-ink">Réglages</h1>
      <SettingsTabs current="perso" />
      <ScopeNote scope="perso" />
      {error && <p role="alert" className="m-0 text-sm text-warning-text">{error}</p>}

      <InstallSection settings={settings} platform={platform} openHome={() => openFolder('home')} onRestart={onRestart} />

      <TeamSection settings={settings} platform={platform} openShared={() => openFolder('shared')}
        onSaved={(s) => { setSettings(s); onSaved(); }} />

      {settings && (
        <section aria-labelledby="avance-h" className="flex flex-col gap-3 rounded-lg border border-line bg-surface px-6 py-5">
          <h2 id="avance-h" className="m-0 text-[13px] font-semibold uppercase tracking-wide text-ink-subtle">Option avancée</h2>
          <label className="flex cursor-pointer items-start gap-3">
            <input type="checkbox" className="mt-1 h-4 w-4" checked={settings.catalogue_admin}
              onChange={async (e) => { setSettings(await api.saveCatalogueAdmin(e.target.checked)); onSaved(); }} />
            <span className="flex flex-col gap-0.5">
              <span className="text-[15px] font-semibold text-ink">Je gère le catalogue de l'équipe</span>
              <span className="text-sm text-ink-muted">Affiche l'onglet « Préparer pour l'équipe » : choisir les apps proposées à l'équipe et rédiger leur fiche. À laisser décoché si vous utilisez seulement les apps.</span>
            </span>
          </label>
        </section>
      )}

      <section aria-labelledby="aide-h" className="flex flex-col gap-2 rounded-lg bg-surface-2 px-6 py-5">
        <h2 id="aide-h" className="m-0 text-[15px] font-bold text-ink">Aide</h2>
        <span className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <a href="#/visite" className="text-accent no-underline hover:underline">Visite guidée de l'accueil</a>
          <a href="#/bienvenue" className="text-accent no-underline hover:underline">Revoir le tutoriel de première connexion</a>
        </span>
      </section>
    </div>
  );
};

/* ---------- Les applications de l'équipe : dossier réseau ou en ligne ---------- */

type Source = 'reseau' | 'en-ligne';

const sectionTitle = (n: number, title: string, subtitle: string) => <SectionTitle n={n} title={title} subtitle={subtitle} />;

const TeamSection: React.FC<{
  settings: Settings | null; platform: 'windows' | 'mac' | 'linux'; openShared: () => void; onSaved: (s: Settings) => void;
}> = ({ settings, platform, openShared, onSaved }) => {
  // Le dossier réseau passe avant le catalogue en ligne : c'est la source utilisée s'il est réglé
  const current: Source | null = settings?.shared_folder ? 'reseau' : settings?.catalogue_link ? 'en-ligne' : null;
  const [source, setSource] = React.useState<Source>('reseau');
  React.useEffect(() => { if (current) setSource(current); }, [current]);

  const option = (value: Source, label: string, hint: string) => (
    <label className={`flex flex-1 cursor-pointer items-start gap-3 rounded-md border px-4 py-3 ${source === value ? 'border-primary bg-surface' : 'border-line bg-surface-2 hover:border-line-strong'}`}>
      <input type="radio" name="source-equipe" className="mt-1" checked={source === value} onChange={() => setSource(value)} />
      <span className="flex flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-2 text-sm font-semibold text-ink">
          {label}
          {current === value && <span className="rounded-full bg-success-soft px-2 py-px text-[12px] font-medium text-success-text">utilisé</span>}
        </span>
        <span className="text-[13px] text-ink-muted">{hint}</span>
      </span>
    </label>
  );

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
      {sectionTitle(2, 'Les applications de l\'équipe', 'Où Studio Dock trouve les apps proposées par l\'équipe et leurs nouvelles versions. Il les copie ensuite dans votre dossier ci-dessus.')}
      <fieldset className="m-0 flex flex-col gap-2.5 border-0 p-0 sm:flex-row">
        <legend className="sr-only">Où se trouvent les applications de l'équipe</legend>
        {option('reseau', 'Dossier réseau Windows', 'Un lecteur réseau de l\'entreprise (par exemple Q:). Recommandé : mises à jour en un clic.')}
        {option('en-ligne', 'Dossier en ligne', 'SharePoint ou Teams, ouvert dans le navigateur avec votre compte de l\'entreprise.')}
      </fieldset>
      {source === 'reseau'
        ? <NetworkPanel settings={settings} platform={platform} openShared={openShared} onSaved={onSaved} />
        : <OnlinePanel settings={settings} onSaved={onSaved} />}
    </section>
  );
};

const fieldClass = 'h-11 min-w-0 flex-[1_1_320px] rounded border border-line-strong bg-surface-2 px-3.5 font-mono text-sm text-ink focus:outline focus:outline-2 focus:outline-focus';
const saveClass = 'flex h-11 items-center gap-2 rounded border-0 bg-primary px-5 font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:bg-primary-disabled disabled:text-primary-on-disabled';

export const NetworkPanel: React.FC<{
  settings: Settings | null; platform: 'windows' | 'mac' | 'linux'; openShared: () => void; onSaved: (s: Settings) => void;
}> = ({ settings, platform, openShared, onSaved }) => {
  const [value, setValue] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  React.useEffect(() => { if (settings) setValue(settings.shared_folder); }, [settings?.shared_folder]);

  const save = async (folder: string) => {
    setBusy(true);
    setMessage(null);
    try {
      const s = await api.saveSettings(folder);
      onSaved(s);
      setMessage(!folder ? 'Dossier réseau retiré.'
        : s.hasCatalogue ? 'Dossier réseau enregistré : les apps de l\'équipe viennent maintenant de ce dossier.'
          : 'Enregistré, mais le catalogue de l\'équipe est introuvable à cet endroit.');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Enregistrement impossible.');
    } finally {
      setBusy(false);
    }
  };
  const choose = async () => {
    const { path } = await api.chooseFolder();
    if (path) { setValue(path); await save(path); }
  };
  const status = settings?.shared_folder
    ? settings.hasCatalogue ? { ok: true, text: 'Accessible, catalogue de l\'équipe trouvé.' }
      : settings.reachable ? { ok: false, text: 'Dossier accessible, mais le catalogue de l\'équipe n\'y est pas.' }
        : { ok: false, text: 'Dossier inaccessible depuis ce poste (réseau, VPN, droits).' }
    : null;

  return (
    <div className="flex flex-col gap-3 border-t border-line pt-4">
      <p className="m-0 text-sm text-ink-body">
        Le dossier de l'équipe qui contient son catalogue et un sous-dossier par application.
        Les apps n'y sont jamais lancées : elles sont copiées sur ce poste.
      </p>
      <form className="flex flex-wrap gap-2.5" onSubmit={(e) => { e.preventDefault(); save(value.trim()); }}>
        <label htmlFor="partage" className="sr-only">Chemin du dossier réseau de l'équipe</label>
        <input id="partage" value={value} onChange={(e) => setValue(e.target.value)} className={fieldClass} aria-describedby="partage-exemple" />
        {settings?.canChooseFolder && (
          <button type="button" onClick={choose} disabled={busy}
            className="flex h-11 items-center gap-2 rounded border border-line-strong bg-surface px-4 font-medium text-ink-body hover:bg-surface-3">
            <IconFolder /> Choisir…
          </button>
        )}
        <button type="submit" disabled={busy || value.trim() === (settings?.shared_folder ?? '')} className={saveClass}>
          {busy && <IconSpinner />} Enregistrer
        </button>
      </form>
      <p id="partage-exemple" className="-mt-1 m-0 text-[13px] text-ink-muted">
        Par exemple <span className="font-mono">{platform === 'mac' ? '/Volumes/Equipe UX/Studio Dock' : 'Q:\\Studio Dock'}</span>
        {platform !== 'mac' && <> ou <span className="font-mono">{'\\\\serveur\\partage\\Studio Dock'}</span></>}.
      </p>
      {status && (
        <p className={`m-0 flex flex-wrap items-center gap-2 text-sm ${status.ok ? 'text-success-text' : 'text-warning-text'}`}>
          {status.ok ? <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" /> : <IconAlert />} {status.text}
          {settings?.reachable && <button type="button" onClick={openShared} className="border-0 bg-transparent p-0 text-accent underline">Ouvrir</button>}
        </p>
      )}
      {message && <p role="status" className="m-0 text-sm text-ink-muted">{message}</p>}
      {settings?.shared_folder && (
        <button type="button" onClick={() => save('')} disabled={busy} className="self-start border-0 bg-transparent p-0 text-sm text-accent underline">
          Ne plus utiliser de dossier réseau
        </button>
      )}
    </div>
  );
};

export const OnlinePanel: React.FC<{ settings: Settings | null; onSaved: (s: Settings) => void }> = ({ settings, onSaved }) => {
  const [value, setValue] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  React.useEffect(() => { if (settings) setValue(settings.catalogue_link); }, [settings?.catalogue_link]);
  const networkFirst = !!settings?.shared_folder;

  const save = async () => {
    setBusy(true);
    setMessage(null);
    try {
      let s = await api.saveCatalogueLink(value.trim());
      // Choisir le dossier en ligne : le dossier réseau, prioritaire, est retiré
      if (value.trim() && s.shared_folder) s = await api.saveSettings('');
      onSaved(s);
      setMessage(value.trim() ? 'Lien enregistré : les apps de l\'équipe viennent maintenant du dossier en ligne.' : 'Lien retiré.');
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Enregistrement impossible.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 border-t border-line pt-4">
      <p className="m-0 text-sm text-ink-body">
        Le lien du catalogue en ligne de l'équipe. Le navigateur télécharge le catalogue et les applications,
        Studio Dock les récupère dans vos Téléchargements et les installe sur ce poste. Le lien est repris du catalogue dès le premier import.
      </p>
      {networkFirst && (
        <p className="m-0 flex items-start gap-2 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
          <IconAlert className="mt-0.5 shrink-0" />
          Le dossier réseau est réglé et passe avant : enregistrer ce lien le retire, et les apps viendront du dossier en ligne.
        </p>
      )}
      <form className="flex flex-wrap gap-2.5" onSubmit={(e) => { e.preventDefault(); save(); }}>
        <label htmlFor="lien-catalogue" className="sr-only">Lien du catalogue en ligne</label>
        <input id="lien-catalogue" value={value} onChange={(e) => setValue(e.target.value)} className={fieldClass} aria-describedby="lien-exemple" />
        <button type="submit" disabled={busy || (value.trim() === (settings?.catalogue_link ?? '') && !(networkFirst && value.trim()))} className={saveClass}>
          {busy && <IconSpinner />} {networkFirst && value.trim() ? 'Utiliser le dossier en ligne' : 'Enregistrer'}
        </button>
      </form>
      <p id="lien-exemple" className="-mt-1 m-0 text-[13px] text-ink-muted">
        Le lien de partage du dossier, par exemple <span className="font-mono">https://entreprise.sharepoint.com/…</span>
      </p>
      {message && <p role="status" className="m-0 text-sm text-ink-muted">{message}</p>}
      {settings && <p className="m-0 text-[13px] text-ink-subtle">Téléchargements surveillés : <span className="font-mono" title={settings.downloads}>{shortPath(settings.downloads)}</span></p>}
    </div>
  );
};

const AppsHint: React.FC = () => (
  <p className="m-0 text-[13px] text-ink-muted">
    Chaque app a son propre dossier dans <span className="font-mono text-ink-body">apps</span>.
    Pour installer vous-même une version (sans l'équipe), déposez son exe dans le dossier de l'app ; Studio Dock lance la plus récente.
  </p>
);

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
        {sectionTitle(1, 'Mes applications', 'Sur ce poste : vos applications installées sont rangées ici, une par dossier, et lancées depuis cet endroit.')}
        <div className="flex flex-wrap items-center gap-3">
          <span title={settings?.home} className="min-w-0 flex-grow break-all rounded bg-surface-2 px-3.5 py-2.5 font-mono text-sm">{shortPath(settings?.home)}</span>
          <button type="button" onClick={openHome}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
            <IconFolder /> {show}
          </button>
        </div>
        <AppsHint />
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
      {sectionTitle(1, 'Mes applications', 'Le dossier de ce poste où sont installés Studio Dock et vos applications, et d\'où elles sont lancées. Il vous est propre : personne d\'autre n\'y écrit.')}
      {!editing ? (
        <div className="flex flex-wrap items-center gap-3">
          <span title={install.folder ?? undefined} className="min-w-0 flex-grow break-all rounded bg-surface-2 px-3.5 py-2.5 font-mono text-sm">{shortPath(install.folder)}</span>
          <button type="button" onClick={openHome}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
            <IconFolder /> {show}
          </button>
          <button type="button" onClick={() => setEditing(true)}
            className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
            Changer de dossier
          </button>
          <div className="basis-full"><AppsHint /></div>
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
