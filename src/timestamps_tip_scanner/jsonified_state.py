import json
import time
from datetime import datetime
from logging import Logger
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests
from eth_typing.evm import ChecksumAddress
from eth_utils import to_checksum_address
from hexbytes import HexBytes

from timestamps_tip_scanner.constants import CHAIN_ID_MAPPING
from timestamps_tip_scanner.constants import REPORTS_FILENAME
from timestamps_tip_scanner.utils import EventData


class JSONifiedState:
    """Store the state of scanned blocks and all events.

    All state is an in-memory dict.
    Simple load/store massive JSON on start up.
    """

    def __init__(self, chain_id: int, address: str, logger: Logger) -> None:
        self.chain_id = chain_id
        self.chain_name = CHAIN_ID_MAPPING[self.chain_id]["name"]
        self.address = to_checksum_address(address)
        self.logger = logger
        # self.state: Dict[str, Any] = {}
        self.eligible = None
        self.single_tips: Optional[Dict[str, Any]] = None
        self.freports = REPORTS_FILENAME
        self.fsingletips = "single_tips.json"
        self.ffeedtips = "feed_tips.json"
        # How many second ago we saved the JSON file
        self.last_save: int = 0
        self.date = datetime.today().strftime("%b-%d-%Y")

    def reset(self, starter_block: Optional[int] = None) -> None:
        """Create initial state of nothing scanned."""
        if starter_block is not None:
            self.logger.info(f"Scan starting from block: {starter_block}")
        else:
            url = CHAIN_ID_MAPPING[self.chain_id]["explorer_api"]
            res = requests.get(url)
            result = res.json()
            starter_block = int(result["result"])
            self.logger.info(f"Starting block was not selected so starting from: {starter_block}")

        self.state = {self.chain_name: {self.address: {"last_scanned_block": int(starter_block)}}}
        return None

    def restore(self) -> None:
        """Restore the last scan state from a file."""
        try:
            self.state = json.load(open(self.freports, "rt"))
            if self.state is None:
                self.logger.info("State starting from scratch")
                self.reset()
            else:
                self.logger.info(
                    "Restored existing state, last block scan ended at "
                    f"{self.state[self.chain_name][self.address]['last_scanned_block']}"
                )
        except (IOError, json.decoder.JSONDecodeError):
            print("State starting from scratch")
            self.reset()

    def save(self) -> None:
        """Save everything we have scanned so far in a file."""
        with open(self.freports, "wt") as f:
            json.dump(self.state, f)
        self.last_save = int(time.time())

    def reset_feedtips(self) -> None:
        self.feed_tips: Dict[str, Any] = {"feed_tips": {}}

    def reset_singletips(self) -> None:
        self.single_tips = {"single_tips": {}}

    def timestampsperEOA(self, EOA: ChecksumAddress) -> Any:
        try:
            return self.state[self.chain_name][EOA]
        except KeyError:
            print(f"Timestamps for {EOA}, on {self.chain_name} not found in json!")
            return None

    def save_single_tips(self) -> None:
        with open(self.fsingletips, "wt") as f:
            json.dump(self.single_tips, f)

    def save_feed_tips(self) -> None:
        with open(self.ffeedtips, "wt") as f:
            json.dump(self.feed_tips, f)

    def process_feed_timestamps(self, query_id: str, feed_id: str, timestamp: int) -> None:
        feed_tips = self.feed_tips["feed_tips"]
        if query_id not in feed_tips:
            feed_tips[query_id] = {}

        if feed_id not in feed_tips[query_id]:
            feed_tips[query_id][feed_id] = []
            feed_tips[query_id][feed_id].append(timestamp)
        else:
            feed_tips[query_id][feed_id].append(timestamp)
            feed_tips[query_id][feed_id] = [*set(feed_tips[query_id][feed_id])]

    def process_feed_timestamps_zero_balance(self, query_id: str, feed_id: str, timestamp: int) -> None:
        feed_tips = self.feed_tips["feed_tips"]
        if "feed_tips_no_balance" not in feed_tips:
            feed_tips["feed_tips_no_balance"] = {}
            feed_tips = feed_tips["feed_tips_no_balance"]
        if query_id not in feed_tips:
            feed_tips[query_id] = {}

        if feed_id not in feed_tips[query_id]:
            feed_tips[query_id][feed_id] = []
            feed_tips[query_id][feed_id].append(timestamp)
        else:
            feed_tips[query_id][feed_id].append(timestamp)
            feed_tips[query_id][feed_id] = [*set(feed_tips[query_id][feed_id])]

    def process_singletip_timestamps(self, query_id: str, timestamp: int) -> None:
        single_tips = self.single_tips["single_tips"]
        if query_id not in single_tips:
            single_tips[query_id] = []
            single_tips[query_id].append(timestamp)
        else:
            single_tips[query_id].append(timestamp)
            single_tips[query_id] = [*set(single_tips[query_id])]

    def get_last_scanned_block(self) -> int:
        """The number of the last block we have stored."""
        return self.state[self.chain_name][self.address]["last_scanned_block"]

    def end_chunk(self, block_number: int) -> None:
        """Save at the end of each block, so we can resume in the case of a crash or CTRL+C"""
        # Next time the scanner is started we will resume from this block
        current_time = int(time.time())
        self.state[self.chain_name][self.address]["last_scanned_block"] = block_number
        self.state[self.chain_name][self.address]["last_scanned_time"] = current_time

        # Save the database file for every minute
        if current_time - self.last_save > 60:
            self.save()

    def process_event(self, event: EventData) -> str:
        """Record NewReport event and tip eligible timestamps."""
        log_index = event.logIndex  # Log index within the block
        txhash = event.transactionHash.hex()  # Transaction hash
        args = event.args
        reporter_addr = to_checksum_address(args._reporter)
        query_id = HexBytes(args._queryId).hex()

        reporter = self.state[self.chain_name][reporter_addr]

        if query_id not in reporter:
            reporter[query_id] = []  # type: ignore

        queryId: List[int] = reporter[query_id]  # type: ignore

        queryId.append(args._time)
        queryId = [*set(queryId)]
        return f"{txhash}-{log_index}"

    def serve(self):
        if self.chain_name in self.state:
            return self.state[self.chain_name]
        return {}
