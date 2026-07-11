// Mirrors the Pydantic models in backend/. Keep in sync with the API.

export interface Project {
  id: string;
  name: string;
  research_question: string;
  hypothesis: string | null;
  scope_notes: string | null;
  created_at: string;
  updated_at: string;
  paper_count: number;
  board_item_count: number;
}

export interface ProjectCreate {
  name: string;
  research_question: string;
  hypothesis?: string;
  scope_notes?: string;
}

export interface Health {
  ok: boolean;
  board_generation_available: boolean;
}

export type ReadStatus = "unread" | "reading" | "read" | "important" | "rejected";
export type EnrichmentStatus = "pending" | "enriched" | "not_found" | "no_abstract";

export interface Paper {
  id: string;
  project_id: string;
  openalex_id: string | null;
  doi: string | null;
  title: string;
  authors: string | null;
  abstract: string | null;
  year: number | null;
  venue: string | null;
  cited_by_count: number | null;
  pdf_url: string | null;
  source: string;
  enrichment_status: EnrichmentStatus;
  read_status: ReadStatus;
  tags: string[];
  added_at: string;
  updated_at: string;
}

export interface SearchResult extends Paper {
  score: number | null;
  match: "semantic" | "keyword" | "both";
}

export interface ImportResult {
  imported: number;
  duplicates: number;
  errors: string[];
  enrich_job_id: string | null;
}

export interface Job {
  id: string;
  project_id: string;
  type: "enrich" | "generate_board";
  status: "queued" | "running" | "done" | "error";
  progress_done: number;
  progress_total: number;
  error: string | null;
}
