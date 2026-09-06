export type MessageRole = "user" | "assistant";

/** What the pipeline decided to do with the question behind an assistant message. */
export type MessageOutcome = "answered" | "needs_human" | "out_of_scope";

/** A policy document cited by an assistant answer. */
export interface Source {
  document: string;
  page?: number;
  heading?: string;
}

/** A human handoff raised for a `needs_human` message. */
export interface Escalation {
  channel: string;
  reference?: string;
  url?: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  /** Markdown for assistant messages, plain text for user messages. */
  content: string;
  createdAt: string;
  sources?: Source[];
  outcome?: MessageOutcome;
  escalation?: Escalation;
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
