from dota_oracle_common.models.match import MatchTable, MatchNotifcationAPIPayload


def map_match_table_to_notification_payload(db_match: MatchTable) -> MatchNotifcationAPIPayload:
    payload_data = db_match.model_dump()

    predicted_outcome = None

    if db_match.predictions:
        first_prediction = db_match.predictions[0]
        if first_prediction:
            predicted_outcome = first_prediction.prediction

    return MatchNotifcationAPIPayload(**payload_data, predicted_outcome=predicted_outcome)
