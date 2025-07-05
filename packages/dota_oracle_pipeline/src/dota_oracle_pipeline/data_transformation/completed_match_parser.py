from dota_oracle_common.models.match import MatchesAPIResponse, MatchWithOutcome
from pydantic import ValidationError
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.time_utils import to_utc_datetime_object

logger = get_logger(__name__)


async def parse_completed_matches(raw_match_data: MatchesAPIResponse) -> MatchWithOutcome:
    # Initialize player slots dictionaries

    try:
        # Create match data dictionary with required fields

        match_data = {
            "match_id": raw_match_data.match_id,
            "leagueid": raw_match_data.league.leagueid if raw_match_data.league is not None else 0,
            "radiant_name": raw_match_data.radiant_name,
            "radiant_team_id": raw_match_data.radiant_team_id if raw_match_data.radiant_team_id is not None else 0,
            "dire_name": raw_match_data.dire_name,
            "dire_team_id": raw_match_data.dire_team_id if raw_match_data.dire_team_id is not None else 0,
            "start_time": to_utc_datetime_object(raw_match_data.start_time),
            "duration": raw_match_data.duration,
            "radiant_win": raw_match_data.radiant_win,
        }

        for player in raw_match_data.players:
            slot = player.player_slot

            match_data[f"slot_{slot}_hero_id"] = player.hero_id
            match_data[f"slot_{slot}_account_id"] = player.account_id

        # Create and return the Match model
        return MatchWithOutcome(**match_data)
    except ValidationError as ve:
        logger.error(f"validation error for match {raw_match_data.match_id}, {ve}", exc_info=True)
        raise ve
    except Exception as e:
        logger.error(f"Exception occured: {e}", exc_info=True)
        raise e
