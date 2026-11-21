import React from 'react';
import { ActionError, catalogueApi, toBase64 } from './api';
import type { CatalogueApp, CatalogueEdit } from './types';
import { IconAlert, IconSpinner } from './ui';

/* Préparer pour l'équipe › Applications : la liste des apps du catalogue et leur fiche, par formulaire. */

const field = 'h-10 w-full min-w-0 rounded border border-line-strong bg-surface-2 px-3 text-sm text-ink placeholder:text-ink-subtle focus:outline focus:outline-2 focus:outline-focus';
const area = 'min-h-[88px] w-full rounded border border-line-strong bg-surface-2 px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline focus:outline-2 focus:outline-focus';
const secondary = 'flex h-9 items-center gap-1.5 rounded border border-line-strong bg-surface px-3 text-sm font-medium text-ink-body hover:bg-surface-3 disabled:cursor-not-allowed disabled:opacity-50';
const primary = 'flex h-10 items-center gap-2 rounded border-0 bg-primary px-4 text-sm font-medium text-primary-on hover:bg-primary-hover disabled:opacity-60';
const message = (e: unknown) => (e instanceof ActionError || e instanceof Error ? e.message : String(e));

const MODES: { value: CatalogueApp['mode']; label: string; hint: string }[] = [
  { value: 'optionnel', label: 'Proposée', hint: 'Chacun l\'installe s\'il le souhaite.' },
  { value: 'auto', label: 'Pour toute l\'équipe', hint: 'Installée et mise à jour d\'office chez tout le monde.' },
  { value: 'masque', label: 'Masquée', hint: 'Retirée de la liste, sans être supprimée du catalogue.' },
];
const modeLabel = (m: CatalogueApp['mode']) => MODES.find((x) => x.value === m)?.label ?? m;

const vide = (): CatalogueApp => ({
  id: '', name: '', kind: 'web', port: null, ai: false, exe: '', source: '', mode: 'optionnel', install_name: null,
  tagline: '', description: '', points: [], tutorial: [], links: [], icon: { file: null, style: 'logo' },
});

const iconUrl = (folder: string, file: string, stamp: number) =>
  `/api/admin/catalogue/icon?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(file)}&v=${stamp}`;

const Label: React.FC<{ htmlFor?: string; children: React.ReactNode; optional?: boolean }> = ({ htmlFor, children, optional }) => (
  <label htmlFor={htmlFor} className="text-sm font-medium text-ink">
    {children}{optional && <span className="ml-1.5 font-normal text-ink-subtle">facultatif</span>}
  </label>
);
const Hint: React.FC<{ children: React.ReactNode }> = ({ children }) => <span className="text-[13px] text-ink-muted">{children}</span>;

/** Vignette de l'icône, comme sur les cartes : « logo » remplit la vignette, « symbole » est posé sur fond navy. */
const Tile: React.FC<{ src: string | null; style: 'logo' | 'symbole'; size?: number }> = ({ src, style, size = 48 }) => (
  <span className={`flex shrink-0 items-center justify-center overflow-hidden rounded-[22%] ${style === 'symbole' || !src ? 'bg-primary' : 'bg-surface-3'}`}
    style={{ width: size, height: size }}>
    {src ? <img src={src} alt="" className={style === 'symbole' ? 'h-[62%] w-[62%] object-contain' : 'h-full w-full object-cover'} />
      : <span className="text-[11px] font-semibold text-primary-on">?</span>}
  </span>
);

/* ---------- Listes éditables (points forts, prise en main, liens) ---------- */

function moveItem<T>(list: T[], i: number, d: number): T[] {
  const j = i + d;
  if (j < 0 || j >= list.length) return list;
  const copy = [...list];
  [copy[i], copy[j]] = [copy[j], copy[i]];
  return copy;
}

const RowTools: React.FC<{ label: string; i: number; n: number; onMove: (d: number) => void; onRemove: () => void }> = ({ label, i, n, onMove, onRemove }) => (
  <span className="flex shrink-0 gap-1">
    <button type="button" aria-label={`Monter ${label}`} disabled={i === 0} onClick={() => onMove(-1)} className={`${secondary} w-9 justify-center px-0`}>↑</button>
    <button type="button" aria-label={`Descendre ${label}`} disabled={i === n - 1} onClick={() => onMove(1)} className={`${secondary} w-9 justify-center px-0`}>↓</button>
    <button type="button" aria-label={`Retirer ${label}`} onClick={onRemove} className={`${secondary} w-9 justify-center px-0`}>×</button>
  </span>
);

/* ---------- Formulaire d'une app ---------- */

const AppForm: React.FC<{
  folder: string; existing: CatalogueApp | null; others: CatalogueApp[];
  onSaved: (s: CatalogueEdit) => void; onCancel: () => void;
}> = ({ folder, existing, others, onSaved, onCancel }) => {
  const [app, setApp] = React.useState<CatalogueApp>(() => existing ? structuredClone(existing) : vide());
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [pendingIcon, setPendingIcon] = React.useState<File | null>(null);
  const [preview, setPreview] = React.useState<string | null>(null);
  const [stamp] = React.useState(() => Date.now());
  const iconInput = React.useRef<HTMLInputElement>(null);
  const set = <K extends keyof CatalogueApp>(key: K, value: CatalogueApp[K]) => setApp((a) => ({ ...a, [key]: value }));

  React.useEffect(() => {
    if (!pendingIcon) { setPreview(null); return undefined; }
    const url = URL.createObjectURL(pendingIcon);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingIcon]);

  const compact = app.name.normalize('NFKD').replace(/[^A-Za-z0-9]+/g, '');
  const portTaken = app.kind === 'web' && app.port != null && others.some((o) => o.port === app.port);
  const iconSrc = preview ?? (app.icon.file && existing?.iconFound ? iconUrl(folder, app.icon.file, stamp) : null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      // Nouvelle app : enregistrée d'abord pour connaître son identifiant, puis l'icône lui est attachée
      let state = await catalogueApi.save(folder, existing?.id ?? null, app);
      if (pendingIcon) {
        const id = existing?.id ?? state.saved ?? '';
        const { file } = await catalogueApi.uploadIcon(folder, id, pendingIcon.name, await toBase64(pendingIcon));
        const saved = state.apps.find((a) => a.id === id);
        if (saved) state = await catalogueApi.save(folder, id, { ...saved, icon: { ...app.icon, file } });
      }
      onSaved(state);
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label={existing ? `Modifier ${existing.name}` : 'Nouvelle app'} className="flex flex-col rounded-lg border border-line-strong bg-surface">
      <div className="flex flex-wrap items-center gap-4 border-b border-line px-6 py-5">
        <Tile src={iconSrc} style={app.icon.style} />
        <div className="flex min-w-0 flex-1 flex-col">
          <h3 className="m-0 truncate text-[17px] font-bold text-ink">{app.name || (existing ? existing.name : 'Nouvelle app')}</h3>
          <span className="truncate text-sm text-ink-muted">{app.tagline || 'Aperçu de la carte'}</span>
        </div>
      </div>

      <div className="grid gap-6 px-6 py-5 lg:grid-cols-2">
        {/* Colonne 1 : l'essentiel */}
        <div className="flex flex-col gap-4">
          <h4 className="m-0 text-[13px] font-semibold uppercase tracking-wide text-ink-subtle">L'app</h4>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ed-name">Nom</Label>
            <input id="ed-name" className={field} value={app.name} onChange={(e) => set('name', e.target.value)} placeholder="Nom de l'app" />
            {!existing && app.name && <Hint>Identifiant, programme et sous-dossier déduits du nom : <span className="font-mono">{compact || '—'}</span></Hint>}
          </div>
          <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
            <legend className="mb-1.5 text-sm font-medium text-ink">Type</legend>
            {([['web', 'S\'ouvre dans le navigateur', 'Comme SpecGen : un exe que Studio Dock copie et lance.'],
               ['native', 'App de bureau', 'Comme Mapline : un installateur (.exe ou .msi) lancé par Studio Dock.']] as const).map(([value, label, hint]) => (
              <label key={value} className="flex cursor-pointer items-start gap-2.5 rounded border border-line px-3 py-2 hover:bg-surface-2">
                <input type="radio" name="ed-kind" className="mt-0.5" checked={app.kind === value} onChange={() => set('kind', value)} />
                <span className="flex flex-col"><span className="text-sm text-ink">{label}</span><Hint>{hint}</Hint></span>
              </label>
            ))}
          </fieldset>
          <label className="flex cursor-pointer items-center gap-2.5 text-sm text-ink">
            <input type="checkbox" checked={app.ai} onChange={(e) => set('ai', e.target.checked)} />
            Utilise l'IA <Hint>(reçoit un modèle dans Réglages › Modèles d'IA)</Hint>
          </label>
          <fieldset className="m-0 flex flex-col gap-1.5 border-0 p-0">
            <legend className="mb-1.5 text-sm font-medium text-ink">Pour l'équipe</legend>
            {MODES.map((m) => (
              <label key={m.value} className="flex cursor-pointer items-baseline gap-2.5 text-sm text-ink">
                <input type="radio" name="ed-mode" checked={app.mode === m.value} onChange={() => set('mode', m.value)} />
                {m.label} <Hint>{m.hint}</Hint>
              </label>
            ))}
          </fieldset>

          <div className="flex flex-col gap-1.5">
            <Label>Icône</Label>
            <div className="flex flex-wrap items-center gap-2.5">
              <button type="button" className={secondary} onClick={() => iconInput.current?.click()}>{app.icon.file || pendingIcon ? 'Remplacer…' : 'Choisir un fichier…'}</button>
              <select aria-label="Style de l'icône" className={`${field} h-9 w-auto`} value={app.icon.style}
                onChange={(e) => set('icon', { ...app.icon, style: e.target.value as 'logo' | 'symbole' })}>
                <option value="logo">Logo : remplit la vignette</option>
                <option value="symbole">Symbole : posé sur fond navy</option>
              </select>
              <span className="font-mono text-[12px] text-ink-subtle">{pendingIcon?.name ?? app.icon.file ?? 'aucune'}</span>
            </div>
            <Hint>SVG ou PNG carré. Pour en créer une dans le style de la suite : skill « icône app suite ».</Hint>
            <input ref={iconInput} type="file" accept=".svg,.png,image/svg+xml,image/png" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) setPendingIcon(f); e.target.value = ''; }} />
          </div>

          <details className="rounded border border-line px-3 py-2">
            <summary className="cursor-pointer text-sm font-medium text-ink-muted hover:text-ink">Détails techniques</summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ed-exe">Nom du programme</Label>
                <input id="ed-exe" className={`${field} font-mono`} value={app.exe} onChange={(e) => set('exe', e.target.value)} placeholder={compact || 'MonApp'} />
                <Hint>Début du nom du fichier, sans version : <span className="font-mono">{app.exe || compact || 'MonApp'}-1.0.0.exe</span></Hint>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ed-source">Sous-dossier</Label>
                <input id="ed-source" className={`${field} font-mono`} value={app.source} onChange={(e) => set('source', e.target.value)} placeholder={compact || 'MonApp'} />
                <Hint>Où vous déposez ses versions{existing && !existing.sourceFound ? ' (créé à l\'enregistrement)' : ''}.</Hint>
              </div>
              {app.kind === 'web' ? (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="ed-port">Port</Label>
                  <input id="ed-port" type="number" min={1024} max={65535} className={`${field} ${portTaken ? 'border-danger' : ''}`} value={app.port ?? ''}
                    onChange={(e) => set('port', e.target.value ? Number(e.target.value) : null)} placeholder="choisi automatiquement" />
                  <Hint>{portTaken ? 'Déjà utilisé par une autre app.' : 'Laissez vide : un port libre est choisi.'}</Hint>
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="ed-install" optional>Nom dans « Applications installées »</Label>
                  <input id="ed-install" className={field} value={app.install_name ?? ''} onChange={(e) => set('install_name', e.target.value || null)} placeholder={app.name || 'Mapline'} />
                  <Hint>Seulement s'il diffère du nom de l'app.</Hint>
                </div>
              )}
            </div>
          </details>
        </div>

        {/* Colonne 2 : la fiche */}
        <div className="flex flex-col gap-4">
          <h4 className="m-0 text-[13px] font-semibold uppercase tracking-wide text-ink-subtle">La fiche</h4>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ed-tagline">Accroche</Label>
            <input id="ed-tagline" className={field} value={app.tagline} maxLength={90} onChange={(e) => set('tagline', e.target.value)} placeholder="Une phrase, sous le nom sur la carte" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ed-desc">Description</Label>
            <textarea id="ed-desc" className={area} value={app.description} onChange={(e) => set('description', e.target.value)} placeholder="À quoi sert l'app, pour qui." />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Points forts</Label>
            {app.points.map((p, i) => (
              <div key={i} className="flex gap-2">
                <input aria-label={`Point fort ${i + 1}`} className={field} value={p} onChange={(e) => set('points', app.points.map((x, j) => (j === i ? e.target.value : x)))} />
                <RowTools label={`le point ${i + 1}`} i={i} n={app.points.length} onMove={(d) => set('points', moveItem(app.points, i, d))} onRemove={() => set('points', app.points.filter((_, j) => j !== i))} />
              </div>
            ))}
            <button type="button" className={`${secondary} self-start`} onClick={() => set('points', [...app.points, ''])}>+ Ajouter un point fort</button>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Prise en main</Label>
            {app.tutorial.map((s, i) => (
              <div key={i} className="flex gap-2 rounded border border-line p-2.5">
                <span className="mt-2 w-5 shrink-0 text-center text-sm font-semibold text-ink-subtle">{i + 1}</span>
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <input aria-label={`Titre de l'étape ${i + 1}`} className={field} value={s.title} placeholder="Titre de l'étape"
                    onChange={(e) => set('tutorial', app.tutorial.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)))} />
                  <textarea aria-label={`Texte de l'étape ${i + 1}`} className={`${area} min-h-[60px]`} value={s.text} placeholder="Ce qu'il faut faire"
                    onChange={(e) => set('tutorial', app.tutorial.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))} />
                </div>
                <RowTools label={`l'étape ${i + 1}`} i={i} n={app.tutorial.length} onMove={(d) => set('tutorial', moveItem(app.tutorial, i, d))} onRemove={() => set('tutorial', app.tutorial.filter((_, j) => j !== i))} />
              </div>
            ))}
            <button type="button" className={`${secondary} self-start`} onClick={() => set('tutorial', [...app.tutorial, { title: '', text: '' }])}>+ Ajouter une étape</button>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label optional>Liens</Label>
            {app.links.map((l, i) => (
              <div key={i} className="flex flex-wrap gap-2 sm:flex-nowrap">
                <input aria-label={`Libellé du lien ${i + 1}`} className={`${field} sm:w-[40%]`} value={l.label} placeholder="Documentation"
                  onChange={(e) => set('links', app.links.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} />
                <input aria-label={`Adresse du lien ${i + 1}`} className={`${field} font-mono`} value={l.url} placeholder="https://…"
                  onChange={(e) => set('links', app.links.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)))} />
                <RowTools label={`le lien ${i + 1}`} i={i} n={app.links.length} onMove={(d) => set('links', moveItem(app.links, i, d))} onRemove={() => set('links', app.links.filter((_, j) => j !== i))} />
              </div>
            ))}
            <button type="button" className={`${secondary} self-start`} onClick={() => set('links', [...app.links, { label: '', url: '' }])}>+ Ajouter un lien</button>
          </div>
        </div>
      </div>

      {error && <p role="alert" className="mx-6 mb-4 mt-0 flex items-start gap-2 rounded-md border border-warning-line bg-warning-soft px-3 py-2 text-sm text-warning-text"><IconAlert className="mt-0.5 shrink-0" /> {error}</p>}
      <div className="flex flex-wrap items-center justify-end gap-3 rounded-b-lg border-t border-line bg-surface-2 px-6 py-4">
        <button type="button" onClick={onCancel} className="h-10 border-0 bg-transparent px-2 text-sm font-medium text-ink-muted hover:text-ink">Annuler</button>
        <button type="button" onClick={save} disabled={busy || !app.name.trim() || portTaken} className={primary}>
          {busy && <IconSpinner />} {existing ? 'Enregistrer la fiche' : 'Ajouter au catalogue'}
        </button>
      </div>
    </section>
  );
};

/* ---------- Liste des apps ---------- */

export const CatalogueApps: React.FC<{ state: CatalogueEdit; onChanged: (s: CatalogueEdit) => void }> = ({ state, onChanged }) => {
  const [editing, setEditing] = React.useState<string | 'new' | null>(null);
  const [confirm, setConfirm] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [stamp, setStamp] = React.useState(() => Date.now());
  const act = async (action: () => Promise<CatalogueEdit>) => {
    setError(null);
    try { onChanged(await action()); setStamp(Date.now()); } catch (e) { setError(message(e)); }
  };
  const saved = (s: CatalogueEdit) => { onChanged(s); setEditing(null); setStamp(Date.now()); };

  return (
    <div className="flex flex-col gap-3">
      {editing === 'new' && <AppForm folder={state.folder} existing={null} others={state.apps} onSaved={saved} onCancel={() => setEditing(null)} />}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {state.apps.map((a, i) => editing === a.id ? (
          <li key={a.id}><AppForm folder={state.folder} existing={a} others={state.apps.filter((o) => o.id !== a.id)} onSaved={saved} onCancel={() => setEditing(null)} /></li>
        ) : (
          <li key={a.id} className="flex flex-wrap items-center gap-4 rounded-lg border border-line bg-surface px-4 py-3">
            <Tile src={a.icon?.file && a.iconFound ? iconUrl(state.folder, a.icon.file, stamp) : null} style={a.icon?.style ?? 'logo'} size={40} />
            <div className="flex min-w-[220px] flex-1 flex-col">
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink">{a.name}</span>
                <span className="rounded-full border border-line px-2 py-px text-[12px] text-ink-muted">{a.kind === 'native' ? 'App de bureau' : 'Navigateur'}</span>
                {a.ai && <span className="rounded-full border border-line px-2 py-px text-[12px] text-ink-muted">IA</span>}
                <span className={`rounded-full px-2 py-px text-[12px] ${a.mode === 'masque' ? 'bg-surface-3 text-ink-subtle' : a.mode === 'auto' ? 'bg-accent-soft text-accent-ink' : 'border border-line text-ink-muted'}`}>{modeLabel(a.mode)}</span>
              </span>
              {a.invalid
                ? <span className="text-[13px] text-warning-text">Fiche invalide : {a.invalid}</span>
                : <span className="truncate text-[13px] text-ink-muted">{a.tagline || <em>sans accroche</em>}</span>}
              {!a.invalid && (!a.iconFound || !a.sourceFound) && (
                <span className="text-[12px] text-warning-text">{[!a.iconFound && 'icône manquante', !a.sourceFound && `sous-dossier ${a.source}/ absent`].filter(Boolean).join(' · ')}</span>
              )}
            </div>
            <span className="flex flex-wrap gap-1.5">
              <button type="button" aria-label={`Monter ${a.name}`} disabled={i === 0 || editing !== null} className={`${secondary} w-9 justify-center px-0`}
                onClick={() => act(() => catalogueApi.move(state.folder, a.id, -1))}>↑</button>
              <button type="button" aria-label={`Descendre ${a.name}`} disabled={i === state.apps.length - 1 || editing !== null} className={`${secondary} w-9 justify-center px-0`}
                onClick={() => act(() => catalogueApi.move(state.folder, a.id, 1))}>↓</button>
              <button type="button" disabled={!!a.invalid || editing !== null} className={secondary} onClick={() => setEditing(a.id)}>Modifier</button>
              {confirm === a.id ? (
                <>
                  <button type="button" className={`${secondary} border-danger text-danger-text`} onClick={() => { setConfirm(null); act(() => catalogueApi.remove(state.folder, a.id)); }}>Retirer du catalogue</button>
                  <button type="button" className="h-9 border-0 bg-transparent px-2 text-sm text-ink-muted" onClick={() => setConfirm(null)}>Annuler</button>
                </>
              ) : (
                <button type="button" disabled={editing !== null} className={secondary} onClick={() => setConfirm(a.id)}>Retirer</button>
              )}
            </span>
          </li>
        ))}
      </ul>
      {confirm && <p className="m-0 text-[13px] text-ink-muted">L'app disparaît de Studio Dock chez vos collègues ; ses fichiers restent dans le dossier. Pour la cacher sans la retirer : « Masquée ».</p>}
      {error && <p role="alert" className="m-0 flex items-start gap-2 text-sm text-warning-text"><IconAlert className="mt-0.5 shrink-0" /> {error}</p>}
      {editing === null && (
        <button type="button" className={`${primary} self-start`} onClick={() => setEditing('new')}>+ Ajouter une app</button>
      )}
    </div>
  );
};
