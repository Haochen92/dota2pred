"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Collapse,
  Divider,
  Grid,
  Group,
  MultiSelect,
  Paper,
  Select,
  Autocomplete,
  TextInput,
} from "@mantine/core";
import { IconChevronDown, IconChevronUp, IconFilter, IconX } from "@tabler/icons-react";
import { useConstantsStore } from "@/hooks/useConstantsStore";
import { useDisclosure } from "@mantine/hooks";

import { TextMdMedium } from "@/components/typography/TextVariants";
import { MatchStatusControl } from "./MatchStatusControl";


// Keep in sync with completed page Filters type
import type { LeagueData } from "@/types/contracts";
import type { MatchFilterOptions } from "@/types/domain";

type FiltersBarProps = {
  filterValues: MatchFilterOptions;
  onChange: (f: MatchFilterOptions) => void;
};

export default function FiltersBar({ filterValues, onChange }: FiltersBarProps) {
  // Fetch Data from global store for filter options
  const {
    patches, heroes, leagues, hasFetched, isLoading, fetchConstants,
    tournamentIdToNameMap, tournamentNameToIdMap
  } = useConstantsStore();

  // Fetch constants on mount if not already done
  useEffect(() => {
    if (!hasFetched && !isLoading) void fetchConstants();
  }, [hasFetched, isLoading, fetchConstants]);


  // Filter value States. We are updating all the filter values at once on Apply.
  const [teamName, setTeamName] = useState<string>(filterValues.teamName ?? "");
  const [patch, setPatch] = useState<string | undefined>(filterValues.patchNumber);
  const [league, setLeague] = useState<number | undefined>(filterValues.leagueId);
  const [heroFilters, setHeroFilters] = useState<number[]>(filterValues.heroIds ?? []);

  // Separate state to manage Autocomplete input text for league filter
  const [leagueInputText, setLeagueInputText] = useState<string | undefined>('');


  useEffect(() => {
    setTeamName(filterValues.teamName ?? '');
    setPatch(filterValues.patchNumber ?? undefined);
    setHeroFilters(filterValues.heroIds ?? []);
    setLeague(filterValues.leagueId ?? undefined);
    setLeagueInputText(filterValues.leagueId ? tournamentIdToNameMap.get(filterValues.leagueId) : '');
  }, [filterValues, tournamentIdToNameMap]);

  // Local UI states

  // UI State for Collapse of filter section
  const [expanded, { toggle: toggleExpanded }] = useDisclosure(false);

  // UI state for rendering number of active filters
  const activeCount = useMemo(() => {
    let count = 0;
    if (filterValues.teamName?.trim()) count += 1;
    if (filterValues.patchNumber?.trim()) count += 1;
    if (filterValues.heroIds?.length) count += 1;
    if (filterValues.leagueId) count += 1;
  // Count matchStatus only if set (undefined == All)
  if (filterValues.matchStatus) count += 1;
    return count;
  }, [filterValues]);

  // UI state for selection components
  const patchOptions = useMemo(
    () => (patches ?? []).map((p) => ({ value: p, label: p })),
    [patches]
  );

  const heroOptions = useMemo(
    () => (heroes ?? [])
    .sort((a, b) => a.hero_id - b.hero_id)
    .map((h) => ({ value: h.hero_id.toString(), label: h.hero_name })),
    [heroes]
  );


  const leagueOptions = useMemo(
    () => (leagues?? []).filter((l): l is LeagueData & { name: string } => Boolean(l.name))
    .sort((a, b) => b.leagueid - a.leagueid)
    .map(l => ({value: l.leagueid.toString(), label: l.name})),
    [leagues]
  )

  const matchStatusOptions = [
    { value: 'All', label: 'All Matches' },
    { value: 'Live', label: 'Live Matches Only' },
    { value: 'Completed', label: 'Past Matches Only' },
  ]

  const handleApply = () => {
    onChange({
  // Keep current immediate status from global filters
  matchStatus: filterValues.matchStatus,
  teamName: teamName?.trim() || '',
      patchNumber: patch?.trim() || undefined,
      heroIds: heroFilters.length ? heroFilters : undefined,
      leagueId: leagueInputText ? tournamentNameToIdMap.get(leagueInputText) : undefined,
    });
  };


  const handleClear = () => {
    setTeamName('');
    setPatch(undefined);
    setHeroFilters([]);
    setLeague(undefined);
    setLeagueInputText(undefined);
  onChange({}); // Reset all filters, including matchStatus
  };

  return (
    <Paper
      p="md"
      radius="md"
      withBorder
      style={(theme) => ({
        background: `linear-gradient(180deg, ${theme.colors.gray[8]} 0%, ${theme.colors.gray[9]} 100%)`,
      })}
    >
      {/* Header with integrated MatchStatusControl */}
      <Group justify="space-between" align="center">
        {/* Left */}
        <Group gap="xs" align="center">
          <IconFilter size={16} />
          {/* Desktop only Text, visible from breakpoint sm */}
          <TextMdMedium visibleFrom="sm">Filters</TextMdMedium>
        </Group>

        {/* Center - Immediate action control */}
        <MatchStatusControl filters={filterValues} onFilterChange={onChange} />

        {/* Right */}
        <Group gap="xs" align="center">
          <Badge color={activeCount > 0 ? "teal.5" : "gray.4"} variant="filled" size="sm">
            {activeCount} active
          </Badge>
          <ActionIcon variant="subtle" onClick={toggleExpanded} aria-label="Toggle filters">
            {expanded ? <IconChevronUp size={20} /> : <IconChevronDown size={20} />}
          </ActionIcon>
        </Group>
      </Group>


      <Collapse in={expanded} transitionDuration={200}>

        <Divider color="dark.5" my="md" />

        <Grid gutter="md">
          <Grid.Col span={{ base: 12, md: 6, lg: 4 }}>
            {/* Team Name Filter */}
            <TextInput
              label="Team Name"
              placeholder="e.g. Team Spirit"
              value={teamName}
              onChange={(e) => setTeamName(e.currentTarget.value)}
              variant="filled"
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6, lg: 4 }}>
            {/* Patch Version Filter */}
            <Select
              label="Patch Version"
              placeholder={isLoading ? "Loading patches..." : "Select patch"}
              data={patchOptions}
              value={patch || null}
              onChange={(val) => setPatch(val ?? "")}
              variant="filled"
              searchable
              clearable
              nothingFoundMessage={isLoading ? "Loading..." : "No patches"}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 12, lg: 4 }}>
            {/* Heroes Filter */}
            <MultiSelect
              label="Heroes"
              placeholder={isLoading ? "Loading heroes..." : "Search and select heroes"}
              data={heroOptions}
              value={heroFilters.map(String)}
              onChange={(val) => setHeroFilters(val.map(Number))}
              variant="filled"
              searchable
              clearable
              nothingFoundMessage={isLoading ? "Loading..." : "No heroes found"}
              maxDropdownHeight={300}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 12, lg: 4 }}>
            {/* Tournament Filter */}
            <Autocomplete
              label="Tournament"
              placeholder={isLoading ? "Loading tournaments..." : "Enter tournament name"}
              data={leagueOptions}
              value={leagueInputText || undefined}
              onChange={(val) => setLeagueInputText(val)}
              variant="filled"
              limit={15}
              clearable
              maxDropdownHeight={300}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 12, lg: 4 }}>
            {/* Match Status (view only; immediate via header) */}
            <Select
              label="Match Status"
              placeholder="Select match status"
              data={matchStatusOptions}
              value={filterValues.matchStatus ?? 'All'}
              disabled
              variant="filled"
            />
          </Grid.Col>
        </Grid>

        <Group justify="flex-end" mt="xl">
          <Button
            variant="subtle"
            onClick={handleClear}
            disabled={activeCount === 0}
            leftSection={<IconX size={16} />}
          >
            Clear
          </Button>
          <Button color="teal.5" onClick={handleApply}>
            Apply Filters
          </Button>
        </Group>
      </Collapse>
    </Paper>
  );
}
