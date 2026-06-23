import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Pure logic tests (no DOM). Component tests can opt into jsdom later.
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
