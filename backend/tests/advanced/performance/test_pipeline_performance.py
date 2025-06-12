# tests/integration/test_performance.py
import pytest
import asyncio
import time
from typing import List

from dota_oracle.utils.async_utils import TaskRunner
from dota_oracle.models.utils import AsyncTask


@pytest.mark.asyncio
async def test_concurrent_match_processing():
    """
    MVP Performance Test: Verify system can handle multiple concurrent matches.
    """
    # 1. Create mock processing function
    async def process_match(match_id: int) -> dict:
        """Simulate match processing with some delay"""
        await asyncio.sleep(0.1)  # Simulate work
        return {"match_id": match_id, "status": "processed"}
    
    # 2. Create tasks for concurrent processing
    num_matches = 50
    tasks = []
    
    start_time = time.time()
    
    for i in range(num_matches):
        task = AsyncTask(
            key=f"match_{i}",
            coro=process_match(i)
        )
        tasks.append(task)
    
    # 3. Process all matches concurrently
    results = await TaskRunner.run_concurrently(tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 4. Verify all processed successfully
    assert len(results) == num_matches
    successful = sum(1 for r in results if r.exception is None)
    assert successful == num_matches
    
    # 5. Check performance
    # With 0.1s delay per match, sequential would take 5 seconds
    # Concurrent should be much faster
    assert duration < 1.0, f"Took {duration}s - too slow for concurrent processing!"
    
    print(f"✅ Processed {num_matches} matches in {duration:.2f}s")
    print(f"   Rate: {num_matches/duration:.1f} matches/second")


@pytest.mark.asyncio
async def test_redis_stream_throughput(test_redis_client):
    """
    MVP: Test Redis stream can handle expected message rate.
    """
    stream_key = "test:performance:stream"
    num_messages = 100
    
    # 1. Write messages as fast as possible
    start_time = time.time()
    
    for i in range(num_messages):
        await test_redis_client.xadd(
            stream_key,
            {"match_id": str(i), "timestamp": str(time.time())}
        )
    
    write_duration = time.time() - start_time
    write_rate = num_messages / write_duration
    
    # 2. Read messages back
    start_time = time.time()
    
    messages = await test_redis_client.xread({stream_key: '0'}, count=num_messages)
    
    read_duration = time.time() - start_time
    read_rate = num_messages / read_duration
    
    # 3. Verify performance
    assert len(messages[0][1]) == num_messages, "Lost messages!"
    assert write_rate > 100, f"Write rate {write_rate:.1f} msg/s too slow"
    assert read_rate > 100, f"Read rate {read_rate:.1f} msg/s too slow"
    
    print(f"✅ Redis performance:")
    print(f"   Write: {write_rate:.1f} messages/second")
    print(f"   Read: {read_rate:.1f} messages/second")
    
    # Cleanup
    await test_redis_client.delete(stream_key)


# Simple load test for your pipeline
@pytest.mark.asyncio
async def test_pipeline_under_load(mock_redis_service, mock_async_engine):
    """
    MVP: Test feature engineering can handle multiple matches concurrently.
    """
    from dota_oracle.live_pipeline.feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator
    from ..factories.unit_test_factory import FeatureEngineeringWorkItemFactory
    
    # Mock dependencies
    mock_data_provider = AsyncMock()
    mock_event_processor = AsyncMock()
    
    orchestrator = FeatureEngineeringOrchestrator(
        redis_service=mock_redis_service,
        data_provider=mock_data_provider,
        event_processor=mock_event_processor
    )
    
    # Create many work items
    num_items = 20
    work_items = [FeatureEngineeringWorkItemFactory.build() for _ in range(num_items)]
    mock_data_provider.get_work_items.return_value = work_items
    
    # Make processing take some time
    async def slow_process(item):
        await asyncio.sleep(0.05)
        return None
    
    mock_event_processor.process_event.side_effect = slow_process
    
    # Time the processing
    start_time = time.time()
    result = await orchestrator.run_feature_engineering_cycle()
    duration = time.time() - start_time
    
    # Verify
    assert result == num_items
    assert duration < 1.0, f"Processing {num_items} items took {duration}s - too slow!"
    
    rate = num_items / duration
    print(f"✅ Processed {num_items} items in {duration:.2f}s ({rate:.1f} items/s)")