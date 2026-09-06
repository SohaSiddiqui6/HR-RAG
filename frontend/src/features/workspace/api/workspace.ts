import { apiClient } from "@/lib/api-client";
import type { WorkspaceStats } from "@/types/workspace";

interface WorkspaceStatsDto {
  documents: string[];
  document_count: number;
  chunk_count: number;
}

function toStats(dto: WorkspaceStatsDto): WorkspaceStats {
  return {
    documents: dto.documents,
    documentCount: dto.document_count,
    chunkCount: dto.chunk_count,
  };
}

export async function getWorkspaceStats(): Promise<WorkspaceStats> {
  return toStats(await apiClient.get<WorkspaceStatsDto>("/workspace"));
}
