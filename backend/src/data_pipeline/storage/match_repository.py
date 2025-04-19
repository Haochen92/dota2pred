from typing import List, Optional
from pydantic_models import Match
from database.schemas.matches import ProMatch, ProMatchID
from postgresql import get_async_session
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select, delete
import logging

logger = logging.getLogger(__name__)

async def insert_pro_matches(matches: List[Match], conflict_column: Optional[str] = "match_id") -> Optional[List[int]]:
    if not matches:
        logger.info("No matches to insert")
        return None
    
    match_dicts = [match.model_dump() for match in matches]
    async with get_async_session() as session:
        try:
            table = ProMatch.__table__
            stmt = insert(table).values(match_dicts)
            if conflict_column:
                stmt = stmt.on_conflict_do_nothing(index_elements=[conflict_column]) 

            await session.execute(stmt)
            
            match_ids = [match.match_id for match in matches] 

            await session.commit()
            
            return match_ids
        except Exception as e:
            await session.rollback()
            logger.error(f"Error inserting matches into pro_match table: {e}")
            
            raise e


async def promatch_ids_from_db(batch_size: Optional[int] = 1):
    async with get_async_session() as session:
        try:
            stmt = select(ProMatchID.match_id).limit(batch_size)
            result = await session.execute(stmt)
            match_ids = [row[0] for row in result.fetchall()]
            return match_ids
        except Exception as e:
            logger.error(f"Error reading match IDs from db: {e}")
            raise

async def delete_processed_matches(list_match_ids: List[int]) -> bool:
    async with get_async_session() as session:
        try:
            stmt = delete(ProMatchID).where(ProMatchID.match_id.in_(list_match_ids))
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Failure to delete data for batch size ending {list_match_ids[-1]} error: {e}")
            raise 
    