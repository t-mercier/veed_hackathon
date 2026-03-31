/**
 * Side panel showing scene narration and bullet points.
 */
interface Panel {
  title: string;
  bullets: string[];
}

interface InfoPanelProps {
  sceneTitle: string;
  goal: string;
  narration: string;
  panel: Panel | null;
}

export default function InfoPanel({ sceneTitle, goal, narration, panel }: InfoPanelProps) {
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto rounded-xl border border-white/10 bg-black/60 backdrop-blur-md p-5">
      <div>
        <h3 className="text-lg font-bold text-white">{sceneTitle}</h3>
        {goal && <p className="mt-1 text-xs text-white/40">{goal}</p>}
      </div>

      {narration && (
        <div className="rounded-lg bg-white/5 p-3">
          <p className="text-sm leading-relaxed text-white/80">{narration}</p>
        </div>
      )}

      {panel && (
        <div>
          <h4 className="text-sm font-semibold text-white/70">{panel.title}</h4>
          <ul className="mt-2 space-y-1.5">
            {panel.bullets.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-white/60">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                {b}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
