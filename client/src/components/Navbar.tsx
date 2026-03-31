import { Link, useLocation, useNavigate } from "react-router-dom";

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="font-display text-xl font-bold tracking-tight">
            Code<span className="hero-accent-text">Viz</span>
          </span>
        </Link>

        <div className="flex items-center gap-4">
          <div className="flex items-center rounded-lg border bg-secondary p-0.5 text-xs font-semibold">
            <button
              onClick={() => navigate("/concepts")}
              className={`rounded-md px-3 py-1.5 transition-all ${location.pathname === "/concepts" ? "bg-card shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              Concepts
            </button>
            <button
              onClick={() => navigate("/premium")}
              className={`rounded-md px-3 py-1.5 transition-all ${location.pathname === "/premium" ? "bg-card shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              Studio
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
