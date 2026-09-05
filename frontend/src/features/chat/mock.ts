import type { Message } from "@/features/chat/types";

/** Stand-in assistant answer used until the real API is wired in Step 3. */
export const CANNED_REPLY = `Eligible employees can take up to **16 weeks** of paid parental leave following the birth, adoption, or placement of a child. Leave can be taken continuously or split into two periods within the first 12 months.

- Available to all full-time employees after 90 days of service
- Primary caregivers receive 16 weeks; secondary caregivers receive 8 weeks
- Submit your request to your manager and People Ops at least 30 days ahead when possible`;

/** Fixture for tests and manual review. */
export const MOCK_MESSAGES: Message[] = [
  {
    id: "m1",
    role: "user",
    content: "What is the parental leave policy?",
    createdAt: "2026-01-01T10:42:00.000Z",
  },
  {
    id: "m2",
    role: "assistant",
    content: CANNED_REPLY,
    createdAt: "2026-01-01T10:42:03.000Z",
  },
];
