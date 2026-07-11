import { Link, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api/client";

export function AppLayout() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });

  return (
    <div className="min-h-screen">
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Research Navigator
          </Link>
          {health.data && !health.data.board_generation_available && (
            <span className="text-xs text-amber-600 dark:text-amber-400">
              AI board generation disabled (no API key)
            </span>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
