export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  /** Markdown for assistant messages, plain text for user messages. */
  content: string;
  createdAt: string;
}
