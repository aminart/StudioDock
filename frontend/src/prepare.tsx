import React from 'react';
import { ActionError, api } from './api';
import type { PrepareState } from './types';
import { IconAlert, IconBack, IconFolder, IconSpinner, ScopeNote, SettingsTabs } from './ui';

const input = 'h-10 min-w-0 rounded border border-line-strong bg-surface-2 px-3 font-mono text-[13px] text-ink focus:outline focus:outline-2 focus:outline-focus';

/** Préparer le catalogue en ligne (administratrice) : versions trouvées, liens des dossiers en ligne, zip à publier. */
export const PreparePage: React.FC<{ canChoose: boolean }> = ({ canChoose }) => {
  const [folder, setFolder] = React.useState('');
  const [state, setState] = React.useState<PrepareState | null>(null);
  const [links, setLinks] = React.useState<Record<string, string>>({});
  const [dockLink, setDockLink] = React.useState('');
  const [catalogueLink, setCatalogueLink] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [built, setBuilt] = React.useState<string | null>(null);

  const apply = (s: PrepareState) => {
    setState(s);
    setFolder(s.folder);
    setLinks(Object.fromEntries(s.apps.map((a) => [a.id, a.link])));
    setDockLink(s.studiodock.link);
    setCatalogueLink(s.link);
  };

  const load = async (path: string) => {
    if (!path.trim()) return;
    setBusy(true);
    setError(null);
    setBuilt(null);
    try {
      apply(await api.prepare(path.trim()));
    } catch (e) {
      setState(null);
      setError(e instanceof ActionError ? e.message : 'Lecture impossible.');
    } finally {
      setBusy(false);
    }
  };

  React.useEffect(() => {
    api.settings().then((s) => { if (s.prepare_folder) { setFolder(s.prepare_folder); load(s.prepare_folder); } }).catch(() => undefined);
  }, []);

  const choose = async () => {
    const { path } = await api.chooseFolder();
    if (path) { setFolder(path); load(path); }
  };

  const build = async () => {
    if (!state) return;
    setBusy(true);
    setError(null);
    try {
      const s = await api.build({ folder: state.folder, links, studiodockLink: dockLink, catalogueLink });
      apply(s);
      setBuilt(s.zip ?? null);
    } catch (e) {
      setError(e instanceof ActionError ? e.message : 'Fabrication impossible.');
    } finally {
      setBusy(false);
    }
  };

  const missing = state ? state.apps.filter((a) => !a.link.trim() && !links[a.id]?.trim()).length : 0;

  return (
    <div className="flex flex-col gap-6">
      <a href="#/" className="flex min-h-8 items-center gap-1.5 self-start text-sm text-ink-muted no-underline hover:text-ink">
        <IconBack /> Mes applications
      </a>
      <h1 className="m-0 text-[30px] font-bold leading-tight text-ink">Réglages</h1>
      <SettingsTabs current="equipe" />
      <ScopeNote scope="equipe" />
      <p className="m-0 max-w-[820px] text-[15px] text-ink-muted">
        Pour la personne qui tient le catalogue de l'équipe. Gardez sur votre poste une copie du dossier en ligne :
        <span className="font-mono"> catalogue.json</span>, <span className="font-mono">icons/</span> et un sous-dossier par app avec son exe
        ou son installateur. Studio Dock y lit les versions, vous collez les liens des dossiers en ligne, et il fabrique le fichier à mettre en ligne.
      </p>

      <section className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-6">
        <h2 className="m-0 text-[19px] font-bold text-ink">1 · Dossier de préparation</h2>
        <form className="flex flex-wrap gap-2.5" onSubmit={(e) => { e.preventDefault(); load(folder); }}>
          <label htmlFor="preparation" className="sr-only">Dossier de préparation</label>
          <input id="preparation" value={folder} onChange={(e) => setFolder(e.target.value)} placeholder="C:\Users\vous\Documents\Studio Dock - équipe"
            className={`${input} h-11 flex-[1_1_320px] text-sm`} />
          {canChoose && (
            <button type="button" onClick={choose} disabled={busy}
              className="flex h-11 items-center gap-2 rounded border border-line-strong bg-surface px-4 font-medium text-ink-body hover:bg-surface-3">
              <IconFolder /> Choisir…
            </button>
          )}
          <button type="submit" disabled={busy || !folder.trim()}
            className="flex h-11 items-center gap-2 rounded border border-line-strong bg-surface px-4 font-medium text-ink-body hover:bg-surface-3 disabled:opacity-50">
            Lire le dossier
          </button>
        </form>
      </section>

      {error && (
        <p role="alert" className="m-0 flex items-start gap-2 rounded-md border border-warning-line bg-warning-soft px-4 py-3 text-sm text-warning-text">
          <IconAlert className="mt-0.5 shrink-0" /> {error}
        </p>
      )}

      {state && (
        <section className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
          <div className="flex flex-col gap-1">
            <h2 className="m-0 text-[19px] font-bold text-ink">2 · Versions et liens</h2>
            <p className="m-0 text-sm text-ink-muted">
              Pour chaque dossier en ligne : « Copier le lien », accès « Personnes de votre organisation ». Le lien est ouvert
              dans le navigateur quand un membre clique sur Installer ou Mettre à jour.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[13px] text-ink-subtle">
                  <th scope="col" className="py-2 pr-3 font-medium">Application</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Version trouvée</th>
                  <th scope="col" className="py-2 font-medium">Lien du dossier en ligne</th>
                </tr>
              </thead>
              <tbody>
                {state.apps.map((a) => (
                  <tr key={a.id} className="border-b border-line align-top">
                    <td className="py-3 pr-3">
                      <span className="font-medium text-ink">{a.name}</span>
                      <span className="block font-mono text-[12px] text-ink-subtle">{a.source}/</span>
                      {!a.icon && <span className="block text-[12px] text-warning-text">icône introuvable</span>}
                    </td>
                    <td className="py-3 pr-3">
                      {a.found ? (
                        <><span className="font-medium text-ink">{a.version ?? '—'}</span><span className="block font-mono text-[12px] text-ink-subtle">{a.found}</span></>
                      ) : (
                        <span className="text-warning-text">aucun fichier{a.version ? ` (catalogue : ${a.version})` : ''}</span>
                      )}
                    </td>
                    <td className="py-3">
                      <label className="sr-only" htmlFor={`lien-${a.id}`}>Lien du dossier de {a.name}</label>
                      <input id={`lien-${a.id}`} value={links[a.id] ?? ''} onChange={(e) => setLinks({ ...links, [a.id]: e.target.value })}
                        placeholder="https://…" className={`${input} w-full`} />
                    </td>
                  </tr>
                ))}
                <tr className="border-b border-line align-top">
                  <td className="py-3 pr-3"><span className="font-medium text-ink">Studio Dock</span>
                    <span className="block font-mono text-[12px] text-ink-subtle">{state.studiodock.source}/</span></td>
                  <td className="py-3 pr-3">
                    {state.studiodock.found
                      ? <><span className="font-medium text-ink">{state.studiodock.version ?? '—'}</span><span className="block font-mono text-[12px] text-ink-subtle">{state.studiodock.found}</span></>
                      : <span className="text-ink-subtle">aucun fichier</span>}
                  </td>
                  <td className="py-3">
                    <label className="sr-only" htmlFor="lien-dock">Lien du dossier de Studio Dock</label>
                    <input id="lien-dock" value={dockLink} onChange={(e) => setDockLink(e.target.value)} placeholder="https://…" className={`${input} w-full`} />
                  </td>
                </tr>
                <tr className="align-top">
                  <td className="py-3 pr-3"><span className="font-medium text-ink">Le catalogue</span>
                    <span className="block text-[12px] text-ink-subtle">studio-dock-catalogue.zip</span></td>
                  <td className="py-3 pr-3 text-ink-subtle">{state.published ? `fabriqué le ${state.published}` : 'jamais fabriqué'}</td>
                  <td className="py-3">
                    <label className="sr-only" htmlFor="lien-catalogue-prep">Lien du catalogue</label>
                    <input id="lien-catalogue-prep" value={catalogueLink} onChange={(e) => setCatalogueLink(e.target.value)} placeholder="https://…" className={`${input} w-full`} />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {missing > 0 && (
            <p className="m-0 flex items-center gap-2 text-sm text-warning-text"><IconAlert /> {missing} {missing > 1 ? 'apps sans lien : elles ne pourront pas' : 'app sans lien : elle ne pourra pas'} être installées depuis Studio Dock.</p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={build} disabled={busy}
              className="flex h-11 items-center gap-2 rounded border-0 bg-primary px-5 font-medium text-primary-on hover:bg-primary-hover disabled:opacity-60">
              {busy && <IconSpinner />} Fabriquer le catalogue
            </button>
            <span className="text-sm text-ink-muted">Écrit les versions et les liens dans catalogue.json, puis crée studio-dock-catalogue.zip à côté.</span>
          </div>
        </section>
      )}

      {built && state && (
        <section role="status" className="flex flex-col gap-3 rounded-lg border border-line bg-success-soft p-6 text-success-text">
          <h2 className="m-0 text-[19px] font-bold">3 · À mettre en ligne</h2>
          <p className="m-0 text-sm">Catalogue fabriqué : <span className="font-mono">{built}</span></p>
          <ol className="m-0 flex flex-col gap-1 pl-5 text-sm">
            <li>Déposez <span className="font-mono">studio-dock-catalogue.zip</span> dans le dossier en ligne, à la place de l'ancien.</li>
            <li>Déposez les nouveaux exe dans le sous-dossier en ligne de chaque app (et de Studio Dock).</li>
            <li>Vos collègues cliquent sur « Vérifier les mises à jour » dans Studio Dock.</li>
          </ol>
          <button type="button" onClick={() => api.showPrepare(state.folder)}
            className="flex h-10 items-center gap-2 self-start rounded border border-line-strong bg-surface px-4 text-sm font-medium text-ink-body hover:bg-surface-3">
            <IconFolder /> Afficher le dossier
          </button>
        </section>
      )}
    </div>
  );
};
