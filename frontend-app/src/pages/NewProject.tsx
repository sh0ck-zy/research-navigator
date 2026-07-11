import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function NewProject() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    research_question: "",
    hypothesis: "",
    scope_notes: "",
  });

  const create = useMutation({
    mutationFn: api.createProject,
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${project.id}/library`);
    },
  });

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const canSubmit = form.name.trim() && form.research_question.trim();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">New research project</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!canSubmit) return;
          create.mutate({
            name: form.name.trim(),
            research_question: form.research_question.trim(),
            hypothesis: form.hypothesis.trim() || undefined,
            scope_notes: form.scope_notes.trim() || undefined,
          });
        }}
        className="space-y-5"
      >
        <Field label="Project name">
          <input
            value={form.name}
            onChange={set("name")}
            placeholder="xAI on fMRI"
            className={inputClass}
            autoFocus
          />
        </Field>
        <Field label="Research question" hint="The one question this project exists to answer.">
          <textarea
            value={form.research_question}
            onChange={set("research_question")}
            placeholder="Can query-conditioned representations reduce the compute cost of fMRI models?"
            rows={2}
            className={inputClass}
          />
        </Field>
        <Field label="Working hypothesis" hint="Optional — what you currently believe.">
          <textarea value={form.hypothesis} onChange={set("hypothesis")} rows={2} className={inputClass} />
        </Field>
        <Field label="Scope notes" hint="Optional — boundaries, timeframe, what's in or out.">
          <textarea value={form.scope_notes} onChange={set("scope_notes")} rows={2} className={inputClass} />
        </Field>

        {create.error && <p className="text-sm text-red-600">{(create.error as Error).message}</p>}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={!canSubmit || create.isPending}
            className="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-neutral-900"
          >
            {create.isPending ? "Creating…" : "Create project"}
          </button>
          <button type="button" onClick={() => navigate("/")} className="px-4 py-2 text-sm text-neutral-500">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-neutral-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      {hint && <span className="ml-2 text-xs text-neutral-400">{hint}</span>}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}
