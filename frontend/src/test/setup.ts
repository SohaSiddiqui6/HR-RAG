import "@testing-library/jest-dom/vitest";

import { afterAll, afterEach, beforeAll } from "vitest";

import { resetStore, server } from "@/test/msw";

// jsdom doesn't implement the <dialog> modal methods; map them to the `open`
// attribute so ConfirmDialog works under test.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  };
}

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

afterEach(() => {
  server.resetHandlers();
  resetStore();
  localStorage.clear();
});

afterAll(() => server.close());
