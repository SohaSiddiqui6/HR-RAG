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
  sources?: Source[];
  /** Client-side only — the request failed; `content` holds the error text. */
  failed?: boolean;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updatedAt: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
}
