import type { Conversation } from "@/types/conversation";

/** Pre-fill the HR request from the conversation — no LLM, just the question in context. */
export function buildDraft(
  conversation: Conversation | undefined,
  messageId: string,
): { subject: string; body: string } {
  if (!conversation) return { subject: "", body: "" };

  const index = conversation.messages.findIndex((m) => m.id === messageId);
  const question = index > 0 ? (conversation.messages[index - 1]?.content ?? "") : "";

  return {
    subject: conversation.title,
    body: question
      ? `I asked: "${question}"\n\nThe assistant couldn't find this in the current HR policies.`
      : "The assistant couldn't answer this from the current HR policies.",
  };
}
