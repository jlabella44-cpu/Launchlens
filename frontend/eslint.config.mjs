import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Generated from the backend OpenAPI spec by `npm run generate-api`.
    "src/lib/generated/**",
  ]),
  {
    rules: {
      // Follow-up: type the ~47 `any`s in api-client/analytics payloads (Phase 8 typing pass).
      "@typescript-eslint/no-explicit-any": "warn",
      // Follow-up: migrate the ~22 raw <img> tags to next/image once R2 media hosts are in remotePatterns.
      "@next/next/no-img-element": "warn",
      // Follow-up: rework the mount-time setState hooks (theme, offline, notifications) to useSyncExternalStore.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
