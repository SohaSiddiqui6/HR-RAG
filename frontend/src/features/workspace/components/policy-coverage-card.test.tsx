import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { PolicyCoverageCard } from "@/features/workspace/components/policy-coverage-card";
import { server } from "@/test/msw";
import { renderWithProviders } from "@/test/render";

describe("PolicyCoverageCard", () => {
  it("shows the indexed document count and names", async () => {
    renderWithProviders(<PolicyCoverageCard />);

    expect(
      await screen.findByText("2 policies · 137 passages indexed"),
    ).toBeInTheDocument();
    expect(screen.getByText("pto-and-leave-policy")).toBeInTheDocument();
    expect(screen.getByText("code-of-conduct")).toBeInTheDocument();
  });

  it("falls back quietly when the index is unavailable", async () => {
    server.use(
      http.get("*/api/workspace", () => HttpResponse.json(null, { status: 500 })),
    );
    renderWithProviders(<PolicyCoverageCard />);

    expect(await screen.findByText("Source index unavailable.")).toBeInTheDocument();
  });
});
