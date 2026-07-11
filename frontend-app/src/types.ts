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
