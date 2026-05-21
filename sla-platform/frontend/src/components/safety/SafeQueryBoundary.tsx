import type { UseQueryResult } from "@tanstack/react-query";
import { Spin, Empty, Alert } from "antd";
import type { ReactNode } from "react";

interface Props<T> {
  query: UseQueryResult<T>;
  /** Render function called only when data is defined and not loading. */
  children: (data: T) => ReactNode;
  /** Empty check — defaults to "data is null/undefined OR array length is 0". */
  isEmpty?: (data: T) => boolean;
  /** Custom loading element. */
  loading?: ReactNode;
  /** Empty-state text. */
  emptyText?: string;
  /** Show a 60px-tall block instead of a full-page spinner. */
  compact?: boolean;
}

/**
 * Renders the standard loading / error / empty / data lifecycle in ONE
 * place. Encourages the call-site pattern:
 *
 *   const q = useQuery(...);
 *   useMemo(...)                  // ← hooks ALWAYS run, no guards needed
 *   useMemo(...)                  //
 *   return (
 *     <SafeQueryBoundary query={q}>
 *       {(data) => <RealUI data={data} />}
 *     </SafeQueryBoundary>
 *   );
 *
 * This prevents the hooks-after-conditional-return bug class that
 * crashed /sla-loss and /forensics. The boundary itself is a regular
 * component — no hooks inside, no rules-of-hooks concerns.
 */
export default function SafeQueryBoundary<T>({
  query,
  children,
  isEmpty,
  loading,
  emptyText = "Нет данных",
  compact = false,
}: Props<T>) {
  if (query.isLoading || query.isPending) {
    return (
      <div style={{ textAlign: "center", padding: compact ? 12 : 40 }}>
        {loading ?? <Spin size={compact ? "small" : "large"} />}
      </div>
    );
  }
  if (query.isError) {
    const message = (query.error as Error | undefined)?.message ?? "Ошибка загрузки";
    return (
      <Alert
        type="error"
        showIcon
        message="Не удалось загрузить данные"
        description={message}
        style={{ margin: compact ? 8 : 16 }}
      />
    );
  }
  const data = query.data;
  if (data === undefined || data === null) {
    return <Empty description={emptyText} style={{ marginTop: compact ? 12 : 40 }} />;
  }
  const empty =
    isEmpty
      ? isEmpty(data)
      : Array.isArray(data)
        ? (data as unknown[]).length === 0
        : false;
  if (empty) {
    return <Empty description={emptyText} style={{ marginTop: compact ? 12 : 40 }} />;
  }
  return <>{children(data)}</>;
}
