import { Link } from "react-router-dom";
import { Crown, Lock } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

type PremiumGateProps = {
  children: React.ReactNode;
  /** Message shown to free users */
  message?: string;
  /** Render inline (no overlay) — just hides children and shows CTA */
  inline?: boolean;
};

/**
 * Wraps premium-only content. Free users see an upgrade prompt instead.
 */
const PremiumGate = ({
  children,
  message = "This feature is available for Premium users",
  inline = false,
}: PremiumGateProps) => {
  const { isPremium, user } = useAuth();

  // If not logged in or is premium, render children
  if (isPremium) return <>{children}</>;

  if (inline) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-accent/30 bg-accent/5 p-8 text-center">
        <Lock className="h-6 w-6 text-muted-foreground" />
        <p className="text-sm font-medium text-muted-foreground">{message}</p>
        <Link
          to={user ? "/premium" : "/login"}
          className="mt-2 inline-flex h-10 items-center gap-2 rounded-xl bg-accent px-5 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90"
        >
          <Crown className="h-4 w-4" />
          {user ? "Upgrade to Premium" : "Log in to Upgrade"}
        </Link>
      </div>
    );
  }

  // Overlay mode
  return (
    <div className="relative">
      <div className="pointer-events-none select-none opacity-40">{children}</div>
      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-2xl bg-card/80 backdrop-blur-[2px]">
        <Lock className="h-8 w-8 text-muted-foreground" />
        <h3 className="mt-3 font-display text-lg font-semibold">{message}</h3>
        <Link
          to={user ? "/premium" : "/login"}
          className="mt-5 inline-flex h-11 items-center gap-2 rounded-xl bg-accent px-6 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90"
        >
          <Crown className="h-4 w-4" />
          {user ? "Upgrade to Premium" : "Log in to Upgrade"}
        </Link>
      </div>
    </div>
  );
};

export default PremiumGate;
