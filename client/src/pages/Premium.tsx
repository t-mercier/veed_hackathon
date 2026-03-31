/** Premium page — avatar/voice selection and generation with Supabase polling. */
import { useEffect, useRef, useState, useCallback } from "react";
import { Check, Crown, Download, Play, Square, X } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "@/hooks/use-toast";
import { API_BASE } from "@/lib/utils";
import { getCookingMessage } from "@/lib/cooking-messages";

const IS_DEV = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

const avatars = [
  { id: "c3po", name: "C-3PO", image: "/c3po.jpg", position: "center" },
  { id: "super_man", name: "Super Man", image: "/super_man.jpg", position: "top" },
  { id: "wonder_woman", name: "Wonder Woman", image: "/wonder_woman.jpg", position: "top" },
];

const moods = ["Friendly", "Technical", "Energetic", "Calm"];
const levels = ["Beginner", "Advanced", "Expert"];

const RUNWARE_VOICES = [
  "Abby","Alex","Amina","Anjali","Arjun","Ashley","Blake","Brian",
  "Callum","Carter","Celeste","Chloe","Claire","Clive","Craig",
  "Darlene","Deborah","Dennis","Dominus","Edward","Elizabeth","Elliot",
  "Ethan","Evan","Evelyn","Gareth","Graham","Grant","Hades","Hamish",
  "Hana","Hank","James","Jason","Jessica","Julia","Julie","Kayla",
  "Kelsey","Lauren","Liam","Loretta","Luna","Malcolm","Marlene","Mark",
  "Miranda","Mortimer","Nate","Oliver","Olivia","Pippa","Pixie","Priya",
  "Ronald","Rupert","Saanvi","Sarah","Sebastian","Serena","Shaun","Simon",
  "Snik","Theodore","Timothy","Tessa","Tyler","Victor","Victoria","Vinny",
  "Veronica","Wendy",
];

const POLL_INTERVAL = 3000;
const POLL_TIMEOUT = 10 * 60 * 1000; // 10 minutes — avatar gen can be slow
const COOKING_ROTATE_INTERVAL = 4000; // rotate fun message every 4 seconds

const Premium = () => {
  const { user, loading, isPremium, profileLoading } = useAuth();
  const navigate = useNavigate();

  // Premium controls
  const [selectedAvatar, setSelectedAvatar] = useState("c3po");
  const [customAvatarUrl, setCustomAvatarUrl] = useState("");
  const [selectedVoice, setSelectedVoice] = useState("Oliver");
  const [roboticVoice, setRoboticVoice] = useState(false);
  const [previewingVoice, setPreviewingVoice] = useState(false);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const [mode, setMode] = useState<"concept" | "code">("concept");
  const [mood, setMood] = useState("Friendly");
  const [level, setLevel] = useState("Beginner");
  const [prompt, setPrompt] = useState("");
  const [url, setUrl] = useState("");

  // Generation state
  const [generating, setGenerating] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  // Polling state
  const [requestId, setRequestId] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollStartRef = useRef<number>(0);

  // Rotating cooking message tick
  const [cookingTick, setCookingTick] = useState(0);

  const videoRef = useRef<HTMLVideoElement>(null);

  // Stop polling helper
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Poll for status updates
  const startPolling = useCallback((reqId: string) => {
    pollStartRef.current = Date.now();

    pollRef.current = setInterval(async () => {
      if (Date.now() - pollStartRef.current > POLL_TIMEOUT) {
        stopPolling();
        setGenerating(false);
        setCurrentStatus(null);
        setErrorMessage("Taking longer than expected. Check back later.");
        return;
      }

      const { data, error } = await supabase
        .from("video_requests")
        .select("status, error_message, backend_job_id, job_type")
        .eq("id", reqId)
        .maybeSingle();

      if (error || !data) return;

      setCurrentStatus(data.status);

      if (data.status === "completed") {
        stopPolling();
        setGenerating(false);

        if (data.job_type === "repo" && data.backend_job_id) {
          navigate(`/repo/${data.backend_job_id}`);
          return;
        }

        if (data.job_type === "concept_algo" && data.backend_job_id) {
          navigate(`/concept/${data.backend_job_id}`);
          return;
        }

        if (data.job_type === "prompt" && data.backend_job_id) {
          navigate(`/prompt/${data.backend_job_id}`);
          return;
        }

        const { data: videoData } = await supabase
          .from("generated_videos")
          .select("video_url")
          .eq("request_id", reqId)
          .maybeSingle();

        if (videoData?.video_url) setVideoUrl(videoData.video_url);
      } else if (data.status === "failed") {
        stopPolling();
        setGenerating(false);
        setErrorMessage(data.error_message || "An unknown error occurred.");
      }
    }, POLL_INTERVAL);
  }, [stopPolling, navigate]);

  // Local dev polling: poll backend /jobs/:id directly
  const startLocalPolling = useCallback((jobId: string) => {
    pollStartRef.current = Date.now();

    pollRef.current = setInterval(async () => {
      if (Date.now() - pollStartRef.current > POLL_TIMEOUT) {
        stopPolling();
        setGenerating(false);
        setErrorMessage("Taking longer than expected. Check the server logs.");
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/jobs/${jobId}`);
        if (!res.ok) return;
        const data = await res.json();

        setCurrentStatus(data.status);

        if (data.status === "done") {
          stopPolling();
          setGenerating(false);

          if (data.job_type === "repo") {
            navigate(`/repo/${jobId}`);
            return;
          }

          if (data.job_type === "concept_algo") {
            navigate(`/concept/${jobId}`);
            return;
          }

          if (data.job_type === "prompt") {
            navigate(`/prompt/${jobId}`);
            return;
          }

          if (data.final_url) setVideoUrl(data.final_url);
          else if (data.animation_url) setVideoUrl(data.animation_url);
        } else if (data.status === "failed") {
          stopPolling();
          setGenerating(false);
          setErrorMessage(data.error || "An unknown error occurred.");
        }
      } catch {
        // Network error — keep polling
      }
    }, POLL_INTERVAL);
  }, [stopPolling, navigate]);

  // Cleanup on unmount
  useEffect(() => {
    return () => { stopPolling(); };
  }, [stopPolling]);

  // Rotate cooking message while generating
  useEffect(() => {
    if (!generating) return;
    const id = setInterval(() => setCookingTick((t) => t + 1), COOKING_ROTATE_INTERVAL);
    return () => clearInterval(id);
  }, [generating]);

  // Voice preview
  const handlePreviewVoice = async () => {
    if (previewingVoice) {
      previewAudioRef.current?.pause();
      previewAudioRef.current = null;
      setPreviewingVoice(false);
      return;
    }
    setPreviewingVoice(true);
    try {
      const res = await fetch(`${API_BASE}/preview-voice/${encodeURIComponent(selectedVoice)}?robotic=${roboticVoice}`);
      if (!res.ok) throw new Error("Preview failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      previewAudioRef.current = audio;
      audio.onended = () => { setPreviewingVoice(false); URL.revokeObjectURL(url); };
      audio.onerror = () => { setPreviewingVoice(false); };
      await audio.play();
    } catch {
      setPreviewingVoice(false);
      toast({ title: "Could not preview voice", variant: "destructive" });
    }
  };

  // Premium user: real generation
  const handlePremiumGenerate = async () => {
    const isPromptMode = mode === "concept";
    if (isPromptMode ? !prompt.trim() : !url.trim()) return;
    if (generating) return;

    setGenerating(true);
    // Stop any playing voice preview
    if (previewAudioRef.current) { previewAudioRef.current.pause(); previewAudioRef.current = null; setPreviewingVoice(false); }
    setVideoUrl(null);
    setRequestId(null);
    setCurrentStatus("pending");
    setErrorMessage(null);

    try {
      let jobId: string;

      if (IS_DEV) {
        // Local dev: call backend directly, poll via /jobs/:id
        const res = await fetch(`${API_BASE}/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: isPromptMode ? prompt.trim() : url.trim(),
            mood: mood.toLowerCase(),
            level: level.toLowerCase(),
            mode: "concept",
            avatar: selectedAvatar,
            voice: selectedVoice,
            robotic: roboticVoice,
            avatar_image_url: customAvatarUrl.trim() || null,
          }),
        });
        if (!res.ok) throw new Error(`Backend error: ${res.status}`);
        const result = await res.json();
        jobId = result.job_id;
        setRequestId(jobId);
        setCurrentStatus("pending");
        startLocalPolling(jobId);
      } else {
        // Production: call Supabase edge function, poll via Supabase
        const { data, error } = await supabase.functions.invoke("generate-video", {
          body: {
            topic: isPromptMode ? prompt.trim() : url.trim(),
            mode: isPromptMode ? "prompt" : "repo",
            avatar: selectedAvatar,
            voice: selectedVoice,
            robotic: roboticVoice,
            avatar_image_url: customAvatarUrl.trim() || null,
            mood: mood.toLowerCase(),
            level: level.toLowerCase(),
            github_url: url.trim() || null,
          },
        });
        if (error) throw new Error(error.message || "Failed to invoke edge function");
        const reqId = data?.request_id;
        if (!reqId) throw new Error("No request_id returned");
        setRequestId(reqId);
        setCurrentStatus("pending");
        startPolling(reqId);
      }
    } catch (err: any) {
      setGenerating(false);
      setErrorMessage(err.message || "Something went wrong.");
    }
  };

  const handleCancel = () => {
    stopPolling();
    setVideoUrl(null);
    setGenerating(false);
    setRequestId(null);
    setCurrentStatus(null);
    setErrorMessage(null);
  };

  if (!IS_DEV && (loading || profileLoading)) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  if (!IS_DEV && !user) return <Navigate to="/login" replace />;
  if (!IS_DEV && !isPremium) return <Navigate to="/concepts" replace />;

  // ── PREMIUM USER LAYOUT ──
  return (
    <div className="px-6 py-12">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center gap-2 rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
            <Crown className="h-3.5 w-3.5" /> Premium
          </div>
        </div>
        <h1 className="mt-2 font-display text-3xl font-bold">Create Your Video</h1>
        <p className="mt-2 text-muted-foreground">
          Select an avatar, write your prompt, and generate an animated explanation.
        </p>

        {/* Avatar Selection */}
        <section className="mt-10">
          <h2 className="font-display text-lg font-semibold">Choose Avatar</h2>
          <div className="mt-4 grid grid-cols-3 gap-4">
            {avatars.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelectedAvatar(a.id)}
                disabled={generating}
                className={`relative flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition-all hover:shadow-md ${
                  selectedAvatar === a.id ? "border-accent bg-accent/5 shadow-md" : "border-transparent bg-card"
                } disabled:opacity-50`}
              >
                {selectedAvatar === a.id && (
                  <div className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-accent">
                    <Check className="h-3 w-3 text-accent-foreground" />
                  </div>
                )}
                <img src={a.image} alt={a.name} className="h-16 w-16 rounded-full object-cover" style={{ objectPosition: a.position }} />
                <span className="text-xs font-medium">{a.name}</span>
              </button>
            ))}
          </div>

          {/* Custom avatar URL */}
          <div className="mt-4">
            <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
              Custom Avatar Image URL <span className="text-xs">(optional — overrides selection above)</span>
            </label>
            <input
              type="url"
              value={customAvatarUrl}
              onChange={(e) => setCustomAvatarUrl(e.target.value)}
              disabled={generating}
              className="flex h-11 w-full rounded-xl border bg-card px-4 text-sm outline-none transition-colors focus:ring-2 focus:ring-ring disabled:opacity-50"
              placeholder="https://example.com/my-avatar.jpg"
            />
          </div>

          {/* Voice selector */}
          <div className="mt-4">
            <label className="mb-1.5 block text-sm font-medium">Voice</label>
            <div className="flex items-center gap-2">
              <select
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                disabled={generating}
                className="rounded-xl border bg-card px-3 py-2 text-sm outline-none transition-colors focus:ring-2 focus:ring-ring disabled:opacity-50"
              >
                {RUNWARE_VOICES.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
              <button
                onClick={handlePreviewVoice}
                disabled={generating}
                title={previewingVoice ? "Stop preview" : "Preview voice"}
                className="flex h-9 w-9 items-center justify-center rounded-xl border bg-card text-muted-foreground transition-colors hover:bg-accent/10 hover:text-accent disabled:opacity-50"
              >
                {previewingVoice ? <Square className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 fill-current" />}
              </button>
              {previewingVoice && <span className="text-xs text-muted-foreground animate-pulse">Playing…</span>}
              <button
                onClick={() => setRoboticVoice((v) => !v)}
                disabled={generating}
                title="Toggle robotic effect (lower pitch + slower)"
                className={`ml-2 flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-medium transition-all ${
                  roboticVoice ? "border-accent bg-accent/10 text-accent" : "bg-card text-muted-foreground hover:text-foreground"
                } disabled:opacity-50`}
              >
                🤖 Robotic
              </button>
            </div>
          </div>
        </section>

        {/* Prompt Section */}
        <section className="mt-10">
          <h2 className="font-display text-lg font-semibold">Your Prompt</h2>
          <div className="mt-4 space-y-4">
            <div className="inline-flex rounded-xl border bg-secondary p-1">
              {(["concept", "code"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => !generating && setMode(m)}
                  className={`rounded-lg px-5 py-2 text-sm font-medium transition-all ${
                    mode === m ? "bg-card shadow-sm" : "text-muted-foreground hover:text-foreground"
                  } ${generating ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  {m === "concept" ? "Prompt Mode" : "Repo Mode"}
                </button>
              ))}
            </div>
            {mode === "concept" ? (
              <>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">Prompt</label>
                  <p className="mb-2 text-xs text-muted-foreground">Paste a concept description or a code snippet to animate.</p>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={6}
                    disabled={generating}
                    className="flex w-full rounded-xl border bg-card px-4 py-3 font-mono text-sm outline-none transition-colors focus:ring-2 focus:ring-ring disabled:opacity-50"
                    placeholder={"Explain how recursion works with a visual tree diagram\n\ndef factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n - 1)"}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">GitHub Link <span className="text-muted-foreground font-normal">(optional)</span></label>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={generating}
                    className="flex h-11 w-full rounded-xl border bg-card px-4 text-sm outline-none transition-colors focus:ring-2 focus:ring-ring disabled:opacity-50"
                    placeholder="https://github.com/user/repo"
                  />
                </div>
              </>
            ) : (
              <div>
                <label className="mb-1.5 block text-sm font-medium">Repository Link</label>
                <p className="mb-2 text-xs text-muted-foreground">Paste a GitHub repo URL — we'll analyze the code and generate a visual walkthrough.</p>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={generating}
                  className="flex h-11 w-full rounded-xl border bg-card px-4 text-sm outline-none transition-colors focus:ring-2 focus:ring-ring disabled:opacity-50"
                  placeholder="https://github.com/user/repo"
                />
              </div>
            )}
          </div>
        </section>

        {/* Settings */}
        <section className="mt-10">
          <h2 className="font-display text-lg font-semibold">Settings</h2>
          <div className="mt-4 grid gap-6 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">Mood / Intonation</label>
              <div className="flex flex-wrap gap-2">
                {moods.map((m) => (
                  <button key={m} onClick={() => !generating && setMood(m)}
                    className={`rounded-lg border px-4 py-2 text-sm font-medium transition-all ${
                      mood === m ? "border-accent bg-accent/10 text-accent" : "bg-card text-muted-foreground hover:text-foreground"
                    } ${generating ? "opacity-50 cursor-not-allowed" : ""}`}
                  >{m}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Experience Level</label>
              <div className="flex flex-wrap gap-2">
                {levels.map((l) => (
                  <button key={l} onClick={() => !generating && setLevel(l)}
                    className={`rounded-lg border px-4 py-2 text-sm font-medium transition-all ${
                      level === l ? "border-accent bg-accent/10 text-accent" : "bg-card text-muted-foreground hover:text-foreground"
                    } ${generating ? "opacity-50 cursor-not-allowed" : ""}`}
                  >{l}</button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Generate Button — hidden during generation */}
        <section className="mt-10">
          {!generating && (
            <div className="flex items-center gap-3">
              <button
                onClick={handlePremiumGenerate}
                disabled={mode === "concept" ? !prompt.trim() : !url.trim()}
                className="inline-flex h-12 items-center gap-2 rounded-xl bg-accent px-8 text-sm font-semibold text-accent-foreground shadow-lg shadow-accent/20 transition-all hover:bg-accent/90 disabled:opacity-50 disabled:shadow-none"
              >
                Generate Video
              </button>
            </div>
          )}

          {/* Cooking animation — sole feedback during generation */}
          {generating && (
            <div className="mt-6 flex flex-col items-center justify-center rounded-2xl border bg-card p-12 text-center">
              <div className="relative mb-6">
                <div className="h-16 w-16 animate-spin rounded-full border-4 border-muted border-t-accent" />
                <span className="absolute inset-0 flex items-center justify-center text-2xl">🧑‍🍳</span>
              </div>
              <p className="text-lg font-semibold text-foreground transition-all duration-500">
                {getCookingMessage(currentStatus, cookingTick)}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                This usually takes 2–4 minutes. Grab a coffee ☕
              </p>
              <button
                onClick={handleCancel}
                className="mt-6 inline-flex h-10 items-center gap-2 rounded-xl border px-5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <X className="h-4 w-4" /> Cancel
              </button>
            </div>
          )}

          {/* Error state */}
          {errorMessage && !generating && (
            <div className="mt-6 rounded-xl border border-destructive/30 bg-destructive/5 p-6">
              <h3 className="font-display text-lg font-semibold text-destructive">Generation Failed</h3>
              <p className="mt-2 text-sm text-muted-foreground">{errorMessage}</p>
              <button
                onClick={handleCancel}
                className="mt-4 inline-flex h-10 items-center rounded-xl border px-5 text-sm font-medium transition-colors hover:bg-secondary"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Video player */}
          {videoUrl && !generating && (
            <div className="mt-6 overflow-hidden rounded-2xl border bg-card shadow-lg">
              <div className="relative aspect-video bg-black">
                <video ref={videoRef} src={videoUrl} className="h-full w-full object-contain" controls autoPlay playsInline />
              </div>
              <div className="flex items-center justify-between p-4">
                <p className="text-sm font-medium">Your Generated Video</p>
                <div className="flex items-center gap-3">
                  <a
                    href={videoUrl}
                    download
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                  >
                    <Download className="h-4 w-4" /> Download
                  </a>
                  <button
                    onClick={handleCancel}
                    className="inline-flex h-9 items-center rounded-lg border px-4 text-sm font-medium transition-colors hover:bg-secondary"
                  >
                    Create Another
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default Premium;
