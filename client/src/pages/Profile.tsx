import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Play, Crown, Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "@/hooks/use-toast";

const demoVideos = [
  { title: "Recursion Explained", duration: "2:34", color: "from-accent/20 to-accent/5" },
  { title: "Binary Search Animation", duration: "1:58", color: "from-blue-100 to-blue-50" },
  { title: "TCP Handshake", duration: "3:12", color: "from-orange-100 to-orange-50" },
];

const Profile = () => {
  const { user, loading, isPremium, tier, profile, profileLoading, refreshProfile } = useAuth();
  const [upgrading, setUpgrading] = useState(false);

  const handleUpgrade = async () => {
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
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const displayName =
    profile?.full_name ||
    user.user_metadata?.full_name ||
    user.user_metadata?.name ||
    user.email?.split("@")[0] ||
    "User";
  const email = user.email || "";
  const avatarUrl = profile?.avatar_url || user.user_metadata?.avatar_url;
  const initials = displayName
    .split(" ")
    .map((w: string) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="px-6 py-12">
      <div className="mx-auto max-w-4xl">
        {/* User Header */}
        <div className="flex items-center gap-4">
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={displayName}
              className="h-16 w-16 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10 font-display text-xl font-bold text-accent">
              {initials}
            </div>
          )}
          <div>
            <h1 className="font-display text-2xl font-bold">{displayName}</h1>
            <p className="text-sm text-muted-foreground">
              {email} ·{" "}
              {isPremium ? (
                <span className="inline-flex items-center gap-1 text-accent">
                  <Crown className="h-3.5 w-3.5" /> Premium
                </span>
              ) : (
                "Free Plan"
              )}
              {profileLoading && " (loading…)"}
            </p>
          </div>
        </div>

        {/* Free user: Primary CTA to explore & generate */}
        {!isPremium && (
          <section className="mt-10">
            <Link
              to="/premium"
              className="group flex items-center gap-5 rounded-2xl border border-accent/20 bg-gradient-to-r from-accent/10 via-accent/5 to-transparent p-6 transition-all hover:border-accent/40 hover:shadow-lg hover:shadow-accent/10"
            >
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-accent text-accent-foreground shadow-md shadow-accent/20">
                <Sparkles className="h-6 w-6" />
              </div>
              <div className="flex-1">
                <h2 className="font-display text-lg font-bold">Explore Algorithm Videos</h2>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Browse 50+ topics — pick one and watch an AI-generated animated explanation instantly.
                </p>
              </div>
              <ArrowRight className="h-5 w-5 shrink-0 text-accent transition-transform group-hover:translate-x-1" />
            </Link>
          </section>
        )}

        {/* Demo Videos — visible to all */}
        <section className="mt-10">
          <h2 className="font-display text-xl font-semibold">Example Videos</h2>
          <p className="mt-1 text-sm text-muted-foreground">Watch pre-rendered demo explanations</p>
          <div className="mt-6 grid gap-6 sm:grid-cols-3">
            {demoVideos.map((v) => (
              <div key={v.title} className="group cursor-pointer overflow-hidden rounded-2xl border bg-card transition-all hover:shadow-lg">
                <div className={`flex aspect-video items-center justify-center bg-gradient-to-br ${v.color}`}>
                  <Play className="h-10 w-10 rounded-full bg-primary/90 p-2.5 text-primary-foreground opacity-80 transition-opacity group-hover:opacity-100" />
                </div>
                <div className="p-4">
                  <h3 className="text-sm font-semibold">{v.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">{v.duration}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Generation History — premium users see content, free users see simple message */}
        {isPremium && (
          <section className="mt-12">
            <h2 className="font-display text-xl font-semibold">Generation History</h2>
            <p className="mt-1 text-sm text-muted-foreground">Your previously generated videos</p>
            <div className="mt-6">
              <p className="py-8 text-center text-sm text-muted-foreground">
                No generated videos yet. Head to the{" "}
                <Link to="/premium" className="font-medium text-accent hover:underline">
                  generation page
                </Link>{" "}
                to create your first video.
              </p>
            </div>
          </section>
        )}

        {/* Subtle upgrade note for free users */}
        {!isPremium && (
          <section className="mt-12 rounded-2xl border border-accent/20 bg-accent/5 p-6 text-center">
            <Crown className="mx-auto h-7 w-7 text-accent" />
            <h3 className="mt-2 font-display text-base font-semibold">Want custom prompts, avatars & mood settings?</h3>
            <p className="mt-1 text-sm text-muted-foreground">Upgrade to Premium for the full experience.</p>
            <button
              onClick={handleUpgrade}
              disabled={upgrading}
              className="mt-4 inline-flex h-10 items-center gap-2 rounded-xl bg-accent px-6 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90 disabled:opacity-50"
            >
              {upgrading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Crown className="h-4 w-4" />}
              {upgrading ? "Upgrading…" : "Upgrade to Premium"}
            </button>
          </section>
        )}
      </div>
    </div>
  );
};

export default Profile;
