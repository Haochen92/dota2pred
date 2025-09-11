from dota_oracle_common.models.match import MatchTable, MatchNotifcationAPIPayload
from dota_oracle_common.models.match.schema import LeagueData


def map_match_table_to_notification_payload(db_match: MatchTable) -> MatchNotifcationAPIPayload:
    payload_data = db_match.model_dump()

    predicted_outcome = None

    if db_match.predictions:
        first_prediction = db_match.predictions[0]
        if first_prediction:
            predicted_outcome = first_prediction.prediction

    # Map league_data from the relationship
    league_data = None
    if db_match.league_data:
        league_data = LeagueData(
            leagueid=db_match.league_data.leagueid, name=db_match.league_data.name, tier=db_match.league_data.tier
        )

    return MatchNotifcationAPIPayload(**payload_data, predicted_outcome=predicted_outcome, league_data=league_data)
