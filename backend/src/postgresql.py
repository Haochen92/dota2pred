import os
from sqlalchemy.engine import create_engine, URL
from sqlalchemy import MetaData, Table, select, delete
from sqlalchemy.dialects.postgresql import insert
from functools import lru_cache
import logging
from prefect_sqlalchemy import SqlAlchemyConnector
from models import ProMatchID

# Set up logging
logging.basicConfig(filename='lru_info.log', level=logging.ERROR)
logger = logging.getLogger(__name__)

# Singleton pattern for engine instance
_engine_instance = None

def get_engine():
    global _engine_instance
    if _engine_instance is None:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            _engine_instance = create_engine(db_url)
        else:
            url_object = URL.create(
                "postgresql+psycopg2",
                username='liuhaochen',
                host='localhost',
                port='5432',
                password='110799',
                database='dota2'
            )
            _engine_instance = create_engine(url_object)
    return _engine_instance

@lru_cache(maxsize=128)
def get_table(table_name: str, metadata, conn):
    return Table(table_name, metadata, autoload_with=conn)

def create_records(df, table_name: str, replace=False):
    engine = get_engine()
    replace_type = 'replace' if replace else 'append'
    df.to_sql(f'{table_name}', engine, index=False, if_exists=replace_type)
    
    
def insert_to_table(table_name: str, list_records: list[dict], uuid: str = None):
    engine = get_engine()
    metadata = MetaData()
    try:
        with engine.begin() as conn:
            table = Table(table_name, metadata, autoload_with=conn)
            stmt = insert(table).values(list_records)

            if uuid is not None:
                stmt = stmt.on_conflict_do_nothing(index_elements=[uuid])

            conn.execute(stmt)
            logger.info(f"Successfully inserted records into {table_name}")
            match_ids = [row["match_id"] for row in list_records]
            delete_processed_matches(match_ids, conn)
            
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise


async def insert_to_table_async(table_name: str, list_records: list[dict], uuid: str = None):
    database_block = await SqlAlchemyConnector.load("psql")
    with database_block.get_connection(begin=False) as conn: 
        logger.info("Database Connection Established")
        metadata = MetaData()
        table = get_table(table_name, metadata, conn)
        stmt = insert(table).values(list_records)
        
        if uuid is not None:
            stmt = stmt.on_conflict_do_nothing(index_elements=[uuid])
        
        try:
            conn.execute(stmt)
            conn.commit()
            logger.info(f"Successfully inserted records into {table_name}")
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            raise

def insert_promatch_ids(data_json):
    '''
    Saves match IDs from json data to the PostgreSQL database
    '''
    engine = get_engine()
    try:
        with engine.begin() as conn:
            match_ids = [{"match_id": x['match_id']} for x in data_json]
            stmt = insert(ProMatchID).values(match_ids).on_conflict_do_nothing(
                index_elements=["match_id"]
            )
            conn.execute(stmt)
    except Exception as e:
        logger.error(f"failed to insert promatch_id into database {e}")
        raise
    
    
def fetch_promatch_ids(batch_size: int = 10):
    engine = get_engine()
    try:
        with engine.begin() as conn:
            stmt = select(ProMatchID.match_id).limit(batch_size)
            result = conn.execute(stmt) # Returns a iterator
            match_ids = [row[0] for row in result.fetchall()]
            return match_ids
    except Exception as e:
        logger.error(f"Error reading match IDs from db: {e}")
        raise
    
def delete_processed_matches(list_match_ids: list, conn):
    try:
        stmt = delete(ProMatchID).where(ProMatchID.match_id.in_(list_match_ids))
        conn.execute(stmt)
    except Exception as e:
        logger.error(f"Failure to delete data for batch size ending {list_match_ids[-1]} error: {e}")
        raise