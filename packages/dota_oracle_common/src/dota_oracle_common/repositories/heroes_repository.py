from ..models.heroes import HeroDataTable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Optional, List
from sqlmodel import select
from ..utils.set_logging import get_logger
from .base_repository import BaseRepository

logger = get_logger(__name__)


class HeroesRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def upsert_hero_data(self, heroes_input: Dict[str, HeroDataTable]) -> None:
        if not heroes_input:
            logger.warning(f"Missing heroes_data: {heroes_input}")
            return
        try:
            upsert_instances = [hero_instance for hero_instance in heroes_input.values()]
            await self._upsert_data(model_class=HeroDataTable, instances=upsert_instances)
        except Exception as e:
            logger.error(f"Error inserting hero data: {e}", exc_info=True)
            raise e

    async def get_hero_data_by_id(self, hero_id: int) -> Optional[HeroDataTable]:
        try:
            res = await self._get_data(model_class=HeroDataTable, id_filters=[hero_id], limit=1)
            if not res:
                logger.debug(f"no data found for hero_id, {hero_id}")
                return None

            hero_data = res[0]

            return hero_data
        except Exception as e:
            logger.error(f"Error fetching data from hero_id {hero_id}")
            raise e

    async def get_hero_id_map(self) -> Dict[int, str]:
        try:
            stmt = select(HeroDataTable.id, HeroDataTable.localized_name)
            res = await self.session.execute(stmt)
            rows = res.mappings().all()
            if not rows:
                logger.warning("Missing Hero map data")
                return {}

            hero_map: Dict[int, str] = {row["id"]: row["localized_name"] for row in rows}
            return hero_map
        except SQLAlchemyError as e:
            logger.error(f"Database error when attempting to create hero map: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error when attempting to create hero map: {e}", exc_info=True)
            raise
    
    async def get_all_hero_data(self) -> List[HeroDataTable]:
        try:
            stmt = select(HeroDataTable)
            res = await self.session.execute(stmt)
            heroes = res.scalars().all()
            if not heroes:
                logger.warning("Missing Hero data")
                return []

            return heroes # type: ignore
        except SQLAlchemyError as e:
            logger.error(f"Database error when attempting to fetch all hero data: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error when attempting to fetch all hero data: {e}", exc_info=True)
            raise
