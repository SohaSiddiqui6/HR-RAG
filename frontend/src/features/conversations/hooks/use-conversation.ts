import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  createConversation,
  getConversation,
} from "@/features/conversations/api/conversations";
import { conversationKeys } from "@/features/conversations/api/keys";
import { streamMessage } from "@/features/conversations/api/messages";
import { ApiError } from "@/types/api";
import type { Message } from "@/types/conversation";

function errorMessage(error: unknown): Message {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content:
      error instanceof ApiError
        ? error.message
        : "Something went wrong. Please try again.",
    createdAt: new Date().toISOString(),
    failed: true,
  };
}

/**
 * One conversation and the action to add to it. A send creates the conversation
 * first if there is none yet, then streams the answer: `pendingText` holds the
 * user's bubble and `streamingText` the assistant's, both cleared once the
 * persisted pair has been refetched.
 */
export function useConversation(conversationId?: string) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const [localError, setLocalError] = useState<Message | null>(null);

  const query = useQuery({
    queryKey: conversationKeys.detail(conversationId ?? ""),
    queryFn: () => getConversation(conversationId!),
    enabled: Boolean(conversationId),
  });

  async function runSend(text: string) {
    let id = conversationId;
    if (!id) {
      const conversation = await createConversation();
      queryClient.setQueryData(conversationKeys.detail(conversation.id), conversation);
      void queryClient.invalidateQueries({ queryKey: conversationKeys.all });
      navigate(`/c/${conversation.id}`);
      id = conversation.id;
    }

    await streamMessage(id, text, (token) =>
      setStreamingText((prev) => (prev ?? "") + token),
    );

    // Refetch the persisted pair before clearing the overlays (onSettled).
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: conversationKeys.detail(id) }),
      queryClient.invalidateQueries({ queryKey: conversationKeys.all }),
    ]);
  }

  const mutation = useMutation({ mutationFn: runSend });

  function send(text: string) {
    if (mutation.isPending) return; // one question at a time
    setPendingText(text);
    setStreamingText(null);
    setLocalError(null);
    mutation.mutate(text, {
      onError: (error) => setLocalError(errorMessage(error)),
      onSettled: () => {
        setPendingText(null);
        setStreamingText(null);
      },
    });
  }

  const messages = query.data?.messages ?? [];

  return {
    messages: localError ? [...messages, localError] : messages,
    pendingText,
    streamingText,
    isPending: mutation.isPending,
    isLoading: query.isLoading,
    loadFailed: query.isError,
    send,
  };
}
