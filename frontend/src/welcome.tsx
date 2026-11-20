import React from 'react';
import { api, iaApi } from './api';
import { ConnectionEditor, OllamaSection } from './ia';
import { NetworkPanel, OnlinePanel } from './screens';
import type { AiState, DockApp, DockState, Settings } from './types';
import { DockLogo, IconFolder, IconSpinner, PlatformContext } from './ui';

/* Tutoriel de première connexion : ce qu'est Studio Dock, où sont vos apps, d'où viennent celles de l'équipe,
   les modèles d'IA, et comment se servir des cartes. Revu à tout moment depuis le pied de page. */

const secondary = 'flex h-11 items-center gap-2 rounded border border-line-strong bg-surface px-4 text-sm font-medium text-ink-body hover:bg-surface-3 disabled:opacity-50';
const primary = 'flex h-11 items-center gap-2 rounded border-0 bg-primary px-5 text-sm font-medium text-primary-on hover:bg-primary-hover disabled:opacity-60';

const Point: React.FC<{ n: string; title: string; children: React.ReactNode }> = ({ n, title, children }) => (
  <li className="flex gap-3.5">
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-[15px] font-bold text-accent-ink" aria-hidden="true">{n}</span>
    <span className="flex flex-col gap-0.5">
      <span className="font-semibold text-ink">{title}</span>
      <span className="text-sm text-ink-muted">{children}</span>
    </span>
  </li>
);

/** Petite carte d'app factice, pour montrer où cliquer. */
const DemoCard: React.FC<{ label: string; action: string; tone: 'primary' | 'secondary'; status: string }> = ({ label, action, tone, status }) => (
  <div className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-4" aria-hidden="true">
    <div className="flex items-center gap-3">
      <span className="h-10 w-10 rounded-[22%] bg-gradient-to-br from-accent to-primary" />
      <span className="flex flex-col"><span className="font-semibold text-ink">{label}</span><span className="text-[13px] text-ink-muted">{status}</span></span>
    </div>
    <span className={`flex h-9 items-center justify-center rounded text-sm font-medium ${tone === 'primary' ? 'bg-primary text-primary-on' : 'border border-line-strong text-ink-body'}`}>{action}</span>
  </div>
);

type Source = 'reseau' | 'en-ligne' | 'plus-tard';
type Ia = 'service' | 'ollama' | 'plus-tard';

export const Welcome: React.FC<{ state: DockState; onDone: (next?: string) => void; openHome: () => void }> = ({ state, onDone, openHome }) => {
  const platform = React.useContext(PlatformContext);
  const [step, setStep] = React.useState(0);
  const [settings, setSettings] = React.useState<Settings | null>(null);
  const [source, setSource] = React.useState<Source>('reseau');
  const [closing, setClosing] = React.useState(false);
  const [ia, setIa] = React.useState<Ia>('service');
  const [aiState, setAiState] = React.useState<AiState | null>(null);
  const [chosen, setChosen] = React.useState<Set<string>>(new Set());
  const [chosenInit, setChosenInit] = React.useState(false);
  const titre = React.useRef<HTMLHeadingElement>(null);

  React.useEffect(() => {
    api.settings().then((s) => {
      setSettings(s);
      setSource(s.shared_folder ? 'reseau' : s.catalogue_link ? 'en-ligne' : 'reseau');
    }).catch(() => undefined);
  }, []);
  React.useEffect(() => { iaApi.state().then(setAiState).catch(() => undefined); }, []);
  // Le focus suit l'étape : un lecteur d'écran annonce le nouveau titre
  React.useEffect(() => { if (step > 0) titre.current?.focus(); }, [step]);

  const ai = state.apps.some((a) => a.ai);
  // Apps de l'équipe pas encore installées : à cocher pour les installer à la fin du tutoriel
  const installables = state.apps.filter((a) => !a.installed && a.availableVersion && a.mode !== 'masque');
  React.useEffect(() => {
    if (chosenInit || !installables.length) return;
    setChosen(new Set(installables.map((a) => a.id)));
    setChosenInit(true);
  }, [installables.length, chosenInit]);
  const steps = ['Bienvenue', 'Vos applications', 'Les applications de l\'équipe', ...(ai ? ['Modèles d\'IA'] : []),
    'Vos premières apps', 'C\'est prêt'];
  const connections = aiState?.connections ?? [];
  const last = step === steps.length - 1;
  const teamOk = !!settings && (settings.shared_folder ? settings.hasCatalogue : !!settings.catalogue_link);
  const folder = settings?.install.folder ?? settings?.home ?? state.home;
  const sep = platform === 'windows' ? '\\' : '/';

  const finish = async (next?: string, installer = false) => {
    setClosing(true);
    try { await api.welcomeDone(true); } catch { /* le tutoriel reviendra au prochain lancement */ }
    if (installer) {
      // Une à une : en ligne, chacune ouvre sa page de téléchargement
      for (const app of installables.filter((a) => chosen.has(a.id))) {
        try { await api.install(app.id); if (app.isNew) await api.seen([app.id]); } catch { /* signalé sur sa carte */ }
      }
    }
    onDone(next);
  };
  const toInstall = installables.filter((a) => chosen.has(a.id));

  const body = () => {
    switch (steps[step]) {
      case 'Bienvenue':
        return (
          <>
            <div className="flex items-center gap-4">
              <DockLogo />
              <div className="flex flex-col">
                <h1 ref={titre} tabIndex={-1} className="m-0 text-[28px] font-bold leading-tight text-ink outline-none">Bienvenue dans Studio Dock</h1>
                <p className="m-0 text-[15px] text-ink-muted">Vos outils de design, réunis au même endroit.</p>
              </div>
            </div>
            <ul className="m-0 flex list-none flex-col gap-4 p-0">
              <Point n="1" title="Installez les outils de l'équipe">SpecGen, AuditErgo, DocAnalyser, Mapline… en un clic, sans chercher les fichiers.</Point>
              <Point n="2" title="Lancez-les depuis ici">Chaque outil s'ouvre dans votre navigateur ou dans sa fenêtre ; Studio Dock les garde en route.</Point>
              <Point n="3" title="Recevez les nouvelles versions">Quand l'équipe publie une mise à jour, sa carte vous la propose.</Point>
            </ul>
            <p className="m-0 text-sm text-ink-muted">Quelques réglages rapides et c'est parti. Tout se modifie ensuite dans Réglages.</p>
          </>
        );
      case 'Vos applications':
        return (
          <>
            <h1 ref={titre} tabIndex={-1} className="m-0 text-[26px] font-bold leading-tight text-ink outline-none">Vos applications, sur ce poste</h1>
            <p className="m-0 text-[15px] text-ink-body">
              Studio Dock et vos applications sont installés dans votre dossier personnel. Elles en sont lancées :
              c'est le seul endroit autorisé par l'entreprise, ni le dossier de l'équipe, ni vos Téléchargements.
            </p>
            <div className="flex flex-col gap-2 rounded-md bg-surface-2 p-4">
              <span className="text-[13px] font-medium text-ink-subtle">Votre dossier</span>
              <span className="break-all font-mono text-sm text-ink">{folder}</span>
              <span className="text-[13px] text-ink-muted">Une application par dossier : <span className="font-mono">{`${folder}${sep}apps${sep}`}&lt;app&gt;</span></span>
              <button type="button" onClick={openHome} className={`${secondary} mt-1 h-9 self-start`}><IconFolder /> Afficher le dossier</button>
            </div>
            <p className="m-0 text-sm text-ink-muted">Il vous est propre : personne d'autre n'y écrit. Pour le déplacer : Réglages › Mon espace.</p>
          </>
        );
      case 'Les applications de l\'équipe':
        return (
          <>
            <h1 ref={titre} tabIndex={-1} className="m-0 text-[26px] font-bold leading-tight text-ink outline-none">Où sont les applications de l'équipe ?</h1>
            <p className="m-0 text-[15px] text-ink-body">
              L'équipe dépose ses outils et leurs nouvelles versions dans un dossier commun. Indiquez-le à Studio Dock :
              il y trouvera les apps à vous proposer et les copiera dans votre dossier.
            </p>
            <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
              <legend className="sr-only">Où sont les applications de l'équipe</legend>
              {([
                ['reseau', 'Un dossier réseau Windows', 'Un lecteur de l\'entreprise, par exemple Q:\\Studio Dock. Le plus simple.'],
                ['en-ligne', 'Un dossier en ligne', 'SharePoint ou Teams, ouvert avec votre compte de l\'entreprise.'],
                ['plus-tard', 'Je le ferai plus tard', 'Vous pourrez l\'indiquer dans Réglages › Mon espace.'],
              ] as const).map(([value, label, hint]) => (
                <label key={value} className={`flex cursor-pointer items-start gap-3 rounded-md border px-4 py-3 ${source === value ? 'border-primary bg-surface' : 'border-line bg-surface-2 hover:border-line-strong'}`}>
                  <input type="radio" name="welcome-source" className="mt-1" checked={source === value} onChange={() => setSource(value)} />
                  <span className="flex flex-col"><span className="text-sm font-semibold text-ink">{label}</span><span className="text-[13px] text-ink-muted">{hint}</span></span>
                </label>
              ))}
            </fieldset>
            {source === 'reseau' && <NetworkPanel settings={settings} platform={platform} openShared={() => api.openFolder('shared')} onSaved={setSettings} />}
            {source === 'en-ligne' && <OnlinePanel settings={settings} onSaved={setSettings} />}
            {source !== 'plus-tard' && !teamOk && (
              <p className="m-0 text-[13px] text-ink-subtle">Vous ne connaissez pas l'adresse ? Demandez-la à la personne qui gère le catalogue de l'équipe.</p>
            )}
          </>
        );
      case 'Modèles d\'IA':
        return (
          <>
            <h1 ref={titre} tabIndex={-1} className="m-0 text-[26px] font-bold leading-tight text-ink outline-none">L'IA, réglée une seule fois</h1>
            <p className="m-0 text-[15px] text-ink-body">
              {state.apps.filter((a) => a.ai).map((a) => a.name).join(', ')} utilisent un modèle d'IA. Réglez votre connexion ici :
              toutes ces apps la reprennent. Vous pourrez en ajouter d'autres et choisir un modèle par app dans Réglages › Modèles d'IA.
            </p>
            {connections.length > 0 && (
              <p role="status" className="m-0 flex items-center gap-2 rounded-md bg-success-soft px-4 py-2.5 text-sm text-success-text">
                <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" />
                Déjà réglé : {connections.map((c) => `${c.name} (${c.models.length} modèle${c.models.length > 1 ? 's' : ''})`).join(', ')}.
              </p>
            )}
            <fieldset className="m-0 flex flex-col gap-2 border-0 p-0 sm:flex-row">
              <legend className="sr-only">Connexion aux modèles d'IA</legend>
              {([
                ['service', 'Le service de l\'entreprise', 'Adresse et clé fournies par l\'informatique.'],
                ['ollama', 'Des modèles sur ce poste', 'Avec Ollama : rien ne sort de l\'ordinateur.'],
                ['plus-tard', 'Plus tard', 'Chaque app garde ses propres réglages.'],
              ] as const).map(([value, label, hint]) => (
                <label key={value} className={`flex flex-1 cursor-pointer items-start gap-3 rounded-md border px-4 py-3 ${ia === value ? 'border-primary bg-surface' : 'border-line bg-surface-2 hover:border-line-strong'}`}>
                  <input type="radio" name="welcome-ia" className="mt-1" checked={ia === value} onChange={() => setIa(value)} />
                  <span className="flex flex-col"><span className="text-sm font-semibold text-ink">{label}</span><span className="text-[13px] text-ink-muted">{hint}</span></span>
                </label>
              ))}
            </fieldset>
            {ia === 'service' && (
              connections.some((c) => c.provider !== 'ollama')
                ? <p className="m-0 text-sm text-ink-muted">Un service est déjà enregistré. Pour en ajouter un autre : Réglages › Modèles d'IA.</p>
                : <ConnectionEditor key="nouveau" existing={null} onSaved={setAiState} onCancel={() => setIa('plus-tard')} />
            )}
            {ia === 'ollama' && <OllamaSection onChanged={setAiState} />}
          </>
        );
      case 'Vos premières apps':
        return (
          <>
            <h1 ref={titre} tabIndex={-1} className="m-0 text-[26px] font-bold leading-tight text-ink outline-none">Vos premières applications</h1>
            {installables.length ? (
              <>
                <p className="m-0 text-[15px] text-ink-body">
                  Cochez celles à installer : Studio Dock s'en occupe à la fin du tutoriel.
                  {state.source === 'online' && ' Pour chacune, une page de téléchargement s\'ouvre dans le navigateur : téléchargez le fichier, Studio Dock le récupère.'}
                </p>
                <ul className="m-0 flex list-none flex-col divide-y divide-line rounded-md border border-line p-0">
                  {installables.map((a: DockApp) => (
                    <li key={a.id}>
                      <label className="flex cursor-pointer items-center gap-3.5 px-4 py-3 hover:bg-surface-2">
                        <input type="checkbox" className="h-4 w-4" checked={chosen.has(a.id)}
                          onChange={(e) => setChosen((c) => { const n = new Set(c); if (e.target.checked) n.add(a.id); else n.delete(a.id); return n; })} />
                        {a.iconUrl ? <img src={a.iconUrl} alt="" width={36} height={36} className="rounded-[22%]" /> : <span className="h-9 w-9 rounded-[22%] bg-surface-3" />}
                        <span className="flex min-w-0 flex-1 flex-col">
                          <span className="font-medium text-ink">{a.name} <span className="text-[13px] font-normal text-ink-subtle">{a.availableVersion}</span></span>
                          <span className="truncate text-[13px] text-ink-muted">{a.tagline}</span>
                        </span>
                        {a.mode === 'auto' && <span className="rounded-full bg-accent-soft px-2 py-px text-[12px] text-accent-ink">pour toute l'équipe</span>}
                      </label>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="m-0 text-[15px] text-ink-body">
                {state.source === 'local'
                  ? 'Aucune application de l\'équipe pour l\'instant : indiquez le dossier de l\'équipe (étape précédente ou Réglages › Mon espace), elles apparaîtront ici et sur la page d\'accueil.'
                  : 'Toutes les applications de l\'équipe sont déjà installées sur ce poste.'}
              </p>
            )}
          </>
        );
      default:
        return (
          <>
            <h1 ref={titre} tabIndex={-1} className="m-0 text-[26px] font-bold leading-tight text-ink outline-none">C'est prêt</h1>
            <p className="m-0 text-[15px] text-ink-body">
              {toInstall.length ? `${toInstall.map((a) => a.name).join(', ')} ${toInstall.length > 1 ? 'vont être installées' : 'va être installée'} : suivez l'avancement sur ${toInstall.length > 1 ? 'leur carte' : 'sa carte'}.`
                : teamOk ? 'Les applications de l\'équipe apparaissent dans « Disponibles pour vous ».'
                  : 'Dès que le dossier de l\'équipe sera indiqué, ses applications apparaîtront dans « Disponibles pour vous ».'}
            </p>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="flex flex-col gap-2">
                <DemoCard label="SpecGen" status="Disponible" action="Installer" tone="primary" />
                <span className="text-[13px] text-ink-muted"><b className="text-ink">Installer</b> copie l'app dans votre dossier.</span>
              </div>
              <div className="flex flex-col gap-2">
                <DemoCard label="SpecGen" status="Installée" action="Lancer" tone="primary" />
                <span className="text-[13px] text-ink-muted"><b className="text-ink">Lancer</b> l'ouvre ; un clic sur la carte affiche sa fiche et sa prise en main.</span>
              </div>
              <div className="flex flex-col gap-2">
                <DemoCard label="SpecGen" status="Version 1.4.0 disponible" action="Mettre à jour" tone="secondary" />
                <span className="text-[13px] text-ink-muted"><b className="text-ink">Mettre à jour</b> quand l'équipe publie une version.</span>
              </div>
            </div>
            <p className="m-0 text-sm text-ink-muted">
              Les apps qui s'ouvrent dans le navigateur s'arrêtent quand vous fermez Studio Dock : gardez-le ouvert pendant que vous travaillez.
              La visite guidée vous montre ensuite chaque élément de la page ; elle et ce tutoriel restent accessibles en bas de la page.
            </p>
          </>
        );
    }
  };

  return (
    <section aria-label="Tutoriel de première connexion" className="mx-auto flex w-full max-w-[760px] flex-col overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <ol className="m-0 flex list-none gap-1.5 border-b border-line bg-surface-2 px-8 py-4" aria-label="Étapes">
        {steps.map((label, i) => (
          <li key={label} className="flex flex-1 flex-col gap-1.5" aria-current={i === step ? 'step' : undefined}>
            <span className={`h-1.5 rounded-full ${i <= step ? 'bg-primary' : 'bg-surface-3'}`} />
            <span className={`hidden text-[12px] sm:block ${i === step ? 'font-semibold text-ink' : 'text-ink-subtle'}`}>{label}</span>
          </li>
        ))}
      </ol>
      <div className="flex min-h-[380px] flex-col gap-5 px-8 py-7">{body()}</div>
      <div className="flex flex-wrap items-center gap-3 border-t border-line bg-surface-2 px-8 py-4">
        <button type="button" onClick={() => finish()} disabled={closing} className="h-11 border-0 bg-transparent px-1 text-sm text-ink-muted hover:text-ink">
          Passer le tutoriel
        </button>
        <span className="flex-grow" />
        {step > 0 && <button type="button" onClick={() => setStep(step - 1)} className={secondary}>Précédent</button>}
        {last ? (
          <>
            <button type="button" onClick={() => finish('#/visite', true)} disabled={closing} className={secondary}>
              Faire la visite guidée
            </button>
            <button type="button" onClick={() => finish(undefined, true)} disabled={closing} className={primary}>
              {closing && <IconSpinner />} {toInstall.length ? 'Installer et voir mes applications' : 'Voir mes applications'}
            </button>
          </>
        ) : (
          <button type="button" onClick={() => setStep(step + 1)} className={primary}>
            {steps[step] === 'Les applications de l\'équipe' && source !== 'plus-tard' && !teamOk ? 'Continuer sans' : 'Suivant'}
          </button>
        )}
      </div>
    </section>
  );
};
