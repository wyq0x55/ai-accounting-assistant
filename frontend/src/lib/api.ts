// Typed client for the assistant REST API.

export interface Transaction {
  id: number;
  raw_text: string;
  source_channel: string;
  amount: number | null;
  merchant: string | null;
  direction: string;
  pay_method: string | null;
  category: string | null;
  book: string;
  confidence: number;
  classify_source: string;
  state: string;
  date: string | null;
  synced: boolean;
  actual_txn_id: string | null;
  sync_error: string | null;
  needs_manual?: boolean;
}

export interface Category {
  id: number;
  name: string;
  is_default: boolean;
}

export interface MerchantMapping {
  id: number;
  merchant_key: string;
  merchant_name: string;
  category: string;
  hit_count: number;
}

export interface Stats {
  month: string | null;
  total_expense: number;
  total_income: number;
  transaction_count: number;
  category_breakdown: { category: string; amount: number; percent: number }[];
  top_merchants: { merchant: string; amount: number }[];
  trend: { month: string; expense: number }[];
}

export interface MonthlyReport {
  summary: string;
  source: string;
  stats: Stats;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<Record<string, unknown>>('/health'),

  ingestText: (text: string, book = 'personal') =>
    req<Transaction>('/ingest/text', {
      method: 'POST',
      body: JSON.stringify({ text, book }),
    }),

  ingestManual: (payload: {
    amount: number;
    category: string;
    merchant?: string;
    direction?: string;
    note?: string;
    auto_confirm?: boolean;
  }) =>
    req<Transaction>('/ingest/manual', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  ingestCsv: (csv: string) =>
    req<{ imported: number }>('/ingest/csv', {
      method: 'POST',
      body: JSON.stringify({ csv }),
    }),

  listTransactions: (bucket?: string) =>
    req<{ count: number; items: Transaction[] }>(
      `/transactions${bucket ? `?bucket=${bucket}` : ''}`,
    ),

  updateTransaction: (id: number, fields: Partial<Transaction>) =>
    req<Transaction>(`/transactions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(fields),
    }),

  confirmTransaction: (id: number) =>
    req<Transaction>(`/transactions/${id}/confirm`, { method: 'POST' }),

  deleteTransaction: (id: number) =>
    req<{ status: string }>(`/transactions/${id}`, { method: 'DELETE' }),

  retrySync: () => req<{ attempted: number; synced: number }>('/sync/retry', { method: 'POST' }),

  listCategories: () => req<{ items: Category[] }>('/categories'),
  createCategory: (name: string) =>
    req<Category>('/categories', { method: 'POST', body: JSON.stringify({ name }) }),
  deleteCategory: (id: number) =>
    req<{ status: string }>(`/categories/${id}`, { method: 'DELETE' }),

  listMappings: () => req<{ items: MerchantMapping[] }>('/mappings'),
  deleteMapping: (id: number) =>
    req<{ status: string }>(`/mappings/${id}`, { method: 'DELETE' }),

  stats: (month?: string) =>
    req<Stats>(`/stats${month ? `?month=${month}` : ''}`),
  monthlyReport: (month?: string) =>
    req<MonthlyReport>(`/report/monthly${month ? `?month=${month}` : ''}`),
};
