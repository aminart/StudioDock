import React from 'react';
import { ActionError, api, iaApi, toBase64 } from './api';
import type { AiApp, AiChoice, AiConnection, AiState, ConnectionForm, ConnectionTest, OllamaState } from './types';
import { IconAlert, IconBack, IconDownload, IconExternal, IconRefresh, IconSpinner, PlatformContext, SettingsTabs } from './ui';

/* Réglages › Modèles d'IA : connexions communes à toutes les apps de la suite (même modèle que DocAnalyser),
   modèles locaux avec Ollama, et modèle utilisé par chaque app. */

const input = (invalid?: boolean) =>
  `h-11 w-full min-w-0 rounded border bg-surface-2 px-3.5 text-sm text-ink placeholder:text-ink-subtle focus:outline focus:outline-2 focus:outline-focus ${invalid ? 'border-danger' : 'border-line-strong'}`;
const secondary = 'flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3 disabled:cursor-not-allowed disabled:opacity-50';
const primary = 'flex h-10 items-center gap-2 rounded border-0 bg-primary px-4 text-sm font-medium text-primary-on hover:bg-primary-hover disabled:cursor-default disabled:bg-primary-disabled disabled:text-primary-on-disabled';
const message = (e: unknown) => (e instanceof ActionError || e instanceof Error ? e.message : String(e));
const dateTime = (iso: string) => new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
const date = (iso: string) => new Date(iso).toLocaleDateString('fr-FR');
const OLLAMA = 'http://localhost:11434';

const Field: React.FC<{ label: string; htmlFor?: string; optional?: boolean; hint?: React.ReactNode; children: React.ReactNode }> = ({
  label, htmlFor, optional, hint, children,
}) => (
  <div className="flex flex-col gap-1.5">
    {React.createElement(htmlFor ? 'label' : 'span', { htmlFor, className: 'text-sm font-medium text-ink' }, label,
      optional && <span className="ml-1.5 font-normal text-ink-subtle">facultatif</span>)}
    {children}
    {hint && <span className="text-[13px] text-ink-muted">{hint}</span>}
  </div>
);

const TestBanner: React.FC<{ test: ConnectionTest }> = ({ test }) => (
  <div role={test.ok ? 'status' : 'alert'}
    className={`flex items-start gap-2.5 rounded-md border px-4 py-3 text-sm ${test.ok ? 'border-line bg-success-soft text-success-text' : 'border-warning-line bg-warning-soft text-warning-text'}`}>
    {test.ok ? <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-success" aria-hidden="true" /> : <IconAlert className="mt-0.5 shrink-0" />}
    <span><strong className="font-semibold">{test.title}</strong>
      <span className="block">{test.ok ? `Testée le ${dateTime(test.at)} · ` : ''}{test.message}</span></span>
  </div>
);

/* ---------- Formulaire d'une connexion ---------- */

export const ConnectionEditor: React.FC<{ existing: AiConnection | null; onSaved: (s: AiState) => void; onCancel: () => void }> = ({
  existing, onSaved, onCancel,
}) => {
  const platform = React.useContext(PlatformContext);
  const [form, setForm] = React.useState<ConnectionForm>(() => existing
    ? { name: existing.name, api_base: existing.api_base, api_key: existing.has_api_key ? null : '', models: existing.models, context_tokens: existing.context_tokens }
    : { name: '', api_base: '', api_key: '', models: [], context_tokens: null });
  const [newModel, setNewModel] = React.useState('');
  const [showKey, setShowKey] = React.useState(false);
  const [pendingCert, setPendingCert] = React.useState<File | null>(null);
  const [dropCert, setDropCert] = React.useState(false);
  const [test, setTest] = React.useState<ConnectionTest | null>(existing?.last_test ?? null);
  const [busy, setBusy] = React.useState<'test' | 'save' | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const certInput = React.useRef<HTMLInputElement>(null);

  const set = <K extends keyof ConnectionForm>(key: K, value: ConnectionForm[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    if (key === 'api_base' || key === 'api_key') setTest(null);
  };
  const addModels = (raw: string) => {
    const names = raw.split(/[,\n]/).map((m) => m.trim()).filter(Boolean);
    if (names.length) setForm((f) => ({ ...f, models: [...f.models, ...names.filter((n) => !f.models.includes(n))] }));
  };
  const withPending = (): ConnectionForm => {
    const extra = newModel.split(/[,\n]/).map((m) => m.trim()).filter((m) => m && !form.models.includes(m));
    return extra.length ? { ...form, models: [...form.models, ...extra] } : form;
  };
  const complete = /^https?:\/\//i.test(form.api_base.trim()) && form.models.length + (newModel.trim() ? 1 : 0) > 0;
  const failed = test && !test.ok ? test.field : null;
  const certificate = dropCert ? null : existing?.certificate ?? null;

  const run = async (kind: 'test' | 'save', action: () => Promise<void>) => {
    setBusy(kind);
    setError(null);
    try { await action(); } catch (e) { setError(message(e)); } finally { setBusy(null); }
  };
  const doTest = () => run('test', async () => {
    const f = withPending();
    setForm(f);
    setNewModel('');
    setTest(await iaApi.test({ ...f, id: existing?.id, certificate_b64: pendingCert ? await toBase64(pendingCert) : undefined }));
  });
  const doSave = () => run('save', async () => {
    const f = withPending();
    const payload = { ...f, last_test: test ?? undefined };
    let state = existing ? await iaApi.update(existing.id, payload) : await iaApi.create(payload);
    const id = existing?.id ?? state.created;
    if (id && dropCert && existing?.certificate) state = await iaApi.removeCertificate(id);
    if (id && pendingCert) {
      await iaApi.uploadCertificate(id, pendingCert.name, await toBase64(pendingCert));
      // L'import efface le dernier test : celui fait avec ce certificat avant d'enregistrer reste valable
      state = test ? await iaApi.update(id, { ...f, api_key: null, last_test: test }) : await iaApi.state();
    }
    onSaved(state);
  });
  const suggestions = (test?.available ?? []).filter((m) => !form.models.includes(m) && !form.models.includes(m.split(':')[0]));

  return (
    <section aria-label={existing ? `Modifier ${existing.name}` : 'Nouvelle connexion'} className="flex flex-col rounded-lg border border-line-strong bg-surface">
      <div className="flex flex-col gap-1 px-6 pt-6">
        <h3 className="m-0 text-[17px] font-bold text-ink">{existing ? `Modifier « ${existing.name} »` : 'Nouvelle connexion'}</h3>
        <p className="m-0 text-sm text-ink-muted">Ces informations sont fournies par votre service informatique ou par le fournisseur du service d'IA.</p>
      </div>
      <div className="flex flex-col gap-5 px-6 py-5">
        {test && <TestBanner test={test} />}
        <Field label="Nom" htmlFor="c-name" hint="Affiché à côté de chaque modèle, dans Studio Dock et dans les apps.">
          <input id="c-name" className={input()} value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Passerelle de l'entreprise" />
        </Field>
        <Field label="Adresse du service" htmlFor="c-url" hint="Compatible OpenAI, elle se termine souvent par /v1. Exemple : https://llm.mon-entreprise.fr/v1">
          <input id="c-url" type="url" className={`${input(failed === 'api_base')} font-mono`} value={form.api_base}
            onChange={(e) => set('api_base', e.target.value)} placeholder="https://llm.mon-entreprise.fr/v1" />
        </Field>
        {form.api_key === null ? (
          <Field label="Clé API" hint={platform === 'windows' ? 'Chiffrée avec votre compte Windows : jamais réaffichée en clair.' : 'Enregistrée sur ce poste : jamais réaffichée en clair.'}>
            <div className={`flex min-h-11 items-center gap-3 rounded border bg-surface-2 pl-3.5 pr-1.5 ${failed === 'api_key' ? 'border-danger' : 'border-line-strong'}`}>
              <span className="flex-1 font-mono text-sm tracking-[0.08em] text-ink-body">•••• •••• {existing?.api_key_hint}</span>
              <button type="button" className={secondary} onClick={() => set('api_key', '')}>Modifier</button>
            </div>
          </Field>
        ) : (
          <Field label="Clé API" htmlFor="c-key" optional hint="Laissez vide pour un service qui n'en demande pas.">
            <div className="flex gap-2">
              <input id="c-key" type={showKey ? 'text' : 'password'} autoComplete="off" className={`${input(failed === 'api_key')} font-mono`}
                value={form.api_key} onChange={(e) => set('api_key', e.target.value)} placeholder="Collez votre clé API" />
              <button type="button" className={`${secondary} shrink-0`} onClick={() => setShowKey((v) => !v)}>{showKey ? 'Masquer' : 'Afficher'}</button>
            </div>
            {existing?.has_api_key && (
              <button type="button" className="self-start border-0 bg-transparent p-0 text-[13px] font-medium text-accent underline" onClick={() => set('api_key', null)}>
                Garder la clé enregistrée
              </button>
            )}
          </Field>
        )}
        <Field label="Certificat de l'entreprise" optional={!certificate && !pendingCert}
          hint={certificate || pendingCert ? undefined : "Seulement pour une adresse https dont le certificat est signé par une autorité interne (fichier .crt fourni par l'informatique)."}>
          {certificate || pendingCert ? (
            <div className={`flex flex-wrap items-center gap-3 rounded border bg-surface px-3.5 py-2.5 ${failed === 'certificate' ? 'border-danger' : 'border-line-strong'}`}>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-ink">{pendingCert?.name ?? certificate?.name}</div>
                <div className="text-[13px] text-ink-muted">
                  {failed === 'certificate' ? 'Non reconnu par le serveur' : pendingCert ? 'Sera enregistré avec la connexion'
                    : [certificate?.imported_at && `importé le ${date(certificate.imported_at)}`, certificate?.expires_at && `expire le ${date(certificate.expires_at)}`].filter(Boolean).join(' · ')}
                </div>
              </div>
              <button type="button" className={secondary} onClick={() => certInput.current?.click()}>Remplacer</button>
              <button type="button" className={secondary} onClick={() => { setPendingCert(null); setDropCert(true); setTest(null); }}>Retirer</button>
            </div>
          ) : (
            <button type="button" onClick={() => certInput.current?.click()}
              className={`flex h-11 items-center justify-center rounded border border-dashed bg-transparent text-sm font-medium text-accent hover:bg-surface-2 ${failed === 'certificate' ? 'border-danger' : 'border-line-strong'}`}>
              Choisir le fichier .crt
            </button>
          )}
          <input ref={certInput} type="file" accept=".crt,.pem,.cer" className="hidden" onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) { setPendingCert(file); setDropCert(false); setTest(null); }
            e.target.value = '';
          }} />
        </Field>
        <Field label="Modèles" hint="Les modèles de ce service à proposer aux apps. Tapez un nom puis Entrée.">
          <div className={`flex flex-wrap items-center gap-2 rounded border bg-surface-2 px-2.5 py-2 ${failed === 'models' ? 'border-danger' : 'border-line-strong'}`}>
            {form.models.map((m) => (
              <span key={m} className={`inline-flex items-center gap-1 rounded py-1 pl-2.5 pr-1 font-mono text-[13px] ${test?.missing?.includes(m) ? 'bg-warning-soft text-warning-text' : 'bg-accent-soft text-accent-ink'}`}>
                {m}
                <button type="button" aria-label={`Retirer ${m}`} onClick={() => set('models', form.models.filter((x) => x !== m))}
                  className="flex h-5 w-5 items-center justify-center rounded border-0 bg-transparent text-current hover:bg-surface-3">×</button>
              </span>
            ))}
            <input aria-label="Ajouter un modèle" value={newModel} onChange={(e) => setNewModel(e.target.value)}
              placeholder={form.models.length ? 'Ajouter un modèle…' : 'Nom du modèle, puis Entrée (ex. mistral-large-latest)'}
              className="min-h-8 min-w-[200px] flex-1 border-0 bg-transparent px-1 font-mono text-sm text-ink placeholder:font-sans placeholder:text-ink-subtle focus:outline-none"
              onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ',') && newModel.trim()) { e.preventDefault(); addModels(newModel); setNewModel(''); } }}
              onBlur={() => { if (newModel.trim()) { addModels(newModel); setNewModel(''); } }} />
          </div>
          {suggestions.length > 0 && (
            <div className="flex flex-col gap-2 rounded bg-surface-2 px-3.5 py-3">
              <span className="text-[13px] text-ink-muted">Proposés par le service : cliquez pour ajouter</span>
              <div className="flex flex-wrap gap-1.5">
                {suggestions.map((m) => (
                  <button key={m} type="button" onClick={() => addModels(m)}
                    className="rounded border border-line-strong bg-surface px-2.5 py-1 font-mono text-[13px] text-ink hover:border-accent hover:text-accent">+ {m}</button>
                ))}
              </div>
            </div>
          )}
        </Field>
        <details className="border-t border-line pt-4">
          <summary className="cursor-pointer text-sm font-medium text-ink-muted hover:text-ink">
            Options avancées · fenêtre de contexte {form.context_tokens ? `${form.context_tokens.toLocaleString('fr-FR')} tokens` : 'par défaut'}
          </summary>
          <div className="mt-4 max-w-[320px]">
            <Field label="Fenêtre de contexte (tokens)" htmlFor="c-ctx" hint="Taille de texte que le modèle accepte en une requête : au-delà, les apps découpent les documents.">
              <input id="c-ctx" type="number" min={1000} className={input()} value={form.context_tokens ?? ''} placeholder="128 000"
                onChange={(e) => set('context_tokens', e.target.value ? Number(e.target.value) : null)} />
            </Field>
          </div>
        </details>
        {error && <p role="alert" className="m-0 rounded-md border border-warning-line bg-warning-soft px-3 py-2 text-sm text-warning-text">{error}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-3 rounded-b-lg border-t border-line bg-surface-2 px-6 py-4">
        <p className="m-0 flex-[1_1_220px] text-[13px] text-ink-subtle">
          {!complete ? "Renseignez l'adresse et au moins un modèle pour tester." : test && !test.ok ? "Vous pouvez enregistrer malgré l'échec : les apps risquent de ne pas fonctionner." : "Testez la connexion avant d'enregistrer."}
        </p>
        <button type="button" onClick={onCancel} className="h-10 border-0 bg-transparent px-2 text-sm font-medium text-ink-muted hover:text-ink">Annuler</button>
        <button type="button" disabled={!complete || busy !== null} onClick={doTest} className={secondary}>
          {busy === 'test' && <IconSpinner />} {busy === 'test' ? 'Test en cours…' : test && !test.ok ? 'Tester à nouveau' : 'Tester la connexion'}
        </button>
        <button type="button" disabled={!complete || busy !== null} onClick={doSave} className={primary}>
          {busy === 'save' && <IconSpinner />} Enregistrer
        </button>
      </div>
    </section>
  );
};

/* ---------- Une connexion, en lecture ---------- */

const ConnectionCard: React.FC<{ c: AiConnection; onEdit: () => void; onChanged: (s: AiState) => void }> = ({ c, onEdit, onChanged }) => {
  const [busy, setBusy] = React.useState(false);
  const [confirm, setConfirm] = React.useState(false);
  const [test, setTest] = React.useState<ConnectionTest | null>(c.last_test);
  const runTest = async () => {
    setBusy(true);
    try {
      setTest(await iaApi.test({ id: c.id, name: c.name, api_base: c.api_base, api_key: null, models: c.models, context_tokens: c.context_tokens }));
    } finally { setBusy(false); }
  };
  return (
    <article className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <h3 className="m-0 text-[17px] font-bold text-ink">{c.name}</h3>
          <span className="break-all font-mono text-[13px] text-ink-muted">{c.api_base}</span>
        </div>
        <button type="button" onClick={runTest} disabled={busy} className={secondary}>{busy ? <IconSpinner /> : <IconRefresh />} Tester</button>
        <button type="button" onClick={onEdit} className={secondary}>Modifier</button>
        {confirm ? (
          <>
            <button type="button" onClick={async () => onChanged(await iaApi.remove(c.id))} className={`${secondary} border-danger text-danger-text`}>Confirmer la suppression</button>
            <button type="button" onClick={() => setConfirm(false)} className="h-10 border-0 bg-transparent px-2 text-sm text-ink-muted">Annuler</button>
          </>
        ) : (
          <button type="button" onClick={() => setConfirm(true)} className={secondary}>Supprimer</button>
        )}
      </div>
      <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
        <dt className="text-ink-muted">Clé API</dt><dd className="m-0 font-mono">{c.has_api_key ? `•••• ${c.api_key_hint}` : <span className="font-sans text-ink-subtle">aucune</span>}</dd>
        <dt className="text-ink-muted">Certificat</dt><dd className="m-0">{c.certificate ? [c.certificate.name, c.certificate.expires_at && `expire le ${date(c.certificate.expires_at)}`].filter(Boolean).join(' · ') : <span className="text-ink-subtle">aucun</span>}</dd>
        <dt className="text-ink-muted">Modèles</dt>
        <dd className="m-0 flex flex-wrap gap-1.5">{c.models.map((m) => <span key={m} className="rounded bg-surface-2 px-2 py-0.5 font-mono text-[13px] text-ink">{m}</span>)}</dd>
      </dl>
      {test ? <TestBanner test={test} /> : <p className="m-0 text-[13px] text-ink-subtle">Pas encore testée.</p>}
    </article>
  );
};

/* ---------- Modèle de chaque app ---------- */

type Option = { value: string; label: string };
const encode = (choice: AiChoice | null | undefined) =>
  !choice ? '' : 'own' in choice ? 'own' : `${choice.connection}|${choice.model}`;
const decode = (value: string): AiChoice | null => {
  if (!value) return null;
  if (value === 'own') return { own: true };
  const [connection, ...model] = value.split('|');
  return { connection, model: model.join('|') };
};

const ModelSelect: React.FC<{ id: string; value: string; onChange: (v: string) => void; connections: AiConnection[]; extra: Option[]; label: string }> = ({
  id, value, onChange, connections, extra, label,
}) => (
  <>
    <label htmlFor={id} className="sr-only">{label}</label>
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)}
      className="h-10 min-w-0 max-w-full flex-[1_1_280px] rounded border border-line-strong bg-surface-2 px-3 text-sm text-ink focus:outline focus:outline-2 focus:outline-focus">
      {extra.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      {connections.map((c) => (
        <optgroup key={c.id} label={c.name}>
          {c.models.map((m) => <option key={m} value={`${c.id}|${m}`}>{m}</option>)}
        </optgroup>
      ))}
    </select>
  </>
);

const Assignments: React.FC<{ state: AiState; onChanged: (s: AiState) => void }> = ({ state, onChanged }) => {
  const [error, setError] = React.useState<string | null>(null);
  const choices = (apps: AiApp[]) => Object.fromEntries(apps.filter((a) => a.choice).map((a) => [a.id, a.choice as AiChoice]));
  const save = async (def: AiState['default'], apps: Record<string, AiChoice>) => {
    setError(null);
    try { onChanged(await iaApi.choose({ default: def, apps })); } catch (e) { setError(message(e)); }
  };
  const label = (choice: AiState['default']) => {
    if (!choice) return 'aucun';
    const c = state.connections.find((x) => x.id === choice.connection);
    return c ? `${choice.model} · ${c.name}` : choice.model;
  };
  if (!state.connections.length) {
    return <p className="m-0 rounded-md border border-dashed border-line-strong px-4 py-3 text-sm text-ink-muted">Ajoutez une connexion ou des modèles Ollama ci-dessous : vous choisirez ensuite le modèle de chaque app.</p>;
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="w-[200px] text-sm font-medium text-ink">Modèle par défaut</span>
        <ModelSelect id="ia-defaut" label="Modèle par défaut" value={encode(state.default)} connections={state.connections} extra={[]}
          onChange={(v) => save(decode(v) as AiState['default'], choices(state.apps))} />
      </div>
      {state.apps.length > 0 ? (
        <ul className="m-0 flex list-none flex-col divide-y divide-line rounded-md border border-line p-0">
          {state.apps.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <span className="flex w-[200px] items-center gap-2.5">
                {a.iconUrl ? <img src={a.iconUrl} alt="" width={28} height={28} className="rounded" /> : <span className="h-7 w-7 rounded bg-surface-3" />}
                <span className="flex flex-col"><span className="text-sm font-medium text-ink">{a.name}</span>
                  {!a.installed && <span className="text-[12px] text-ink-subtle">pas installée</span>}</span>
              </span>
              <ModelSelect id={`ia-${a.id}`} label={`Modèle de ${a.name}`} value={encode(a.choice)} connections={state.connections}
                extra={[{ value: '', label: `Modèle par défaut (${label(state.default)})` }, { value: 'own', label: `Configuration propre à ${a.name}` }]}
                onChange={(v) => {
                  const next = choices(state.apps);
                  const choice = decode(v);
                  if (choice) next[a.id] = choice; else delete next[a.id];
                  save(state.default, next);
                }} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="m-0 text-sm text-ink-muted">Aucune app du catalogue n'utilise l'IA pour l'instant.</p>
      )}
      {error && <p role="alert" className="m-0 text-sm text-warning-text">{error}</p>}
    </div>
  );
};

/* ---------- Ollama ---------- */

export const OllamaSection: React.FC<{ onChanged: (s: AiState) => void }> = ({ onChanged }) => {
  const [state, setState] = React.useState<OllamaState | null>(null);
  const [address, setAddress] = React.useState(OLLAMA);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [context, setContext] = React.useState<number | null>(null);
  const [pull, setPull] = React.useState('');
  const [busy, setBusy] = React.useState<'load' | 'save' | 'pull' | null>('load');
  const [error, setError] = React.useState<string | null>(null);
  const [saved, setSaved] = React.useState(false);

  const apply = (s: OllamaState, init = false) => {
    setState(s);
    if (init) {
      setAddress(s.address);
      setSelected(s.connection?.models ?? []);
      setContext(s.connection?.context_tokens ?? null);
    }
  };
  const load = async (addr?: string, init = false) => {
    setBusy((b) => b ?? 'load');
    setError(null);
    try { apply(await iaApi.ollama(addr), init); } catch (e) { setError(message(e)); } finally { setBusy(null); }
  };
  React.useEffect(() => { load(undefined, true); }, []);
  // Téléchargements en cours : avancement relu toutes les secondes
  const pulling = !!state?.pulls.some((p) => !p.finished);
  React.useEffect(() => {
    if (!pulling) return undefined;
    const t = window.setInterval(() => iaApi.ollama(address).then((s) => apply(s)).catch(() => undefined), 1000);
    return () => window.clearInterval(t);
  }, [pulling, address]);

  const offered = state?.connection?.models ?? [];
  const changed = JSON.stringify([...selected].sort()) !== JSON.stringify([...offered].sort())
    || (selected.length > 0 && (context ?? 4096) !== (state?.connection?.context_tokens ?? 4096));
  const save = async () => {
    setBusy('save');
    setError(null);
    try {
      const r = await iaApi.offerOllama(address, selected, context);
      onChanged(r);
      apply(r.ollama, true);
      setSaved(true);
    } catch (e) { setError(message(e)); } finally { setBusy(null); }
  };
  const startPull = async () => {
    if (!pull.trim()) return;
    setBusy('pull');
    setError(null);
    try { apply(await iaApi.pull(pull.trim(), address)); setPull(''); } catch (e) { setError(message(e)); } finally { setBusy(null); }
  };
  // Modèle téléchargé : coché d'office
  const finished = state?.pulls.filter((p) => p.finished && !p.error).map((p) => p.model).join(',') ?? '';
  React.useEffect(() => {
    if (!state || !finished) return;
    const names = state.models.map((m) => m.name);
    const toAdd = finished.split(',').map((f) => names.find((n) => n === f || n.split(':')[0] === f)).filter((n): n is string => !!n);
    setSelected((s) => [...s, ...toAdd.filter((n) => !s.includes(n))]);
  }, [finished]);

  return (
    <section aria-labelledby="ollama-h" className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-1">
          <h2 id="ollama-h" className="m-0 text-[19px] font-bold text-ink">Modèles locaux avec Ollama</h2>
          <p className="m-0 text-sm text-ink-muted">
            Les modèles tournent sur ce poste : rien ne sort de l'ordinateur, sans clé ni abonnement. Il faut Ollama installé
            et un poste assez puissant (16 Go de mémoire pour un modèle de 7 à 8 milliards de paramètres).
          </p>
        </div>
        {state && (
          <span className={`flex items-center gap-2 rounded-full border px-3 py-1 text-[13px] font-medium ${state.running ? 'border-line bg-success-soft text-success-text' : 'border-line-strong text-ink-muted'}`}>
            <span className={`h-2 w-2 rounded-full ${state.running ? 'bg-success' : 'bg-ink-subtle'}`} aria-hidden="true" />
            {state.running ? `Ollama ${state.version ?? ''} démarré` : 'Ollama non détecté'}
          </span>
        )}
      </div>

      {busy === 'load' && !state && <p className="m-0 flex items-center gap-2 text-sm text-ink-muted"><IconSpinner /> Recherche d'Ollama…</p>}

      {state && !state.running && (
        <div className="flex flex-col gap-3 rounded-md bg-surface-2 px-4 py-4 text-sm text-ink-body">
          <p className="m-0">Ollama ne répond pas à <span className="font-mono">{state.address}</span>. Installez-le, ou démarrez-le s'il l'est déjà, puis réessayez.</p>
          <div className="flex flex-wrap gap-2.5">
            <button type="button" className={secondary} onClick={() => api.openLink('https://ollama.com/download')}><IconExternal /> Télécharger Ollama</button>
            <button type="button" className={secondary} onClick={() => load(address)}><IconRefresh /> Réessayer</button>
          </div>
          {offered.length > 0 && <p className="m-0 text-[13px] text-ink-muted">Modèles proposés aux apps : {offered.join(', ')}. Ils resteront indisponibles tant qu'Ollama est arrêté.</p>}
        </div>
      )}

      {state?.running && (
        <>
          {state.models.length ? (
            <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
              <legend className="mb-2 text-sm font-medium text-ink">Modèles installés : cochez ceux à proposer aux apps</legend>
              <ul className="m-0 flex list-none flex-col divide-y divide-line rounded-md border border-line p-0">
                {state.models.map((m) => (
                  <li key={m.name}>
                    <label className="flex cursor-pointer items-center gap-3 px-4 py-2.5 hover:bg-surface-2">
                      <input type="checkbox" className="h-4 w-4 accent-[var(--nn-primary,currentColor)]" checked={selected.includes(m.name)}
                        onChange={(e) => { setSaved(false); setSelected((s) => e.target.checked ? [...s, m.name] : s.filter((x) => x !== m.name)); }} />
                      <span className="flex-1 font-mono text-sm text-ink">{m.name}</span>
                      <span className="text-[13px] text-ink-muted">{[m.parameters, m.size].filter(Boolean).join(' · ')}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
          ) : (
            <p className="m-0 text-sm text-ink-muted">Aucun modèle installé dans Ollama : téléchargez-en un ci-dessous.</p>
          )}

          <Field label="Télécharger un modèle" htmlFor="ollama-pull"
            hint={<>Nom dans la bibliothèque d'Ollama, par exemple <span className="font-mono">mistral-small</span>, <span className="font-mono">llama3.2</span> ou <span className="font-mono">qwen3:8b</span>. Plusieurs Go : prévoyez du temps et de l'espace disque.</>}>
            <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); startPull(); }}>
              <input id="ollama-pull" className={`${input()} flex-[1_1_240px] font-mono`} value={pull} onChange={(e) => setPull(e.target.value)} placeholder="mistral-small" />
              <button type="submit" disabled={!pull.trim() || busy === 'pull'} className={secondary}><IconDownload /> Télécharger</button>
              <button type="button" className={secondary} onClick={() => api.openLink('https://ollama.com/library')}><IconExternal /> Bibliothèque</button>
            </form>
          </Field>
          {state.pulls.map((p) => (
            <div key={p.model} className="flex flex-col gap-1.5" role="status">
              <div className="flex justify-between gap-3 text-sm">
                <span className="font-mono text-ink">{p.model}</span>
                <span className={p.error ? 'text-warning-text' : 'text-ink-muted'}>
                  {p.error ?? `${p.status}${p.total && !p.finished ? ` ${Math.round((p.completed / p.total) * 100)} %` : ''}`}
                </span>
              </div>
              {!p.finished && (
                <div className="h-1.5 overflow-hidden rounded-full bg-surface-3">
                  <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${p.total ? Math.round((p.completed / p.total) * 100) : 4}%` }} />
                </div>
              )}
            </div>
          ))}

          <details className="border-t border-line pt-4">
            <summary className="cursor-pointer text-sm font-medium text-ink-muted hover:text-ink">
              Options avancées · contexte {(context ?? 4096).toLocaleString('fr-FR')} tokens · {address}
            </summary>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Field label="Fenêtre de contexte (tokens)" htmlFor="ollama-ctx"
                hint="Ollama utilise 4 096 tokens par défaut, même si le modèle accepte plus. Si vous l'avez augmentée dans les réglages d'Ollama, indiquez la même valeur.">
                <input id="ollama-ctx" type="number" min={1000} className={input()} value={context ?? ''} placeholder="4 096"
                  onChange={(e) => { setSaved(false); setContext(e.target.value ? Number(e.target.value) : null); }} />
              </Field>
              <Field label="Adresse d'Ollama" htmlFor="ollama-url" hint="À changer seulement pour un serveur Ollama sur un autre ordinateur.">
                <div className="flex gap-2">
                  <input id="ollama-url" className={`${input()} font-mono`} value={address} onChange={(e) => setAddress(e.target.value)} />
                  <button type="button" className={`${secondary} shrink-0`} onClick={() => load(address)}>Lire</button>
                </div>
              </Field>
            </div>
          </details>

          <div className="flex flex-wrap items-center gap-3">
            <button type="button" disabled={!changed || busy === 'save'} onClick={save} className={primary}>
              {busy === 'save' && <IconSpinner />} Proposer {selected.length > 1 ? `ces ${selected.length} modèles` : selected.length ? 'ce modèle' : 'aucun modèle'} aux apps
            </button>
            {saved && !changed && <span role="status" className="text-sm text-success-text">Enregistré.</span>}
          </div>
        </>
      )}
      {error && <p role="alert" className="m-0 text-sm text-warning-text">{error}</p>}
    </section>
  );
};

/* ---------- Page ---------- */

export const AiPage: React.FC = () => {
  const platform = React.useContext(PlatformContext);
  const [state, setState] = React.useState<AiState | null>(null);
  const [editing, setEditing] = React.useState<string | 'new' | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { iaApi.state().then(setState).catch((e) => setError(message(e))); }, []);
  const services = state?.connections.filter((c) => c.provider !== 'ollama') ?? [];

  return (
    <div className="flex flex-col gap-6">
      <a href="#/" className="flex min-h-8 items-center gap-1.5 self-start text-sm text-ink-muted no-underline hover:text-ink">
        <IconBack /> Mes applications
      </a>
      <h1 className="m-0 text-[30px] font-bold leading-tight text-ink">Réglages</h1>
      <SettingsTabs current="ia" />
      <p className="m-0 flex items-start gap-2.5 rounded-md border border-line bg-surface px-4 py-3 text-sm text-ink-body">
        <span><strong className="font-semibold text-ink">Réglés une fois, utilisés par toutes vos apps.</strong> SpecGen, AuditErgo,
          DocAnalyser et les prochaines apps de la suite reprennent ces connexions. Elles restent sur ce poste
          {platform === 'windows' ? ' ; les clés sont chiffrées avec votre compte Windows' : ''} et ne changent rien pour vos collègues.</span>
      </p>
      {error && <p role="alert" className="m-0 text-sm text-warning-text">{error}</p>}

      <section aria-labelledby="choix-h" className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6">
        <div className="flex flex-col gap-1">
          <h2 id="choix-h" className="m-0 text-[19px] font-bold text-ink">Modèle utilisé par les apps</h2>
          <p className="m-0 text-sm text-ink-muted">Le modèle par défaut sert à toutes les apps, sauf celles pour lesquelles vous en choisissez un autre.
            Dans les apps, on peut aussi prendre un autre de ces modèles au moment de lancer une génération ou une analyse.</p>
        </div>
        {state ? <Assignments state={state} onChanged={setState} /> : <p className="m-0 flex items-center gap-2 text-sm text-ink-muted"><IconSpinner /> Chargement…</p>}
      </section>

      <section aria-labelledby="services-h" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-1">
            <h2 id="services-h" className="m-0 text-[19px] font-bold text-ink">Services d'IA</h2>
            <p className="m-0 text-sm text-ink-muted">Passerelle de l'entreprise, Mistral, OpenAI, Gemini… tout service compatible OpenAI, avec sa clé et ses modèles.</p>
          </div>
          {editing === null && (
            <button type="button" onClick={() => setEditing('new')} className={primary}>+ Ajouter un service</button>
          )}
        </div>
        {editing === 'new' && <ConnectionEditor existing={null} onCancel={() => setEditing(null)} onSaved={(s) => { setState(s); setEditing(null); }} />}
        {services.map((c) => editing === c.id
          ? <ConnectionEditor key={c.id} existing={c} onCancel={() => setEditing(null)} onSaved={(s) => { setState(s); setEditing(null); }} />
          : <ConnectionCard key={`${c.id}-${c.last_test?.at ?? ''}`} c={c} onEdit={() => setEditing(c.id)} onChanged={setState} />)}
        {state && !services.length && editing === null && (
          <p className="m-0 rounded-md border border-dashed border-line-strong px-4 py-3 text-sm text-ink-muted">Aucun service enregistré.</p>
        )}
      </section>

      <OllamaSection onChanged={setState} />

      {state && <p className="m-0 text-[13px] text-ink-subtle">Enregistré dans <span className="font-mono">{state.folder}</span></p>}
    </div>
  );
};
