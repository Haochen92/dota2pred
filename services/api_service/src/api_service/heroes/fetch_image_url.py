from api_service.dependencies import DatabaseSession
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api.schema import HeroImageResponse, HeroImageData
from dota_oracle_common.models.heroes import HeroDataTable
from dota_oracle_common.repositories.heroes_repository import HeroesRepository


logger = get_logger(__name__)

async def fetch_hero_image_urls(
    db_session: DatabaseSession,
) -> HeroImageResponse:
    """
    Fetches hero image URLs from Database
    """
    hero_repo = HeroesRepository(db_session)
    
    hero_data_list = await hero_repo.get_all_hero_data()

    return await _convert_to_hero_image_response(hero_data_list)


async def _convert_to_hero_image_response(
    hero_data_list: list[HeroDataTable],
) -> HeroImageResponse:
    """
    Converts hero data list to HeroImageResponse
    """
    list_hero_image_data = []
    for hero_data in hero_data_list:
        hero_image_data = HeroImageData(
            hero_id=hero_data.id,
            hero_name=hero_data.localized_name,
            image_url=hero_data.img,
            icon_url=hero_data.icon,
            primary_attr=hero_data.primary_attr,
        )
        list_hero_image_data.append(hero_image_data)

    return HeroImageResponse(heroes=list_hero_image_data)
