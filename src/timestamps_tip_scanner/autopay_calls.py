import json
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from multicall import Call
from multicall import Multicall
from web3 import Web3

from timestamps_tip_scanner.constants import CHAIN_ID_MAPPING
from timestamps_tip_scanner.constants import REPORTS_FILENAME
from timestamps_tip_scanner.utils import FeedDetails

def feed_details(value):
    return FeedDetails(*value)
class AutopayCalls:
    def __init__(self, w3: Web3, wallet: ChecksumAddress, autopay_address: ChecksumAddress) -> None:
        self.w3 = w3
        self.wallet = wallet
        self.autopay_address = autopay_address
        self.log = logging.getLogger(__name__)
        self.chain_name = CHAIN_ID_MAPPING[self.w3.eth.chain_id]["name"]
        with open(REPORTS_FILENAME, "r") as f:
            self.reports: Dict[str, Dict[str, Dict[str, Union[int, List[int]]]]] = json.load(f)

    def read_reports(self) -> Optional[Dict[str, List[int]]]:
        reports_by_chain = self.reports.get(self.chain_name)
        if reports_by_chain is None:
            self.log.info(f"No reports for chain {self.chain_name}")
            return None
        reports_by_address = reports_by_chain.get(self.wallet)
        if reports_by_address is None:
            self.log.info(f"No reports for address {self.wallet}")
            return None
        if "last_scanned_block" in reports_by_address:
            del reports_by_address["last_scanned_block"]
        return reports_by_address  # type: ignore

    def feed_ids_call(self) -> Optional[List[Call]]:
        """Assemble feed ids 'Call' object"""
        reports = self.read_reports()
        if reports is None:
            return None

        calls = [
            Call(
                self.autopay_address,
                ["getCurrentFeeds(bytes32)(bytes32[])", HexBytes(query_id)],
                [[query_id, None]],
            )
            for query_id in reports
        ]
        return calls

    def get_feed_ids(self) -> Optional[Dict[str, Any]]:
        """Returns feed ids for every query id"""
        calls = self.feed_ids_call()
        if calls is None:
            return None
        return Multicall(calls=calls, _w3=self.w3, require_success=True)()  # type: ignore

    def feed_details_call(self, feed_ids: Dict[str, Any]) -> Optional[List[Call]]:
        """Assemble feed details 'Call' object"""
        calls = [
            Call(
                self.autopay_address,
                ["getDataFeed(bytes32)((uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256))", feed_id],
                [[(query_id, HexBytes(feed_id)), feed_details]],
            )
            for query_id, feeds in feed_ids.items()
            for feed_id in feeds
            if len(feeds) > 0
        ]
        return calls

    def get_feed_details(self) -> Any:
        """Returns feed details for all feed Ids"""
        # store them like this {(query_id, feed_id): details}
        feed_ids = self.get_feed_ids()
        if feed_ids is None:
            self.log.warning("No feed ids found in autopay")
            return None
        calls = self.feed_details_call(feed_ids)
        return Multicall(calls=calls, _w3=self.w3, require_success=True)()
    
    
    def get_feed_details_and_timestamps_before(self):
        feed_ids = self.get_feed_ids()
        feed_details_calls = self.feed_details_call(feed_ids)
        timestamps_before_calls = self.timestamps_before_call()
        calls = feed_details_calls + timestamps_before_calls
        return Multicall(calls=calls, _w3=self.w3, require_success=True)()

    
    def timestamps_before_call(self, reports: Optional[Dict[str, List[int]]] = None) -> List[Call]:
        """Assemble timestamps before 'Call' object"""
        if reports is None:
            reports = self.read_reports()
            if reports is None:
                return []
        calls = [
            Call(
                self.autopay_address,
                ["getDataBefore(bytes32,uint256)(bytes,uint256)", HexBytes(query_id), timestamp],
                # allows returned values to be overwritten since they're not needed here
                [["values", None], [(query_id, timestamp), None]],
            )
            for query_id, timestamps in reports.items()
            for timestamp in timestamps
        ]
        return calls

    def get_timestamps_before(self) -> Dict[str, Any]:
        """Get timestamps before"""
        calls = self.timestamps_before_call()
        multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)()
        # remove values key since its not needed
        multi_call.pop("values", None)
        return multi_call  # type: ignore

    def past_tips_call(self, reports: Optional[Dict[str, List[int]]] = None) -> List[Call]:
        """Assemble past tips 'Call' object"""
        if reports is None:
            reports = self.read_reports()
            if reports is None:
                return []
        calls = [
            Call(
                self.autopay_address,
                ["getPastTips(bytes32)((uint256,uint256)[])", HexBytes(query_id)],
                [[("past_tips", query_id), None]],
            )
            for query_id in reports
        ]
        return calls

    def get_past_tips(self) -> Dict[str, Any]:
        """get past tips from autopay"""
        calls = self.past_tips_call()
        return Multicall(calls=calls, _w3=self.w3, require_success=True)()  # type: ignore

    def get_past_tips_and_timestamps_before(self) -> Dict[Tuple[str, Any], Any]:
        """get past tips and timestamps before from autopay"""
        reports = self.read_reports()
        calls = self.past_tips_call(reports) + self.timestamps_before_call(reports)
        multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)()
        # remove values key since its not needed
        multi_call.pop("values", None)
        return multi_call  # type: ignore

    def get_reward_claimed_status(self, query_id: bytes, feed_id: bytes, timestamps: List[int]) -> Dict[str, Any]:
        """check if a reported timestamp has already claimed"""
        calls = [
            Call(
                self.autopay_address,
                ["getRewardClaimStatusList(bytes32,bytes32,uint256[])(bool[])", feed_id, query_id, timestamps],
                [[feed_id.hex(), None]],
            )
        ]
        return Multicall(calls=calls, _w3=self.w3, require_success=True)()  # type: ignore
