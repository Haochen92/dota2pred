import { ModelHistoryRequest, ModelHistoryResponse } from "@/types/contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';

const fetchModelHistory = async (historyParams: ModelHistoryRequest): Promise<ModelHistoryResponse> => {
  const basePath = `${API_BASE_URL}/inference/model_history`;
  const q = new URLSearchParams();

  if (historyParams?.history_range) q.set('history_range', String(historyParams.history_range));
  else if (historyParams?.history_range === 0) q.set('history_range', '0'); // Handle 'all time' case

  if (historyParams?.aggregate_by) q.set('aggregate_by', String(historyParams.aggregate_by));

  const fullUrl = `${basePath}?${q.toString()}`;
  const res = await fetch(fullUrl, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch model history: ${res.status} ${res.statusText} ${text}`);
  }

  const data = (await res.json()) as ModelHistoryResponse;
  return data;
};

export default fetchModelHistory;
