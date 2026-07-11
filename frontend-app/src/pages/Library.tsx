import { useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { EnrichmentStatus, Paper, ReadStatus } from "../types";

const READ_STATUSES: ReadStatus[] = ["unread", "reading", "read", "important", "rejected"];

const ENRICH_LABEL: Record<EnrichmentStatus, string> = {
  pending: "enriching…",
  enriched: "enriched",
  not_found: "not on OpenAlex",
  no_abstract: "no abstract",
};

export function Library() {
  const { projectId } = useOutletContext<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [activeJob, setActiveJob] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const papers = useQuery({
    queryKey: ["papers", projectId],
    queryFn: () => api.listPapers(projectId),
  });

  // Poll the enrichment job; refresh the paper list as it progresses.
  const job = useQuery({
    queryKey: ["job", activeJob],
    queryFn: () => api.getJob(activeJob!),
    enabled: !!activeJob,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "done" || s === "error" ? false : 1000;
    },
  });
  if (job.data && (job.data.status === "done" || job.data.status === "error") && activeJob) {
    setActiveJob(null);
    queryClient.invalidateQueries({ queryKey: ["papers", projectId] });
    queryClient.invalidateQueries({ queryKey: ["project", projectId] });
  }

  const importFile = useMutation({
    mutationFn: (file: File) => api.importFile(projectId, file),
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: ["papers", projectId] });
      if (r.enrich_job_id) setActiveJob(r.enrich_job_id);
    },
  });

  const addByRef = useMutation({
    mutationFn: (ref: string) =>
      api.addPaper(projectId, ref.startsWith("http") ? { url: ref } : { doi: ref }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["papers", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  const setStatus = useMutation({
    mutationFn: ({ id, read_status }: { id: string; read_status: ReadStatus }) =>
      api.updatePaper(projectId, id, { read_status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["papers", projectId] }),
  });

  return (
    <div className="space-y-6">
      <ImportRow
        onFile={(f) => importFile.mutate(f)}
        onRef={(r) => addByRef.mutate(r)}
        fileInput={fileInput}
        importing={importFile.isPending}
        adding={addByRef.isPending}
        addError={addByRef.error as Error | null}
      />

      {job.data && job.data.status !== "done" && (
        <ProgressBar done={job.data.progress_done} total={job.data.progress_total} />
      )}

      {papers.isLoading && <p className="text-neutral-500">Loading…</p>}
      {papers.data?.length === 0 && !importFile.isPending && (
        <p className="rounded-xl border border-dashed border-neutral-300 py-12 text-center text-neutral-500 dark:border-neutral-700">
          No papers yet. Import a Zotero .bib/.ris export or add one by DOI.
        </p>
      )}

      <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
        {papers.data?.map((p) => (
          <PaperRow key={p.id} p={p} onStatus={(s) => setStatus.mutate({ id: p.id, read_status: s })} />
        ))}
      </ul>
    </div>
  );
}

function ImportRow({
  onFile,
  onRef,
  fileInput,
  importing,
  adding,
  addError,
}: {
  onFile: (f: File) => void;
  onRef: (r: string) => void;
  fileInput: React.RefObject<HTMLInputElement>;
  importing: boolean;
  adding: boolean;
  addError: Error | null;
}) {
  const [ref, setRef] = useState("");
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => fileInput.current?.click()}
          disabled={importing}
          className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium hover:border-neutral-500 disabled:opacity-40 dark:border-neutral-700"
        >
          {importing ? "Importing…" : "Import .bib / .ris"}
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".bib,.bibtex,.ris"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
            e.target.value = "";
          }}
        />
        <span className="text-sm text-neutral-400">or</span>
        <form
          className="flex flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (ref.trim()) {
              onRef(ref.trim());
              setRef("");
            }
          }}
        >
          <input
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            placeholder="Add by DOI or URL (arXiv / OpenAlex)"
            className="min-w-0 flex-1 rounded-lg border border-neutral-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700"
          />
          <button
            type="submit"
            disabled={adding || !ref.trim()}
            className="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-neutral-900"
          >
            {adding ? "Adding…" : "Add"}
          </button>
        </form>
      </div>
      {addError && <p className="text-sm text-red-600">{addError.message}</p>}
    </div>
  );
}

function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-neutral-500">
        <span>Enriching from OpenAlex…</span>
        <span>{done}/{total}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
        <div className="h-full bg-neutral-900 transition-all dark:bg-white" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const STATUS_COLOR: Record<ReadStatus, string> = {
  unread: "text-neutral-400",
  reading: "text-blue-500",
  read: "text-green-600",
  important: "text-amber-500",
  rejected: "text-neutral-400 line-through",
};

function PaperRow({ p, onStatus }: { p: Paper; onStatus: (s: ReadStatus) => void }) {
  return (
    <li className="py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className={`font-medium ${p.read_status === "rejected" ? "line-through opacity-60" : ""}`}>
            {p.title}
          </h3>
          <p className="mt-0.5 truncate text-sm text-neutral-500">
            {[p.authors, p.year, p.venue].filter(Boolean).join(" · ") || "—"}
          </p>
          <div className="mt-1.5 flex items-center gap-2 text-xs text-neutral-400">
            <span>{p.cited_by_count != null ? `${p.cited_by_count} citations` : "—"}</span>
            <span>·</span>
            <span className={p.enrichment_status === "enriched" ? "text-green-600" : ""}>
              {ENRICH_LABEL[p.enrichment_status]}
            </span>
          </div>
        </div>
        <select
          value={p.read_status}
          onChange={(e) => onStatus(e.target.value as ReadStatus)}
          className={`shrink-0 rounded-md border border-neutral-300 bg-transparent px-2 py-1 text-xs ${STATUS_COLOR[p.read_status]} dark:border-neutral-700`}
        >
          {READ_STATUSES.map((s) => (
            <option key={s} value={s} className="text-neutral-900">
              {s}
            </option>
          ))}
        </select>
      </div>
    </li>
  );
}
