import { toMessage } from "@/features/conversations/api/conversations";
import type { Message } from "@/types/conversation";
import { apiClient } from "@/lib/api-client";

interface SendMessageDto {
  user_message: Parameters<typeof toMessage>[0];
  assistant_message: Parameters<typeof toMessage>[0];
}

/** POST /api/conversations/{id}/messages — append a question and get the answer. */
export async function sendMessage(
  conversationId: string,
  question: string,
): Promise<{ userMessage: Message; assistantMessage: Message }> {
  const dto = await apiClient.post<SendMessageDto>(
    `/conversations/${conversationId}/messages`,
    { question },
  );
  return {
    userMessage: toMessage(dto.user_message),
    assistantMessage: toMessage(dto.assistant_message),
  };
}
