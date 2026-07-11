import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function ProjectLayout() {
  const { id } = useParams<{ id: string }>();
  const project = useQuery({
    queryKey: ["project", id],
    queryFn: () => api.getProject(id!),
    enabled: !!id,
  });

  return (
    <div>
      <Link to="/" className="text-sm text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200">
        ← All projects
      </Link>

      {project.data && (
        <div className="mt-3">
          <h1 className="text-2xl font-semibold tracking-tight">{project.data.name}</h1>
          <p className="mt-1 text-sm text-neutral-500">{project.data.research_question}</p>
        </div>
      )}

      <nav className="mt-5 flex items-center gap-1 border-b border-neutral-200 dark:border-neutral-800">
        <Tab to={`/projects/${id}/library`}>Library</Tab>
        <Tab to={`/projects/${id}/board`}>Board</Tab>
        <span className="ml-auto flex gap-3 pb-1 text-xs text-neutral-400">
          <a href={`/api/projects/${id}/export.bib`} className="hover:text-neutral-700 dark:hover:text-neutral-200">
            Export .bib
          </a>
          <a href={`/api/projects/${id}/export.md`} className="hover:text-neutral-700 dark:hover:text-neutral-200">
            Export board .md
          </a>
        </span>
      </nav>

      <div className="pt-6">
        <Outlet context={{ projectId: id }} />
      </div>
    </div>
  );
}

function Tab({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
          isActive
            ? "border-neutral-900 text-neutral-900 dark:border-white dark:text-white"
            : "border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
        }`
      }
    >
      {children}
    </NavLink>
  );
}
