
const RADIANT_SLOTS = [0, 1, 2, 3, 4] as const
const DIRE_SLOTS = [128, 129, 130, 131, 132] as const

type RadiantSlot = typeof RADIANT_SLOTS[number]
type DireSlot = typeof DIRE_SLOTS[number]
type Slot = RadiantSlot | DireSlot
type SlotKey = `slot_${Slot}_hero_id`

type MatchWithHeroSlots = Record<SlotKey, number>

function getHeroId(match: MatchWithHeroSlots, slot: Slot): number {
  return match[`slot_${slot}_hero_id` as SlotKey]
}

export function getRadiantHeroPicks(match: MatchWithHeroSlots): number[] {
  return RADIANT_SLOTS.map((s) => getHeroId(match, s))
}

export function getDireHeroPicks(match: MatchWithHeroSlots): number[] {
  return DIRE_SLOTS.map((s) => getHeroId(match, s))
}

export function extractHeroPicks(match: MatchWithHeroSlots): { radiant: number[]; dire: number[] } {
  return {
    radiant: getRadiantHeroPicks(match),
    dire: getDireHeroPicks(match),
  }
}