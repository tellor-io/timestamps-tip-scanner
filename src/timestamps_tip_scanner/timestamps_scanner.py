import logging
import os
import time
from typing import Optional

from eth_typing import ChecksumAddress
from tqdm import tqdm
from web3 import Web3
from web3.contract import Contract

from timestamps_tip_scanner.event_scanner import EventScanner
from timestamps_tip_scanner.jsonified_state import JSONifiedState


def run(
    *,
    w3: Web3,
    reporter: ChecksumAddress,
    tellorflex_contract: Contract,
    chain_id: int,
    starting_block: Optional[int] = None,
) -> JSONifiedState:
    """Scan the Ethereum blockchain for events and store them in a JSON file."""

    # Restore/create our persistent state
    state = JSONifiedState(chain_id=chain_id, address=reporter)
    if starting_block is None:
        state.restore()
    else:
        state.reset(starting_block)

    max_batch_scan_size = int(os.getenv("BATCH_SIZE", 100000))

    scanner = EventScanner(
        web3=w3,
        state=state,
        reporter=reporter,
        contract=tellorflex_contract,
        events=[tellorflex_contract.events.NewReport],
        filters={"address": tellorflex_contract.address},
        # Infura max block ranger
        max_chunk_scan_size=max_batch_scan_size,
    )
    # Scan from [last block scanned] - [latest ethereum block]
    # Note that our chain reorg safety blocks cannot go negative

    start_block = state.get_last_scanned_block()
    end_block = scanner.get_suggested_scan_end_block()

    blocks_to_scan = end_block - start_block

    logging.info(f"Scanning events from blocks {start_block} - {end_block}")

    # Render a progress bar in the console
    start = time.time()
    with tqdm(total=blocks_to_scan) as progress_bar:

        def _update_progress(current: int, chunk_size: int, events_count: int) -> None:
            progress_bar.set_description(
                f"Current block: {current}, "
                f"blocks in a scan batch: {chunk_size}, events processed in a batch {events_count}"
            )
            progress_bar.update(chunk_size)

        # Run the scan
        result, total_chunks_scanned = scanner.scan(
            start_block,
            end_block,
            progress_callback=_update_progress,
            start_chunk_size=max_batch_scan_size,
        )

    state.save()
    duration = time.time() - start
    logging.info(
        f"Scanned total {len(result)} TellorFlex NewReport events, in {duration} seconds, "
        f"total {total_chunks_scanned} chunk scans performed"
    )

    return state
