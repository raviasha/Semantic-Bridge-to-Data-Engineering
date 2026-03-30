const API_BASE = import.meta.env.VITE_API_URL || '/api';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  // Interviews
  startInterview: (title: string, description?: string) =>
    apiFetch('/interviews', {
      method: 'POST',
      body: JSON.stringify({ title, description }),
    }),

  listInterviews: () => apiFetch<any[]>('/interviews'),

  getInterview: (id: string) => apiFetch<any>(`/interviews/${id}`),

  sendMessage: (id: string, message: string) =>
    apiFetch<any>(`/interviews/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),

  getFlowDiagram: (id: string) => apiFetch<any>(`/interviews/${id}/flow-diagram`),

  // Schema
  listTables: () => apiFetch<any>('/schema/tables'),
  getTable: (name: string) => apiFetch<any>(`/schema/tables/${name}`),
  getColumnMetadata: (table: string, column: string) =>
    apiFetch<any>(`/schema/tables/${table}/columns/${column}/metadata`),
  updateColumnMetadata: (table: string, column: string, data: Record<string, any>) =>
    apiFetch<any>(`/schema/tables/${table}/columns/${column}/metadata`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // Applications
  listApplications: () => apiFetch<any>('/schema/applications'),
  getApplication: (appId: string) => apiFetch<any>(`/schema/applications/${appId}`),

  // Natural Language
  nlPreview: (instruction: string, context?: { table_name: string; column_name: string }) =>
    apiFetch<any>('/schema/nl-preview', {
      method: 'POST',
      body: JSON.stringify({ instruction, context: context || null }),
    }),

  nlApply: (previews: any[]) =>
    apiFetch<any>('/schema/nl-apply', {
      method: 'POST',
      body: JSON.stringify({ previews }),
    }),

  // Cross-app usage
  getColumnUsage: (table: string, column: string) =>
    apiFetch<any>(`/schema/tables/${table}/columns/${column}/usage`),

  // Column history
  getColumnHistory: (table: string, column: string) =>
    apiFetch<any>(`/schema/tables/${table}/columns/${column}/history`),

  revertChange: (table: string, column: string, historyId: number) =>
    apiFetch<any>(`/schema/tables/${table}/columns/${column}/revert`, {
      method: 'POST',
      body: JSON.stringify({ history_id: historyId }),
    }),

  deleteHistoryEntries: (table: string, column: string, historyIds: number[]) =>
    apiFetch<any>(`/schema/tables/${table}/columns/${column}/history/delete`, {
      method: 'POST',
      body: JSON.stringify({ history_ids: historyIds }),
    }),

  // Impact analysis
  getImpactAnalysis: (table: string, column: string, proposedChanges: Record<string, any>, currentAppId: string) =>
    apiFetch<any>('/schema/impact-analysis', {
      method: 'POST',
      body: JSON.stringify({
        table_name: table,
        column_name: column,
        proposed_changes: proposedChanges,
        current_app_id: currentAppId,
      }),
    }),

  // SQL Generation
  generateSQL: (id: string) =>
    apiFetch<any>(`/generate/${id}/sql`, { method: 'POST' }),
};
