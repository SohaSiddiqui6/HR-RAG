import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/app/layout/app-layout";
import { ChatView } from "@/features/conversations/components/chat/chat-view";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <ChatView /> },
      // A conversation deep-link. Renders the same view for now; Step 4 loads
      // the conversation by id.
      { path: "/c/:conversationId", element: <ChatView /> },
    ],
  },
]);
