import client from './client';

type ScopeParams = Record<string, string | undefined>;

/**
 * Queue Intelligence API client. Every endpoint accepts an optional
 * `scope` object built by `useTimeScope().toParams()` so the global
 * TimeScopeToolbar drives the data window. The legacy `days=30` default
 * is preserved for callers that don't pass scope.
 */
export const queueIntelligenceApi = {
  getOverview: (days = 30, scope?: ScopeParams) =>
    client.get('/queue-intelligence/overview',
      { params: { days, ...(scope || {}) } }).then(r => r.data),

  getQueueFlowMap: (days = 30, scope?: ScopeParams) =>
    client.get('/queue-intelligence/queue-flow-map',
      { params: { days, ...(scope || {}) } }).then(r => r.data),

  getQueueForensics: (days = 30, scope?: ScopeParams) =>
    client.get('/queue-intelligence/queue-forensics',
      { params: { days, ...(scope || {}) } }).then(r => r.data),

  getTransferAnalytics: (days = 30, scope?: ScopeParams) =>
    client.get('/queue-intelligence/transfer-analytics',
      { params: { days, ...(scope || {}) } }).then(r => r.data),

  getServiceDeskIntelligence: (days = 30, scope?: ScopeParams) =>
    client.get('/queue-intelligence/servicedesk-intelligence',
      { params: { days, ...(scope || {}) } }).then(r => r.data),

  getTicketForensic: (ticketId: number) =>
    client.get(`/queue-intelligence/ticket-forensic/${ticketId}`).then(r => r.data),

  getTicketRootCause: (ticketId: number) =>
    client.get(`/queue-intelligence/ticket-root-cause/${ticketId}`).then(r => r.data),
};
