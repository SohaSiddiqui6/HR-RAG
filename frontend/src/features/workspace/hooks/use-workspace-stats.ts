import { useQuery } from "@tanstack/react-query";

import { workspaceKeys } from "@/features/workspace/api/keys";
import { getWorkspaceStats } from "@/features/workspace/api/workspace";

/** Indexed-corpus coverage for the workspace pane. Rarely changes — cache it. */
export function useWorkspaceStats() {
  return useQuery({
    queryKey: workspaceKeys.stats,
    queryFn: getWorkspaceStats,
    staleTime: 5 * 60 * 1000,
  });
}
