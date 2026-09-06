import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  deleteConversation,
  listConversations,
} from "@/features/conversations/api/conversations";
import { conversationKeys } from "@/features/conversations/api/keys";

/**
 * The conversation list for the sidebar, plus the action to delete one. Deleting
 * the conversation that is currently open sends the user back to a fresh chat.
 */
export function useConversations() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { conversationId } = useParams();

  const query = useQuery({
    queryKey: conversationKeys.all,
    queryFn: listConversations,
  });

  const remove = useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_, id) => {
      void queryClient.invalidateQueries({ queryKey: conversationKeys.all });
      if (id === conversationId) navigate("/");
    },
  });

  return {
    conversations: query.data ?? [],
    isLoading: query.isLoading,
    remove: remove.mutate,
  };
}
