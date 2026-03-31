/** Home page — main prompt input for both code snippets and GitHub repo URLs. */
import { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Play, Code, Sparkles, Video, Loader2, Check, X, Github } from "lucide-react";
import { API_BASE } from "@/lib/utils";
import { getCookingMessage } from "@/lib/cooking-messages";

const logoNames = ["TechCorp", "DevStudio", "CodeBase", "Synthetix", "NeuralNet", "DataFlow", "CloudOps"];

const COOKING_ROTATE_INTERVAL = 4000; // rotate fun message every 4s

const Index = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState("");
  const [cookingTick, setCookingTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [doneVideo, setDoneVideo] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, []);

  // Rotate cooking message while generating
  useEffect(() => {
    if (!generating) return;
    const id = setInterval(() => setCookingTick((t) => t + 1), COOKING_ROTATE_INTERVAL);
    return () => clearInterval(id);
  }, [generating]);

  const handleGenerate = async () => {
    const input = prompt.trim();
    if (!input || generating) return;

    setGenerating(true);
    setProgress("Submitting…");
    setError(null);
    setDoneVideo(null);

    try {
      // Submit job
      const res = await fetch(`${API_BASE}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input, mood: "friendly", level: "beginner", mode: "concept" }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const { job_id } = await res.json();

      // Poll for completion
      const poll = async () => {
        try {
          const r = await fetch(`${API_BASE}/jobs/${job_id}`);
          const data = await r.json();

          setProgress(data.progress || "Processing…");

          if (data.status === "failed") {
            setError(data.error || "Generation failed");
            setGenerating(false);
            return;
          }

          if (data.status === "done") {
            setGenerating(false);
            if (data.job_type === "repo") {
              // Redirect to React Flow player
              navigate(`/repo/${job_id}`);
            } else {
              // Show video inline
              setDoneVideo(data.animation_url || data.final_url);
            }
            return;
          }

          pollRef.current = setTimeout(poll, 2000);
        } catch (err: any) {
          setError(err.message);
          setGenerating(false);
        }
      };

      pollRef.current = setTimeout(poll, 1000);
    } catch (err: any) {
      setError(err.message);
      setGenerating(false);
    }
  };

  const handleClose = () => {
    if (pollRef.current) clearTimeout(pollRef.current);
    setDoneVideo(null);
    setGenerating(false);
    setProgress("");
    setError(null);
  };

  const isGithubUrl = prompt.trim().startsWith("https://github.com/");

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden px-6 pb-20 pt-24">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="font-display text-5xl font-bold leading-tight tracking-tight lg:text-6xl">
            Turn code into animated
            <br />
            <span className="hero-gradient-text">explanations with </span>
            <span className="hero-accent-text">AI</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Paste a GitHub repo URL or describe a concept — our AI generates beautiful animated
            explanations in seconds. Learn, teach, and share visually.
          </p>
        </div>

       
      </section>

      {/* How It Works */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center font-display text-3xl font-bold">How it works</h2>
          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {[
              { icon: Code, step: "01", title: "Input your code or concept", desc: "Paste a code snippet, describe an algorithm, or link a GitHub repo." },
              { icon: Sparkles, step: "02", title: "AI generates explanation", desc: "Our AI analyzes the architecture, writes a script, and creates an interactive walkthrough." },
              { icon: Video, step: "03", title: "Watch and share", desc: "Get a narrated visual explanation you can explore, download, or share." },
            ].map((item) => (
              <div key={item.step} className="group rounded-2xl border bg-card p-8 transition-all hover:shadow-lg">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10">
                  <item.icon className="h-6 w-6 text-accent" />
                </div>
                <div className="mb-2 font-display text-xs font-semibold tracking-widest text-accent">{item.step}</div>
                <h3 className="font-display text-lg font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Logos */}
      <section className="border-t px-6 py-12">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-10">
          {logoNames.map((name) => (
            <span key={name} className="font-display text-sm font-bold tracking-wider text-muted-foreground/50 uppercase">
              {name}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Index;
