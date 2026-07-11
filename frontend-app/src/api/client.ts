import type {
  BoardKind,
  BoardResponse,
  BoardStatus,
  Health,
  ImportResult,
  Job,
  Paper,
  Project,
  ProjectCreate,
  ReadStatus,
  SearchResult,
} from "../types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  health: () => request<Health>("/api/health"),

  listProjects: () =>
    request<{ projects: Project[] }>("/api/projects").then((r) => r.projects),

  getProject: (id: string) => request<Project>(`/api/projects/${id}`),

  createProject: (body: ProjectCreate) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteProject: (id: string) =>
    request<void>(`/api/projects/${id}`, { method: "DELETE" }),

  listPapers: (projectId: string, params?: { status?: string; tag?: string; q?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params ?? {}).filter(([, v]) => v) as [string, string][],
    ).toString();
    return request<{ papers: Paper[] }>(
      `/api/projects/${projectId}/papers${qs ? `?${qs}` : ""}`,
    ).then((r) => r.papers);
  },

  importFile: async (projectId: string, file: File): Promise<ImportResult> => {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`/api/projects/${projectId}/papers/import`, { method: "POST", body });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
    return res.json();
  },

  addPaper: (projectId: string, body: { doi?: string; url?: string }) =>
    request<Paper>(`/api/projects/${projectId}/papers`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updatePaper: (projectId: string, paperId: string, body: { read_status?: ReadStatus; tags?: string[] }) =>
    request<Paper>(`/api/projects/${projectId}/papers/${paperId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deletePaper: (projectId: string, paperId: string) =>
    request<void>(`/api/projects/${projectId}/papers/${paperId}`, { method: "DELETE" }),

  search: (projectId: string, q: string) =>
    request<{ query: string; results: SearchResult[] }>(
      `/api/projects/${projectId}/search?q=${encodeURIComponent(q)}`,
    ).then((r) => r.results),

  getJob: (jobId: string) => request<Job>(`/api/jobs/${jobId}`),

  getBoard: (projectId: string) => request<BoardResponse>(`/api/projects/${projectId}/board`),

  generateBoard: (projectId: string, paperIds?: string[]) =>
    request<{ job_id: string }>(`/api/projects/${projectId}/board/generate`, {
      method: "POST",
      body: JSON.stringify(paperIds ? { paper_ids: paperIds } : {}),
    }),

  createBoardItem: (projectId: string, body: { kind: BoardKind; text: string; paper_ids?: string[] }) =>
    request<{ id: string }>(`/api/projects/${projectId}/board/items`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateBoardItem: (projectId: string, itemId: string, body: { status?: BoardStatus; text?: string }) =>
    request<{ ok: boolean }>(`/api/projects/${projectId}/board/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteBoardItem: (projectId: string, itemId: string) =>
    request<void>(`/api/projects/${projectId}/board/items/${itemId}`, { method: "DELETE" }),
};
