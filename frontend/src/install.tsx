import React from 'react';
import { ActionError, api } from './api';
import type { Settings } from './types';
import { DockLogo, IconAlert, IconFolder, IconSpinner } from './ui';

/** Champ « dossier d'installation » : saisie, sélecteur natif, bouton d'action. */
export const InstallFolderForm: React.FC<{
  initial: string;
  canChoose: boolean;
  submitLabel: string;
  onRestart: (folder: string) => void;
  onCancel?: () => void;
  /** Dossier actuel : le bouton reste inactif tant qu'il n'est pas changé. */
  current?: string | null;
}> = ({ initial, canChoose, submitLabel, onRestart, onCancel, current }) => {
  const [value, setValue] = React.useState(initial);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => setValue(initial), [initial]);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.installDock(value.trim());
      onRestart(r.folder);
    } catch (e) {
      setError(e instanceof ActionError ? e.message : 'Installation impossible : Studio Dock ne répond pas.');
      setBusy(false);
    }
  };

  const choose = async () => {
    const { path } = await api.chooseFolder();
    if (path) setValue(path);
  };

  return (
    <div className="flex flex-col gap-3">
      <form className="flex flex-wrap gap-2.5" onSubmit={(e) => { e.preventDefault(); if (value.trim()) submit(); }}>
        <label htmlFor="installation" className="sr-only">Dossier d'installation</label>
        <input id="installation" value={value} onChange={(e) => setValue(e.target.value)} placeholder="C:\Users\vous\Apps\StudioDock"
          className="h-11 min-w-0 flex-[1_1_320px] rounded border border-line-strong bg-surface-2 px-3.5 font-mono text-sm text-ink focus:outline focus:outline-2 focus:outline-focus" />
        {canChoose && (
          <button type="button" onClick={choose} disabled={busy}
            className="flex h-11 items-center gap-2 rounded border border-line-strong bg-surface px-4 font-medium text-ink-body hover:bg-surface-3">
            <IconFolder /> Choisir…
          </button>
        )}
        <button type="submit" disabled={busy || !value.trim() || value.trim() === current}
          className="flex h-11 items-center gap-2 rounded border-0 bg-primary px-5 font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:bg-primary-disabled disabled:text-primary-on-disabled">
          {busy && <IconSpinner />} {submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={busy}
            className="h-11 border-0 bg-transparent px-2 text-sm text-ink-muted underline">Annuler</button>
        )}
      </form>
      {error && (
        <p role="alert" className="m-0 flex items-start gap-2 text-sm text-danger-text"><IconAlert className="mt-0.5 shrink-0" /> {error}</p>
      )}
    </div>
  );
};

/** Message affiché pendant que Studio Dock redémarre depuis son dossier d'installation. */
export const Restarting: React.FC<{ folder: string }> = ({ folder }) => (
  <div role="status" className="flex flex-col gap-2 rounded-md bg-accent-soft px-5 py-4 text-sm text-accent-ink">
    <span className="flex items-center gap-2 font-medium"><IconSpinner /> Studio Dock redémarre depuis son dossier d'installation…</span>
    <span className="break-all font-mono text-[13px]">{folder}</span>
    <span>Cette fenêtre va se fermer et Studio Dock se rouvrir. Ensuite, retrouvez-le dans le menu Démarrer.</span>
  </div>
);

/** Premier lancement sous Windows : choisir le dossier où installer Studio Dock et les applications. */
export const InstallScreen: React.FC<{ onRestart: (folder: string) => void; restartingIn: string | null }> = ({ onRestart, restartingIn }) => {
  const [settings, setSettings] = React.useState<Settings | null>(null);
  React.useEffect(() => { api.settings().then(setSettings).catch(() => undefined); }, []);
  const install = settings?.install;
  const moved = !!install?.folder; // installé ailleurs, mais copie introuvable

  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-6 pt-4">
      <DockLogo size={64} />
      <div className="flex flex-col gap-2">
        <h1 className="m-0 text-[30px] font-bold leading-tight text-ink">Installer Studio Dock sur ce poste</h1>
        <p className="m-0 text-ink-muted">
          Choisissez le dossier de ce poste où installer Studio Dock et vos applications : chaque app y sera copiée
          et lancée depuis cet endroit. Prenez le dossier autorisé par votre entreprise pour les applications.
        </p>
      </div>
      {restartingIn ? <Restarting folder={restartingIn} /> : (
        <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
          {moved && (
            <p className="m-0 flex items-start gap-2 text-sm text-warning-text">
              <IconAlert className="mt-0.5 shrink-0" /> Studio Dock est introuvable dans votre dossier d'installation ({install?.folder}). Réinstallez-le.
            </p>
          )}
          <InstallFolderForm initial={install?.folder ?? install?.suggested ?? ''} canChoose={!!settings?.canChooseFolder}
            submitLabel="Installer ici" onRestart={onRestart} />
          <ul className="m-0 flex flex-col gap-1.5 pl-5 text-sm text-ink-muted">
            <li>Un dossier de ce poste, pas un dossier réseau ni le dossier partagé de l'équipe.</li>
            <li>Un raccourci « Studio Dock » est ajouté au menu Démarrer.</li>
            <li>Le fichier que vous venez d'ouvrir n'est plus utile ensuite ; s'il est dans le dossier partagé, laissez-le pour vos collègues.</li>
          </ul>
        </section>
      )}
    </div>
  );
};
