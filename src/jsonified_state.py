from typing import List
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
        self.fname = "record.json"
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
            "reporter": {}
        }

    def restore(self):
        """Restore the last scan state from a file."""
        try:
            self.state = json.load(open(self.fname, "rt"))
            print(
                f"Restored the state, last block scan ended at {self.state['last_scanned_block']}")
        except (IOError, json.decoder.JSONDecodeError):
            print("State starting from scratch")
            self.reset()

    def save(self):
        """Save everything we have scanned so far in a file."""
        with open(self.fname, "wt") as f:
            json.dump(self.state, f)
        self.last_save = time.time()

    #
    # EventScannerState methods implemented below
    #

    def get_last_scanned_block(self):
        """The number of the last block we have stored."""
        return self.state["last_scanned_block"]

    def delete_data(self, since_block):
        """Remove potentially reorganised blocks from the scan data."""
        # for block_num in range(since_block, self.get_last_scanned_block()):
        #     if block_num in self.state["blocks"]:
        #         del self.state["blocks"][block_num]
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

        if reporter_addr not in self.state["reporter"]:
            self.state["reporter"][reporter_addr] = {}

        reporter = self.state["reporter"][reporter_addr]

        if self.date not in reporter:
            reporter[self.date] = {}

        dates = reporter[self.date]

        if query_id not in dates:
            dates[query_id] = {}

        if "all_submissions" not in dates[query_id]:
            dates[query_id]["all_submissions"] = []

        dates[query_id]["all_submissions"].append(args._time)
        return f"{txhash}-{log_index}"

    def filter_timestamps(self, web3: Web3, reporter: ChecksumAddress, query_id: str):
        # get timestamps from json
        if reporter in self.state["reporter"]:
            logger.debug(reporter)
            submissions_list = self.state["reporter"][reporter][self.date][query_id]["all_submissions"]
            eligible_timestamps = self.state["reporter"][reporter][self.date][query_id]
            timestamp_list = _checker_one_time_tip(web3, query_id, submissions_list)
            logger.debug(timestamp_list)
            if timestamp_list:
                if "one_time_tips" not in eligible_timestamps:
                    eligible_timestamps["one_time_tips"] = timestamp_list

                    return eligible_timestamps

    def get_query_ids(self, reporter: ChecksumAddress) -> List:
        """get query id from state"""
        if reporter in self.state["reporter"]:
            ids = self.state["reporter"][reporter][self.date]
            logger.debug(ids)
            return [query_id for query_id in ids]


def _checker_one_time_tip(web3: Web3, query_id: str, timestamps: List):
    """OneTimeTip checker"""
    with open('abi/autopay.json') as autopay:
        autopay = json.load(autopay)
    autopay_address = "0xD789488E5ee48Ef8b0719843672Bc04c213b648c"
    autopay_contract = web3.eth.contract(address=autopay_address, abi=autopay)
    eligible_list = []
    tips_list = autopay_contract.functions.getPastTips(query_id).call()
    count = len(tips_list)
    for i in timestamps:
        if count > 0:
            mini = 0
            maxi = count
            while maxi - mini > 1:
                mid = int((maxi + mini) / 2)
                tip_info = tips_list[mid]
                if tip_info[1] > i:
                    maxi = mid
                else:
                    mini = mid
            timestamp_before = autopay_contract.functions.getDataBefore(
                query_id, i).call()
            tip_info = tips_list[mini]
            if timestamp_before[2] < tip_info[1]:
                eligible_list.append(int(tip_info[1]))

    return eligible_list

def _checker_feed_tips():
    pass
