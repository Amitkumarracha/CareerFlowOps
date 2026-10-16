import { useEffect, useState } from "react";
import { NavLink, Outlet, Link, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  BriefcaseBusiness,
  Sparkles,
  UserRound,
  FileText,
  Columns3,
  ChartNoAxesCombined,
  FlaskConical,
  Activity,
  ArrowUpRight,
  Layers,
  KeyRound,
  Menu,
  X,
  Bookmark,
  Network,
} from "lucide-react";
const links = [
  { label: "Overview", to: "/", Icon: LayoutDashboard },
  { label: "Discover jobs", to: "/jobs", Icon: BriefcaseBusiness },
  { label: "For you", to: "/recommended", Icon: Sparkles },
  { label: "Saved jobs", to: "/saved", Icon: Bookmark },
  { label: "Profile", to: "/profile", Icon: UserRound },
  { label: "Resume", to: "/resume", Icon: FileText },
  { label: "Applications", to: "/applications", Icon: Columns3 },
  { label: "Placement analytics", to: "/tpo", Icon: ChartNoAxesCombined },
  { label: "Model experiments", to: "/mlops", Icon: FlaskConical },
  { label: "Source health", to: "/admin", Icon: Activity },
  { label: "System & guide", to: "/system", Icon: Network },
];
export function Layout() {
  const [access, setAccess] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [saved, setSaved] = useState(false);
  const [accessVersion, setAccessVersion] = useState(0);
  const location = useLocation();
  const currentPage =
    links.find(({ to }) =>
      to === "/" ? location.pathname === "/" : location.pathname.startsWith(to),
    )?.label ?? "Opportunity details";
  useEffect(() => {
    document.title = `${currentPage} · CareerFlowOps`;
  }, [currentPage]);
  const cache = useQueryClient();
  return (
    <div
      className="app-shell"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          setMobile(false);
          setAccess(false);
        }
      }}
    >
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      {mobile && (
        <button
          className="nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <aside
        id="workspace-navigation"
        className={`sidebar ${mobile ? "open" : ""}`}
      >
        <Link to="/" className="brand">
          <span className="brand-mark">
            <Layers size={23} />
          </span>
          <span>
            CareerFlow<span className="brand-ops">Ops</span>
            <small>YOUR NEXT CHAPTER</small>
          </span>
        </Link>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          {links.map(({ label, to, Icon }, index) => (
            <div key={to}>
              {index === 7 && (
                <p className="nav-label nav-second">INTELLIGENCE</p>
              )}
              <NavLink
                end={to === "/"}
                to={to}
                onClick={() => setMobile(false)}
              >
                <Icon size={18} />
                {label}
                {to === "/recommended" && <span className="nav-dot" />}
              </NavLink>
            </div>
          ))}
        </nav>
        <div className="sidebar-tip">
          <div className="tip-icon">
            <Sparkles size={20} />
          </div>
          <h3>A clearer next move.</h3>
          <p>Add your resume to discover where your skills fit.</p>
          <Link to="/resume">
            Build your profile <ArrowUpRight size={16} />
          </Link>
        </div>
        <div className="sidebar-foot">
          <span className="status-dot" /> Human-reviewed applications
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Toggle navigation"
            aria-expanded={mobile}
            aria-controls="workspace-navigation"
            onClick={() => setMobile(!mobile)}
          >
            {mobile ? <X size={21} /> : <Menu size={21} />}
          </button>
          <span className="breadcrumb">
            Your workspace <span>/</span> <strong>{currentPage}</strong>
          </span>
          <button
            className="access-button"
            aria-expanded={access}
            aria-controls="workspace-access"
            onClick={() => {
              setAccess(!access);
              setSaved(false);
            }}
          >
            <KeyRound size={16} /> Workspace access
          </button>
          <span className="avatar">CF</span>
        </header>
        {access && (
          <form
            id="workspace-access"
            className="access-panel"
            onSubmit={async (event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              await cache.cancelQueries();
              cache.clear();
              for (const role of ["candidate", "admin"]) {
                const value = String(data.get(role) ?? "").trim();
                if (value)
                  sessionStorage.setItem(`careerflowops-${role}`, value);
                else sessionStorage.removeItem(`careerflowops-${role}`);
              }
              setAccessVersion((value) => value + 1);
              setSaved(true);
            }}
          >
            <h2>Connect your local workspace</h2>
            <p>
              Use the access tokens from your local .env. Tokens stay in this
              browser tab’s session.
            </p>
            <div className="form-grid">
              <label>
                Candidate token
                <input
                  type="password"
                  autoComplete="off"
                  name="candidate"
                  defaultValue={
                    sessionStorage.getItem("careerflowops-candidate") ?? ""
                  }
                />
              </label>
              <label>
                Admin / TPO token
                <input
                  type="password"
                  autoComplete="off"
                  name="admin"
                  defaultValue={
                    sessionStorage.getItem("careerflowops-admin") ?? ""
                  }
                />
              </label>
            </div>
            <button className="button">Save access</button>
            <button
              className="button secondary"
              type="button"
              onClick={async () => {
                await cache.cancelQueries();
                sessionStorage.removeItem("careerflowops-candidate");
                sessionStorage.removeItem("careerflowops-admin");
                cache.clear();
                setAccessVersion((value) => value + 1);
                setAccess(false);
              }}
            >
              Disconnect this tab
            </button>
            {saved && (
              <span role="status" className="success">
                Access saved. Open a protected page to verify it.
              </span>
            )}
          </form>
        )}
        <main id="main-content" tabIndex={-1}>
          <Outlet key={accessVersion} />
        </main>
        <footer className="footer">
          CareerFlowOps{" "}
          <span>Discover earlier. Match smarter. Apply better.</span>
          <a
            href={`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            API docs <ArrowUpRight size={13} />
          </a>
        </footer>
      </div>
    </div>
  );
}
