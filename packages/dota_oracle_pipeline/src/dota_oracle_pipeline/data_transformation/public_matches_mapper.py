from datetime import datetime, timezone

from dota_oracle_common.models.match import PublicMatch, PublicMatchTable


def to_public_match_table(m: PublicMatch) -> PublicMatchTable:
    """Map PublicMatch schema to PublicMatchTable row, validating team sizes."""
    if len(m.radiant_team) != 5 or len(m.dire_team) != 5:
        raise ValueError(f"Invalid team sizes for match {m.match_id}: {len(m.radiant_team)} / {len(m.dire_team)}")

    return PublicMatchTable(
        match_id=m.match_id,
        start_time=datetime.fromtimestamp(m.start_time, tz=timezone.utc),
        duration=int(m.duration),
        avg_rank_tier=int(m.avg_rank_tier),
        num_rank_tier=int(m.num_rank_tier),
        radiant_win=bool(m.radiant_win),
        slot_0_hero_id=m.radiant_team[0],
        slot_1_hero_id=m.radiant_team[1],
        slot_2_hero_id=m.radiant_team[2],
        slot_3_hero_id=m.radiant_team[3],
        slot_4_hero_id=m.radiant_team[4],
        slot_128_hero_id=m.dire_team[0],
        slot_129_hero_id=m.dire_team[1],
        slot_130_hero_id=m.dire_team[2],
        slot_131_hero_id=m.dire_team[3],
        slot_132_hero_id=m.dire_team[4],
    )
