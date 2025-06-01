from typing import List
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.models.leagues.schema import LeagueItem
from .schemas.leagues import LeagueTable
from .base_repository import BaseRepository

logger = get_logger(__name__)

class LeaguesRepository(BaseRepository):
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)
        
    async def store_league_data(self, league_inputs: List[LeagueItem]):
        async with AsyncSession(self.engine) as session:
            try:
                # Convert pydantic models to dictionaries
                leagues_data = [league.model_dump() for league in league_inputs]
                
                # Create insert statement with on_conflict_do_nothing
                stmt = insert(LeagueTable).values(leagues_data).on_conflict_do_nothing()
                
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Successfully stored {len(leagues_data)} league records")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error inserting league data: {e}", exc_info=True)
                raise e
            
    async def get_league_data_by_id(self):
        pass
    
    async def get_all_league_data(self):
        pass