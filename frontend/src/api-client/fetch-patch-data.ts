type PatchDataAPIResponse = {
  patches: string[]
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api'

export default async function fetchPatchData(): Promise<string[]> {
  const endpointUrl = `${API_BASE_URL}/patches/ids`
  const res = await fetch(endpointUrl, { next: { revalidate: 3600 * 24 } })
  if (!res.ok) {
    throw new Error('Failed to fetch patch data')
  }
  const data: PatchDataAPIResponse = await res.json()
  return data.patches ?? []
}
