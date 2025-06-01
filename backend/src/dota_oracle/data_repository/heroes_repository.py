from dota_oracle.models.heroes import HeroData
from .schemas.heroes import HeroDataTable
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from typing import Dict, Optional
from sqlmodel import select
from sqlalchemy.dialects.postgresql import insert
from dota_oracle.utils.set_logging import get_logger
from .base_repository import BaseRepository

logger = get_logger(__name__)

class HeroesRepository(BaseRepository):
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)
        
    async def store_hero_data(self, heroes_input: Dict[str, HeroDataTable]):
        if not heroes_input:
            logger.warning(f"Missing heroes_data: {heroes_input}")
            return
        
        async with AsyncSession(self.engine) as session:
            async with session.begin(): 
                try:
                    heroes_data = [hero.model_dump() for hero in heroes_input.values()]
                    stmt = insert(HeroDataTable).values(heroes_data)
                    update_dict = {
                        col.name: getattr(stmt.excluded, col.name)
                        for col in HeroDataTable.__table__.columns # type: ignore
                        if col.name != 'id' 
                    }
                        
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["id"],
                        set_=update_dict
                    )
                    
                    await session.execute(stmt)
                except Exception as e:
                    logger.error(f"Error inserting hero data: {e}", exc_info=True)
                    raise e 
            
    async def get_hero_data_by_id(self, hero_id: int) -> Optional[HeroDataTable]:
        try:
            instance: Optional[HeroDataTable] = await self._get_instance_by_id(HeroDataTable, hero_id)
            if instance is None:
                return None
            
            return instance
        except Exception as e:
            logger.error(f"Error fetching data from hero_id {hero_id}")
            raise e
    
    async def get_hero_id_map(self)-> Dict[int, str]:
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(HeroDataTable.id, HeroDataTable.localized_name)
                res = await session.execute(stmt)
                rows = res.mappings().all()
                if not rows:
                    raise AttributeError("No hero data found")
                
                hero_map: Dict[int, str] = {row['id']: row['localized_name'] for row in rows}
                return hero_map
            except Exception as e:
                logger.error(f"Error when attempting to create hero map, {e}")
                raise

