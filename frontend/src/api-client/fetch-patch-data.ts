type PatchDataAPIResponse = {
  patches: string[]
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';

export default async function fetchPatchData(): Promise<string[]> {
  const endpointUrl = `${API_BASE_URL}/patches/ids`;
  const res = await fetch(endpointUrl, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to fetch patch data: ${res.status} ${res.statusText} ${text}`);
  }

  const data: PatchDataAPIResponse = await res.json();
  return data.patches ?? [];
}
