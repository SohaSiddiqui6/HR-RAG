/** Runtime configuration, read once from Vite env vars. */
export const config = {
  /** Base URL for the backend API. Defaults to the Vite dev proxy path. */
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "/api",
} as const;
