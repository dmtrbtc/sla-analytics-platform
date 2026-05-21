/**
 * ESLint configuration — focused narrowly on the runtime invariants
 * the project actually needs to catch:
 *
 *   1. react-hooks/rules-of-hooks (ERROR)
 *      Catches the exact bug that took /sla-loss down:
 *      hooks called after a conditional return, hooks inside loops,
 *      hooks inside try/catch. This MUST be an error.
 *
 *   2. react-hooks/exhaustive-deps (WARN)
 *      Surfaces stale-closure bugs in useEffect/useMemo without
 *      blocking the build on every legitimate edge case.
 *
 *   3. no-unused-vars (WARN)
 *      Light hygiene. Off for arguments prefixed with `_`.
 *
 * We deliberately do NOT pull in airbnb/standard configs — they add
 * 200+ stylistic rules that would block on day 1 without improving
 * runtime stability.
 */
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
    ecmaFeatures: { jsx: true },
  },
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  plugins: ["@typescript-eslint", "react", "react-hooks"],
  settings: { react: { version: "detect" } },
  rules: {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
    "@typescript-eslint/no-unused-vars": [
      "warn",
      { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
    ],
    "no-unused-vars": "off",
    "react/jsx-key": "error",
    "react/no-direct-mutation-state": "error",
    "react/no-deprecated": "warn",
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
  },
  ignorePatterns: [
    "dist/**",
    "node_modules/**",
    "*.cjs",
    "*.config.ts",
    "*.config.js",
  ],
};
