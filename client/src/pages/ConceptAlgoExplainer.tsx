/**
 * Concept / Algorithm Explainer page — plays a single-scene Manim animation video.
 * Route: /concept/:jobId
 * Same UX as RepoExplainer: full screen, start button, then autoplay.
 */
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { API_BASE } from "@/lib/utils";
import { getCookingMessage } from "@/lib/cooking-messages";

const COOKING_ROTATE_INTERVAL = 4000;

interface JobData {
  job_id: string;
  status: string;
  progress: string;
  job_type: string | null;
  animation_url: string | null;
  final_url: string | null;
  tts_script: { intro: string; info: string; outro: string } | null;
  error: string | null;
}

export default function ConceptAlgoExplainer() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cookingTick, setCookingTick] = useState(0);
  const [started, setStarted] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const isWaiting = !!job && (job.status === "pending" || job.status === "running");
  useEffect(() => {
    if (!isWaiting) return;
    const id = setInterval(() => setCookingTick((t) => t + 1), COOKING_ROTATE_INTERVAL);
    return () => clearInterval(id);
  }, [isWaiting]);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs/${jobId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: JobData = await res.json();
        if (cancelled) return;
        setJob(data);
        if (data.status === "pending" || data.status === "running") {
          setTimeout(poll, 2000);
        }
      } catch (err: any) {
        if (!cancelled) setError(err.message);
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [jobId]);

  if (!job && !error) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-white/40" />
      </div>
    );
  }

  if (error || job?.status === "failed") {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
        <p className="text-red-400 text-sm">{error || job?.error || "Job failed"}</p>
      </div>
    );
  }

  if (job && (job.status === "pending" || job.status === "running")) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
        <div className="relative">
          <div className="h-14 w-14 animate-spin rounded-full border-4 border-white/10 border-t-blue-400" />
          <span className="absolute inset-0 flex items-center justify-center text-xl">🧑‍🍳</span>
        </div>
        <p className="text-sm text-white/70 transition-all duration-300">
          {getCookingMessage(job.progress, cookingTick)}
        </p>
        <p className="text-[11px] text-white/30">This usually takes 2–4 minutes</p>
      </div>
    );
  }

  const videoUrl = job?.final_url || job?.animation_url;
  if (!videoUrl) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <p className="text-white/40 text-sm">No video available</p>
      </div>
    );
  }

  if (!started) {
    return (
      <div className="flex h-[calc(100vh-80px)] flex-col items-center justify-center gap-6 bg-gray-950">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white">
            {job?.tts_script?.intro
              ? job.tts_script.intro.split(" ").slice(0, 6).join(" ") + "…"
              : "Concept Explanation"}
          </h2>
          <p className="mt-2 text-sm text-white/50 max-w-md">
            {job?.tts_script?.info?.slice(0, 120)}…
          </p>
        </div>
        <button
          onClick={() => setStarted(true)}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 hover:bg-blue-500 transition-colors"
        >
          ▶ Start Explanation
        </button>
        <p className="text-[11px] text-white/30">Narrated visual walkthrough</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-80px)] items-center justify-center bg-black">
      <video
        ref={videoRef}
        src={videoUrl}
        autoPlay
        playsInline
        controls
        className="max-h-full max-w-full"
      />
    </div>
  );
}
