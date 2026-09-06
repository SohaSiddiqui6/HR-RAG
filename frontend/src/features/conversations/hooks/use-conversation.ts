import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  createConversation,
  getConversation,
} from "@/features/conversations/api/conversations";
import { conversationKeys } from "@/features/conversations/api/keys";
import { sendMessage } from "@/features/conversations/api/messages";
import type { Message } from "@/types/conversation";
import { ApiError } from "@/types/api";

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
 * One conversation and the action to add to it. Loads from the server; a send
 * either appends to the current conversation or (when there is none yet) creates
 * one and navigates to it.
 */
export function useConversation(conversationId?: string) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [localError, setLocalError] = useState<Message | null>(null);

  const query = useQuery({
    queryKey: conversationKeys.detail(conversationId ?? ""),
    queryFn: () => getConversation(conversationId!),
    enabled: Boolean(conversationId),
  });

  const create = useMutation({
    mutationFn: createConversation,
    onSuccess: (conversation) => {
      queryClient.setQueryData(conversationKeys.detail(conversation.id), conversation);
      void queryClient.invalidateQueries({ queryKey: conversationKeys.all });
      navigate(`/c/${conversation.id}`);
    },
  });

  const append = useMutation({
    mutationFn: (question: string) => sendMessage(conversationId!, question),
    // Await the refetch so the persisted pair is on screen before the pending
    // overlay clears (onSettled) — avoids a flash of a duplicate user bubble.
    // Also refresh the sidebar list: the first message names the conversation
    // and bumps its position.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: conversationKeys.detail(conversationId!),
        }),
        queryClient.invalidateQueries({ queryKey: conversationKeys.all }),
      ]),
  });

  function send(text: string) {
    setPendingText(text);
    setLocalError(null);
    const mutation = conversationId ? append : create;
    mutation.mutate(text, {
      onError: (error) => setLocalError(errorMessage(error)),
      onSettled: () => setPendingText(null),
    });
  }

  const messages = query.data?.messages ?? [];
  const isPending = create.isPending || append.isPending;

  return {
    messages: localError ? [...messages, localError] : messages,
    pendingText,
    isPending,
    isLoading: query.isLoading,
    send,
  };
}
