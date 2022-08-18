import os
import asyncio
from dotenv import load_dotenv
from jsonified_state import JSONifiedState
from autopay_calls import AutopayCalls
from utils import FeedDetails
from utils import one_time_tips
from utils import is_timestamp_first_in_window
from utils import w3_instance


async def main():
    print(f"env loaded: {load_dotenv()}")

    autopay_address = os.getenv("AUTOPAY_ADDRESS", None)
    print(f"AUTOPAY_ADDRESS: {autopay_address}")

    state = JSONifiedState()
    state.restore()
    state.restore_singletips()
    state.restore_feed_tips()

    eoa, w3 = w3_instance()

    eoa_reported_ids = state.timestampsperEOA(eoa)

    fetch_feed_ids = AutopayCalls(eoa_reported_ids, w3, autopay_address)

    feed_details = await fetch_feed_ids.get_feed_details()

    timestamps_before = await fetch_feed_ids.get_timestamps_before()

    all_tips = await fetch_feed_ids.get_past_tips()

    for query_id, timestamps in eoa_reported_ids.items():
        for timestamp in timestamps:
            timestamp_before = timestamps_before[query_id, timestamp]
            if len(all_tips[query_id]) > 0:
                single_tips = one_time_tips(
                    all_tips[query_id], timestamp, timestamp_before
                )
            else:
                continue

            if single_tips:
                state.process_singletip_timestamps(query_id, timestamp)
                state.save_single_tips()

            for (q_id, feed_id), details in feed_details.items():
                detail = FeedDetails(*details)
                if query_id == q_id:

                    # check if timestamp is eligible and add to json
                    check_timestamp = is_timestamp_first_in_window(
                        timestamp_before=timestamp_before,
                        timestamp_to_check=timestamp,
                        feed_start_timestamp=detail.startTime,
                        feed_window=detail.window,
                        feed_interval=detail.interval,
                    )
                    if check_timestamp is True:
                        # store
                        if detail.balance == 0:
                            state.process_feed_timestamps_zero_balance(
                                query_id=query_id,
                                feed_id=feed_id.hex(),
                                timestamp=timestamp,
                            )
                        else:
                            state.process_feed_timestamps(
                                query_id=query_id,
                                feed_id=feed_id.hex(),
                                timestamp=timestamp,
                            )
                        state.save_feed_tips()


if __name__ == "__main__":
    asyncio.run(main())
