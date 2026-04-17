from api_service.dependencies import DatabaseSession
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api.schema import LeagueDataResponse, LeagueData
from dota_oracle_common.models.leagues import LeagueTable
from dota_oracle_common.repositories.leagues_repository import LeaguesRepository


logger = get_logger(__name__)


async def fetch_league_info(
    db_session: DatabaseSession,
) -> LeagueDataResponse:
    """
    Fetches league information from Database
    """
    league_repo = LeaguesRepository(db_session)

    league_data_list = await league_repo.get_all_league_data()

    return await _convert_to_league_data_response(league_data_list)


async def _convert_to_league_data_response(
    league_data_list: list[LeagueTable],
) -> LeagueDataResponse:
    """
    Converts league data list to LeagueDataResponse
    """
    list_league_data = []
    for league_data in league_data_list:
        league_data_item = LeagueData(
            leagueid=league_data.leagueid,
            tier=league_data.tier,
            name=league_data.name,
        )
        list_league_data.append(league_data_item)

    return LeagueDataResponse(leagues=list_league_data)
