/**
 * Prompt Explainer page — fetches a job by ID and renders the scene-based walkthrough.
 * Route: /prompt/:jobId
 */
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Loader2, ArrowLeft } from "lucide-react";
import PromptPlayer from "@/components/prompt-explainer/PromptPlayer";
import { API_BASE } from "@/lib/utils";
import { getCookingMessage } from "@/lib/cooking-messages";

const COOKING_ROTATE_INTERVAL = 4000;

interface JobData {
  job_id: string;
  status: string;
  progress: string;
  job_type: string | null;
  explanation: any;
  storyboard: any;
  narration: any;
  tts_script: any;
  error: string | null;
}

export default function PromptExplainer() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cookingTick, setCookingTick] = useState(0);

  // Rotate cooking message while waiting
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

  // Loading state
  if (!job && !error) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-white/40" />
      </div>
    );
  }

  // Error state
  if (error || job?.status === "failed") {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
        <p className="text-red-400 text-sm">{error || job?.error || "Job failed"}</p>
        <Link to="/" className="text-xs text-white/40 hover:text-white/60 flex items-center gap-1">
          <ArrowLeft className="h-3 w-3" /> Back to home
        </Link>
      </div>
    );
  }

  // Still running — show fun cooking messages
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
        <p className="text-[11px] text-white/30">This usually takes 1–2 minutes</p>
      </div>
    );
  }

  // Prompt job done — render player
  if (job?.explanation && job?.storyboard && job?.narration) {
    return (
      <div className="h-[calc(100vh-80px)]">
        <PromptPlayer
          explanation={job.explanation}
          storyboard={job.storyboard}
          narration={job.narration}
          jobId={jobId}
        />
      </div>
    );
  }

  return (
    <div className="flex h-[80vh] items-center justify-center">
      <p className="text-white/40 text-sm">No data available</p>
    </div>
  );
}
