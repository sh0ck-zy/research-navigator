import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { BoardItem, BoardKind } from "../types";

// Board sections, in reading order. Evidence hangs under its claim, so it has
// no top-level section here.
const SECTIONS: { kind: BoardKind; title: string; blurb: string }[] = [
  { kind: "concept", title: "Central concepts", blurb: "The ideas this literature is built on" },
  { kind: "claim", title: "Claims", blurb: "What the papers assert — with supporting and contradicting evidence" },
  { kind: "open_question", title: "Open questions", blurb: "What the field hasn't settled" },
  { kind: "next_action", title: "Next actions", blurb: "Where to take the research" },
];

export function Board() {
  const { projectId } = useOutletContext<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [activeJob, setActiveJob] = useState<string | null>(null);

  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const board = useQuery({
    queryKey: ["board", projectId],
    queryFn: () => api.getBoard(projectId),
  });

  const job = useQuery({
    queryKey: ["board-job", activeJob],
    queryFn: () => api.getJob(activeJob!),
    enabled: !!activeJob,
    refetchInterval: (q) =>
      ["done", "error"].includes(q.state.data?.status ?? "") ? false : 1200,
  });
  if (job.data && ["done", "error"].includes(job.data.status) && activeJob) {
    setActiveJob(null);
    queryClient.invalidateQueries({ queryKey: ["board", projectId] });
  }

  const generate = useMutation({
    mutationFn: () => api.generateBoard(projectId),
    onSuccess: (r) => setActiveJob(r.job_id),
  });

  const items = board.data?.items ?? [];
  const canGenerate = health.data?.board_generation_available;
  const generating = generate.isPending || (!!job.data && job.data.status !== "done" && job.data.status !== "error");
  const gen = board.data?.last_generation;

  return (
    <div className="space-y-6">
      <p className="rounded-lg border border-amber-300/60 bg-amber-50 px-4 py-2.5 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
        Drafted from titles and abstracts only — verify against the full text before relying on any claim.
      </p>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-neutral-500">
          {gen?.token_usage && (
            <span>
              Last run: {gen.token_usage.input_tokens.toLocaleString()} in /{" "}
              {gen.token_usage.output_tokens.toLocaleString()} out
              {gen.dropped_items > 0 && ` · ${gen.dropped_items} unverifiable items dropped`}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {!canGenerate && (
            <span className="text-xs text-amber-600 dark:text-amber-400">
              Set ANTHROPIC_API_KEY to enable AI drafting
            </span>
          )}
          <button
            onClick={() => generate.mutate()}
            disabled={!canGenerate || generating}
            className="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-neutral-900"
          >
            {generating ? "Drafting…" : items.length ? "Regenerate draft" : "Draft the board"}
          </button>
        </div>
      </div>

      {job.data?.status === "error" && (
        <p className="text-sm text-red-600">Generation failed: {job.data.error}</p>
      )}
      {generating && (
        <p className="text-sm text-neutral-500">
          Reading the papers and drafting the board — this takes a minute or two.
        </p>
      )}

      {board.isLoading && <p className="text-neutral-500">Loading…</p>}
      {!board.isLoading && items.length === 0 && !generating && (
        <div className="rounded-xl border border-dashed border-neutral-300 py-16 text-center dark:border-neutral-700">
          <p className="text-neutral-500">The board is empty.</p>
          <p className="mt-1 text-sm text-neutral-400">
            Draft it from your library, or add items by hand as you read.
          </p>
        </div>
      )}

      {SECTIONS.map((s) => (
        <Section key={s.kind} section={s} items={items} projectId={projectId} />
      ))}
    </div>
  );
}

function Section({
  section,
  items,
  projectId,
}: {
  section: { kind: BoardKind; title: string; blurb: string };
  items: BoardItem[];
  projectId: string;
}) {
  const mine = items.filter((i) => i.kind === section.kind);
  const evidenceByClaim = (claimId: string) =>
    items.filter((i) => i.parent_id === claimId);
  if (mine.length === 0) return null;

  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">{section.title}</h2>
      <p className="mb-3 text-xs text-neutral-400">{section.blurb}</p>
      <div className="space-y-2">
        {mine.map((item) => (
          <div key={item.id}>
            <ItemCard item={item} projectId={projectId} />
            {item.kind === "claim" && (
              <div className="ml-6 mt-2 space-y-2 border-l border-neutral-200 pl-4 dark:border-neutral-800">
                {evidenceByClaim(item.id).map((ev) => (
                  <ItemCard key={ev.id} item={ev} projectId={projectId} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

const KIND_ACCENT: Partial<Record<BoardKind, string>> = {
  evidence_support: "border-l-2 border-l-green-500",
  evidence_contradiction: "border-l-2 border-l-red-500",
};

function ItemCard({ item, projectId }: { item: BoardItem; projectId: string }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.text);
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["board", projectId] });

  const patch = useMutation({
    mutationFn: (body: { status?: "accepted" | "rejected"; text?: string }) =>
      api.updateBoardItem(projectId, item.id, body),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: () => api.deleteBoardItem(projectId, item.id),
    onSuccess: invalidate,
  });

  const proposed = item.status === "proposed";
  const evidencePrefix =
    item.kind === "evidence_support" ? "Supports: " :
    item.kind === "evidence_contradiction" ? "Contradicts: " : "";

  return (
    <div
      className={`rounded-lg border p-3 ${KIND_ACCENT[item.kind] ?? ""} ${
        proposed
          ? "border-dashed border-neutral-300 bg-neutral-50/50 dark:border-neutral-700 dark:bg-neutral-900/40"
          : item.status === "rejected"
          ? "border-neutral-200 opacity-50 dark:border-neutral-800"
          : "border-neutral-200 dark:border-neutral-800"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        {editing ? (
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={2}
            className="flex-1 rounded border border-neutral-300 bg-transparent px-2 py-1 text-sm dark:border-neutral-700"
            autoFocus
          />
        ) : (
          <p className={`flex-1 text-sm ${item.status === "rejected" ? "line-through" : ""}`}>
            {evidencePrefix && <span className="text-neutral-400">{evidencePrefix}</span>}
            {item.text}
          </p>
        )}
        <ProvenanceBadge provenance={item.provenance} status={item.status} />
      </div>

      {item.papers.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {item.papers.map((p) => (
            <PaperChip key={p.paper_id} paper={p} />
          ))}
        </div>
      )}

      <div className="mt-2 flex gap-3 text-xs">
        {editing ? (
          <>
            <button
              onClick={() => { patch.mutate({ text: draft }); setEditing(false); }}
              className="font-medium text-neutral-900 dark:text-white"
            >
              Save
            </button>
            <button onClick={() => { setDraft(item.text); setEditing(false); }} className="text-neutral-400">
              Cancel
            </button>
          </>
        ) : (
          <>
            {proposed && (
              <button
                onClick={() => patch.mutate({ status: "accepted" })}
                className="font-medium text-green-600"
              >
                Accept
              </button>
            )}
            <button onClick={() => setEditing(true)} className="text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200">
              Edit
            </button>
            {proposed ? (
              <button onClick={() => patch.mutate({ status: "rejected" })} className="text-neutral-500 hover:text-red-600">
                Reject
              </button>
            ) : (
              <button onClick={() => remove.mutate()} className="text-neutral-500 hover:text-red-600">
                Delete
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function ProvenanceBadge({ provenance, status }: { provenance: string; status: string }) {
  const label =
    provenance === "user_created" ? "you" :
    provenance === "user_edited" ? "you (edited)" :
    status === "accepted" ? "AI · accepted" :
    status === "rejected" ? "AI · rejected" : "AI · proposed";
  return (
    <span className="shrink-0 whitespace-nowrap rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-neutral-500 dark:bg-neutral-800">
      {label}
    </span>
  );
}

function PaperChip({ paper }: { paper: BoardItem["papers"][number] }) {
  const [open, setOpen] = useState(false);
  const first = (paper.authors ?? "").split(",")[0].trim();
  const label = `${first || "—"}${paper.year ? ` ${paper.year}` : ""}`;
  const hasQuote = paper.quote != null;
  return (
    <span className="relative">
      <button
        onClick={() => hasQuote && setOpen((o) => !o)}
        title={paper.title}
        className={`rounded-full px-2 py-0.5 text-[11px] ${
          paper.quote_valid
            ? "bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-400"
            : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
        }`}
      >
        {label}
        {hasQuote && (paper.quote_valid ? " ✓" : "")}
      </button>
      {open && paper.quote && (
        <span className="absolute left-0 top-full z-10 mt-1 block w-72 rounded-lg border border-neutral-200 bg-white p-2 text-xs italic text-neutral-600 shadow-lg dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
          “{paper.quote}”
        </span>
      )}
    </span>
  );
}
