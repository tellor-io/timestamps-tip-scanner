import json
import os
import sys
import time

from tqdm import tqdm
from web3 import Web3
from dotenv import load_dotenv
from event_scanner import EventScanner
from jsonified_state import JSONifiedState
from web3.providers.rpc import HTTPProvider

print(f"env loaded: {load_dotenv()}")

# We use tqdm library to render a nice progress bar in the console
# https://pypi.org/project/tqdm/


def run():
    reporter = input("reporter address: ")
    if not Web3.isChecksumAddress(reporter):
            print("wrong address type ...")
            sys.exit(1)
    
    api_url = os.getenv("NODE_API")
    print(api_url)

    provider = HTTPProvider(api_url)

    # Remove the default JSON-RPC retry middleware
    # as it correctly cannot handle eth_getLogs block range
    # throttle down.
    provider.middlewares.clear()

    w3 = Web3(provider)

    # Prepare contract object
    with open('abi/tellorflex.json') as tellorflex_abi:
        tellorflex_abi = json.load(tellorflex_abi)

    tellorflex_address = "0x41b66dd93b03e89D29114a7613A6f9f0d4F40178"
    tellorflex_contract = w3.eth.contract(
        address=tellorflex_address, abi=tellorflex_abi)

    # Restore/create our persistent state
    state = JSONifiedState()
    state.restore()

    # chain_id: int, web3: Web3, abi: dict, state: EventScannerState, events: List, filters: {}, max_chunk_scan_size: int=10000
    scanner = EventScanner(
        web3=w3,
        state=state,
        reporter=Web3.toChecksumAddress(reporter),
        contract=tellorflex_contract,
        events=[tellorflex_contract.events.NewReport],
        filters={"address": tellorflex_address},
        # Infura max block range
        max_chunk_scan_size=3499
    )

    # Assume we might have scanned the blocks all the way to the last Ethereum block
    # that mined a few seconds before the previous scan run ended.
    # Because there might have been a minor Etherueum chain reorganisations
    # since the last scan ended, we need to discard
    # the last few blocks from the previous scan results.
    chain_reorg_safety_blocks = 10
    scanner.delete_potentially_forked_block_data(
        state.get_last_scanned_block() - chain_reorg_safety_blocks)

    # Scan from [last block scanned] - [latest ethereum block]
    # Note that our chain reorg safety blocks cannot go negative
    start_block = max(state.get_last_scanned_block() - \
                      chain_reorg_safety_blocks, 0)
    end_block = scanner.get_suggested_scan_end_block()

    blocks_to_scan = end_block - start_block

    print(f"Scanning events from blocks {start_block} - {end_block}")

    # Render a progress bar in the console
    start = time.time()
    with tqdm(total=blocks_to_scan) as progress_bar:
        def _update_progress(start, end, current, chunk_size, events_count):
            progress_bar.set_description(
                f"Current block: {current}, blocks in a scan batch: {chunk_size}, events processed in a batch {events_count}")
            progress_bar.update(chunk_size)

        # Run the scan
        result, total_chunks_scanned = scanner.scan(
            start_block, end_block, progress_callback=_update_progress)

    state.save()
    duration = time.time() - start
    print(
        f"Scanned total {len(result)} TellorFlex NewReport events, in {duration} seconds, total {total_chunks_scanned} chunk scans performed")

run()
