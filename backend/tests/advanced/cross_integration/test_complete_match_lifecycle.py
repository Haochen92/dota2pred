# # tests/integration/test_complete_pipeline.py
# import pytest
# import asyncio
# from datetime import datetime
# from unittest.mock import patch, AsyncMock

# from dota_oracle.models.live_games.schema import LiveLeagueGame
# from dota_oracle.live_pipeline.app_container import AppContainer
# from dota_oracle.constants.redis_constants import STREAM_NEW_MATCHES, STREAM_PENDING_PREDICTION, STREAM_PENDING_COMPLETION

# from ..factories.unit_test_factory import LiveLeagueGameFactory
# from ..factories.repository_factories import MatchTableFactory


# @pytest.mark.asyncio
# async def test_complete_match_lifecycle(mocker, test_redis_client, db_session):
#     """
#     The Crown Jewel Test - Simplified and consistent with your style
#     """
#     # Mock external APIs
#     mock_match = LiveLeagueGameFactory.build(match_id=7890123)
    
#     mocker.patch(
#         'dota_oracle.data_extraction.fetch_live_leagues.fetch_live_league_games',
#         return_value=[mock_match]
#     )
    
#     mock_fetch_outcome = mocker.patch(
#         'dota_oracle.data_extraction.fetch_pro_match.fetch_pro_match',
#         return_value=[]
#     )
    
#     # Your test logic here...
    
#     # Change mock behavior mid-test
#     mock_fetch_outcome.return_value = [{'match_id': mock_match.match_id, 'radiant_win': True}]


# # Simplified version focusing on data flow
# @pytest.mark.asyncio
# async def test_data_consistency_across_stages(db_session, test_redis_client):
#     """
#     MVP: Test that data remains consistent as it flows through the pipeline.
#     Uses your existing fixtures for simplicity.
#     """
#     match_id = 12345
    
#     # 1. Simulate match in Redis (as if discovered)
#     await test_redis_client.xadd(
#         STREAM_NEW_MATCHES, 
#         {'match_id': str(match_id), 'timestamp': datetime.utcnow().isoformat()}
#     )
    
#     # 2. Verify we can read it back
#     messages = await test_redis_client.xread({STREAM_NEW_MATCHES: '0'})
#     assert len(messages) > 0
#     assert messages[0][1][0][1]['match_id'] == str(match_id)
    
#     # 3. In real test, would process through each stage and verify data integrity
#     # For MVP, just verify the pattern works
#     print(f"✅ Data flow verified for match {match_id}")