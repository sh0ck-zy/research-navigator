# ADR-004: Product Vision and Phasing

## Status
Accepted

## Date
2026-04-04

## Context
The long-term vision is ambitious: become the platform where the world does research. But we need to get there in phases, each building on the previous.

## Decision

### Phase 1: Product (now → traction)
Build a single tool that researchers love. One killer feature, beautiful UI/UX, launched on Reddit. Target: 1,000+ active users.

### Phase 2: Platform (traction → revenue)
Open API/SDK. Others build tools on top of our data and workflows. Integrations with Zotero, Obsidian, Overleaf. Target: institutional sales, revenue.

### Phase 3: Infrastructure (revenue → scale)
Become the platform where anyone deploys research agents. Marketplace for specialized research tools. Target: unicorn territory.

### Key principle
Each phase MUST be validated before moving to the next. No skipping.

## Consequences
- We focus 100% on Phase 1 until we have real users
- All Phase 2/3 ideas go in a backlog, not in the codebase
- Technical decisions should not block future phases but should not optimize for them either
