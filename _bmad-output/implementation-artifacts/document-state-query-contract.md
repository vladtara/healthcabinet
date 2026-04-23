# Document State & Query Contract

Canonical reference for document status semantics and TanStack Query cache behavior.
**Read this before writing any story that touches documents, health values, or dashboard state.**

---

## Document Status Semantics

| Status | Meaning | SSE Active? | Values Available? |
|--------|---------|------------|------------------|
| `pending` | Queued for ARQ worker | Yes | No |
| `processing` | Worker actively extracting | Yes | No |
| `completed` | All values extracted successfully | No | Yes |
| `partial` | Extraction partially succeeded (low confidence or incomplete) | No | Possibly — check `health_values` |
| `failed` | Extraction failed entirely | No | No |

### Rules

1. `partial` and `failed` are **product behaviors**, not implementation details. The UI must treat them distinctly:
   - `partial` → show recovery UI (re-upload CTA + keep-partial option)
   - `failed` → show failure UI (re-upload CTA only, no keep-partial)
2. A `partial` document with `keep_partial: true` has been acknowledged by the user. Do not show recovery UI in this state.
3. SSE connections are opened for `pending` and `processing` documents and closed on any terminal event.
4. `health_values` are only queryable after a `completed` or `partial` terminal state.

---

## Query Keys

```typescript
// Full list of query keys used in the project
['documents']                          // list of all user documents
['documents', docId]                   // individual document + health_values detail
['health_values']                      // all user health values (flat)
['baseline']                           // profile-based dashboard baseline
['timeline', canonicalBiomarkerName]   // per-biomarker time-series values
['timeline']                           // prefix — invalidates ALL timeline queries
```

---

## Cache Invalidation Rules

### After SSE Terminal Event

```typescript
// documents/+page.svelte SSE handler
if (status === 'completed' || status === 'partial') {
  queryClient.invalidateQueries({ queryKey: ['documents'] });
  queryClient.invalidateQueries({ queryKey: ['documents', docId] });
  queryClient.invalidateQueries({ queryKey: ['health_values'] });
  queryClient.invalidateQueries({ queryKey: ['timeline'] }); // prefix: invalidates all biomarkers
}

if (status === 'failed') {
  queryClient.invalidateQueries({ queryKey: ['documents'] });
  queryClient.invalidateQueries({ queryKey: ['documents', docId] });
  // NOTE: no health_values or timeline invalidation — no values were extracted
}
```

### After Document Delete

```typescript
// optimistic removal from list — no refetch wait
queryClient.setQueryData(['documents'], (old) => old?.filter(d => d.id !== docId));
// invalidate detail so stale data isn't served on re-open
queryClient.invalidateQueries({ queryKey: ['documents', docId] });
// invalidate health_values since deleted document's values are gone
queryClient.invalidateQueries({ queryKey: ['health_values'] });
```

### After Flag Health Value

```typescript
// HealthValueRow flagMutation onSuccess
queryClient.invalidateQueries({ queryKey: ['documents', documentId] });
queryClient.invalidateQueries({ queryKey: ['health_values'] });
// NOTE: timeline is NOT invalidated — flagging doesn't change the value itself
```

### After Keep Partial

```typescript
// keepPartialMutation onSuccess
// Optimistic update to list (avoids waiting for refetch)
queryClient.setQueryData(['documents'], (old) =>
  old?.map(d => d.id === docId ? { ...d, keep_partial: true } : d)
);
// Optimistic update to detail (hides recovery card immediately)
queryClient.setQueryData(['documents', docId], (old) =>
  old ? { ...old, keep_partial: true } : old
);
// Background refetch for consistency
queryClient.invalidateQueries({ queryKey: ['documents', docId] });
```

---

## Upload Page State Machine

```
idle → success (DocumentUploadZone emits upload complete)
     → failed (upload error)

success → done (SSE document.completed)
        → partial (SSE document.partial)
        → failed (SSE document.failed or stream-error)
```

Located in: `frontend/src/routes/(app)/documents/upload/page-state.ts`

`handleProcessingComplete` invalidates: `['documents']`, `['health_values']`
`handleProcessingFailure('partial')` invalidates: `['documents']`, `['health_values']`
`handleProcessingFailure('failed' | 'stream-error')` — no invalidation (nothing changed)

---

## Rule Checklist for New Stories

A story that changes authoritative document or health-value state must define:

- [ ] Which query keys are affected
- [ ] Whether the change uses `setQueryData` (optimistic) or `invalidateQueries` (background refetch)
- [ ] Whether `['timeline']` needs to be invalidated (use prefix invalidation — covers all biomarkers)
- [ ] Whether `['baseline']` needs to be invalidated (baseline is profile-derived, not document-derived — rarely needed)
- [ ] What the terminal/failure behavior looks like and how the UI reflects it
