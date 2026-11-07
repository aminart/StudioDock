import React from 'react';
import type { DockApp } from './types';

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
  <span className="flex shrink-0 items-center justify-center rounded-md bg-primary" style={{ width: size, height: size }}>
    <svg width={size / 2} height={size / 2} viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
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
  <header className="border-b border-line bg-surface">
    <div className="mx-auto flex max-w-[1120px] items-center gap-4 px-6 py-3.5">
      <a href="#/" className="flex flex-grow items-center gap-3 no-underline">
        <DockLogo />
        <span className="text-[17px] font-bold leading-tight text-ink">Studio Dock</span>
      </a>
      <ThemeToggle />
    </div>
  </header>
);

/* ---------- Pièces communes à la carte et à la fiche ---------- */

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

const statusText = (app: DockApp): string => {
  switch (app.state) {
    case 'on': return 'En cours';
    case 'starting': return 'Démarrage…';
    case 'off': return 'Arrêtée';
    case 'missing': return app.kind === 'native' ? 'Non installée' : 'Introuvable';
    case 'error': return app.error?.code === 'port_busy' ? 'Impossible de lancer' : 'Erreur';
  }
};

const dotClass = (app: DockApp) =>
  app.state === 'on' ? 'bg-success' : app.state === 'starting' ? 'bg-warning' : app.state === 'error' ? 'bg-danger' : 'bg-line-dashed';
const statusClass = (app: DockApp) =>
  app.state === 'on' ? 'text-success-text' : app.state === 'starting' ? 'text-warning-text' : app.state === 'error' ? 'text-danger-text' : 'text-ink-subtle';

export const where = (app: DockApp) => (app.kind === 'web' ? `localhost:${app.port}` : 'Application de bureau');

export const StatusLine: React.FC<{ app: DockApp }> = ({ app }) => (
  <div className="flex min-w-0 items-center gap-2 text-[13px] text-ink-subtle">
    <span className={`h-2 w-2 shrink-0 rounded-full ${dotClass(app)}`} aria-hidden="true" />
    <span className={`whitespace-nowrap font-medium ${statusClass(app)}`}>{statusText(app)}</span>
    <span className="clamp-1 font-mono">· {where(app)}{app.external && app.state === 'on' ? ' · lancée hors de Studio Dock' : ''}</span>
  </div>
);

export type Actions = {
  launch: (app: DockApp) => void;
  stop: (app: DockApp) => void;
  open: (app: DockApp) => void;
  dismiss: (app: DockApp) => void;
  folder: (app: DockApp) => void;
  logs: () => void;
  link: (url: string) => void;
};

const btnPrimary = 'flex h-11 items-center justify-center gap-2 rounded border-0 bg-primary px-5 font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:opacity-60 disabled:hover:bg-primary';
const btnInk = 'flex h-11 min-w-0 flex-1 items-center justify-center gap-2 whitespace-nowrap rounded border-0 bg-ink px-5 font-medium text-surface hover:opacity-90';
const btnGhost = 'flex h-11 min-w-0 items-center justify-center gap-2 whitespace-nowrap rounded border border-line-strong bg-surface px-4 font-medium text-ink-body hover:bg-surface-3';

/** Message sous la carte : app introuvable ou erreur au lancement. */
export const AppNotice: React.FC<{ app: DockApp; actions: Actions }> = ({ app, actions }) => {
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
  if (app.state === 'missing' && app.kind === 'web') {
    return (
      <div className="flex items-start gap-2 rounded-md border border-line bg-surface-2 px-3 py-2 text-[13px] text-ink-muted">
        <IconFolder className="mt-0.5 shrink-0" />
        <span>Déposez <span className="font-mono">{app.exe}.exe</span> (ou <span className="font-mono">{app.exe}-X.Y.Z.exe</span>) dans le dossier de l'app.</span>
      </div>
    );
  }
  return null;
};

/** Boutons selon l'état et le type d'app. */
export const AppActions: React.FC<{ app: DockApp; actions: Actions; pending: boolean; wide?: boolean }> = ({ app, actions, pending, wide }) => {
  const fill = wide ? 'min-w-[170px]' : 'w-full';
  if (app.state === 'starting' || pending) {
    return (
      <button type="button" disabled className={`${btnPrimary} ${fill}`}>
        <IconSpinner />{app.state === 'on' ? 'Patientez…' : 'Démarrage…'}
      </button>
    );
  }
  if (app.state === 'on' && app.kind === 'web') {
    return (
      <div className={`flex gap-2.5 ${wide ? '' : 'w-full'}`}>
        <button type="button" onClick={() => actions.open(app)} className={btnInk} aria-label={`Ouvrir ${app.name} dans le navigateur`}>
          Ouvrir <IconExternal />
        </button>
        <button type="button" onClick={() => actions.stop(app)} className={`${btnGhost} flex-1`}>
          <IconStop /> Arrêter
        </button>
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
  if (app.state === 'missing') {
    if (app.kind === 'native') {
      const link = app.links[0];
      return link ? (
        <button type="button" onClick={() => actions.link(link.url)} className={`${btnPrimary} ${fill}`}>
          <IconDownload /> Télécharger
        </button>
      ) : null;
    }
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
