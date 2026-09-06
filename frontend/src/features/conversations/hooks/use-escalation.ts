import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  submitEscalation,
  type EscalationInput,
} from "@/features/conversations/api/escalation";
import { conversationKeys } from "@/features/conversations/api/keys";

/** Submit a human-handoff request for a message; refreshes the conversation on success. */
export function useEscalation(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: EscalationInput) => submitEscalation(conversationId, input),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: conversationKeys.detail(conversationId),
      }),
  });
}
