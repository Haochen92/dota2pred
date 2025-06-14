import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from dota_oracle_pipeline.data_extraction.fetch_hero_data import fetch_hero_data
from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.postgresql import DatabaseEngineFactory
from dota_oracle_common.models.heroes import HeroDataTable

async def update_hero_data(session: AsyncSession):
    hero_data = await fetch_hero_data()
    hero_data_table = {key : HeroDataTable.model_validate(value) for key, value in hero_data.items()}
    
    hero_repo = HeroesRepository(session)
    try:
        await hero_repo.store_hero_data(hero_data_table)
        print(f"Successfully stored {len(hero_data_table)} hero data")
    except Exception as e:
        raise e

async def main():
    db_engine = DatabaseEngineFactory.get_engine()
    async with AsyncSession(db_engine) as session:
        async with session.begin():
            await update_hero_data(session)
    
if __name__ == "__main__":
    asyncio.run(main())