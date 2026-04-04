# ADR-010: Roadmap Real

## Status
Accepted

## Date
2026-04-04

## Overrides
Substitui ADR-007 e ADR-008 em partes. Este é o roadmap real.

## Objectivo do produto (sempre)
Researchers fly blind. We give them the map.

---

## Fase 0: Demo para o amigo (AGORA — 1-2 semanas)

**Objectivo:** Mostrar ao teu amigo algo real que ele possa usar no PhD dele. Validar que isto é útil para um researcher real. Corre tudo local no teu Mac.

**O que faz:**
- Script Python que pega nos 10k papers de ML que já tens
- Gera embeddings (sentence-transformers)
- Projecta em 2D (UMAP)
- Detecta comunidades (Leiden)
- Nomeia clusters com Claude
- Renderiza num HTML interactivo local (browser)
- O teu amigo abre, vê o mapa de ML, explora clusters, clica em papers

**O que NÃO faz:**
- Não tem backend/API
- Não tem auth
- Não tem base de dados
- Não está na web
- Não suporta pesquisa por campo (é só ML, hardcoded)

**Output:** um ficheiro HTML + JSON que abres no browser e vês o mapa.

**Tech:**
- Python scripts (reutiliza código dos teus projectos)
- sentence-transformers (all-MiniLM-L6-v2)
- umap-learn
- leidenalg
- Claude API (cluster naming)
- HTML + Canvas/JS (visualização)

**Critério de sucesso:** o teu amigo abre e diz "fogo, isto é útil" ou "isto não serve para nada". Ambas as respostas são boas.

---

## Fase 1: MVP público (2-4 semanas após Fase 0)

**Objectivo:** Pôr na web, qualquer pessoa pode usar. Post no Reddit. Medir tração.

**O que muda vs Fase 0:**
- Backend com API (FastAPI)
- Suporta múltiplos campos (não só ML) — usa OpenAlex para buscar papers de qualquer área
- User escreve um tópico → pipeline processa → mapa aparece
- Deploy na web (VPS)
- Landing page com waitlist
- URL partilhável por mapa

**O que NÃO faz:**
- Contas de user
- Guardar mapas
- Upload de papers próprios
- Chat ou agents

**Critério de sucesso:** 500+ signups ou post no Reddit com tração significativa

---

## Fase 2: Produto real (1-3 meses após Fase 1)

**Objectivo:** Revenue. Users que voltam.

**O que muda vs Fase 1:**
- Contas de user (guardar mapas, histórico)
- Zoom multi-nível (campo → sub-campo → papers)
- Paper detail com abstract, citações, vizinhos semânticos
- Integrações: export para Zotero, Obsidian
- Alertas: "avisam-te quando aparecem papers novos no teu campo"
- Pricing: free tier + paid (institucional)

---

## Fase 3: Plataforma (6-12 meses após Fase 2)

**Objectivo:** Escala. Fundraising.

**O que muda vs Fase 2:**
- API pública (outros constroem em cima)
- Dados privados de empresas (enclaves seguros)
- Marketplace de agents de research
- Enterprise sales

---

## Resumo

| Fase | O quê | Onde corre | Dataset | Timeline |
|------|-------|-----------|---------|----------|
| 0 | Demo para o amigo | Local (Mac) | 10k papers ML (já tens) | 1-2 semanas |
| 1 | MVP público | VPS | OpenAlex (qualquer campo) | 2-4 semanas |
| 2 | Produto real | VPS | OpenAlex (todos os campos) | 1-3 meses |
| 3 | Plataforma | Cloud | Tudo + dados privados | 6-12 meses |
