export type MessageRole = "user" | "assistant";

/** A policy document cited by an assistant answer. */
export interface Source {
  document: string;
  page?: number;
  heading?: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  /** Markdown for assistant messages, plain text for user messages. */
  content: string;
  createdAt: string;
  /** Assistant only — documents the answer is grounded in. */
  sources?: Source[];
  /** Assistant only — the request failed; `content` holds the error text. */
  failed?: boolean;
}

/** Domain shape of a successful `POST /api/ask` response. */
export interface AssistantReply {
  content: string;
  sources: Source[];
}
