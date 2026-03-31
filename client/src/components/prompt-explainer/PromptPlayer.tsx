/**
 * Full narrated playback controller for prompt/concept explanations.
 *
 * Playback sequence:
 *   1. Avatar intro video (if available)
 *   2. Scene-by-scene: React Flow visualization + TTS audio per scene
 *   3. Avatar outro video (if available)
 *
 * Auto-advances when each audio/video finishes.
 * Falls back to timer-based advancement if no audio available.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Download } from "lucide-react";
import PromptExplainerFlow from "./PromptExplainerFlow";
import { API_BASE } from "@/lib/utils";

type PlaybackPhase =
  | { kind: "intro" }
  | { kind: "scene"; index: number }
  | { kind: "outro" }
  | { kind: "done" };

interface Narration {
  intro: string;
  intro_video_url?: string;
  scenes: { scene_id: string; narration: string; audio_url?: string }[];
  outro: string;
  outro_video_url?: string;
}

interface PromptPlayerProps {
  explanation: any;
  storyboard: any;
  narration: Narration;
  jobId?: string;
}

const FALLBACK_SCENE_DURATION = 6000;

export default function PromptPlayer({ explanation, storyboard, narration, jobId }: PromptPlayerProps) {
  const [started, setStarted] = useState(false);
  const [phase, setPhase] = useState<PlaybackPhase>({ kind: "intro" });
  const [autoPlay, setAutoPlay] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const pipVideoRef = useRef<HTMLVideoElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const totalScenes = storyboard.scenes.length;
  const hasIntroVideo = !!narration.intro_video_url;
  const hasOutroVideo = !!narration.outro_video_url;

  // Build a lookup from scene_id → narration entry
  const narrationBySceneId = useMemo(() => {
    const map = new Map<string, { narration: string; audio_url?: string }>();
    for (const s of narration.scenes) {
      map.set(s.scene_id, s);
    }
    return map;
  }, [narration.scenes]);

  // Determine starting phase
  useEffect(() => {
    if (!hasIntroVideo) {
      setPhase({ kind: "scene", index: 0 });
    }
  }, [hasIntroVideo]);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const advanceToNext = useCallback(() => {
    if (!autoPlay) return;
    clearTimer();

    setPhase((prev) => {
      if (prev.kind === "intro") {
        return { kind: "scene", index: 0 };
      }
      if (prev.kind === "scene") {
        const next = prev.index + 1;
        if (next < totalScenes) {
          return { kind: "scene", index: next };
        }
        return hasOutroVideo ? { kind: "outro" } : { kind: "done" };
      }
      if (prev.kind === "outro") {
        return { kind: "done" };
      }
      return prev;
    });
  }, [autoPlay, totalScenes, hasOutroVideo, clearTimer]);

  // Handle scene audio playback — match by scene_id, not array index
  useEffect(() => {
    if (phase.kind !== "scene" || !autoPlay) return;

    const storyScene = storyboard.scenes[phase.index];
    const sceneNarr = storyScene ? narrationBySceneId.get(storyScene.id) : undefined;
    const audioUrl = sceneNarr?.audio_url;

    if (audioUrl && audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.play().catch(() => {
        timerRef.current = setTimeout(advanceToNext, FALLBACK_SCENE_DURATION);
      });
    } else {
      timerRef.current = setTimeout(advanceToNext, FALLBACK_SCENE_DURATION);
    }

    return clearTimer;
  }, [phase, autoPlay, storyboard.scenes, narrationBySceneId, advanceToNext, clearTimer]);

  // Manual scene control
  const goToScene = useCallback((index: number) => {
    clearTimer();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setPhase({ kind: "scene", index });
  }, [clearTimer]);

  const handlePrev = useCallback(() => {
    if (phase.kind === "scene" && phase.index > 0) {
      goToScene(phase.index - 1);
    }
  }, [phase, goToScene]);

  const handleNext = useCallback(() => {
    if (phase.kind === "scene" && phase.index < totalScenes - 1) {
      goToScene(phase.index + 1);
    } else {
      advanceToNext();
    }
  }, [phase, totalScenes, goToScene, advanceToNext]);

  const toggleAutoPlay = useCallback(() => {
    setAutoPlay((prev) => {
      if (prev) {
        clearTimer();
        if (audioRef.current) audioRef.current.pause();
        if (pipVideoRef.current) pipVideoRef.current.pause();
      } else {
        if (pipVideoRef.current) pipVideoRef.current.play().catch(() => {});
      }
      return !prev;
    });
  }, [clearTimer]);

  const handleRestart = useCallback(() => {
    clearTimer();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setAutoPlay(true);
    setPhase(hasIntroVideo ? { kind: "intro" } : { kind: "scene", index: 0 });
  }, [hasIntroVideo, clearTimer]);

  // ── Render ──────────────────────────────────────────────────────────────

  const audioElement = (
    <audio
      ref={audioRef}
      onEnded={advanceToNext}
      style={{ display: "none" }}
    />
  );

  // Picture-in-picture avatar
  const pipAvatar = hasIntroVideo && phase.kind === "scene" ? (
    <div className="absolute bottom-4 right-4 z-50 h-40 w-32 overflow-hidden rounded-2xl border-2 border-white/20 shadow-2xl shadow-black/50 bg-black">
      <video
        ref={pipVideoRef}
        src={narration.intro_video_url}
        autoPlay
        loop
        muted
        playsInline
        className="h-full w-full object-cover"
        style={{ objectPosition: "50% 5%", transform: "scale(1.7)", transformOrigin: "top center" }}
      />
    </div>
  ) : null;

  // Start screen
  if (!started) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 bg-gray-950">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white">{explanation.title}</h2>
          <p className="mt-2 text-sm text-white/50 max-w-md">{explanation.summary}</p>
        </div>
        <button
          onClick={() => setStarted(true)}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 hover:bg-blue-500 transition-colors"
        >
          ▶ Start Explanation
        </button>
        <p className="text-[11px] text-white/30">{totalScenes} scenes • narrated walkthrough</p>
      </div>
    );
  }

  // Intro video
  if (phase.kind === "intro" && hasIntroVideo) {
    return (
      <div className="flex h-full items-center justify-center bg-black">
        {audioElement}
        <video
          ref={videoRef}
          src={narration.intro_video_url}
          autoPlay
          playsInline
          onEnded={advanceToNext}
          className="max-h-full max-w-full"
        />
      </div>
    );
  }

  // Outro video
  if (phase.kind === "outro" && hasOutroVideo) {
    return (
      <div className="flex h-full items-center justify-center bg-black">
        {audioElement}
        <video
          ref={videoRef}
          src={narration.outro_video_url}
          autoPlay
          playsInline
          onEnded={() => setPhase({ kind: "done" })}
          className="max-h-full max-w-full"
        />
      </div>
    );
  }

  // Done state
  if (phase.kind === "done") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 bg-gray-950">
        {audioElement}
        <p className="text-lg font-semibold text-white/70">Explanation complete</p>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRestart}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
          >
            ↺ Watch again
          </button>
          {jobId && (
            <a
              href={`${API_BASE}/download/${jobId}`}
              download
              className="flex items-center gap-1.5 rounded-lg border border-white/20 px-5 py-2 text-sm font-medium text-white/70 hover:bg-white/10 transition-colors"
            >
              <Download className="h-4 w-4" /> Download Video
            </a>
          )}
        </div>
      </div>
    );
  }

  // Scene playback — React Flow with controls
  const sceneIndex = phase.kind === "scene" ? phase.index : 0;
  const currentScene = storyboard.scenes[sceneIndex];

  return (
    <div className="relative flex h-full flex-col">
      {audioElement}
      {pipAvatar}

      {/* Narration text overlay at top */}
      <div className="shrink-0 border-b border-white/10 bg-black/40 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="rounded bg-blue-600/30 px-2 py-0.5 text-[10px] font-semibold text-blue-300 uppercase tracking-wider">
              Scene {sceneIndex + 1} / {totalScenes}
            </span>
            <span className="text-sm font-medium text-white">{currentScene?.title}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrev}
              disabled={sceneIndex === 0}
              className="rounded px-2 py-1 text-xs text-white/60 hover:bg-white/10 disabled:opacity-30 transition-colors"
            >
              ← Prev
            </button>
            <button
              onClick={toggleAutoPlay}
              className="rounded px-2 py-1 text-xs text-white/60 hover:bg-white/10 transition-colors"
            >
              {autoPlay ? "⏸ Pause" : "▶ Play"}
            </button>
            <button
              onClick={handleNext}
              disabled={sceneIndex === totalScenes - 1 && !hasOutroVideo}
              className="rounded px-2 py-1 text-xs text-white/60 hover:bg-white/10 disabled:opacity-30 transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
        {currentScene?.narration && (
          <p className="mt-2 text-xs leading-relaxed text-white/50 max-w-3xl">
            {currentScene.narration}
          </p>
        )}
      </div>

      {/* React Flow canvas */}
      <div className="flex-1">
        <PromptExplainerFlow
          explanation={explanation}
          storyboard={storyboard}
          activeSceneIndex={sceneIndex}
        />
      </div>
    </div>
  );
}
