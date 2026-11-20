import React from 'react';

/* Boîte de confirmation (ou d'information) modale, appelée comme une promesse :
   const ok = await ask({ title, text, confirm: 'Arrêter' });
   Focus sur l'action la plus sûre à l'ouverture, Échap ou clic à côté = Annuler, focus rendu à la fermeture. */

export interface Question {
  title: string;
  text: React.ReactNode;
  /** Libellé de l'action ; absent : simple message avec « Compris ». */
  confirm?: string;
  cancel?: string;
  /** Action qui interrompt un travail ou supprime quelque chose. */
  danger?: boolean;
}

type Ask = (q: Question) => Promise<boolean>;

export const useConfirm = (): [React.ReactNode, Ask] => {
  const [question, setQuestion] = React.useState<(Question & { resolve: (ok: boolean) => void }) | null>(null);
  const ask = React.useCallback<Ask>((q) => new Promise((resolve) => setQuestion({ ...q, resolve })), []);
  const close = (ok: boolean) => { question?.resolve(ok); setQuestion(null); };
  return [question ? <Dialog question={question} onClose={close} /> : null, ask];
};

const Dialog: React.FC<{ question: Question; onClose: (ok: boolean) => void }> = ({ question, onClose }) => {
  const safe = React.useRef<HTMLButtonElement>(null);
  const box = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    safe.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); onClose(false); }
      if (e.key === 'Tab' && box.current) {
        // Le focus reste dans la boîte
        const items = box.current.querySelectorAll<HTMLElement>('button');
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('keydown', key); before?.focus?.(); };
  }, [onClose]);

  const ghost = 'flex h-10 items-center rounded border border-line-strong bg-surface px-4 text-sm font-medium text-ink-body hover:bg-surface-3';
  const main = question.danger
    ? 'flex h-10 items-center rounded border border-danger bg-danger-soft px-4 text-sm font-semibold text-danger-text hover:opacity-90'
    : 'flex h-10 items-center rounded border-0 bg-primary px-4 text-sm font-medium text-primary-on hover:bg-primary-hover';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(10,16,40,0.55)] p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(false); }}>
      <div ref={box} role="alertdialog" aria-modal="true" aria-labelledby="dialogue-titre" aria-describedby="dialogue-texte"
        className="flex w-full max-w-[460px] flex-col gap-3 rounded-lg border border-line bg-surface p-6 shadow-xl">
        <h2 id="dialogue-titre" className="m-0 text-[18px] font-bold text-ink">{question.title}</h2>
        <div id="dialogue-texte" className="flex flex-col gap-2 text-sm leading-relaxed text-ink-body">{question.text}</div>
        <div className="flex flex-wrap justify-end gap-2 pt-2">
          {question.confirm ? (
            <>
              <button ref={safe} type="button" className={ghost} onClick={() => onClose(false)}>{question.cancel ?? 'Annuler'}</button>
              <button type="button" className={main} onClick={() => onClose(true)}>{question.confirm}</button>
            </>
          ) : (
            <button ref={safe} type="button" className={main} onClick={() => onClose(true)}>Compris</button>
          )}
        </div>
      </div>
    </div>
  );
};
