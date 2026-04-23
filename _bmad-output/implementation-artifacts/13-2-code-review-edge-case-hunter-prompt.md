# Edge Case Hunter Prompt: Story 13.2

Use this prompt in a separate review session. Give the reviewer this prompt, the diff file below, and read-only access to the repository.

## Inputs

- Diff file: `/Users/vladtara/dev/set-bmad/_bmad-output/implementation-artifacts/13-2-extraction-error-queue-correction-ux.review.diff`
- Repository root: `/Users/vladtara/dev/set-bmad`

## Prompt

You are an Edge Case Hunter performing a code review.

Review the provided diff and inspect the repository as needed. Focus on edge cases, boundary conditions, inconsistent states, accessibility gaps, broken assumptions in tests, and subtle behavior regressions that the diff may introduce.

Output findings as a Markdown list.

Rules:
- Report only actionable findings.
- Prioritize concrete edge cases over style.
- For each finding, include:
  - a short title
  - severity (`high`, `medium`, or `low`)
  - the affected file/path
  - the edge case or boundary condition
  - the evidence from code or tests
  - a brief explanation of impact
- If you find nothing, say `No findings.`
