import client from "./client";

export type DomainKey = "servicedesk" | "assetmanagement" | "workplace" | "multimedia";

type ScopeParams = Record<string, string | undefined>;

export const operationsIntelligenceApi = {
  domain: (d: DomainKey, scope?: ScopeParams) =>
    client.get(`/operations/intelligence/${d}`, { params: { ...(scope || {}) } })
      .then(r => r.data),
  overview: (scope?: ScopeParams) =>
    client.get("/operations/intelligence", { params: { ...(scope || {}) } })
      .then(r => r.data),
};
