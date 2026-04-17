import { PredictionDetailsRequest, PredictionDetailsResponse } from "@/types/contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';

const fetchPredictionDetails = async (params: PredictionDetailsRequest): Promise<PredictionDetailsResponse> => {
  const basePath = `${API_BASE_URL}/inference/prediction_details`;
  const q = new URLSearchParams();
  q.set('match_id', String(params.match_id));

  const fullUrl = `${basePath}?${q.toString()}`;
  const res = await fetch(fullUrl, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch prediction details: ${res.status} ${res.statusText} ${text}`);
  }

  const data = (await res.json()) as PredictionDetailsResponse;
  return data;
};

export default fetchPredictionDetails;
