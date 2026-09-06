import type {
  Conversation,
  ConversationSummary,
  Escalation,
  Message,
  MessageOutcome,
  Source,
} from "@/types/conversation";
import { apiClient } from "@/lib/api-client";

// --- backend DTOs ----------------------------------------------------------

interface SourceDto {
  source: string;
  page_no: number | null;
  headings: string | null;
}

interface EscalationDto {
  channel: string;
  reference: string | null;
  url: string | null;
}

interface MessageDto {
  id: string;
  role: Message["role"];
  content: string;
  sources: SourceDto[];
  outcome: MessageOutcome;
  escalation: EscalationDto | null;
  created_at: string;
}

interface ConversationDto {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: MessageDto[];
}

interface SummaryDto {
  id: string;
  title: string;
  updated_at: string;
}

// --- mapping -------------------------------------------------------------

export function toSource(dto: SourceDto): Source {
  return {
    document: dto.source,
    page: dto.page_no ?? undefined,
    heading: dto.headings ?? undefined,
  };
}

function toEscalation(dto: EscalationDto): Escalation {
  return {
    channel: dto.channel,
    reference: dto.reference ?? undefined,
    url: dto.url ?? undefined,
  };
}

export function toMessage(dto: MessageDto): Message {
  return {
    id: dto.id,
    role: dto.role,
    content: dto.content,
    createdAt: dto.created_at,
    sources: dto.sources.map(toSource),
    outcome: dto.outcome,
    escalation: dto.escalation ? toEscalation(dto.escalation) : undefined,
  };
}

function toConversation(dto: ConversationDto): Conversation {
  return {
    id: dto.id,
    title: dto.title,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    messages: dto.messages.map(toMessage),
  };
}

function toSummary(dto: SummaryDto): ConversationSummary {
  return { id: dto.id, title: dto.title, updatedAt: dto.updated_at };
}

// --- endpoints ---------------------------------------------------------

export async function listConversations(): Promise<ConversationSummary[]> {
  const dtos = await apiClient.get<SummaryDto[]>("/conversations");
  return dtos.map(toSummary);
}

export async function createConversation(): Promise<Conversation> {
  return toConversation(await apiClient.post<ConversationDto>("/conversations"));
}

export async function getConversation(id: string): Promise<Conversation> {
  return toConversation(await apiClient.get<ConversationDto>(`/conversations/${id}`));
}

export async function deleteConversation(id: string): Promise<void> {
  await apiClient.delete(`/conversations/${id}`);
}
