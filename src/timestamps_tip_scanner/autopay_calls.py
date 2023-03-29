import json
import logging
from time import time
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
from telliot_feeds.reporters.tips.listener.funded_feeds_filter import FundedFeedFilter
from web3 import Web3

from timestamps_tip_scanner.constants import CHAIN_ID_MAPPING
from timestamps_tip_scanner.constants import FOUR_WEEKS
from timestamps_tip_scanner.constants import REPORTS_FILENAME
from timestamps_tip_scanner.constants import TWELVE_HOURS
from timestamps_tip_scanner.utils import FeedDetails

logger = logging.getLogger(__name__)

PastTipType = Union[Tuple[str, str, int], Tuple[str, str]]


def feed_details(value: FeedDetails) -> FeedDetails:
    """Helper function to convert feed details response from multicall to FeedDetails dataclass"""
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
        reports = self.unwanted_timestamps_removed_for_feeds()
        if reports is None:
            logger.info("No reports to process for feed ids call object construction")
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
            logger.info("Unable to construct feed ids call")
            return None
        feeds = Multicall(calls=calls, _w3=self.w3, require_success=True)()
        feeds = {query_id: feeds[query_id] for query_id in feeds if feeds[query_id]}
        return feeds  # type: ignore

    def feed_details_call(self, feed_ids: Dict[str, Any]) -> Optional[List[Call]]:
        """Assemble feed details 'Call' object"""
        calls = [
            Call(
                self.autopay_address,
                ["getDataFeed(bytes32)((uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256))", feed_id],
                [[(query_id, HexBytes(feed_id).hex()), feed_details]],
            )
            for query_id, feeds in feed_ids.items()
            for feed_id in feeds
        ]
        return calls

    def get_feed_details(self) -> Any:
        """Returns feed details for all feed Ids"""
        feed_ids = self.get_feed_ids()
        if feed_ids is None:
            self.log.warning("No feed ids found in autopay")
            return None
        calls = self.feed_details_call(feed_ids)
        return Multicall(calls=calls, _w3=self.w3, require_success=True)()

    def unwanted_timestamps_removed_for_feeds(self) -> Optional[Dict[str, List[int]]]:
        """Remove timestamps older than 4 weeks and younger than 12 hours since timestamps aren't eligible for tips
        These conditions are specific to feed tips only
        """
        reports = self.read_reports()
        if reports is None:
            return None
        current_time_seconds = int(time())
        filtered_reports = {}
        for query_id in reports:
            # Filter out timestamps older than 4 weeks
            filtered_timestamps = [
                timestamp
                for timestamp in reports[query_id]
                if FOUR_WEEKS > (current_time_seconds - timestamp) > TWELVE_HOURS
            ]
            if filtered_timestamps:
                filtered_reports[query_id] = filtered_timestamps
        return filtered_reports

    def unwanted_timestamps_removed_for_singles(self) -> Optional[Dict[str, List[int]]]:
        """Remove timestamps younger than 12 hours since timestamps aren't eligible for tips
        These conditions are specific to OneTimeTips only
        """
        reports = self.read_reports()
        if reports is None:
            return None
        current_time_seconds = int(time())
        filtered_reports = {}
        for query_id in reports:
            # Filter out timestamps younger than 12 hours
            filtered_timestamps = [
                timestamp for timestamp in reports[query_id] if (current_time_seconds - timestamp) > TWELVE_HOURS
            ]
            if filtered_timestamps:
                filtered_reports[query_id] = filtered_timestamps
        return filtered_reports

    def get_feed_details_and_timestamps_before_and_before_values(
        self,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, List[int]]]]:
        """Fetch feed details and before timestamps and before values for all at once"""
        reports = self.unwanted_timestamps_removed_for_feeds()
        # get feed ids list for each query id
        feed_ids = self.get_feed_ids()
        if not feed_ids:
            logger.info("No feed ids found in autopay")
            return None, None
        # get feed details for each feed id
        feed_details_calls = self.feed_details_call(feed_ids)
        # get timestamp before and value before
        timestamps_before_calls = self.timestamps_before_call(reports=reports)
        if not feed_details_calls or not timestamps_before_calls:
            logger.info("Unable to construct feed details Call")
            return None, None
        calls = feed_details_calls + timestamps_before_calls
        response = Multicall(calls=calls, _w3=self.w3, require_success=True)()
        return response, reports

    def get_valid_timestamps(self) -> Optional[Dict[Tuple[str, str], List[int]]]:
        """Check only if timestamp is first in window ie priceThreshold == zero"""
        data, reports = self.get_feed_details_and_timestamps_before_and_before_values()
        if data is None or reports is None:
            logger.info("Unable to get feed details and timestamps before")
            return None
        # separate data ease of understanding
        values: Dict[Tuple[str, str, int], bytes] = {}
        before_timestamps: Dict[Tuple[str, str, int], int] = {}
        feeds: Dict[Tuple[str, str], FeedDetails] = {}
        claim_params: Dict[Tuple[str, str], List[int]] = {}
        for k in data:
            key = k[0]
            if key == "values":
                values[k] = data[k]
            elif key == "timestamps":
                before_timestamps[k] = data[k]
            else:
                feeds[k] = data[k]
        # check window
        filtr = FundedFeedFilter()
        for query_id, feed_id in feeds:
            if feeds[(query_id, feed_id)].balance == 0:
                continue
            for timestamp in reports[query_id]:
                # check if timestamp in window
                in_window, _ = filtr.is_timestamp_first_in_window(
                    timestamp_before=before_timestamps[("timestamps", query_id, timestamp)],
                    timestamp_to_check=timestamp,
                    feed_start_timestamp=feeds[(query_id, feed_id)].startTime,
                    feed_window=feeds[(query_id, feed_id)].window,
                    feed_interval=feeds[(query_id, feed_id)].interval,
                )
                if in_window:
                    if (feed_id, query_id) not in claim_params:
                        claim_params[(feed_id, query_id)] = []
                    claim_params[(feed_id, query_id)].append(timestamp)
            reward_count = round(feeds[(query_id, feed_id)].balance / feeds[(query_id, feed_id)].reward)
            if (feed_id, query_id) in claim_params:
                if reward_count < len(claim_params[(feed_id, query_id)]):
                    claim_params[(feed_id, query_id)] = claim_params[(feed_id, query_id)][:reward_count]
        return claim_params

    def timestamps_before_call(self, reports: Optional[Dict[str, List[int]]] = None) -> Optional[List[Call]]:
        """Assemble timestamps before 'Call' object"""
        if reports is None:
            reports = self.unwanted_timestamps_removed_for_singles()
            if reports is None:
                logger.info("No reports to contstruct timestamps before call")
                return None
        calls = [
            Call(
                self.autopay_address,
                ["getDataBefore(bytes32,uint256)(bytes,uint256)", HexBytes(query_id), timestamp],
                [[("values", query_id, timestamp), None], [("timestamps", query_id, timestamp), None]],
            )
            for query_id, timestamps in reports.items()
            for timestamp in timestamps
        ]
        return calls

    def get_timestamps_before(self) -> Dict[str, Any]:
        """Get timestamps before"""
        calls = self.timestamps_before_call()
        return Multicall(calls=calls, _w3=self.w3, require_success=True)()  # type: ignore

    def past_tips_call(self, reports: Optional[Dict[str, List[int]]] = None) -> Optional[List[Call]]:
        """Assemble past tips 'Call' object"""
        if reports is None:
            reports = self.unwanted_timestamps_removed_for_singles()
            if reports is None:
                logger.info("No reports to contstruct past tips call object")
                return None

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

    def get_past_tips_and_timestamps_before(self) -> Optional[Dict[PastTipType, Any]]:
        """get past tips and timestamps before from autopay"""
        reports = self.unwanted_timestamps_removed_for_singles()
        if reports is None:
            logger.info("No reports to contstruct timestamps before call")
            return None
        past_tips_call = self.past_tips_call(reports)
        timestamps_before_call = self.timestamps_before_call(reports)
        if past_tips_call is None or timestamps_before_call is None:
            logger.info("Unable to construct past tips and timestamps before call")
            return None
        calls = past_tips_call + timestamps_before_call
        multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)()
        # remove values from dict since not needed
        return {key: multi_call[key] for key in multi_call if "values" not in key}

    def reward_claimed_status_call(self) -> Tuple[Optional[List[Call]], Optional[Dict[Tuple[str, str], List[int]]]]:
        feeds = self.get_valid_timestamps()
        if feeds is None:
            logger.info("No valid timestamps to check reward claimed status")
            return None, None
        calls = [
            Call(
                self.autopay_address,
                [
                    "getRewardClaimStatusList(bytes32,bytes32,uint256[])(bool[])",
                    HexBytes(feed_id),
                    HexBytes(query_id),
                    feeds[(feed_id, query_id)],
                ],
                [[(feed_id, query_id), None]],
            )
            for feed_id, query_id in feeds
        ]
        return calls, feeds

    def reward_claimed_status_check(self) -> Optional[Dict[Tuple[str, str], List[int]]]:
        calls, feeds = self.reward_claimed_status_call()
        if calls is None or feeds is None:
            logger.info("No reward claimed status call object constructed")
            return None
        response = Multicall(calls=calls, _w3=self.w3)()
        filtered_dict = {}

        for key in feeds:
            filtered_timestamps = [timestamp for claimed, timestamp in zip(response[key], feeds[key]) if not claimed]
            if filtered_timestamps:
                filtered_dict[key] = filtered_timestamps
        return filtered_dict


if __name__ == "__main__":
    from eth_utils import to_checksum_address

    feed_filter = FundedFeedFilter()
    web3 = Web3(Web3.HTTPProvider("https://rpc-mumbai.maticvigil.com/"))
    address = to_checksum_address("0xd5f1Cc896542C111c7Aa7D7fae2C3D654f34b927")
    apay = to_checksum_address("0x9BE9B0CFA89Ea800556C6efbA67b455D336db1D0")
    apay_calls = AutopayCalls(w3=web3, wallet=address, autopay_address=apay)
    # print(apay_calls.read_reports())
    # OneTimeTips
    # reports = apay_calls.unwanted_timestamps_removed_for_singles()
    # calls = apay_calls.past_tips_call(reports) + apay_calls.timestamps_before_call(reports)
    # print(apay_calls.get_past_tips_and_timestamps_before())
    # FeedTips
    # print(apay_calls.get_feed_ids())
    # print(apay_calls.get_feed_details())
    # print(apay_calls.get_valid_timestamps())
    # print(apay_calls.reward_claimed_status_check())
