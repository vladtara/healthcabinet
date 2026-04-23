---
stepsCompleted:
  - compiled
  - source-verification
  - repo-fit-analysis
inputDocuments:
  - _bmad-output/implementation-artifacts/5-0-langchain-ai-migration.md
  - _bmad-output/implementation-artifacts/5-4-langgraph-processing-graph-adoption.md
  - _bmad-output/planning-artifacts/architecture.md
workflowType: "research"
lastStep: 1
research_type: "technical"
research_topic: "langchain-langgraph"
research_goals: "Document current LangChain and LangGraph guidance and map each technology to Story 5.0 and Story 5.4 in this repo"
user_name: "DUDE"
date: "2026-03-31"
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-03-31
**Author:** DUDE
**Research Type:** technical

---

## Research Overview

This report consolidates the LangChain and LangGraph research used to scope Story 5.0 and Story 5.4.

Method:
- Verified current official documentation from LangChain/LangGraph on March 31, 2026.
- Compared that guidance against the current HealthCabinet backend structure.
- Mapped the findings to the two existing implementation stories instead of treating LangChain and LangGraph as one migration.

---

## Executive Summary

- LangChain is the correct fit for Story 5.0 because the immediate repo problem is the LLM provider seam inside `healthcabinet/backend/app/ai/`.
- LangGraph is the correct fit for Story 5.4 because the orchestration problem lives in `healthcabinet/backend/app/processing/worker.py`, not in the chat-model adapter layer.
- The architecture document still references older LangGraph and LangChain version targets. Current official docs describe LangGraph v1.x and a broader LangChain runtime surface, so story implementation should follow current official APIs rather than pinning to the older architecture note.
- The clean sequence for this repo is:
  1. Story 5.0: migrate `app/ai/` to a LangChain-backed adapter.
  2. Story 5.4: adopt LangGraph for processing orchestration around the existing extractor and worker boundaries.

---

## Current Official Guidance

### LangChain

- LangChain positions itself as the higher-level application framework for model access, prompts, streaming, structured output, tools, and retrieval.
- For this repo, the relevant capability is the model abstraction seam, not agent tooling.
- The official Anthropic integration exposes `ChatAnthropic`, including async invocation and streaming support, which is sufficient for the current `app/ai/service.py` behaviors.
- Official structured-output guidance is useful for a later extractor refactor, but it is not required for Story 5.0 because Story 5.0 only needs text generation and streaming.

### LangGraph

- LangGraph positions itself as the orchestration runtime for stateful, branching, durable workflows.
- That maps to this repo's document-processing pipeline, where work currently happens in one worker-oriented orchestration path.
- LangGraph is a good fit when the repo needs explicit node boundaries, conditional branching, observable state, and later checkpointing or resumability.
- LangGraph is not the right first move for the current `app/ai/` migration because that work does not need graph orchestration.

### Implication For This Repo

- LangChain solves the provider-abstraction problem.
- LangGraph solves the workflow-orchestration problem.
- Treating them as one story would hide two different migration risks behind one label and make rollback/testing harder.

---

## Repo Fit Analysis

### Current Backend Reality

The current codebase splits the problem into two different areas:

- `healthcabinet/backend/app/ai/service.py` contains direct AI feature usage for interpretation generation, cross-upload pattern detection, and follow-up chat streaming.
- `healthcabinet/backend/app/ai/claude_client.py` was the provider-specific seam and import-time client-creation hotspot addressed by Story 5.0.
- `healthcabinet/backend/app/processing/worker.py` contains the processing orchestration problem that Story 5.4 should refactor.
- `healthcabinet/backend/app/processing/extractor.py` is a separate direct Anthropic consumer and should not be quietly rewritten under the Story 5.0 adapter migration.

The current repo does not yet implement the future-state processing graph described in architecture:

- no `healthcabinet/backend/app/processing/graph.py`
- no `healthcabinet/backend/app/processing/nodes/`
- no LangGraph runtime wired into the worker path

### Story 5.0 Fit: LangChain AI Module Migration

Story file:
- `_bmad-output/implementation-artifacts/5-0-langchain-ai-migration.md`

LangChain is the right technology for Story 5.0 because it matches the required scope:

- replace the direct Anthropic dependency seam inside `app/ai/`
- preserve current HTTP contracts and safety behavior
- preserve streaming semantics for `/api/v1/ai/chat`
- improve testability by patching a local adapter boundary instead of provider-specific helpers

Story 5.0 should remain limited to:

- `healthcabinet/backend/app/ai/`
- backend dependency and config changes
- AI-focused backend tests

Story 5.0 should explicitly avoid:

- `healthcabinet/backend/app/processing/worker.py`
- `healthcabinet/backend/app/processing/extractor.py`
- LangGraph runtime adoption
- queueing or orchestration redesign

### Story 5.4 Fit: LangGraph Processing Graph Adoption

Story file:
- `_bmad-output/implementation-artifacts/5-4-langgraph-processing-graph-adoption.md`

LangGraph is the right technology for Story 5.4 because it matches the actual orchestration refactor:

- convert the current worker pipeline into explicit stateful nodes
- represent branch conditions and terminal outcomes directly in graph flow
- keep ARQ as the job entrypoint while using LangGraph inside the job
- preserve existing SSE event names, payload shape, and fallback semantics

Story 5.4 should focus on:

- `healthcabinet/backend/app/processing/graph.py`
- `healthcabinet/backend/app/processing/nodes/*`
- `healthcabinet/backend/app/processing/worker.py`
- processing-oriented tests

Story 5.4 should explicitly avoid:

- frontend changes
- admin workflows
- Redis checkpoint-resume rollout
- pgvector enrichment nodes
- extractor-provider rewrites unless a later story intentionally takes that on

---

## Recommended Sequencing

1. Complete Story 5.0 first so `app/ai/` has a stable LangChain adapter seam.
2. Use Story 5.4 to refactor processing orchestration around the existing extractor and AI service boundaries.
3. Consider extractor migration only after the orchestration boundary is stable, because extractor migration touches a different failure surface and test matrix.

This order keeps the first migration small and measurable, then moves the graph work into the part of the repo where it actually belongs.

---

## Implementation Risks And Traps

- Do not treat LangChain and LangGraph as interchangeable. They solve different problems in this repo.
- Do not rely on the architecture document's older package-version language as the implementation source of truth; official docs have moved on.
- Do not hide extractor migration inside Story 5.0. `app/processing/extractor.py` has its own API shape and tests.
- Do not let LangGraph adoption change user-visible status events or fallback document-status behavior unless a future story explicitly authorizes that behavior change.
- Do not introduce graph complexity before state boundaries are explicit. For this repo, a minimal graph with a few clear nodes is safer than trying to implement the full target-state architecture in one jump.

---

## Story Mapping

- Story 5.0 research target:
  - `_bmad-output/implementation-artifacts/5-0-langchain-ai-migration.md`
- Story 5.4 research target:
  - `_bmad-output/implementation-artifacts/5-4-langgraph-processing-graph-adoption.md`

Companion research artifact path:
- `_bmad-output/planning-artifacts/research/technical-langchain-langgraph-research-2026-03-31.md`

---

## Sources

Official documentation:
- https://docs.langchain.com/oss/python/langchain/overview
- https://docs.langchain.com/oss/python/langchain/streaming
- https://docs.langchain.com/oss/python/integrations/chat/anthropic
- https://docs.langchain.com/oss/python/langchain/structured-output
- https://docs.langchain.com/oss/python/langgraph/overview
- https://docs.langchain.com/oss/python/langgraph/streaming

Repo sources:
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/implementation-artifacts/5-0-langchain-ai-migration.md`
- `_bmad-output/implementation-artifacts/5-4-langgraph-processing-graph-adoption.md`
- `healthcabinet/backend/app/ai/service.py`
- `healthcabinet/backend/app/ai/claude_client.py`
- `healthcabinet/backend/app/processing/worker.py`
- `healthcabinet/backend/app/processing/extractor.py`
