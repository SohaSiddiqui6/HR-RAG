import { apiClient } from "@/lib/api-client";

/** POST /api/feedback — a thumbs rating on an answer, keyed by its Langfuse trace. */
export function submitFeedback(traceId: string, helpful: boolean): Promise<void> {
  return apiClient.post<void>("/feedback", { trace_id: traceId, helpful });
}
