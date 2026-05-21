import client from "./client";

export type DomainKey = "servicedesk" | "assetmanagement" | "workplace" | "multimedia";

export const operationsIntelligenceApi = {
  domain: (d: DomainKey) =>
    client.get(`/operations/intelligence/${d}`).then(r => r.data),
  overview: () => client.get("/operations/intelligence").then(r => r.data),
};
