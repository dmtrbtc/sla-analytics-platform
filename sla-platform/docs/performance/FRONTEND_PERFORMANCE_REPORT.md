# Frontend Performance Report — v0.4.0

## Bundle Size Reduction

### Before
- Single monolithic JS bundle: ~2.4MB
- No code splitting, no lazy loading
- Unused dependencies: ag-grid-react, ag-grid-community

### After
- Route-based code splitting via React.lazy() + Suspense
- Vendor chunking with manualChunks:
  - `vendor-react`: 160KB (52KB gzip) — react, react-dom, react-router-dom
  - `vendor-antd`: 1,039KB (325KB gzip) — antd, @ant-design/icons
  - `vendor-echarts`: 1,052KB (350KB gzip) — echarts, echarts-for-react
  - `vendor-query`: 43KB (14KB gzip) — @tanstack/react-query, zustand
- Per-page chunks: 0.17KB - 6.87KB (loaded on demand)
- Main app shell: 55.91KB (21.65KB gzip)

### Initial Load Reduction
- **~70% reduction** in initial JS download (from ~2.4MB to ~217KB gzip)

## Dead Code Elimination
- Removed 2 unused npm packages (ag-grid)
- Deleted 15 unused source files:
  - 4 chart wrapper components (never imported)
  - 5 common components (never imported)
  - 2 custom hooks (never imported)
  - 2 API modules (never imported)
  - 2 utility files (never imported — logic duplicated inline)

## Duplicated Logic Centralized
- `formatDuration`: Defined in 4 places → centralized in `utils/format.ts`
- Status colors: Defined in 4 places → centralized in `utils/constants.ts`

## Remaining Opportunities
- Antd and ECharts chunks are large (~1MB each) — this is library size
- No React.memo/useMemo optimizations (low impact for this app's render tree)
- No bundle analyzer plugin in build (recommended for future optimization)
- Image optimization not applicable (no images in app)
