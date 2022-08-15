from typing import List, Optional
from event_scanner_state import EventScannerState
import datetime
import json
import time
from web3.datastructures import AttributeDict
from eth_typing.evm import ChecksumAddress
from web3 import Web3
import logging

logger = logging.getLogger(__name__)


class JSONifiedState(EventScannerState):
    """Store the state of scanned blocks and all events.

    All state is an in-memory dict.
    Simple load/store massive JSON on start up.
    """

    def __init__(self):
        self.state = None
        self.eligible = None
        self.freports = "report_timestamps.json"
        self.fsingletips = "single_tips.json"
        self.ffeedtips = "feed_tips.json"
        # How many second ago we saved the JSON file
        self.last_save = 0
        self.date = datetime.datetime.today().strftime("%b-%d-%Y")

    def reset(self):
        """Create initial state of nothing scanned."""
        import requests

        start_timestamp = int(
            datetime.datetime.today()
            .replace(hour=00, minute=00, second=0, microsecond=0)
            .timestamp()
        )
        print(start_timestamp)
        url = f"https://api-testnet.polygonscan.com/api?module=block&action=getblocknobytime&timestamp={start_timestamp}&closest=before"
        res = requests.get(url)
        result = res.json()
        zero_block = int(result["result"])
        print(f"{zero_block}, zero_block")
        self.state = {
            "last_scanned_block": int(zero_block),
        }

    def restore(self):
        """Restore the last scan state from a file."""
        try:
            self.state = json.load(open(self.freports, "rt"))
            print(
                f"Restored the state, last block scan ended at {self.state['last_scanned_block']}"
            )
            print(self.state["last_scanned_block"])
        except (IOError, json.decoder.JSONDecodeError):
            print("State starting from scratch")
            self.reset()

    def save(self):
        """Save everything we have scanned so far in a file."""
        with open(self.freports, "wt") as f:
            json.dump(self.state, f)
        self.last_save = time.time()

    def reset_feedtips(self):
        self.feed_tips = {"feed_tips": {}}

    def reset_singletips(self):
        self.single_tips = {"single_tips": {}}

    def restore_feed_tips(self):
        """Restore the last scan state from a file."""
        try:
            self.feed_tips = json.load(open(self.ffeedtips, "rt"))
            print(f"Feed-tips file restored")
        except (IOError, json.decoder.JSONDecodeError):
            print("Feed-tips file starting from scratch")
            self.reset_feedtips()

    def restore_singletips(self):
        try:
            self.single_tips = json.load(open(self.fsingletips, "rt"))
            print(f"Single-tips file restored")
        except (IOError, json.decoder.JSONDecodeError):
            print("Single-tips file starting from scratch")
            self.reset_singletips()

    def timestampsperEOA(self, EOA: str) -> Optional[List[int]]:
        try:
            return self.state[f"{EOA}"]
        except KeyError:
            print(f"Timestamps for {EOA} not found in json!")
            return

    def save_single_tips(self):
        with open(self.fsingletips, "wt") as f:
            json.dump(self.single_tips, f)

    def save_feed_tips(self):
        with open(self.ffeedtips, "wt") as f:
            json.dump(self.feed_tips, f)

    def process_feed_timestamps(self, query_id: str, timestamp: int):
        feed_tips = self.feed_tips["feed_tips"]
        if query_id not in feed_tips:
            feed_tips[query_id] = []
        else:
            feed_tips[query_id].append(timestamp)

    def process_singletip_timestamps(self, query_id: str, timestamp: int):
        single_tips = self.single_tips["single_tips"]
        if query_id not in single_tips:
            single_tips[query_id] = []
        else:
            single_tips[query_id].append(timestamp)

    #
    # EventScannerState methods implemented below
    #

    def get_last_scanned_block(self):
        """The number of the last block we have stored."""
        return self.state["last_scanned_block"]

    def delete_data(self, since_block):
        """Remove potentially reorganised blocks from the scan data."""
        pass

    def start_chunk(self, block_number, chunk_size):
        pass

    def end_chunk(self, block_number):
        """Save at the end of each block, so we can resume in the case of a crash or CTRL+C"""
        # Next time the scanner is started we will resume from this block
        self.state["last_scanned_block"] = block_number

        # Save the database file for every minute
        if time.time() - self.last_save > 60:
            self.save()

    def process_event(self, event: AttributeDict) -> str:
        """Record NewReport event and tip eligible timestamps."""

        log_index = event.logIndex  # Log index within the block
        txhash = event.transactionHash.hex()  # Transaction hash
        args = event["args"]
        reporter_addr = args._reporter
        query_id = "0x" + args._queryId.hex()

        if reporter_addr not in self.state:
            self.state[reporter_addr] = {}

        reporter = self.state[reporter_addr]

        if query_id not in reporter:
            reporter[query_id] = []

        queryId = reporter[query_id]

        queryId.append(args._time)
        return f"{txhash}-{log_index}"
