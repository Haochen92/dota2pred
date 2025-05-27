import pytest
import pytest_asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import delete
from dota_oracle.data_repository.history_repository import TeamHistoryTable, PlayerHeroHistoryTable, TeamMatchupHistoryTable
from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.utils.set_logging import get_logger
from datetime import datetime, timezone
from ...factories.histories_models_factory import TeamHistoryTableFactory, PlayerHeroHistoryTableFactory, TeamMatchupHistoryTableFactory

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session') # set all test files to run async and use event_loop scope 'session'

@pytest_asyncio.fixture(scope="function")
async def history_repository_test_subject(test_postgres_engine: AsyncEngine) -> HistoryRepository:
    return HistoryRepository(engine=test_postgres_engine)


@pytest.mark.usefixtures("seed_history_data_for_reads")
class TestHistoryRepositoryReadOps:
    
    PLAYER_HERO_HISTORY_ARGS = [
        "test_id",
        "account_id_input",
        "hero_id_input",
        "before_input",
        "limit_input",
        "expected_win_history"
    ]

    PLAYER_HERO_HISTORY_SCENARIOS = [
        (
            "get_A1H10_limit4",
            1,
            10,
            None,
            4,
            [False,False,True,True],
        ),
        (
            "get_A1H10_limit10_with_before",
            1, 
            10,
            datetime(2023,1,4,tzinfo=timezone.utc),
            10,
            [True, True, True]
        ),
        (
            "get_non_existent_hero",
            1,
            35,
            None,
            5,
            []
        )
        
    ]

    @pytest.mark.parametrize(PLAYER_HERO_HISTORY_ARGS, PLAYER_HERO_HISTORY_SCENARIOS)
    async def test_get_player_hero_win_history(
        self,
        history_repository_test_subject: HistoryRepository,
        test_id: str,
        account_id_input: int,
        hero_id_input: int,
        before_input: datetime,
        limit_input: int,
        expected_win_history: List[bool]
        
        
    ):
        actual_win_history = await history_repository_test_subject.get_player_hero_win_history(
            account_id=account_id_input, hero_id=hero_id_input, before=before_input, limit=limit_input
        )
        
        assert actual_win_history == expected_win_history, \
            f"Test ID '{test_id}: Mismatch, expected {expected_win_history} got {actual_win_history}"
    
    TEAM_HISTORY_ARGS = [
        "test_id",
        "team_name_input",
        "before_input",
        "limit_input",
        "expected_win_history"
    ]

    TEAM_HISTORY_SCENARIOS = [
        (
            "get_team_secret_limit5",
            "team_secret",
            None,
            5,
            [True, True, False, False, True],
        ),
        (
            "get_team_secret_limit5_with_before",
            "team_secret",
            datetime(2023,1,3,tzinfo=timezone.utc),
            5,
            [False, True]
        ),
        (
            "get_non_existent_team",
            "team_spirit",
            None,
            5,
            []
        )
        
    ]
    
    @pytest.mark.parametrize(TEAM_HISTORY_ARGS, TEAM_HISTORY_SCENARIOS)
    async def test_get_team_history(
        self,
        history_repository_test_subject: HistoryRepository,
        test_id: str,
        team_name_input: str,
        before_input: datetime,
        limit_input: int,
        expected_win_history: List[bool]
        
        
    ):
        actual_win_history = await history_repository_test_subject.get_team_history(
            team_name=team_name_input, before=before_input, limit=limit_input
        )
        
        assert actual_win_history == expected_win_history, \
            f"Test ID '{test_id}: Mismatch, expected {expected_win_history} got {actual_win_history}"

    TEAM_MATCHUP_ARGS = [
        "test_id",
        "team1_name_input",
        "team2_name_input",
        "before_input",
        "limit_input",
        "expected_win_history"
    ]

    TEAM_MATCHUP_SCENARIOS = [
        (
            "get_team1_team2_matchup_limit5",
            "team_secret",
            "PSG_LGD",
            None,
            5,
            [True, False, True, False, False],
        ),
        (
            "get_team2_team1_matchup_limit5",
            "PSG_LGD",
            "team_secret",
            None,
            5,
            [True, False, True, False, False],
        ),
        (
            "get_invalid_team1_name",
            "team_spirit",
            "team_secret",
            None,
            10,
            []
        )
        
    ]
    
    @pytest.mark.parametrize(TEAM_MATCHUP_ARGS, TEAM_MATCHUP_SCENARIOS)
    async def test_get_team_matchup_history(
        self,
        history_repository_test_subject: HistoryRepository,
        test_id: str,
        team1_name_input: str,
        team2_name_input: str,
        before_input: datetime,
        limit_input: int,
        expected_win_history: List[bool]
        
        
    ):
        actual_win_history = await history_repository_test_subject.get_team_matchup_history(
            team_one=team1_name_input, 
            team_two=team2_name_input, 
            before=before_input, 
            limit=limit_input
        )
        
        assert actual_win_history == expected_win_history, \
            f"Test ID '{test_id}: Mismatch, expected {expected_win_history} got {actual_win_history}"



@pytest_asyncio.fixture(scope="class")
async def seed_history_data_for_reads(test_postgres_engine: AsyncEngine):
    '''
    Seeds data for all read tests in class TestHistoryRepositoryReadOps
    '''
    
    logger.info("Seeding history data for read operations")
    
    player_hero_data = [
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=True, match_id=1001, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=True, match_id=1002, start_time=datetime(2023,1,2,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=True, match_id=1003, start_time=datetime(2023,1,3,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=False, match_id=1004, start_time=datetime(2023,1,4,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=False, match_id=1005, start_time=datetime(2023,1,5,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=2, hero_id=20, win=True, match_id=2001, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
    ]
    
    team_history_data = [
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1001, win=True, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1002, win=False, start_time=datetime(2023,1,2,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1003, win=False, start_time=datetime(2023,1,3,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1004, win=True, start_time=datetime(2023,1,4,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1005, win=True, start_time=datetime(2023,1,5,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='PSG_LGD', match_id=2001, win=True, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
    ]
    
    team_match_up_data = [
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1001, win=False, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1002, win=False, start_time=datetime(2023,1,2,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1003, win=True, start_time=datetime(2023,1,3,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1004, win=False, start_time=datetime(2023,1,4,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1005, win=True, start_time=datetime(2023,1,5,tzinfo=timezone.utc)),  
    ]
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            all_data = player_hero_data + team_history_data + team_match_up_data
            for instance in all_data:
                session.add(instance)
            await session.commit()
            
        logger.info(f"Seeding complete.")


    yield
    
    logger.info("Cleaning up seeded history data...")
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(PlayerHeroHistoryTable))
            await session.execute(delete(TeamHistoryTable))
            await session.execute(delete(TeamMatchupHistoryTable))
            
        await session.commit()
        
    logger.info("Cleanup complete")
            
            

