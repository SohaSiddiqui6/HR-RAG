import { apiClient } from "@/lib/api-client";
import type { Escalation } from "@/types/conversation";

interface EscalationDto {
  channel: string;
  reference: string | null;
  url: string | null;
}

export interface EscalationInput {
  messageId: string;
  subject: string;
  body: string;
}

/** POST /api/conversations/{id}/escalation — hand a `needs_human` message to a person. */
export async function submitEscalation(
  conversationId: string,
  input: EscalationInput,
): Promise<Escalation> {
  const dto = await apiClient.post<EscalationDto>(
    `/conversations/${conversationId}/escalation`,
    { message_id: input.messageId, subject: input.subject, body: input.body },
  );
  return {
    channel: dto.channel,
    reference: dto.reference ?? undefined,
    url: dto.url ?? undefined,
  };
}
