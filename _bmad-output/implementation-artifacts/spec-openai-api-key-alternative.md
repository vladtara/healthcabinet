---
title: 'OpenAI API key alternative'
type: 'feature'
created: '2026-05-06'
status: 'done'
context:
  - 'CLAUDE.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** AI calls currently require `ANTHROPIC_API_KEY`, which blocks local/dev and deployments where only an OpenAI API key is available.

**Approach:** Add OpenAI as an alternate provider for chat and document extraction while preserving Anthropic as the default provider when both keys are present.

## Boundaries & Constraints

**Always:** Preserve existing Anthropic behavior by default; keep provider configuration environment-driven; keep OpenAI health document bytes inside direct provider API calls and do not persist or log key material.

**Ask First:** Introducing a database-backed provider setting, removing Anthropic support, or changing user-facing AI workflows.

**Never:** Commit real API keys, change frontend UX, or send documents through a third-party proxy.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Anthropic configured | `ANTHROPIC_API_KEY` present | Existing Anthropic chat and extraction paths are used | Existing provider errors still translate to domain errors |
| OpenAI fallback | Anthropic key blank, `OPENAI_API_KEY` present | Chat uses OpenAI model and extraction uses OpenAI Responses API | OpenAI temporary errors translate to temporary domain errors |
| Explicit OpenAI | `AI_CHAT_PROVIDER=openai` or `AI_EXTRACTION_PROVIDER=openai` | Matching flow uses OpenAI even if Anthropic key exists | Missing OpenAI key raises configuration error |
| No provider key | Both keys blank | AI call fails fast with a clear missing key message | No provider request is attempted |

</frozen-after-approval>

## Code Map

- `healthcabinet/backend/app/core/config.py` -- backend settings and provider env vars.
- `healthcabinet/backend/app/ai/llm_client.py` -- LangChain chat adapter and provider error translation.
- `healthcabinet/backend/app/processing/extractor.py` -- document extraction provider boundary.
- `healthcabinet/backend/.env.example` -- documented local/deployment env shape.
- `healthcabinet/backend/pyproject.toml` -- OpenAI dependencies.
- `healthcabinet/backend/tests/ai/test_llm_client.py` -- chat provider selection and errors.
- `healthcabinet/backend/tests/processing/test_extractor.py` -- extraction provider selection and request shape.

## Tasks & Acceptance

**Execution:**
- [x] `healthcabinet/backend/app/core/config.py` -- add OpenAI key/model/provider settings -- enables env-driven fallback.
- [x] `healthcabinet/backend/app/ai/llm_client.py` -- support Anthropic/OpenAI chat providers -- preserves existing service API.
- [x] `healthcabinet/backend/app/processing/extractor.py` -- support Anthropic/OpenAI extraction providers -- makes document processing work with either key.
- [x] `healthcabinet/backend/tests/ai/test_llm_client.py` and `healthcabinet/backend/tests/processing/test_extractor.py` -- add focused provider tests -- locks fallback/explicit behavior.
- [x] `healthcabinet/backend/.env.example` and dependency files -- document and install OpenAI provider support.

**Acceptance Criteria:**
- Given only `OPENAI_API_KEY` is configured, when chat AI is called, then the OpenAI chat model is created and invoked.
- Given only `OPENAI_API_KEY` is configured, when document extraction runs for a PDF or image, then the OpenAI Responses API request includes the document/image and returns validated extraction JSON.
- Given both provider keys are blank, when an AI flow starts, then it raises a clear configuration error naming both supported keys.
- Given Anthropic settings are unchanged, when AI flows run, then existing Anthropic request behavior remains compatible.

## Verification

**Commands:**
- `uv run pytest tests/ai/test_llm_client.py tests/processing/test_extractor.py` -- expected: all focused provider tests pass.
- `uv run ruff check .` -- expected: no lint regressions.
- `uv run mypy app/` -- expected: no type regressions in strict backend typing.
