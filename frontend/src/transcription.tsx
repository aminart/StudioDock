import React from 'react';
import { ActionError, catalogueApi, transcriptionApi } from './api';
import type { CatalogueEdit, TranscriptionState } from './types';
import { IconAlert, IconDownload, IconSpinner, SectionTitle, shortPath } from './ui';

/* Modèle de transcription de l'équipe (faster-whisper) : déclaré dans le catalogue par l'administratrice, installé
   d'office chez chacun, puis utilisé par les apps de transcription (Snappy Transcript). */

const secondary = 'flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3 disabled:cursor-not-allowed disabled:opacity-50';
const primary = 'flex h-10 items-center gap-2 rounded border-0 bg-primary px-4 text-sm font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:bg-primary-disabled disabled:text-primary-on-disabled';
const field = 'h-10 w-full min-w-0 rounded border border-line-strong bg-surface-2 px-3 text-sm text-ink focus:outline focus:outline-2 focus:outline-focus';

const taille = (octets: number | null) => (octets ? `${Math.round(octets / (1024 * 1024))} Mo` : '');

/** Réglages › Modèles d'IA : où en est le modèle sur ce poste. */
export const TranscriptionSection: React.FC<{ n: number }> = ({ n }) => {
  const [state, setState] = React.useState<TranscriptionState | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(() => transcriptionApi.state().then(setState).catch((e) => setError(e instanceof ActionError ? e.message : 'Lecture impossible.')), []);
  React.useEffect(() => { load(); }, [load]);
  // Suivi pendant l'installation ou l'attente du téléchargement
  const suivre = !!state && (state.progress !== null || state.waiting);
  React.useEffect(() => {
    if (!suivre) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [suivre, load]);

  const act = async (f: () => Promise<TranscriptionState>) => {
    setBusy(true);
    setError(null);
    try { setState(await f()); } catch (e) { setError(e instanceof ActionError ? e.message : 'Action impossible.'); } finally { setBusy(false); }
  };

  if (!state) return null;
  if (!state.offered && !state.installed) {
    return (
      <section aria-labelledby="transcription-h" className="flex flex-col gap-2 rounded-lg border border-dashed border-line-strong bg-surface px-6 py-5">
        <SectionTitle n={n} id="transcription-h" title="Transcription audio"
          subtitle="Le catalogue de votre équipe ne propose pas encore de modèle de transcription. Quand il en proposera un, Studio Dock l'installera ici tout seul, pour Snappy Transcript." />
      </section>
    );
  }

  return (
    <section aria-labelledby="transcription-h" className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
      <SectionTitle n={n} id="transcription-h" title="Transcription audio"
        subtitle="Modèle fourni par votre équipe et installé sur ce poste : Snappy Transcript l'utilise sans rien régler. Il fonctionne sans connexion ; aucun son ne quitte le poste." />
      <div aria-live="polite" className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface-2 px-4 py-3">
        <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-0.5">
          <span className="text-sm font-semibold text-ink">{state.name}{state.version ? ` · ${state.version}` : ''}</span>
          <span className="text-[13px] text-ink-muted">
            {state.progress !== null ? `Installation… ${state.progress} %`
              : state.waiting ? 'Téléchargement en cours dans votre navigateur : il sera installé dès son arrivée.'
              : state.installed ? (state.update ? `Version ${state.available} disponible.` : 'Installé sur ce poste.')
              : state.online ? `À télécharger${state.size ? ` (${taille(state.size)})` : ''}.`
              : 'Installation automatique depuis le dossier de l\'équipe…'}
          </span>
          {state.installed && state.path && <span className="font-mono text-[12px] text-ink-subtle" title={state.path}>{shortPath(state.path)}</span>}
        </div>
        {state.progress !== null && <IconSpinner />}
        {state.online && state.canDownload && state.progress === null && !state.waiting && (!state.installed || state.update) && (
          <button type="button" className={primary} disabled={busy} onClick={() => act(transcriptionApi.install)}>
            <IconDownload /> {state.installed ? 'Mettre à jour' : 'Télécharger'}
          </button>
        )}
        {state.waiting && <button type="button" className={secondary} disabled={busy} onClick={() => act(transcriptionApi.cancel)}>Annuler</button>}
        {!state.online && state.error && (
          <button type="button" className={secondary} disabled={busy} onClick={() => act(transcriptionApi.install)}>Réessayer</button>
        )}
      </div>
      {state.error && (
        <p role="alert" className="m-0 flex items-start gap-2 text-sm text-warning-text"><IconAlert className="mt-0.5 shrink-0" /> {state.error}</p>
      )}
      {error && <p role="alert" className="m-0 text-sm text-warning-text">{error}</p>}
    </section>
  );
};

/** Préparer pour l'équipe : déclarer le modèle et son sous-dossier. */
export const TranscriptionCatalogue: React.FC<{ edit: CatalogueEdit; onChanged: (e: CatalogueEdit) => void }> = ({ edit, onChanged }) => {
  const t = edit.transcription;
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState(t?.name ?? 'Whisper small');
  const [source, setSource] = React.useState(t?.source ?? 'Modeles');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const save = async (valeur: { name: string; source: string } | null) => {
    setBusy(true);
    setError(null);
    try { onChanged(await catalogueApi.saveTranscription(edit.folder, valeur)); setOpen(false); }
    catch (e) { setError(e instanceof ActionError ? e.message : 'Enregistrement impossible.'); }
    finally { setBusy(false); }
  };
  const edit_ = () => { setName(t?.name ?? 'Whisper small'); setSource(t?.source ?? 'Modeles'); setOpen(true); };

  return (
    <div className="flex flex-col gap-3 rounded-md border border-line bg-surface-2 p-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-1">
          <h3 className="m-0 text-[15px] font-bold text-ink">Modèle de transcription</h3>
          {t ? (
            t.invalid ? <span className="text-sm text-warning-text">Déclaration invalide : {t.invalid}</span> : (
              <span className="text-sm text-ink-body">
                <strong className="font-semibold text-ink">{t.name}</strong> · sous-dossier <span className="font-mono">{t.source}/</span>{' · '}
                {t.found ? <>archive <span className="font-mono">{t.found}</span>{t.version ? ` (version ${t.version})` : ''}</>
                  : <span className="text-warning-text">aucune archive .zip déposée pour l'instant</span>}
              </span>
            )
          ) : (
            <span className="text-sm text-ink-muted">Pour Snappy Transcript : un modèle faster-whisper (.zip) que Studio Dock installe chez chacun. Personne n'a de chemin à régler.</span>
          )}
        </div>
        {!open && (t
          ? <div className="flex gap-2"><button type="button" className={secondary} onClick={edit_}>Modifier</button>
              <button type="button" className={secondary} disabled={busy} onClick={() => save(null)}>Retirer</button></div>
          : <button type="button" className={secondary} onClick={edit_}>+ Proposer un modèle</button>)}
      </div>
      {open && (
        <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); save({ name, source }); }}>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">Nom affiché
              <input className={field} value={name} onChange={(e) => setName(e.target.value)} required maxLength={60} />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">Sous-dossier du catalogue
              <input className={`${field} font-mono`} value={source} onChange={(e) => setSource(e.target.value)} required />
            </label>
          </div>
          <p className="m-0 text-[13px] text-ink-muted">
            Déposez ensuite dans ce sous-dossier le modèle compressé en .zip (le dossier qui contient config.json et model.bin), par
            exemple <span className="font-mono">faster-whisper-small-1.0.0.zip</span>. Pour le mettre à jour, déposez une archive avec un numéro plus grand.
          </p>
          <div className="flex gap-2">
            <button type="submit" className={primary} disabled={busy || !name.trim() || !source.trim()}>{busy && <IconSpinner />} Enregistrer</button>
            <button type="button" className={secondary} onClick={() => setOpen(false)}>Annuler</button>
          </div>
        </form>
      )}
      {error && <p role="alert" className="m-0 text-sm text-warning-text">{error}</p>}
    </div>
  );
};
