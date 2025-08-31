import { HeroImageData, HeroImageResponse } from '@/types/contracts/index'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default async function fetchHeroData() : Promise<HeroImageData[]> {
    const endpointUrl = new URL('/heroes/get_image_urls', API_BASE_URL).toString()
    const res = await fetch(endpointUrl, { next: { revalidate: 3600 * 24 }})
    if (!res.ok) {
        throw new Error('Failed to fetch hero data')
    }
    const data: HeroImageResponse = await res.json()
    return data.heroes
}
