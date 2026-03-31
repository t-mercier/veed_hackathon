/** Concepts page — browse pre-made code/concept demo videos (no backend generation). */
import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Crown, Download, Play } from "lucide-react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "@/hooks/use-toast";
import AlgorithmBrowser, { type AlgorithmItem } from "@/components/AlgorithmBrowser";
import { getCookingMessage } from "@/lib/cooking-messages";

const premadeItems = [
  { id: "recursion", label: "Recursion", file: "/demo/recursion.mp4" },
  { id: "binary_search", label: "Binary Search", file: "/demo/binary_search.mp4" },
  { id: "tcp_handshake", label: "TCP Handshake", file: "/demo/tcp_handshake.mp4" },
  { id: "gradient_descent", label: "Gradient Descent", file: "/demo/gradient_descent.mp4" },
  { id: "explain_factorial", label: "Factorial", file: "/demo/explain_factorial.mp4" },
  { id: "explain_dijkstra", label: "Dijkstra", file: "/demo/explain_dijkstra.mp4" },
];

const COOKING_ROTATE_INTERVAL = 2000;

const Concepts = () => {
  const { user, loading, isPremium, profileLoading, refreshProfile } = useAuth();
  const [upgrading, setUpgrading] = useState(false);

  const [selectedPremade, setSelectedPremade] = useState<string | null>(null);
  const [selectedPremadeFile, setSelectedPremadeFile] = useState<string | null>(null);
  const [browserOpen, setBrowserOpen] = useState(false);

  const [generating, setGenerating] = useState(false);
  const [cookingTick, setCookingTick] = useState(0);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    return () => {
      timerRef.current.forEach(clearTimeout);
    };
  }, []);

  useEffect(() => {
    if (!generating) return;
    const id = setInterval(() => setCookingTick((t) => t + 1), COOKING_ROTATE_INTERVAL);
    return () => clearInterval(id);
  }, [generating]);

  const handleGenerate = () => {
    if (!selectedPremade || generating) return;
    const item = premadeItems.find((c) => c.id === selectedPremade);
    const file = item?.file ?? selectedPremadeFile;
    if (!file) return;

    setGenerating(true);
    setVideoUrl(null);
    setCookingTick(0);

    timerRef.current.forEach(clearTimeout);
    timerRef.current = [];

    // Fake ~5s delay then reveal the pre-made video
    const t = setTimeout(() => {
      setGenerating(false);
      setVideoUrl(file);
    }, 5000);
    timerRef.current.push(t);
  };

  const handleBrowserSelect = (item: AlgorithmItem) => {
    setSelectedPremade(item.id);
    setSelectedPremadeFile(item.file);
  };

  if (loading || profileLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  const IS_DEV = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
  if (!user && !IS_DEV) return <Navigate to="/login" replace />;

  const activePremadeList = premadeItems;

  return (
    <div className="px-6 py-12">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <h1 className="font-display text-3xl font-bold">Explore Video Explanations</h1>
        <p className="mt-2 text-muted-foreground">
          Pick a topic below and watch an AI-generated animated explanation.
        </p>

        {/* Premade video grid */}
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {activePremadeList.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelectedPremade(item.id)}
              disabled={generating}
              className={`group flex items-center gap-4 rounded-2xl border-2 p-5 text-left transition-all ${
                selectedPremade === item.id
                  ? "border-accent bg-accent/10 shadow-md shadow-accent/10"
                  : "border-transparent bg-card hover:border-accent/30 hover:shadow-sm"
              } disabled:opacity-50`}
            >
              <div
                className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl transition-colors ${
                  selectedPremade === item.id
                    ? "bg-accent text-accent-foreground"
                    : "bg-secondary text-muted-foreground group-hover:bg-accent/10 group-hover:text-accent"
                }`}
              >
                <Play className="h-5 w-5" />
              </div>
              <div>
                <span className="font-semibold">{item.label}</span>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Animated concept breakdown
                </p>
              </div>
              {selectedPremade === item.id && (
                <Check className="ml-auto h-5 w-5 shrink-0 text-accent" />
              )}
            </button>
          ))}
        </div>

        {/* Selected from browser (if not in default list) */}
        {selectedPremade && !activePremadeList.find((i) => i.id === selectedPremade) && (
          <div className="mt-3 flex items-center gap-3 rounded-2xl border-2 border-accent bg-accent/10 p-4 shadow-md shadow-accent/10">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
              <Play className="h-4 w-4" />
            </div>
            <span className="text-sm font-semibold">{selectedPremade.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</span>
            <Check className="ml-auto h-5 w-5 text-accent" />
          </div>
        )}

        {/* See more button */}
        <button
          onClick={() => setBrowserOpen(true)}
          className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-accent transition-colors hover:text-accent/80"
        >
          See more <ChevronDown className="h-4 w-4" />
        </button>

        {/* Algorithm browser dialog */}
        <AlgorithmBrowser open={browserOpen} onClose={() => setBrowserOpen(false)} onSelect={handleBrowserSelect} />

        <div className="mt-8">
          <button
            onClick={handleGenerate}
            disabled={generating || !selectedPremade}
            className="inline-flex h-12 items-center gap-2 rounded-xl bg-accent px-8 text-sm font-semibold text-accent-foreground shadow-lg shadow-accent/20 transition-all hover:bg-accent/90 disabled:opacity-50 disabled:shadow-none"
          >
            Generate Video
          </button>
        </div>

        {/* Cooking animation — consistent with Premium mode */}
        {generating && (
          <div className="mt-6 flex flex-col items-center justify-center rounded-2xl border bg-card p-12 text-center">
            <div className="relative mb-6">
              <div className="h-16 w-16 animate-spin rounded-full border-4 border-muted border-t-accent" />
              <span className="absolute inset-0 flex items-center justify-center text-2xl">🧑‍🍳</span>
            </div>
            <p className="text-lg font-semibold text-foreground transition-all duration-500">
              {getCookingMessage("rendering", cookingTick)}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Preparing your video…
            </p>
          </div>
        )}

        {/* Video player */}
        {videoUrl && (
          <div className="mt-6 overflow-hidden rounded-2xl border bg-card shadow-lg">
            <div className="relative aspect-video bg-black">
              <video ref={videoRef} src={videoUrl} className="h-full w-full object-contain" controls autoPlay playsInline />
            </div>
            <div className="flex items-center justify-between p-4">
              <p className="text-sm font-medium">
                {activePremadeList.find((c) => c.id === selectedPremade)?.label ?? "Video"} — AI Explanation
              </p>
              <a
                href={videoUrl}
                download
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                <Download className="h-4 w-4" /> Download
              </a>
            </div>
          </div>
        )}

        {/* Upgrade banner — only for free users */}
        {!isPremium && (
          <div className="mt-12 rounded-2xl border border-accent/20 bg-accent/5 p-6 text-center">
            <Crown className="mx-auto h-8 w-8 text-accent" />
            <h3 className="mt-3 font-display text-lg font-semibold">Want custom videos?</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Upgrade to Premium to write your own prompts, choose avatars, and customise mood & level.
            </p>
            <button
              onClick={async () => {
                if (!user || upgrading) return;
                setUpgrading(true);
                const { error } = await supabase
                  .from("profiles")
                  .update({ tier: "premium" })
                  .eq("user_id", user.id);
                if (error) {
                  toast({ title: "Error", description: "Upgrade failed. Please try again.", variant: "destructive" });
                } else {
                  await refreshProfile();
                  toast({ title: "🎉 Welcome to Premium!", description: "You now have full access to custom video generation." });
                }
                setUpgrading(false);
              }}
              disabled={upgrading}
              className="mt-4 inline-flex h-10 items-center gap-2 rounded-xl bg-accent px-6 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90 disabled:opacity-50"
            >
              {upgrading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Crown className="h-4 w-4" />}
              {upgrading ? "Upgrading…" : "Upgrade to Premium"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Concepts;
