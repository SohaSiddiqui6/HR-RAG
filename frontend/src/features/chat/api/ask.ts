import type { AssistantReply, Source } from "@/features/chat/types";
import { apiClient } from "@/lib/api-client";

interface AskResponse {
  answer: string;
  sources: { source: string; page_no: number | null; headings: string | null }[];
}

function toSource(dto: AskResponse["sources"][number]): Source {
  return {
    document: dto.source,
    page: dto.page_no ?? undefined,
    heading: dto.headings ?? undefined,
  };
}

/** POST /api/ask — get a grounded answer to an HR question. */
export async function askQuestion(question: string): Promise<AssistantReply> {
  const res = await apiClient.post<AskResponse>("/ask", { question });
  return { content: res.answer, sources: res.sources.map(toSource) };
}
