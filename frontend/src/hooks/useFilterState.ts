'use client'

import { useMemo } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import type { MatchFilterOptions, MatchStatus } from '@/types/domain'

export function useFilterState() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const page = Number(searchParams.get('page') || '1')
  const pageSize = Number(searchParams.get('page_size') || '15')

  const filters: MatchFilterOptions = useMemo(
    () => ({
      teamName: searchParams.get('team_name') ?? undefined,
      patchNumber: searchParams.get('patch_number') ?? undefined,
      heroIds: searchParams.getAll('hero_ids[]').map(id => Number(id)) ?? undefined,
      leagueId: searchParams.get('league_id') ? Number(searchParams.get('league_id')) : undefined,
      matchStatus: searchParams.get('match_status') as MatchStatus ?? undefined,
    }),
    [searchParams]
  )

  const handleStateChange = (newValues: { page?: number; filters?: MatchFilterOptions }) => {
    const newSearchParams = new URLSearchParams(searchParams)
    newSearchParams.set('page', String(newValues.page ?? page))
    newSearchParams.set('page_size', String(pageSize))

    // Reset to first page when filters change
    if (newValues.filters !== undefined) newSearchParams.set('page', '1')

    const newFilters = newValues.filters ?? filters
    newFilters.teamName
      ? newSearchParams.set('team_name', newFilters.teamName)
      : newSearchParams.delete('team_name')
    newFilters.patchNumber
      ? newSearchParams.set('patch_number', newFilters.patchNumber)
      : newSearchParams.delete('patch_number')
    newFilters.leagueId
      ? newSearchParams.set('league_id', String(newFilters.leagueId))
      : newSearchParams.delete('league_id')
    newFilters.matchStatus
      ? newSearchParams.set('match_status', newFilters.matchStatus)
      : newSearchParams.delete('match_status');

    // Handle array params
    newSearchParams.delete('hero_ids[]')
    if (newFilters.heroIds)
      newFilters.heroIds.forEach((id) => newSearchParams.append('hero_ids[]', String(id)))

    router.push(`${pathname}?${newSearchParams.toString()}`)
  }

  const handlePageChange = (p: number) => handleStateChange({ page: p })
  const handleFiltersChange = (f: MatchFilterOptions) => handleStateChange({ filters: f })

  return {
    page,
    pageSize,
    filters,
    handlePageChange,
    handleFiltersChange,
  }
}
