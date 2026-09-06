import { FileText } from "lucide-react";

import { documentName } from "@/lib/format";
import type { Source } from "@/types/conversation";

interface DocSources {
  document: string;
  pages: number[];
  heading?: string;
}

/** Collapse repeated chunks from the same document into one row with its pages. */
function groupByDocument(sources: Source[]): DocSources[] {
  const byDoc = new Map<string, DocSources>();
  for (const source of sources) {
    const entry = byDoc.get(source.document) ?? {
      document: source.document,
      pages: [],
      heading: source.heading || undefined,
    };
    if (source.page != null && !entry.pages.includes(source.page)) {
      entry.pages.push(source.page);
    }
    byDoc.set(source.document, entry);
  }
  for (const entry of byDoc.values()) entry.pages.sort((a, b) => a - b);
  return [...byDoc.values()];
}

/** Disclosure of the policy documents an assistant answer was grounded in. */
export function MessageSources({ sources }: { sources: Source[] }) {
  const docs = groupByDocument(sources);
  if (docs.length === 0) return null;

  return (
    <details className="border-border mt-3 border-t pt-3 text-sm">
      <summary className="text-muted-foreground hover:text-foreground cursor-pointer">
        Sources · {docs.length}
      </summary>
      <ul className="mt-2 space-y-1.5">
        {docs.map((doc) => (
          <li key={doc.document} className="text-muted-foreground flex items-start gap-2">
            <FileText className="mt-0.5 size-3.5 shrink-0" />
            <span className="min-w-0">
              <span className="text-foreground">{documentName(doc.document)}</span>
              {doc.pages.length > 0 && <span> · p. {doc.pages.join(", ")}</span>}
              {doc.heading && (
                <span className="block truncate text-xs">{doc.heading}</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}
