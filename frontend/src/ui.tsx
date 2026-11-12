import React from 'react';
import type { DockApp } from './types';
import logoDock from './assets/studiodock.svg';

/* ---------- Icônes (traits, couleur du texte) ---------- */

type IconProps = { size?: number; className?: string };
const stroke = (size: number, className: string | undefined, children: React.ReactNode) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}>{children}</svg>
);
export const IconPlay = ({ size = 14, className }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className={className}>
    <path d="M7 4.5v15a1 1 0 0 0 1.5.9l12-7.5a1 1 0 0 0 0-1.7l-12-7.5A1 1 0 0 0 7 4.5z" />
  </svg>
);
export const IconStop = ({ size = 14, className }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className={className}>
    <rect x="6" y="6" width="12" height="12" rx="2" />
  </svg>
);
export const IconRefresh = ({ size = 16, className }: IconProps) =>
  stroke(size, className, <><path d="M21 12a9 9 0 1 1-3-6.7L21 8" /><path d="M21 3v5h-5" /></>);
export const IconExternal = ({ size = 16, className }: IconProps) =>
  stroke(size, className, <><path d="M14 4h6v6" /><path d="M20 4l-9 9" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>);
export const IconWindow = ({ size = 16, className }: IconProps) =>
  stroke(size, className, <><rect x="3" y="4" width="18" height="15" rx="2" /><path d="M3 9h18" /></>);
export const IconFolder = ({ size = 16, className }: IconProps) =>
  stroke(size, className, <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />);
export const IconDownload = ({ size = 16, className }: IconProps) =>
  stroke(size, className, <><path d="M12 3v12M7 10l5 5 5-5" /><path d="M5 21h14" /></>);
export const IconChevron = ({ size = 14, className }: IconProps) => stroke(size, className, <path d="M9 6l6 6-6 6" />);
export const IconBack = ({ size = 16, className }: IconProps) => stroke(size, className, <path d="M15 18l-6-6 6-6" />);
export const IconAlert = ({ size = 16, className }: IconProps) =>
  stroke(size, className, <><path d="M12 3l9.5 17h-19z" /><path d="M12 10v4M12 17h.01" /></>);
export const IconSpinner = ({ size = 16 }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"
    strokeLinecap="round" aria-hidden="true" className="sd-spin">
    <path d="M12 3a9 9 0 1 1-9 9" />
  </svg>
);
export const DockLogo = ({ size = 36 }: { size?: number }) => (
  <span className="block shrink-0 shadow-[0_0_0_1px_var(--nn-line-strong),0_4px_10px_-4px_rgba(15,29,150,0.35)]"
    style={{ width: size, height: size, borderRadius: Math.round(size / 4) }}>
    <img src={logoDock} alt="" width={size} height={size} className="block" />
  </span>
);

/* ---------- Thème ---------- */

type Theme = 'light' | 'dark';
declare global {
  interface Window {
    /** Posé par night-navy/theme-toggle (importé dans main.tsx). */
    NightNavy?: { current: () => Theme; set: (theme: Theme | null) => void; toggle: () => void };
  }
}

export const ThemeToggle: React.FC = () => {
  const [theme, setTheme] = React.useState<Theme>(() => window.NightNavy?.current() ?? 'light');
  React.useEffect(() => {
    const sync = () => setTheme(window.NightNavy?.current() ?? 'light');
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    document.documentElement.addEventListener('nn-themechange', sync);
    media?.addEventListener('change', sync);
    return () => {
      document.documentElement.removeEventListener('nn-themechange', sync);
      media?.removeEventListener('change', sync);
    };
  }, []);
  const label = theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre';
  return (
    <button type="button" onClick={() => window.NightNavy?.toggle()} aria-label={label} title={label}
      className="flex h-10 w-10 items-center justify-center rounded border border-line-strong bg-surface text-ink-body hover:bg-surface-3">
      {theme === 'dark'
        ? stroke(18, undefined, <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>)
        : stroke(18, undefined, <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />)}
    </button>
  );
};

export const Header: React.FC = () => (
  <header className="sticky top-0 z-30 border-b border-line bg-surface">
    <div className="mx-auto flex min-h-[72px] max-w-[1200px] items-center gap-3 px-6">
      <a href="#/" className="flex flex-grow items-center gap-3 no-underline">
        <DockLogo />
        <span className="text-lg font-bold leading-tight text-ink">Studio Dock</span>
      </a>
      <a href="#/reglages" aria-label="Réglages de Studio Dock" title="Réglages"
        className="flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body no-underline hover:bg-surface-3">
        {stroke(16, undefined, <><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></>)}
        <span className="hidden sm:inline">Réglages</span>
      </a>
      <ThemeToggle />
    </div>
  </header>
);

/* ---------- Réglages : mon espace / l'équipe ---------- */

/** Onglets des réglages : ce qui ne concerne que ce poste, et ce qui est préparé pour toute l'équipe. */
export const SettingsTabs: React.FC<{ current: 'perso' | 'equipe' }> = ({ current }) => {
  const tab = (id: 'perso' | 'equipe', href: string, label: string, hint: string) => (
    <a href={href} aria-current={current === id ? 'page' : undefined}
      className={`flex min-h-11 flex-col justify-center rounded border px-4 py-1.5 no-underline ${current === id
        ? 'border-line-strong bg-surface text-ink' : 'border-transparent text-ink-muted hover:text-ink'}`}>
      <span className="text-sm font-semibold">{label}</span>
      <span className="text-[12px] text-ink-subtle">{hint}</span>
    </a>
  );
  return (
    <nav aria-label="Réglages" className="flex flex-wrap gap-1 self-start rounded-md border border-line bg-surface-2 p-1">
      {tab('perso', '#/reglages', 'Mon espace', 'Ce poste uniquement')}
      {tab('equipe', '#/catalogue', 'Préparer pour l\'équipe', 'Publié pour tous')}
    </nav>
  );
};

/** Rappelle la portée de ce qui est modifié sur la page. */
export const ScopeNote: React.FC<{ scope: 'perso' | 'equipe' }> = ({ scope }) => (
  scope === 'perso' ? (
    <p className="m-0 flex items-start gap-2.5 rounded-md border border-line bg-surface px-4 py-3 text-sm text-ink-body">
      {stroke(18, 'mt-0.5 shrink-0', <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></>)}
      <span><strong className="font-semibold text-ink">Réglages personnels.</strong> Ils ne concernent que ce poste et ne changent rien pour vos collègues.</span>
    </p>
  ) : (
    <p className="m-0 flex items-start gap-2.5 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
      {stroke(18, 'mt-0.5 shrink-0', <><circle cx="9" cy="8" r="3" /><path d="M3 20a6 6 0 0 1 12 0" /><circle cx="17" cy="9" r="2.5" /><path d="M15.5 14.2A5 5 0 0 1 21 19" /></>)}
      <span><strong className="font-semibold">Pour toute l'équipe.</strong> Le catalogue fabriqué ici est celui que vos collègues recevront
        dès que vous mettrez <span className="font-mono">studio-dock-catalogue.zip</span> en ligne. Rien n'est envoyé automatiquement.</span>
    </p>
  )
);

/* ---------- Pièces communes à la carte et à la fiche ---------- */

/** Système du poste (renvoyé par l'API) : adapte les noms de fichiers dans les messages. */
export const PlatformContext = React.createContext<'windows' | 'mac' | 'linux'>('windows');
/** Catalogue d'équipe (dossier partagé) ou liste locale : change les messages et les actions possibles. */
export const TeamContext = React.createContext<boolean>(false);

export const AppIcon: React.FC<{ app: DockApp; size: number }> = ({ app, size }) => {
  const logo = app.icon.style === 'logo';
  return (
    <span className={`flex shrink-0 items-center justify-center overflow-hidden ${logo ? '' : 'bg-accent-soft text-accent-ink'}`}
      style={{ width: size, height: size, borderRadius: Math.round(size / 4) }}>
      {app.iconUrl ? (
        <img src={app.iconUrl} alt="" width={logo ? size : size / 2} height={logo ? size : size / 2} className="block" />
      ) : (
        <span className="font-bold" style={{ fontSize: size / 2.4 }} aria-hidden="true">{app.name.slice(0, 1)}</span>
      )}
    </span>
  );
};

/** État d'une app en langage courant (les détails techniques sont dans la fiche). */
export const statusText = (app: DockApp): string => {
  if (app.progress !== null) return app.installed ? `Mise à jour… ${app.progress} %` : `Installation… ${app.progress} %`;
  if (app.waiting) return 'Téléchargement attendu…';
  switch (app.state) {
    case 'on': return app.external ? 'Ouverte hors de Studio Dock' : 'Ouverte';
    case 'starting': return 'Démarrage…';
    case 'off': return app.update ? 'Mise à jour disponible' : 'Prête';
    case 'missing': return app.availableVersion || app.kind === 'native' ? 'À installer' : 'Introuvable';
    case 'error': return app.error?.code === 'port_busy' ? 'Impossible de lancer' : 'Erreur au lancement';
  }
};

const dotClass = (app: DockApp) =>
  app.state === 'on' ? 'bg-success'
    : app.state === 'starting' || app.progress !== null || app.waiting ? 'bg-warning'
      : app.state === 'error' ? 'bg-danger'
        : app.update ? 'bg-accent' : 'bg-line-dashed';
const statusClass = (app: DockApp) =>
  app.state === 'on' ? 'text-success-text'
    : app.state === 'starting' || app.progress !== null || app.waiting ? 'text-warning-text'
      : app.state === 'error' ? 'text-danger-text'
        : app.update ? 'text-accent-ink' : 'text-ink-subtle';

export const where = (app: DockApp) => (app.kind === 'web' ? `localhost:${app.port}` : 'Application de bureau');

export const StatusLine: React.FC<{ app: DockApp }> = ({ app }) => (
  <div className="flex min-w-0 items-center gap-2 text-[13px]">
    <span className={`h-2 w-2 shrink-0 rounded-full ${dotClass(app)}`} aria-hidden="true" />
    <span className={`clamp-1 font-medium ${statusClass(app)}`}>{statusText(app)}</span>
  </div>
);

/** Pastille d'état (fiche d'une app). */
export const StatusChip: React.FC<{ app: DockApp }> = ({ app }) => {
  const on = app.state === 'on';
  return (
    <span className={`inline-flex h-7 items-center gap-2 rounded-full px-3 text-[13px] font-medium ${on ? 'bg-success-soft text-success-text' : 'border border-line bg-surface-2'}`}>
      <span className={`h-2 w-2 rounded-full ${dotClass(app)}`} aria-hidden="true" />
      <span className={on ? '' : statusClass(app)}>{statusText(app)}</span>
    </span>
  );
};

export type Actions = {
  launch: (app: DockApp) => void;
  stop: (app: DockApp) => void;
  open: (app: DockApp) => void;
  dismiss: (app: DockApp) => void;
  folder: (app: DockApp) => void;
  logs: () => void;
  link: (url: string) => void;
  install: (app: DockApp) => void;
  uninstall: (app: DockApp) => void;
  cancelDownload: (app: DockApp) => void;
};

const btnPrimary = 'flex h-11 items-center justify-center gap-2 rounded border-0 bg-primary px-5 font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:opacity-60 disabled:hover:bg-primary';
const btnInk = 'flex h-11 min-w-0 flex-1 items-center justify-center gap-2 whitespace-nowrap rounded border-0 bg-ink px-5 font-medium text-surface hover:opacity-90';
const btnGhost = 'flex h-11 min-w-0 items-center justify-center gap-2 whitespace-nowrap rounded border border-line-strong bg-surface px-4 font-medium text-ink-body hover:bg-surface-3';

/** Petit bouton « mettre à jour » à côté de l'action principale d'une carte. */
export const UpdateButton: React.FC<{ app: DockApp; actions: Actions }> = ({ app, actions }) =>
  !app.update || app.progress !== null || app.state === 'starting' || app.waiting ? null : (
    <button type="button" onClick={() => actions.install(app)}
      aria-label={`Mettre à jour ${app.name} en version ${app.availableVersion}${app.state === 'on' ? ' (l\'app sera arrêtée)' : ''}`}
      title={`Mettre à jour en ${app.availableVersion}`}
      className="flex h-11 shrink-0 items-center gap-1.5 whitespace-nowrap rounded border border-line-strong bg-surface px-3 text-sm font-medium text-accent-ink hover:bg-surface-3">
      <IconRefresh /> {app.availableVersion}
    </button>
  );

export const ProgressBar: React.FC<{ app: DockApp }> = ({ app }) =>
  app.progress === null ? null : (
    <div role="progressbar" aria-label={`Installation de ${app.name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={app.progress}
      className="h-2 overflow-hidden rounded-full bg-line">
      <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${app.progress}%` }} />
    </div>
  );

/** Bandeau « nouvelle version » : la version déposée sur le partage est plus récente que celle installée. */
export const UpdateBanner: React.FC<{ app: DockApp; actions: Actions }> = ({ app, actions }) =>
  !app.update || app.progress !== null ? null : (
    <div className="flex items-center gap-2.5 rounded-md border border-warning-line bg-warning-soft px-3 py-2 text-[13px] text-warning-text">
      <IconDownload className="shrink-0" />
      <span className="flex-grow">Version {app.availableVersion} disponible{app.state === 'on' ? ' (l\'app sera arrêtée)' : ''}</span>
      <button type="button" onClick={() => actions.install(app)} className="shrink-0 whitespace-nowrap border-0 bg-transparent p-0 font-medium text-warning-text underline">Mettre à jour</button>
    </div>
  );

/** Message sous la carte : app introuvable, copie impossible ou erreur au lancement. */
export const AppNotice: React.FC<{ app: DockApp; actions: Actions; compact?: boolean }> = ({ app, actions, compact }) => {
  const platform = React.useContext(PlatformContext);
  const team = React.useContext(TeamContext);
  if (app.installError) {
    return (
      <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-soft px-3 py-2 text-[13px] text-danger-text">
        <IconAlert className="mt-0.5 shrink-0" />
        <span className="flex-grow">{app.installError}</span>
        <button type="button" onClick={() => actions.dismiss(app)} className="border-0 bg-transparent p-0 font-medium text-danger-text underline">Masquer</button>
      </div>
    );
  }
  if (app.state === 'error' && app.error) {
    return (
      <div role="alert" className="flex flex-col gap-2 rounded-md bg-danger-soft px-3 py-2 text-[13px] text-danger-text">
        <div className="flex items-start gap-2">
          <IconAlert className="mt-0.5 shrink-0" />
          <span className="whitespace-pre-line">
            {app.error.message}
            {app.error.code === 'port_busy' ? ' Fermez-la, puis réessayez.' : ''}
          </span>
        </div>
        <div className="flex gap-3 pl-6 font-medium">
          <button type="button" onClick={() => actions.logs()} className="border-0 bg-transparent p-0 text-danger-text underline">Journal</button>
          <button type="button" onClick={() => actions.dismiss(app)} className="border-0 bg-transparent p-0 text-danger-text underline">Masquer</button>
        </div>
      </div>
    );
  }
  if (compact) return null; // carte : les explications sont dans la fiche
  if (app.state === 'missing' && team && app.progress === null && !app.availableVersion) {
    return (
      <div className="flex items-start gap-2 rounded-md border border-line bg-surface-2 px-3 py-2 text-[13px] text-ink-muted">
        <IconFolder className="mt-0.5 shrink-0" />
        <span>Pas encore de version disponible pour l'équipe.</span>
      </div>
    );
  }
  if (app.state === 'missing' && app.kind === 'web' && !team) {
    return (
      <div className="flex items-start gap-2 rounded-md border border-line bg-surface-2 px-3 py-2 text-[13px] text-ink-muted">
        <IconFolder className="mt-0.5 shrink-0" />
        {platform === 'windows' ? (
          <span>Déposez <span className="font-mono">{app.exe}.exe</span> (ou <span className="font-mono">{app.exe}-X.Y.Z.exe</span>) dans le dossier de l'app.</span>
        ) : (
          <span>Déposez la version Mac de <span className="font-mono">{app.exe}</span> (ou <span className="font-mono">{app.exe}-X.Y.Z</span>) dans le dossier de l'app.</span>
        )}
      </div>
    );
  }
  return null;
};

/** Boutons selon l'état et le type d'app. */
/** Catalogue en ligne : téléchargement demandé, en attente dans Téléchargements. */
export const WaitingActions: React.FC<{ app: DockApp; actions: Actions; wide?: boolean }> = ({ app, actions, wide }) => (
  <div className={`flex min-w-0 flex-col gap-2 ${wide ? 'min-w-[260px]' : 'flex-1'}`}>
    <div role="status" className="flex items-start gap-2 rounded-md bg-accent-soft px-3 py-2.5 text-[13px] leading-snug text-accent-ink">
      <span className="mt-0.5 shrink-0"><IconSpinner /></span>
      <span>Téléchargez {app.name} dans la page qui s'est ouverte : Studio Dock l'installe dès qu'il arrive dans vos Téléchargements.</span>
    </div>
    <div className="flex gap-2">
      <button type="button" onClick={() => actions.install(app)} className={`${btnGhost} h-9 flex-1 px-3 text-sm`}>
        <IconExternal /> Rouvrir la page
      </button>
      <button type="button" onClick={() => actions.cancelDownload(app)} className={`${btnGhost} h-9 px-3 text-sm`}>Annuler</button>
    </div>
  </div>
);

export const AppActions: React.FC<{ app: DockApp; actions: Actions; pending: boolean; wide?: boolean }> = ({ app, actions, pending, wide }) => {
  const team = React.useContext(TeamContext);
  const fill = wide ? 'min-w-[170px]' : 'min-w-0 flex-1';
  if (app.waiting && app.progress === null) return <WaitingActions app={app} actions={actions} wide={wide} />;
  if (app.progress !== null) {
    return (
      <button type="button" disabled className={`${btnPrimary} ${fill}`}>
        <IconSpinner /> {app.installed ? 'Mise à jour…' : 'Installation…'}
      </button>
    );
  }
  if (app.state === 'starting' || pending) {
    return (
      <button type="button" disabled className={`${btnPrimary} ${fill}`}>
        <IconSpinner />{app.state === 'on' ? 'Patientez…' : 'Démarrage…'}
      </button>
    );
  }
  if (app.state === 'on' && app.kind === 'web') {
    return (
      <div className={`flex gap-2 ${wide ? '' : 'min-w-0 flex-1'}`}>
        <button type="button" onClick={() => actions.open(app)} className={btnInk} aria-label={`Ouvrir ${app.name} dans le navigateur`}>
          <IconExternal /> Ouvrir
        </button>
        {wide ? (
          <button type="button" onClick={() => actions.stop(app)} className={`${btnGhost} flex-1`}>
            <IconStop /> Arrêter
          </button>
        ) : (
          <button type="button" onClick={() => actions.stop(app)} aria-label={`Arrêter ${app.name}`} title="Arrêter"
            className={`${btnGhost} w-11 shrink-0 px-0`}>
            <IconStop size={16} />
          </button>
        )}
      </div>
    );
  }
  if (app.state === 'on') {
    return (
      <button type="button" onClick={() => actions.open(app)} className={`${btnInk} ${fill} flex-none`} aria-label={`Afficher la fenêtre de ${app.name}`}>
        <IconWindow /> Afficher
      </button>
    );
  }
  if (app.state === 'missing' && app.availableVersion) {
    return (
      <button type="button" onClick={() => actions.install(app)} className={`${btnPrimary} ${fill}`}>
        <IconDownload /> Installer
      </button>
    );
  }
  if (app.state === 'missing') {
    if (app.kind === 'native') {
      const link = app.links[0];
      return link ? (
        <button type="button" onClick={() => actions.link(link.url)} className={`${btnPrimary} ${fill}`}>
          <IconDownload /> Télécharger
        </button>
      ) : null;
    }
    if (team) return null;
    return (
      <button type="button" onClick={() => actions.folder(app)} className={`${btnGhost} ${fill}`}>
        <IconFolder /> Ouvrir le dossier
      </button>
    );
  }
  return (
    <button type="button" onClick={() => actions.launch(app)} className={`${btnPrimary} ${fill}`}>
      <IconPlay /> {app.state === 'error' ? 'Réessayer' : 'Lancer'}
    </button>
  );
};
