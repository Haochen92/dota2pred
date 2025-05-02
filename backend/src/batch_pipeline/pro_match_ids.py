from database.schemas.matches import ProMatchID

async def insert_promatch_ids(data_json):
    '''
    Saves match IDs from json data to the PostgreSQL database
    '''
    async with get_async_session() as session:
        try:
            match_ids = [{"match_id": x['match_id']} for x in data_json]
            stmt = insert(ProMatchID).values(match_ids).on_conflict_do_nothing(
                index_elements=["match_id"]
            )
            await session.execute(stmt)
            await session.commit()
        
        except Exception as e:
            logger.error(f"failed to insert promatch_id into database {e}")
            raise