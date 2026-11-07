import React from 'react';
import type { DockApp, DockState } from './types';
import { Actions, AppActions, AppIcon, AppNotice, IconBack, IconChevron, IconFolder, StatusLine, where } from './ui';

/* ---------- Accueil ---------- */

const AppCard: React.FC<{ app: DockApp; actions: Actions; pending: boolean }> = ({ app, actions, pending }) => (
  <article className="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6 hover:border-line-strong">
    <div className="flex items-start gap-3.5">
      <AppIcon app={app} size={48} />
      <div className="flex min-w-0 flex-grow flex-col gap-0.5">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="clamp-1 m-0 min-w-0 text-[19px] font-bold leading-snug text-ink">
            <a href={`#/app/${app.id}`} className="text-inherit no-underline hover:underline">{app.name}</a>
          </h2>
          {app.version && (
            <span className="shrink-0 rounded-full border border-line bg-surface-2 px-2 font-mono text-xs text-ink-subtle">v{app.version}</span>
          )}
        </div>
        {app.tagline && <p className="clamp-1 m-0 text-sm text-ink-body">{app.tagline}</p>}
        <a href={`#/app/${app.id}`} className="mt-1 flex min-h-6 items-center gap-1 self-start text-[13px] font-medium text-accent no-underline hover:underline">
          Fiche et prise en main <IconChevron />
        </a>
      </div>
    </div>
    <AppNotice app={app} actions={actions} />
    <div className="mt-auto flex flex-col gap-3">
      <StatusLine app={app} />
      <AppActions app={app} actions={actions} pending={pending} />
    </div>
  </article>
);

export const Home: React.FC<{ state: DockState; actions: Actions; pending: Set<string> }> = ({ state, actions, pending }) => (
  <div className="flex flex-col gap-6">
    <div className="flex flex-col gap-1.5">
      <h1 className="m-0 text-[30px] font-bold leading-tight text-ink">Mes applications</h1>
      <p className="m-0 max-w-[680px] text-ink-muted">Vos outils, lancés depuis un seul endroit.</p>
    </div>
    {state.apps.length === 0 ? (
      <div className="rounded-lg border border-dashed border-line-dashed bg-surface p-8 text-center text-ink-muted">
        Aucune application dans <span className="font-mono">{state.catalogue}</span>.
      </div>
    ) : (
      <div className="grid gap-5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
        {state.apps.map((app) => <AppCard key={app.id} app={app} actions={actions} pending={pending.has(app.id)} />)}
      </div>
    )}
  </div>
);

/* ---------- Fiche d'une app ---------- */

const Info: React.FC<{ label: string; children: React.ReactNode; mono?: boolean }> = ({ label, children, mono }) => (
  <>
    <dt className="text-ink-subtle">{label}</dt>
    <dd className={`m-0 min-w-0 break-words ${mono ? 'font-mono text-[13px]' : ''}`}>{children}</dd>
  </>
);

export const AppPage: React.FC<{ app: DockApp; actions: Actions; pending: boolean }> = ({ app, actions, pending }) => (
  <div className="flex flex-col gap-7">
    <a href="#/" className="flex min-h-8 items-center gap-1.5 self-start text-sm text-ink-muted no-underline hover:text-ink">
      <IconBack /> Mes applications
    </a>

    <section className="flex flex-wrap items-center gap-x-7 gap-y-5 rounded-lg border border-line bg-surface p-7">
      <AppIcon app={app} size={72} />
      <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="m-0 text-[30px] font-bold leading-tight text-ink">{app.name}</h1>
          {app.version && (
            <span className="rounded-full border border-line bg-surface-2 px-2 font-mono text-xs text-ink-subtle">v{app.version}</span>
          )}
        </div>
        {app.tagline && <p className="m-0 text-[17px] text-ink-muted">{app.tagline}</p>}
        <div className="mt-1"><StatusLine app={app} /></div>
      </div>
      <AppActions app={app} actions={actions} pending={pending} wide />
      {(app.state === 'error' || app.state === 'missing') && (
        <div className="w-full"><AppNotice app={app} actions={actions} /></div>
      )}
    </section>

    <div className="flex flex-wrap items-start gap-7">
      <div className="flex min-w-0 flex-[999_1_560px] flex-col gap-7">
        {(app.description || app.points.length > 0) && (
          <section className="flex flex-col gap-2.5">
            <h2 className="m-0 text-[21px] font-bold text-ink">À quoi sert {app.name}</h2>
            {app.description && <p className="m-0 max-w-[680px] leading-relaxed">{app.description}</p>}
            {app.points.length > 0 && (
              <ul className="m-0 mt-1 flex list-disc flex-col gap-1.5 pl-5">
                {app.points.map((p) => <li key={p}>{p}</li>)}
              </ul>
            )}
          </section>
        )}

        {app.tutorial.length > 0 && (
          <section className="flex flex-col gap-3.5">
            <h2 className="m-0 text-[21px] font-bold text-ink">Prise en main</h2>
            <ol className="m-0 flex list-none flex-col gap-3 p-0">
              {app.tutorial.map((step, i) => (
                <li key={step.title} className="flex gap-4 rounded-md border border-line bg-surface px-[18px] py-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft font-bold text-accent-ink" aria-hidden="true">{i + 1}</span>
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="font-bold text-ink">{step.title}</span>
                    {step.text && <span className="text-sm text-ink-muted">{step.text}</span>}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>

      <aside className="flex min-w-0 flex-[1_1_280px] flex-col gap-4">
        <section className="rounded-md border border-line bg-surface p-[18px]">
          <h2 className="m-0 mb-3 text-base font-bold text-ink">Informations</h2>
          <dl className="m-0 grid gap-x-4 gap-y-2 text-sm" style={{ gridTemplateColumns: 'auto minmax(0, 1fr)' }}>
            <Info label="Version" mono>{app.version ?? '—'}</Info>
            <Info label="Type">{app.kind === 'web' ? 'App web locale' : 'App de bureau'}</Info>
            {app.kind === 'web' && <Info label="Adresse" mono>{where(app)}</Info>}
            <Info label="IA">{app.ai ? 'Utilise vos connexions aux modèles' : 'Aucune'}</Info>
            <Info label="Emplacement" mono>{app.location ?? 'introuvable'}</Info>
          </dl>
          {app.folder && (
            <button type="button" onClick={() => actions.folder(app)}
              className="mt-3.5 flex h-10 items-center gap-2 rounded border border-line-strong bg-surface px-3.5 text-sm font-medium text-ink-body hover:bg-surface-3">
              <IconFolder /> Ouvrir le dossier
            </button>
          )}
        </section>

        {app.links.length > 0 && (
          <section className="flex flex-col gap-2 rounded-md border border-line bg-surface p-[18px] text-sm">
            <h2 className="m-0 mb-0.5 text-base font-bold text-ink">Liens</h2>
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
