/**
 * Scene navigation controls — prev/next buttons + scene indicator.
 */
interface SceneControlsProps {
  currentScene: number;
  totalScenes: number;
  sceneTitle: string;
  onPrev: () => void;
  onNext: () => void;
  playing: boolean;
  onTogglePlay: () => void;
}

export default function SceneControls({
  currentScene,
  totalScenes,
  sceneTitle,
  onPrev,
  onNext,
  playing,
  onTogglePlay,
}: SceneControlsProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/60 backdrop-blur-md px-4 py-2">
      <button
        onClick={onPrev}
        disabled={currentScene === 0}
        className="rounded-lg px-3 py-1.5 text-xs font-medium text-white/80 hover:bg-white/10 disabled:opacity-30 transition-colors"
      >
        ← Prev
      </button>

      <div className="flex flex-col items-center min-w-[160px]">
        <span className="text-xs text-white/50">
          Scene {currentScene + 1} / {totalScenes}
        </span>
        <span className="text-sm font-semibold text-white truncate max-w-[160px]">
          {sceneTitle}
        </span>
      </div>

      <button
        onClick={onNext}
        disabled={currentScene === totalScenes - 1}
        className="rounded-lg px-3 py-1.5 text-xs font-medium text-white/80 hover:bg-white/10 disabled:opacity-30 transition-colors"
      >
        Next →
      </button>

      <div className="mx-1 h-6 w-px bg-white/20" />

      <button
        onClick={onTogglePlay}
        className="rounded-lg px-3 py-1.5 text-xs font-medium text-white/80 hover:bg-white/10 transition-colors"
      >
        {playing ? "⏸ Pause" : "▶ Play"}
      </button>
    </div>
  );
}
