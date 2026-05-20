import client from './client';

export const queueIntelligenceApi = {
  getOverview: (days = 30) =>
    client.get('/queue-intelligence/overview', { params: { days } }).then(r => r.data),

  getQueueFlowMap: (days = 30) =>
    client.get('/queue-intelligence/queue-flow-map', { params: { days } }).then(r => r.data),

  getQueueForensics: (days = 30) =>
    client.get('/queue-intelligence/queue-forensics', { params: { days } }).then(r => r.data),

  getTransferAnalytics: (days = 30) =>
    client.get('/queue-intelligence/transfer-analytics', { params: { days } }).then(r => r.data),

  getServiceDeskIntelligence: (days = 30) =>
    client.get('/queue-intelligence/servicedesk-intelligence', { params: { days } }).then(r => r.data),

  getTicketForensic: (ticketId: number) =>
    client.get(`/queue-intelligence/ticket-forensic/${ticketId}`).then(r => r.data),

  getTicketRootCause: (ticketId: number) =>
    client.get(`/queue-intelligence/ticket-root-cause/${ticketId}`).then(r => r.data),
};
