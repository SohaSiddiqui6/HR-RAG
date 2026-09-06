import { useMutation } from "@tanstack/react-query";

import { askQuestion } from "@/features/chat/api/ask";
import type { Message } from "@/features/chat/types";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { ApiError } from "@/types/api";

const STORAGE_KEY = "hr-rag:conversation";

function newMessage(
  role: Message["role"],
  content: string,
  extra?: Partial<Message>,
): Message {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    createdAt: new Date().toISOString(),
    ...extra,
  };
}

function errorText(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Something went wrong. Please try again.";
}

/**
 * The current conversation and the action to add to it. State is local
 * (localStorage) for now — Step 4 moves it to the server via TanStack Query,
 * without changing this hook's surface.
 */
export function useConversation() {
  const [messages, setMessages] = useLocalStorage<Message[]>(STORAGE_KEY, []);
  const append = (message: Message) => setMessages((prev) => [...prev, message]);

  const { mutate, isPending } = useMutation({
    mutationFn: askQuestion,
    onSuccess: (reply) =>
      append(newMessage("assistant", reply.content, { sources: reply.sources })),
    onError: (error) =>
      append(newMessage("assistant", errorText(error), { failed: true })),
  });

  function send(text: string) {
    append(newMessage("user", text));
    mutate(text);
  }

  function reset() {
    setMessages([]);
  }

  return { messages, send, reset, isPending };
}
