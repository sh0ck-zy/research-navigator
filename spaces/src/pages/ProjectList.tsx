import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function ProjectList() {
  const { data: projects, isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Your research</h1>
        <Link
          to="/projects/new"
          className="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
        >
          New project
        </Link>
      </div>

      {isLoading && <p className="text-neutral-500">Loading…</p>}
      {error && <p className="text-red-600">{(error as Error).message}</p>}

      {projects?.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-300 py-16 text-center dark:border-neutral-700">
          <p className="text-neutral-500">No projects yet.</p>
          <p className="mt-1 text-sm text-neutral-400">
            Start with a research question and a handful of papers.
          </p>
        </div>
      )}

      <ul className="space-y-3">
        {projects?.map((p) => (
          <li key={p.id}>
            <Link
              to={`/projects/${p.id}/board`}
              className="block rounded-xl border border-neutral-200 p-5 transition hover:border-neutral-400 dark:border-neutral-800 dark:hover:border-neutral-600"
            >
              <h2 className="font-medium">{p.name}</h2>
              <p className="mt-1 line-clamp-2 text-sm text-neutral-500">
                {p.research_question}
              </p>
              <p className="mt-3 text-xs text-neutral-400">
                {p.paper_count} papers · {p.board_item_count} board items
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
