# in tests/integration/test_finite_publisher_stream.py
import pytest
import asyncio
import json
from api_service.streaming.redis_pubsub_service import RedisPubSubService
from tests.factories.api_service_factory import LiveStateUpdateRequestFactory


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.integration
async def test_subscriber_receives_all_messages_from_finite_publisher(redis_pubsub_service: RedisPubSubService):
    """
    Tests a continuous subscriber against a finite publisher.
    - The subscriber runs in the background, simulating a permanent service.
    - The publisher sends a fixed number of messages and then stops.
    - The main test thread collects the results from the subscriber via a queue.
    """
    # =================================================================
    # ARRANGE
    # =================================================================
    test_channel = "finite-publisher-test"
    message_count_to_send = 10
    results_queue = asyncio.Queue()
    subscriber_task = None
    publisher_task = None

    # =================================================================
    # ACT & ASSERT
    # =================================================================

    try:
        # 1. Define the continuous subscriber task (unchanged).
        async def subscriber():
            try:
                async for message_str in redis_pubsub_service.listen_to_channel(test_channel):
                    await results_queue.put(message_str)
            except asyncio.CancelledError:
                print("Subscriber task cancelled.")
                raise

        # 2. Define the FINITE publisher task.
        async def publisher():
            """Publishes exactly 10 messages and then finishes."""
            print("Publisher starting: will send 10 messages.")
            for i in range(message_count_to_send):
                payload = LiveStateUpdateRequestFactory.build()
                payload.live_matches[0].match_id = i + 1
                await redis_pubsub_service.publish_live_update(test_channel, payload)
            print("Publisher finished sending all messages.")

        # 3. Start both tasks.
        subscriber_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.1)
        publisher_task = asyncio.create_task(publisher())

        received_messages = []
        for _ in range(message_count_to_send):
            message = await asyncio.wait_for(results_queue.get(), timeout=5.0)
            received_messages.append(json.loads(message))

        # 5. Assertions.
        assert len(received_messages) == message_count_to_send
        assert received_messages[0]["live_matches"][0]["match_id"] == 1
        assert received_messages[9]["live_matches"][0]["match_id"] == 10

    finally:
        # 6. SIMPLIFIED CLEANUP
        print("Test finished, cleaning up tasks...")
        if publisher_task:
            await publisher_task
        if subscriber_task:
            subscriber_task.cancel()

        await asyncio.gather(subscriber_task, return_exceptions=True)
