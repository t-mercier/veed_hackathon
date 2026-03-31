import { Link } from "react-router-dom";

const Footer = () => (
  <footer className="border-t bg-secondary/50">
    <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-8">
      <span className="font-display text-sm font-semibold tracking-tight">
        Code<span className="hero-accent-text">Viz</span>
      </span>
      <div className="flex gap-6 text-sm text-muted-foreground">
        <Link to="/" className="transition-colors hover:text-foreground">About</Link>
        <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="transition-colors hover:text-foreground">GitHub</a>
        <a href="mailto:hello@codeviz.io" className="transition-colors hover:text-foreground">Contact</a>
      </div>
    </div>
  </footer>
);

export default Footer;
