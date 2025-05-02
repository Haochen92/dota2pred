from sqlalchemy.ext.asyncio import AsyncEngine
from data_pipeline.storage.store_live_match import insert_live_match
from data_pipeline.storage.store_live_match import insert_live_match_outcome

class LiveMatchStorage:
    def __init__(self, db_client: AsyncEngine):
        self.engine = db_client
    
    async def store_new_match(self, match_details):
        await insert_live_match(self.engine, match_details)
        
    async def store_match_outcome(self, match_id, match_outcome):
        await insert_live_match_outcome(
                            engine=self.engine,
                            match_id=match_id,
                            outcome=match_outcome  
                        )