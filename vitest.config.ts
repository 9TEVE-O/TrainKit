import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["runtime/tests/**/*.test.ts"],
    environment: "node",
  },
});
