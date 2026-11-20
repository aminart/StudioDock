import React from 'react';

/* Visite guidée : un projecteur passe sur les vrais éléments de la page d'accueil, avec une bulle d'explication.
   Rien n'est réglé ; les étapes dont l'élément n'est pas affiché (pas d'app installée, pas de mise à jour…)
   sont sautées. Clavier : ← → pour naviguer, Échap pour quitter. */

interface Step {
  target?: string; // valeur de data-tour ; absent : bulle centrée
  title: string;
  text: string;
}

const STEPS: Step[] = [
  { title: 'Visite de Studio Dock', text: 'Une minute pour faire le tour : vos applications, comment les lancer, les mettre à jour et où trouver les réglages. Rien n\'est modifié pendant la visite.' },
  { target: 'carte', title: 'Une application installée', text: 'Chaque carte est une app installée sur ce poste. La bordure bleue signale celle qui est ouverte.' },
  { target: 'fiche', title: 'Sa fiche', text: 'Cliquez sur l\'icône ou le nom pour ouvrir la fiche : à quoi sert l\'app, sa prise en main pas à pas et des liens utiles.' },
  { target: 'etat', title: 'Son état et ses boutons', text: 'L\'état indique si l\'app est prête, en cours de démarrage, ouverte ou occupée. « Lancer » l\'ouvre ; une fois lancée, « Ouvrir » la ramène au premier plan.' },
  { target: 'maj', title: 'Une mise à jour', text: 'Quand l\'équipe publie une nouvelle version, ce bouton apparaît : un clic et l\'app est à jour.' },
  { target: 'menu', title: 'Plus d\'actions', text: 'Le menu ⋮ : sa fiche, son dossier sur ce poste, ou la retirer de ce poste.' },
  { target: 'resume', title: 'En un coup d\'œil', text: 'Combien d\'apps sont ouvertes et combien de mises à jour vous attendent.' },
  { target: 'en-ligne', title: 'Le catalogue en ligne', text: 'Votre équipe partage ses apps en ligne : vérifiez ici les mises à jour du catalogue.' },
  { target: 'dispo', title: 'Disponibles pour vous', text: 'Les apps proposées par l\'équipe que vous n\'avez pas encore. « Installer » les copie dans votre dossier ; le badge « Nouveau » signale les dernières arrivées.' },
  { target: 'reglages', title: 'Réglages', text: 'Votre dossier d\'applications, l\'endroit où l\'équipe range les siennes, et les modèles d\'IA communs à toutes vos apps.' },
  { target: 'theme', title: 'Clair ou sombre', text: 'Passez de l\'affichage clair à l\'affichage sombre.' },
  { target: 'pied', title: 'En bas de page', text: 'Relancer cette visite ou le tutoriel, ouvrir votre dossier d\'installation et les journaux à transmettre en cas de souci.' },
  { title: 'C\'est tout !', text: 'Gardez Studio Dock ouvert pendant que vous travaillez : les apps qui s\'ouvrent dans le navigateur s\'arrêtent avec lui. Cette visite se relance en bas de la page.' },
];

const MARGE = 8;

const element = (target?: string): HTMLElement | null =>
  target ? document.querySelector<HTMLElement>(`[data-tour="${target}"]`) : null;

export const Tour: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  // Seules les étapes dont l'élément est affiché, relevées une fois la page dessinée (la visite s'ouvre avec elle)
  const [steps, setSteps] = React.useState<Step[] | null>(null);
  React.useEffect(() => {
    const t = window.setTimeout(() => setSteps(STEPS.filter((s) => !s.target || element(s.target))), 50);
    return () => window.clearTimeout(t);
  }, []);
  if (!steps) return null;
  return <Visite steps={steps} onClose={onClose} />;
};

const Visite: React.FC<{ steps: Step[]; onClose: () => void }> = ({ steps, onClose }) => {
  const [i, setI] = React.useState(0);
  const [rect, setRect] = React.useState<DOMRect | null>(null);
  const bulle = React.useRef<HTMLDivElement>(null);
  const step = steps[i];

  const mesurer = React.useCallback(() => {
    const el = element(step.target);
    setRect(el ? el.getBoundingClientRect() : null);
  }, [step]);

  // Amène l'élément à l'écran (sous l'en-tête fixe), puis suit défilement et redimensionnement
  React.useEffect(() => {
    const el = element(step.target);
    if (el) {
      const r = el.getBoundingClientRect();
      if (r.top < 90 || r.bottom > window.innerHeight - 200) {
        window.scrollTo({ top: window.scrollY + r.top - 120, behavior: 'smooth' });
      }
    }
    mesurer();
    const t = window.setTimeout(mesurer, 350);
    window.addEventListener('scroll', mesurer, { passive: true });
    window.addEventListener('resize', mesurer);
    bulle.current?.focus();
    return () => { window.clearTimeout(t); window.removeEventListener('scroll', mesurer); window.removeEventListener('resize', mesurer); };
  }, [mesurer, step]);

  const suivant = React.useCallback(() => (i < steps.length - 1 ? setI(i + 1) : onClose()), [i, steps.length, onClose]);
  const precedent = React.useCallback(() => setI(Math.max(0, i - 1)), [i]);
  React.useEffect(() => {
    const touche = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowRight') suivant();
      else if (e.key === 'ArrowLeft') precedent();
    };
    document.addEventListener('keydown', touche);
    return () => document.removeEventListener('keydown', touche);
  }, [onClose, suivant, precedent]);

  // Bulle sous l'élément s'il y a la place, sinon au-dessus ; centrée sans élément
  const largeur = Math.min(380, window.innerWidth - 32);
  let style: React.CSSProperties = { left: '50%', top: '50%', transform: 'translate(-50%, -50%)', width: largeur };
  if (rect) {
    const left = Math.min(Math.max(16, rect.left + rect.width / 2 - largeur / 2), window.innerWidth - largeur - 16);
    const dessous = window.innerHeight - rect.bottom > 230;
    style = dessous
      ? { left, top: rect.bottom + MARGE + 12, width: largeur }
      : { left, bottom: window.innerHeight - rect.top + MARGE + 12, width: largeur };
  }
  const trou = rect && {
    x: rect.left - MARGE, y: rect.top - MARGE, w: rect.width + 2 * MARGE, h: rect.height + 2 * MARGE,
  };

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="visite-titre">
      {/* Voile avec une découpe autour de l'élément présenté */}
      <svg className="absolute inset-0 h-full w-full" aria-hidden="true" onClick={onClose}>
        <defs>
          <mask id="visite-masque">
            <rect width="100%" height="100%" fill="white" />
            {trou && <rect x={trou.x} y={trou.y} width={trou.w} height={trou.h} rx="12" fill="black" className="transition-all duration-300" />}
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgba(10, 16, 40, 0.55)" mask="url(#visite-masque)" />
        {trou && <rect x={trou.x} y={trou.y} width={trou.w} height={trou.h} rx="12" fill="none" stroke="white" strokeWidth="2" className="transition-all duration-300" />}
      </svg>
      <div ref={bulle} tabIndex={-1} style={style}
        className="absolute flex flex-col gap-3 rounded-lg border border-line bg-surface p-5 shadow-xl outline-none transition-all duration-300">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[12px] font-medium uppercase tracking-wide text-ink-subtle">{i + 1} / {steps.length}</span>
          <button type="button" onClick={onClose} aria-label="Quitter la visite"
            className="flex h-8 w-8 items-center justify-center rounded border-0 bg-transparent text-lg text-ink-subtle hover:bg-surface-3 hover:text-ink">×</button>
        </div>
        <h2 id="visite-titre" className="m-0 text-[18px] font-bold text-ink">{step.title}</h2>
        <p className="m-0 text-sm leading-relaxed text-ink-body" aria-live="polite">{step.text}</p>
        <div className="flex items-center gap-2 pt-1">
          <span className="flex flex-grow gap-1" aria-hidden="true">
            {steps.map((_, n) => <span key={n} className={`h-1.5 w-1.5 rounded-full ${n === i ? 'bg-primary' : 'bg-surface-3'}`} />)}
          </span>
          {i > 0 && (
            <button type="button" onClick={precedent}
              className="flex h-9 items-center rounded border border-line-strong bg-surface px-3 text-sm font-medium text-ink-body hover:bg-surface-3">Précédent</button>
          )}
          <button type="button" onClick={suivant}
            className="flex h-9 items-center rounded border-0 bg-primary px-4 text-sm font-medium text-primary-on hover:bg-primary-hover">
            {i === steps.length - 1 ? 'Terminer' : i === 0 ? 'Commencer' : 'Suivant'}
          </button>
        </div>
      </div>
    </div>
  );
};
