import asyncio
import argparse
import json
from typing import List

# NOTE: No changes needed in redis_service.py
from live_orchestrator_app.redis_services.redis_service import RedisService
from dota_oracle_common.constants.redis_constants import (
    FAILED_EVENTS_MAPPING,
)
from dota_oracle_common.models.redis.schema import FailureRecord
from live_orchestrator_app.constants.payload_mappings import PAYLOAD_MODEL_MAPPING
import redis.asyncio as redis


class DlqTool:
    """A tool to inspect and manage events in Dead-Letter Queue (DLQ) Hashes."""

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.redis = redis_service.redis

    async def list_dlq_events(self, dlq_hash_name: str) -> List[FailureRecord]:
        """Fetches all failed events from a given DLQ Hash and parses them."""
        print(f"\nFetching events from DLQ: '{dlq_hash_name}'...")
        try:
            # hgetall returns Dict[str, str] because decode_responses=True
            raw_events = await self.redis.hgetall(dlq_hash_name)
            if not raw_events:
                print("No failed events found in this DLQ.")
                return []

            parsed_events = []
            for event_id, event_json in raw_events.items():
                try:
                    # The payload type in FailureRecord is generic, Pydantic needs help
                    # We first parse into a dict, then determine the payload model
                    raw_dict = json.loads(event_json)
                    stream_name = raw_dict.get("original_stream")

                    PayloadType = PAYLOAD_MODEL_MAPPING.get(stream_name)
                    if not PayloadType:
                        print(f"⚠️  Warning: Unknown stream '{stream_name}' for event {event_id}. Cannot parse fully.")
                        continue

                    # Now we can correctly parse the full FailureRecord with its specific payload
                    FailureModel = FailureRecord[PayloadType]
                    parsed_event = FailureModel.model_validate(raw_dict)
                    parsed_events.append(parsed_event)

                except (json.JSONDecodeError, KeyError, Exception) as e:
                    # FIX: Removed .decode() from event_id as it's already a string.
                    print(f"⚠️  Could not parse event data for ID {event_id}: {e}")

            return sorted(parsed_events, key=lambda r: r.failure_timestamp)
        except Exception as e:
            print(f"❌ Error fetching events from '{dlq_hash_name}': {e}")
            return []

    async def reinject_event(self, record: FailureRecord) -> bool:
        """
        Re-injects a failed event back into its original stream and
        deletes it from the DLQ upon success.
        """
        target_stream = record.original_stream
        original_event = record.original_data
        match_id = original_event.match_id
        payload = original_event.payload

        print(f"\nRe-injecting event {record.original_event_id} for match {match_id} into stream '{target_stream}'...")

        try:
            # Use the RedisService's _publish_event method for consistency
            async with self.redis.pipeline(transaction=True) as pipe:
                await self.redis_service._publish_event(pipe, target_stream, match_id, payload)
                pipe.hdel(FAILED_EVENTS_MAPPING[target_stream], record.original_event_id)
                results = await pipe.execute()

            # FIX: Removed .decode() as results are already strings due to decode_responses=True
            new_event_id = results[0]
            print(f"✅ Success! Re-injected as new event ID: {new_event_id}")
            print(f"✅ Removed original failed event {record.original_event_id} from DLQ.")
            return True

        except Exception as e:
            # This will now correctly catch the 'WRONGTYPE' error if you try to reinject
            # into a corrupted stream key, without crashing the tool on startup.
            print(f"❌ CRITICAL: Failed to reinject event {record.original_event_id}: {e}")
            print("   The event has NOT been removed from the DLQ.")
            return False

    async def delete_event(self, record: FailureRecord) -> bool:
        """Permanently deletes an event from the DLQ without reinjecting."""
        target_hash = FAILED_EVENTS_MAPPING.get(record.original_stream)
        if not target_hash:
            print(f"❌ Cannot find DLQ hash for stream '{record.original_stream}'")
            return False

        print(f"\nDeleting event {record.original_event_id} from DLQ '{target_hash}'...")
        try:
            await self.redis.hdel(target_hash, record.original_event_id)
            print(f"✅ Success! Event {record.original_event_id} permanently deleted.")
            return True
        except Exception as e:
            print(f"❌ Failed to delete event {record.original_event_id}: {e}")
            return False


async def main():
    """The main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(description="A tool to manage failed events in the Dota Oracle DLQ.")
    parser.add_argument("--host", default="localhost", help="Redis host")
    parser.add_argument("--port", type=int, default=6379, help="Redis port")
    parser.add_argument("--db", type=int, default=0, help="Redis database")

    args = parser.parse_args()

    # Establish Redis connection and create RedisService
    redis_client = redis.Redis(host=args.host, port=args.port, db=args.db, decode_responses=True)
    try:
        await redis_client.ping()
        print(f"Connected to Redis at {args.host}:{args.port}/{args.db}")
    except Exception as e:
        print(f"❌ Could not connect to Redis: {e}")
        return

    # FIX: Instantiate RedisService directly without calling the .create() classmethod.
    # This avoids the consumer group initialization which was causing the WRONGTYPE crash.
    # The DLQ tool does not need consumer groups to function.
    redis_service = RedisService(redis_client)
    tool = DlqTool(redis_service)

    dlq_hashes = list(FAILED_EVENTS_MAPPING.values())

    # --- Interactive Loop ---
    while True:
        print("\nAvailable DLQs (from FAILED_EVENTS_MAPPING):")
        for i, name in enumerate(dlq_hashes):
            print(f"  {i+1}) {name}")
        print("  q) Quit")

        choice = input("Select a DLQ to inspect: ")
        if choice.lower() == "q":
            break

        try:
            dlq_index = int(choice) - 1
            if not 0 <= dlq_index < len(dlq_hashes):
                raise ValueError
            selected_dlq = dlq_hashes[dlq_index]
        except ValueError:
            print("Invalid choice. Please try again.")
            continue

        # --- Event Management Loop for selected DLQ ---
        while True:
            events = await tool.list_dlq_events(selected_dlq)
            if not events:
                break  # Go back to DLQ selection

            print("\n--- Failed Events ---")
            for i, record in enumerate(events):
                print(
                    f"  {i+1}) ID: {record.original_event_id} "
                    f"| Timestamp: {record.failure_timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"| Error: {record.error_type}"
                )

            print("\nActions: (r)einject, (d)elete, (v)iew details, (b)ack to DLQ list")
            action_choice = input("Choose an event number and action (e.g., '1 r' to reinject event 1): ")

            if action_choice.lower() == "b":
                break

            parts = action_choice.split()
            if len(parts) != 2:
                print("Invalid format. Use 'number action' (e.g., '1 r').")
                continue

            try:
                event_idx = int(parts[0]) - 1
                action = parts[1].lower()
                selected_record = events[event_idx]
            except (ValueError, IndexError):
                print("Invalid event number.")
                continue

            if action == "r":
                await tool.reinject_event(selected_record)
            elif action == "d":
                confirm = input(f"Really delete event {selected_record.original_event_id}? This is permanent. (y/N): ")
                if confirm.lower() == "y":
                    await tool.delete_event(selected_record)
            elif action == "v":
                print("\n--- Event Details ---")
                print(json.dumps(selected_record.model_dump(mode="json"), indent=2))
                input("\nPress Enter to continue...")
            else:
                print(f"Unknown action '{action}'.")

    print("Exiting tool. Goodbye!")
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
