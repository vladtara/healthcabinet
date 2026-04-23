# Svelte 5 Runes — Implementation Cheat Sheet

Reference for the HealthCabinet team. Patterns confirmed through Epic 1–3 code review.
**Use this before writing implementation code — not after review.**

---

## Core Reactive State

```svelte
<script lang="ts">
  // ✅ Mutable reactive state
  let count = $state(0);
  let loading = $state(true);
  let values = $state<HealthValue[]>([]);

  // ✅ Derived value (simple expression — NOT a function call)
  const total = $derived(values.length);
  const hasValues = $derived(values.length > 0);

  // ✅ Derived value (requires multi-line logic) — use $derived.by()
  const grouped = $derived.by(() => {
    const result = new Map<string, HealthValue[]>();
    for (const v of values) {
      const existing = result.get(v.canonical_biomarker_name) ?? [];
      result.set(v.canonical_biomarker_name, [...existing, v]);
    }
    return result;
  });
</script>
```

### ❌ Common Mistake: `$derived` vs `$derived.by`

```svelte
// ❌ WRONG — holds a function object, NOT the computed value
// Changes to `values` are NOT tracked
const grouped = $derived(() => {
  return values.filter(v => v.status === 'optimal');
});

// ✅ CORRECT — reactivity tracks `values`
const optimal = $derived.by(() => {
  return values.filter(v => v.status === 'optimal');
});

// ✅ Also fine for simple expressions (no function wrapper needed)
const optimalCount = $derived(values.filter(v => v.status === 'optimal').length);
```

**Rule:** Use `$derived(expr)` for single expressions. Use `$derived.by(() => { ... })` for any logic that requires statements (loops, if/else, multi-line).

---

## Effects and Lifecycle

```svelte
<script lang="ts">
  // ✅ Effect with cleanup (cancellation guard pattern)
  $effect(() => {
    let cancelled = false;

    fetchData().then((data) => {
      if (cancelled) return;
      values = data;
      loading = false;
    });

    // Return cleanup function — runs before the next effect execution
    return () => {
      cancelled = true;
    };
  });
</script>
```

### ❌ Common Mistake: Missing Cancellation Guard

```svelte
// ❌ WRONG — state updates can fire after component unmounts or effect re-runs
$effect(() => {
  fetchData().then((data) => {
    values = data; // may update stale component
    loading = false;
  });
});

// ✅ CORRECT
$effect(() => {
  let cancelled = false;
  fetchData().then((data) => {
    if (cancelled) return;
    values = data;
    loading = false;
  });
  return () => { cancelled = true; };
});
```

---

## TanStack Query with Svelte 5 (established patterns)

### Querying Data

```svelte
<script lang="ts">
  import { createQuery, useQueryClient } from '@tanstack/svelte-query';
  import { getHealthValues, getDashboardBaseline } from '$lib/api/health-values';

  const queryClient = useQueryClient();

  const valuesQuery = createQuery({
    queryKey: ['health_values'],
    queryFn: getHealthValues
  });

  const baselineQuery = createQuery({
    queryKey: ['baseline'],
    queryFn: getDashboardBaseline
  });

  // ✅ Derive state from query results
  const values = $derived(valuesQuery.data ?? []);
  const loading = $derived(valuesQuery.isPending || baselineQuery.isPending);

  // ✅ Error: both must fail (one partial failure still shows data)
  const error = $derived(
    valuesQuery.isError && baselineQuery.isError
      ? 'Unable to load your health data. Please try again.'
      : null
  );
</script>
```

### Mutations

```svelte
<script lang="ts">
  import { createMutation, useQueryClient } from '@tanstack/svelte-query';

  const queryClient = useQueryClient();

  const flagMutation = createMutation(() => ({
    mutationFn: (id: string) => flagHealthValue(id),
    onSuccess: (_data, id) => {
      // Invalidate affected caches
      queryClient.invalidateQueries({ queryKey: ['health_values'] });
      queryClient.invalidateQueries({ queryKey: ['documents', documentId] });
    }
  }));

  // Usage: flagMutation.mutate(valueId)
</script>
```

### Retry / Manual Invalidation

```svelte
<script lang="ts">
  // ✅ Retry by invalidating queries (no manual re-fetch needed)
  function retry() {
    queryClient.invalidateQueries({ queryKey: ['health_values'] });
    queryClient.invalidateQueries({ queryKey: ['baseline'] });
    queryClient.invalidateQueries({ queryKey: ['timeline'] });
  }
</script>
```

### Wrapping Tests in QueryClientProvider

Tests that render a component using TanStack Query need a wrapper:

```svelte
<!-- DashboardPageTestWrapper.svelte -->
<script lang="ts">
  import { QueryClientProvider } from '@tanstack/svelte-query';
  import type { QueryClient } from '@tanstack/query-core';
  import Page from './+page.svelte';

  const { queryClient }: { queryClient: QueryClient } = $props();
</script>

<QueryClientProvider client={queryClient}>
  <Page />
</QueryClientProvider>
```

```typescript
// In test file
import { QueryClient } from '@tanstack/query-core';
import DashboardPageTestWrapper from './DashboardPageTestWrapper.svelte';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } }
  });
}

test('example', async () => {
  const queryClient = makeQueryClient();
  queryClient.setQueryData(['health_values'], mockValues); // pre-populate
  render(DashboardPageTestWrapper, { props: { queryClient } });
  // ...
});
```

---

## Props (Svelte 5)

```svelte
<script lang="ts">
  // ✅ Destructure directly from $props()
  const { label, status, variant = 'default' }: {
    label: string;
    status: 'optimal' | 'borderline';
    variant?: string;
  } = $props();
</script>
```

---

## ARIA / Accessibility (patterns from review)

| Use Case | Correct Role |
|----------|-------------|
| Status badge (color + text) | `role="img"` with `aria-label="{label} status"` |
| Loading spinner / skeleton | `role="status"` with `aria-label="Loading..."` |
| Live region for announcements | `aria-live="polite"` on a container |
| Inline error | `role="alert"` |

```svelte
<!-- ✅ Status badge — NOT role="status" (that's for live regions) -->
<span role="img" aria-label="{label} status" class="...">
  {label}
</span>

<!-- ✅ Skeleton loader -->
<div role="status" aria-label="Loading health values">
  <div class="animate-pulse ..." />
</div>
```

---

## Query Keys Reference (project-wide)

| Key | Data |
|-----|------|
| `['documents']` | All user documents (list) |
| `['documents', docId]` | Individual document detail |
| `['health_values']` | All user health values |
| `['baseline']` | Dashboard baseline recommendations |
| `['timeline', canonicalBiomarkerName]` | Per-biomarker historical values |
| `['timeline']` (prefix) | All timeline queries (for bulk invalidation) |

---

## Mock Pattern for Tests

When a component imports functions, ALL exports used by that component must be in the mock:

```typescript
// ❌ WRONG — if component also calls getHealthValues, tests will fail
vi.mock('$lib/api/health-values', () => ({
  getDashboardBaseline: vi.fn(),
  flagHealthValue: vi.fn(),
}));

// ✅ CORRECT — include every function the component imports
vi.mock('$lib/api/health-values', () => ({
  getDashboardBaseline: vi.fn(),
  getHealthValues: vi.fn(),
  getHealthValueTimeline: vi.fn(),
  flagHealthValue: vi.fn(),
}));
```
