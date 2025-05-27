import pytest
import pytest_asyncio
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import delete
from sqlmodel import select
from dota_oracle.data_repository.schemas import TeamHistoryTable, PlayerHeroHistoryTable, TeamMatchupHistoryTable
from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.utils.set_logging import get_logger
from datetime import datetime, timezone
from ...factories.repository_factories import TeamHistoryTableFactory, PlayerHeroHistoryTableFactory, TeamMatchupHistoryTableFactory

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session') # set all test files to run async and use event_loop scope 'session'

@pytest_asyncio.fixture(scope="function")
async def history_repository_test_subject(test_postgres_engine: AsyncEngine) -> HistoryRepository:
    return HistoryRepository(engine=test_postgres_engine)


@pytest.mark.usefixtures("seed_history_data")
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


@pytest.mark.usefixtures("seed_history_data")
class TestHistoryRepositoryAddops:
    
    ADD_PLAYER_HERO_ARGS = [
       'test_id',
       'input_account_id',
       'input_hero_id',
       'input_match_id',
       'input_win',
       'input_start_time',
       'expected_result_length',
       'expected_win',
       'expected_start_time'
    ]
    
    ADD_PLAYER_HERO_SCENARIOS = [
        (
            'happy_A3H10',
            3,
            10,
            1003,
            True,
            datetime(2025,1,1,tzinfo=timezone.utc),
            1,
            True,
            datetime(2025,1,1,tzinfo=timezone.utc)
        ),
        (
            'conflict_pkey',
            1,
            10,
            1001,
            False,
            datetime(2025,1,1,tzinfo=timezone.utc),
            1,
            True,
            datetime(2023,1,1,tzinfo=timezone.utc)
        )
    ]
    
    @pytest.mark.parametrize(ADD_PLAYER_HERO_ARGS, ADD_PLAYER_HERO_SCENARIOS)
    async def test_add_player_hero_match_outcome(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine: AsyncEngine,
        test_id: str,
        input_account_id: int,
        input_hero_id: int,
        input_match_id: int,
        input_win: bool,
        input_start_time: datetime,
        expected_result_length: int,
        expected_win: bool,
        expected_start_time: datetime,
    ):
        # ACT
        await history_repository_test_subject.add_player_hero_match_outcome(
            account_id=input_account_id,
            hero_id=input_hero_id,
            match_id=input_match_id,
            win=input_win,
            match_start_time=input_start_time
        )
        
        async with AsyncSession(test_postgres_engine) as session:
            async with session.begin():
                stmt = (
                    select(PlayerHeroHistoryTable)
                    .where(PlayerHeroHistoryTable.account_id == input_account_id)
                    .where(PlayerHeroHistoryTable.hero_id == input_hero_id)
                    .where(PlayerHeroHistoryTable.match_id == input_match_id)
                )
                
                result = await session.execute(stmt)
                records = result.scalars().all()

                # Assert exactly one record exists (no duplicates)
                assert len(records) == expected_result_length, f"Expected {expected_result_length} record, but found {len(records)}"
                
                if len(records) > 0:
                    # Extract the single record
                    actual_record = records[0]
                    
                    # validate data
                    
                    assert actual_record.win == expected_win, f"{test_id}: Expected {expected_win} got {actual_record.win}"
                    assert actual_record.start_time == expected_start_time, f"{test_id}: Expected {expected_start_time} got {actual_record.start_time}"
    
    
    # Test for add_team_match_outcome
    ADD_TEAM_MATCH_ARGS = [
    'test_id',
    'input_team_name',
    'input_match_id',
    'input_win',
    'input_start_time',
    'expected_result_length',
    'expected_win',
    'expected_start_time'
    ]

    ADD_TEAM_MATCH_SCENARIOS = [
        (
            'happy_new_team_match',
            'liquid',
            3001,
            True,
            datetime(2025,1,1,tzinfo=timezone.utc),
            1,  # Should create 1 new record
            True,  # Should have our input win value
            datetime(2025,1,1,tzinfo=timezone.utc)  # Should have our input time
        ),
        (
            'conflict_existing_team_match',
            'team_secret',
            1001,  # This should already exist in seed data
            False,  # Try to insert different win value
            datetime(2025,1,1,tzinfo=timezone.utc),  # Try to insert different time
            1,  # Should still have 1 record (the original)
            True,  # Should keep original win value from seed data
            datetime(2023,1,1,tzinfo=timezone.utc)  # Should keep original time from seed data
        )
    ]

    @pytest.mark.parametrize(ADD_TEAM_MATCH_ARGS, ADD_TEAM_MATCH_SCENARIOS)
    async def test_add_team_match_outcome(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine: AsyncEngine,
        test_id: str,
        input_team_name: str,
        input_match_id: int,
        input_win: bool,
        input_start_time: datetime,
        expected_result_length: int,
        expected_win: bool,
        expected_start_time: datetime,
    ):
        # ACT
        await history_repository_test_subject.add_team_match_outcome(
            team_name=input_team_name,
            match_id=input_match_id,
            win=input_win,
            match_start_time=input_start_time
        )
        
        # ASSERT
        async with AsyncSession(test_postgres_engine) as session:
            stmt = (
                select(TeamHistoryTable)
                .where(TeamHistoryTable.team_name == input_team_name)
                .where(TeamHistoryTable.match_id == input_match_id)
            )
            
            result = await session.execute(stmt)
            records = result.scalars().all()

            # Assert expected number of records
            assert len(records) == expected_result_length, \
                f"{test_id}: Expected {expected_result_length} record(s), but found {len(records)}"
            
            if expected_result_length > 0:
                # Extract and validate the record
                actual_record = records[0]
                
                # Validate core identifying fields
                assert actual_record.team_name == input_team_name, f"{test_id}: team_name mismatch"
                assert actual_record.match_id == input_match_id, f"{test_id}: match_id mismatch"
                
                # Validate expected values (which may be original or new depending on conflict)
                assert actual_record.win == expected_win, \
                    f"{test_id}: Expected win={expected_win}, got {actual_record.win}"
                assert actual_record.start_time == expected_start_time, \
                    f"{test_id}: Expected start_time={expected_start_time}, got {actual_record.start_time}"


    # Test for add_team_match_up_outcome
    ADD_TEAM_MATCHUP_ARGS = [
    'test_id',
    'input_team_one',
    'input_team_two',
    'input_match_id',
    'input_win',
    'input_start_time',
    'expected_result_length',
    'expected_team1_name',
    'expected_team2_name',
    'expected_win',
    'expected_start_time'
    ]

    ADD_TEAM_MATCHUP_SCENARIOS = [
        (
            'happy_new_matchup',
            'liquid',
            'navi',  # Sorted will be: liquid, navi
            3001,
            True,  # liquid wins
            datetime(2025,1,1,tzinfo=timezone.utc),
            1,  # Should create 1 new record
            'liquid',  # Sorted team1_name
            'navi',    # Sorted team2_name
            True,      # Should have our input win value
            datetime(2025,1,1,tzinfo=timezone.utc)  # Should have our input time
        ),
        (
            'conflict_existing_matchup',
            'team_secret',
            'PSG_LGD',  # Sorted will be: PSG_LGD, team_secret (matches seed data)
            1001,  # This should already exist in seed data
            True,  # Try to insert different win value
            datetime(2025,1,1,tzinfo=timezone.utc),  # Try to insert different time
            1,  # Should still have 1 record (the original)
            'PSG_LGD',     # Sorted team1_name (matches seed data)
            'team_secret', # Sorted team2_name (matches seed data)
            False,  # Should keep original win value from seed data
            datetime(2023,1,1,tzinfo=timezone.utc)  # Should keep original time from seed data
        ),
        (
            'team_order_reversed',
            'PSG_LGD',
            'team_secret',  # Even though order is different, should sort to same as above
            1002,  # Different match_id from seed data
            False,  # PSG_LGD loses (team_secret wins)
            datetime(2025,1,2,tzinfo=timezone.utc),
            1,  # Should still have 1 record (the original with match_id 1002)
            'PSG_LGD',     # Sorted team1_name
            'team_secret', # Sorted team2_name
            False,  # Should keep original win value from seed data (PSG_LGD loses)
            datetime(2023,1,2,tzinfo=timezone.utc)  # Should keep original time from seed data
        )
    ]

    @pytest.mark.parametrize(ADD_TEAM_MATCHUP_ARGS, ADD_TEAM_MATCHUP_SCENARIOS)
    async def test_add_team_match_up_outcome(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine: AsyncEngine,
        test_id: str,
        input_team_one: str,
        input_team_two: str,
        input_match_id: int,
        input_win: bool,
        input_start_time: datetime,
        expected_result_length: int,
        expected_team1_name: str,
        expected_team2_name: str,
        expected_win: bool,
        expected_start_time: datetime,
    ):
        # ACT
        await history_repository_test_subject.add_team_match_up_outcome(
            team_one=input_team_one,
            team_two=input_team_two,
            match_id=input_match_id,
            win=input_win,
            match_start_time=input_start_time
        )
        
        # ASSERT
        async with AsyncSession(test_postgres_engine) as session:
            stmt = (
                select(TeamMatchupHistoryTable)
                .where(TeamMatchupHistoryTable.team1_name == expected_team1_name)
                .where(TeamMatchupHistoryTable.team2_name == expected_team2_name)
                .where(TeamMatchupHistoryTable.match_id == input_match_id)
            )
            
            result = await session.execute(stmt)
            records = result.scalars().all()

            # Assert expected number of records
            assert len(records) == expected_result_length, \
                f"{test_id}: Expected {expected_result_length} record(s), but found {len(records)}"
            
            if expected_result_length > 0:
                # Extract and validate the record
                actual_record = records[0]
                
                # Validate core identifying fields (after sorting)
                assert actual_record.team1_name == expected_team1_name, f"{test_id}: team1_name mismatch"
                assert actual_record.team2_name == expected_team2_name, f"{test_id}: team2_name mismatch"
                assert actual_record.match_id == input_match_id, f"{test_id}: match_id mismatch"
                
                # Validate expected values (which may be original or new depending on conflict)
                assert actual_record.win == expected_win, \
                    f"{test_id}: Expected win={expected_win}, got {actual_record.win}"
                assert actual_record.start_time == expected_start_time, \
                    f"{test_id}: Expected start_time={expected_start_time}, got {actual_record.start_time}"


    # Additional test for edge cases
    ADD_TEAM_MATCHUP_EDGE_CASES = [
        (
            'empty_team_one',
            None,  # Empty team_one
            'team_secret',
            4001,
            True,
            datetime(2025,1,1,tzinfo=timezone.utc),
            0,  # Should not create any record
            '',
            '',
            False,
            datetime(2025,1,1,tzinfo=timezone.utc)
        ),
        (
            'empty_team_two',
            'team_secret',
            None,  # Empty team_two
            4002,
            True,
            datetime(2025,1,1,tzinfo=timezone.utc),
            0,  # Should not create any record
            '',
            '',
            False,
            datetime(2025,1,1,tzinfo=timezone.utc)
        )
    ]

    @pytest.mark.parametrize(ADD_TEAM_MATCHUP_ARGS, ADD_TEAM_MATCHUP_EDGE_CASES)
    async def test_add_team_match_up_outcome_edge_cases(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine: AsyncEngine,
        test_id: str,
        input_team_one: Optional[str],
        input_team_two: Optional[str],
        input_match_id: int,
        input_win: bool,
        input_start_time: datetime,
        expected_result_length: int,
        expected_team1_name: str,
        expected_team2_name: str,
        expected_win: bool,
        expected_start_time: datetime,
    ):
        # ACT
        await history_repository_test_subject.add_team_match_up_outcome(
            team_one=input_team_one,
            team_two=input_team_two,
            match_id=input_match_id,
            win=input_win,
            match_start_time=input_start_time
        )
        
        # ASSERT - Check no records created
        async with AsyncSession(test_postgres_engine) as session:
            stmt = select(TeamMatchupHistoryTable).where(TeamMatchupHistoryTable.match_id == input_match_id)
            result = await session.execute(stmt)
            records = result.scalars().all()

            assert len(records) == expected_result_length, \
                f"{test_id}: Expected {expected_result_length} record(s), but found {len(records)}"        
    

@pytest_asyncio.fixture(scope="class")
async def seed_history_data(test_postgres_engine: AsyncEngine):
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
            
