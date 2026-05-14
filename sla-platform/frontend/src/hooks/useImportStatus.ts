import { useQuery } from "@tanstack/react-query";
import { importsApi } from "../api/imports";

export function useImportStatus(sessionId: string | null) {
  return useQuery({
    queryKey: ["import", sessionId],
    queryFn: () => importsApi.get(sessionId!).then((r) => r.data),
    enabled: !!sessionId,
    refetchInterval: (query) =>
      query.state.data?.status === "completed" ||
      query.state.data?.status === "failed"
        ? false
        : 3000,
  });
}
