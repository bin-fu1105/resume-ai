function NavLink({ href, active, onClick, children }) {
  return (
    <a
      href={href}
      onClick={onClick}
      className={`rounded-md transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
        active ? "font-semibold text-ink" : "hover:text-accent"
      }`}
      aria-current={active ? "page" : undefined}
    >
      {children}
    </a>
  );
}

function Navbar({ activeTab = "dashboard", onTabChange }) {
  const goTab = (tab) => (event) => {
    if (typeof onTabChange === "function") {
      event.preventDefault();
      onTabChange(tab);
    }
  };

  return (
    <header className="sticky top-0 z-20 border-b border-line/80 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3.5 sm:px-6 sm:py-4">
        <a
          href="#workspace"
          onClick={goTab("dashboard")}
          className="flex min-w-0 items-center gap-3 rounded-xl transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="ResumeAI home"
        >
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent text-sm font-semibold text-white shadow-sm"
            aria-hidden="true"
          >
            RA
          </div>
          <div className="min-w-0">
            <p className="font-display text-base font-semibold tracking-tight text-ink sm:text-lg">
              ResumeAI
            </p>
            <p className="truncate text-xs text-muted">Optimization dashboard</p>
          </div>
        </a>

        <nav
          aria-label="Primary"
          className="flex items-center gap-3 text-sm font-medium text-muted sm:gap-5"
        >
          <NavLink
            href="#workspace"
            active={activeTab === "dashboard"}
            onClick={goTab("dashboard")}
          >
            Workspace
          </NavLink>
          <NavLink
            href="#results"
            active={activeTab === "dashboard"}
            onClick={goTab("dashboard")}
          >
            Results
          </NavLink>
          <NavLink
            href="#heatmap"
            active={activeTab === "heatmap"}
            onClick={goTab("heatmap")}
          >
            Heatmap
          </NavLink>
          <NavLink
            href="#compare"
            active={activeTab === "compare"}
            onClick={goTab("compare")}
          >
            Compare
          </NavLink>
          <NavLink
            href="#interview"
            active={activeTab === "interview"}
            onClick={goTab("interview")}
          >
            Interview
          </NavLink>
          <NavLink
            href="#jobs"
            active={activeTab === "jobs"}
            onClick={goTab("jobs")}
          >
            Jobs
          </NavLink>
          <NavLink
            href="#coach"
            active={activeTab === "dashboard"}
            onClick={goTab("dashboard")}
          >
            Coach
          </NavLink>
        </nav>
      </div>
    </header>
  );
}

export default Navbar;
