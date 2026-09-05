import { Check } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const remarkPlugins = [remarkGfm];

/**
 * Renders assistant answers. Unordered list items get a mint check marker to
 * match the mockup; everything else is plain prose.
 */
const components: Components = {
  p: ({ children }) => <p className="leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="space-y-2">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal space-y-2 pl-5">{children}</ol>,
  li: ({ children }) => (
    <li className="flex gap-2">
      <Check className="text-primary mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </li>
  ),
  a: ({ children, href }) => (
    <a href={href} className="text-primary underline-offset-2 hover:underline">
      {children}
    </a>
  ),
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  code: ({ children }) => (
    <code className="bg-muted rounded px-1 py-0.5 text-[0.85em]">{children}</code>
  ),
};

export function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-3 text-sm">
      <ReactMarkdown remarkPlugins={remarkPlugins} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
