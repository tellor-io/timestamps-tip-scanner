import ast
import json
import logging
from time import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from eth_abi import decode_single
from hexbytes import HexBytes
from multicall import Call
from multicall import Multicall
from telliot_core.tellor.tellor360.autopay import Tellor360AutopayContract
from telliot_feeds.queries.query_catalog import query_catalog
from telliot_feeds.reporters.tips.listener.funded_feeds_filter import _get_price_change
from telliot_feeds.reporters.tips.listener.funded_feeds_filter import FundedFeedFilter

from timestamps_tip_scanner.constants import CHAIN_ID_MAPPING
from timestamps_tip_scanner.constants import FOUR_WEEKS
from timestamps_tip_scanner.constants import QUERYDATASTORAGEMAPPING
from timestamps_tip_scanner.constants import REPORTS_FILENAME
from timestamps_tip_scanner.constants import TWELVE_HOURS
from timestamps_tip_scanner.utils import FeedDetails


PastTipType = Union[Tuple[str, str, int], Tuple[str, str]]


def decode_typ_name(qdata: bytes) -> str:
    """Decode query type name from query data

    Args:
    - qdata: query data in bytes

    Return: string query type name
    """
    qtype_name: str
    try:
        qtype_name, _ = decode_single("(string,bytes)", qdata)
    except OverflowError:
        # string query for some reason encoding isn't the same as the others
        qtype_name = ast.literal_eval(qdata.decode("utf-8"))["type"]
    return qtype_name


def feed_details(value: FeedDetails) -> FeedDetails:
    """Helper function to convert feed details response from multicall to FeedDetails dataclass"""
    return FeedDetails(*value)


def parse_feed_data(data: Dict[str, Any]) -> Any:
    before_values: Dict[Tuple[str, str, int], bytes] = {}
    current_values: Dict[Tuple[str, str, int], bytes] = {}
    before_timestamps: Dict[Tuple[str, str, int], int] = {}
    feeds: Dict[Tuple[str, str], FeedDetails] = {}
    for k in data:
        key = k[0]
        if key == "before_values":
            before_values[k] = data[k]
        elif key == "timestamps":
            before_timestamps[k] = data[k]
        elif key == "current_values":
            current_values[k] = data[k]
        else:
            feeds[k] = data[k]
    return before_values, current_values, before_timestamps, feeds


class AutopayCalls:
    def __init__(self, autopay_contract: Tellor360AutopayContract) -> None:
        self.w3 = autopay_contract.node._web3
        self.chain_id = autopay_contract.node.chain_id
        self.wallet = self.w3.toChecksumAddress(autopay_contract.account.address)
        self.autopay_address = autopay_contract.address
        self.chain_name = CHAIN_ID_MAPPING[self.chain_id]["name"]

    @property
    def reports(self) -> Dict[str, Dict[str, Dict[str, Union[int, List[int]]]]]:
        with open(REPORTS_FILENAME, "r") as f:
            return json.load(f)

    def read_reports(self) -> Optional[Dict[str, List[int]]]:
        reports_by_chain = self.reports.get(self.chain_name)
        if reports_by_chain is None:
            logging.info(f"No reports for chain {self.chain_name}")
            return None
        reports_by_address = reports_by_chain.get(self.wallet)
        if reports_by_address is None:
            logging.info(f"No reports for address {self.wallet}")
            return None
        if "last_scanned_block" in reports_by_address:
            del reports_by_address["last_scanned_block"]
        if "last_scanned_time" in reports_by_address:
            del reports_by_address["last_scanned_time"]
        return reports_by_address  # type: ignore

    def get_query_type(self, query_id: str) -> Optional[str]:
        """Helper function to get query data from storage contract"""
        abi = [
            {
                "inputs": [{"internalType": "bytes32", "name": "_queryId", "type": "bytes32"}],
                "name": "getQueryData",
                "outputs": [{"internalType": "bytes", "name": "_queryData", "type": "bytes"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]
        try:
            storage_contract = self.w3.eth.contract(address=QUERYDATASTORAGEMAPPING[self.chain_id], abi=abi)
            query_data = storage_contract.functions.getQueryData(query_id).call()
            query_type = decode_typ_name(query_data)
        except Exception as e:
            logging.debug(f"Failed to get query type for query id {query_id}: {e}")
            return None
        return query_type

    def decode_value(self, query_id: str, before_value: bytes, after_value: bytes) -> Any:
        """Helper function to decode value from oracle response"""
        in_catalog = query_catalog.find(query_id=query_id)
        if not in_catalog:
            # attempt to get query data from storage contract
            query_type = self.get_query_type(query_id=query_id)
            if query_type is None:
                return None, None
            in_catalog = query_catalog.find(query_type=query_type)
        try:
            decoder = in_catalog[0].query.value_type.decode
        except IndexError:
            return None, None
        before_val_decoded = decoder(before_value)
        after_val_decoded = decoder(after_value)
        if not isinstance(before_val_decoded, (float, int)) or not isinstance(after_val_decoded, (float, int)):
            return None, None
        return before_val_decoded, after_val_decoded

    def feed_ids_call(self) -> Optional[List[Call]]:
        """Assemble feed ids 'Call' object"""
        reports = self.unwanted_timestamps_removed_for_feeds()
        if reports is None:
            logging.info("No reports to process for feed ids call object construction")
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
            logging.info("Unable to construct feed ids call")
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
            logging.warning("No feed ids found in autopay")
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

    def get_feed_details_and_before_timestamps_and_before_values(
        self,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, List[int]]]]:
        """Fetch feed details and before timestamps and before values for all at once"""
        reports = self.unwanted_timestamps_removed_for_feeds()
        # get feed ids list for each query id
        feed_ids = self.get_feed_ids()
        if not feed_ids:
            logging.info("No feed ids found in autopay")
            return None, None
        # get feed details for each feed id
        feed_details_calls = self.feed_details_call(feed_ids)
        # get timestamp before and value before
        timestamps_before_calls = self.timestamps_before_call(reports=reports)
        value_calls = self.retrieve_data(reports=reports)
        if not feed_details_calls or not timestamps_before_calls or not value_calls:
            logging.info("Unable to construct feed details Call")
            return None, None

        calls = feed_details_calls + timestamps_before_calls + value_calls
        response = Multicall(calls=calls, _w3=self.w3, require_success=True)()
        return response, reports

    def get_valid_timestamps(self) -> Optional[Dict[Tuple[str, str], List[int]]]:
        """Check only if timestamp is first in window ie priceThreshold == zero"""
        data, reports = self.get_feed_details_and_before_timestamps_and_before_values()
        if data is None or reports is None:
            logging.info("Unable to get feed details and timestamps before")
            return None

        before_values, current_values, before_timestamps, feeds = parse_feed_data(data)
        claim_params: Dict[Tuple[str, str], List[int]] = {}
        # check window
        filtr = FundedFeedFilter()
        for query_id, feed_id in feeds:
            if feeds[(query_id, feed_id)].balance == 0:
                continue
            for timestamp in reports[query_id]:
                # check if timestamp in window
                reward_increase = feeds[(query_id, feed_id)].rewardIncreasePerSecond
                reward_amount = feeds[(query_id, feed_id)].reward
                balance = feeds[(query_id, feed_id)].balance
                first_in_window, time_diff = filtr.is_timestamp_first_in_window(
                    timestamp_before=before_timestamps[("timestamps", query_id, timestamp)],
                    timestamp_to_check=timestamp,
                    feed_start_timestamp=feeds[(query_id, feed_id)].startTime,
                    feed_window=feeds[(query_id, feed_id)].window,
                    feed_interval=feeds[(query_id, feed_id)].interval,
                )
                # check if reward amount is covered by balance
                # taking into account reward increase
                reward_amount += reward_increase * time_diff
                if balance < reward_amount:
                    break
                if first_in_window:
                    # if timestamp is first in window, add to list of timestamps for (feedId,)
                    if (feed_id, query_id) not in claim_params:
                        claim_params[(feed_id, query_id)] = []
                    claim_params[(feed_id, query_id)].append(timestamp)
                    # subtract reward amount from balance for next iteration
                    balance -= reward_amount
                elif feeds[(query_id, feed_id)].priceThreshold > 0:
                    before_val = before_values[("before_values", query_id, timestamp)]
                    current_val = current_values[("current_values", query_id, timestamp)]
                    decoded_values = self.decode_value(query_id, before_val, current_val)
                    if decoded_values == (None, None):
                        continue
                    price_change = _get_price_change(decoded_values[0], decoded_values[1])
                    if price_change > feeds[(query_id, feed_id)].priceThreshold:
                        if (feed_id, query_id) not in claim_params:
                            claim_params[(feed_id, query_id)] = []
                        claim_params[(feed_id, query_id)].append(timestamp)
                        balance -= reward_amount

        return claim_params

    def timestamps_before_call(self, reports: Optional[Dict[str, List[int]]] = None) -> Optional[List[Call]]:
        """Assemble timestamps before 'Call' object"""
        if reports is None:
            reports = self.unwanted_timestamps_removed_for_singles()
            if reports is None:
                logging.info("No reports to contstruct timestamps before call")
                return None
        calls = [
            Call(
                self.autopay_address,
                ["getDataBefore(bytes32,uint256)(bytes,uint256)", HexBytes(query_id), timestamp],
                [[("before_values", query_id, timestamp), None], [("timestamps", query_id, timestamp), None]],
            )
            for query_id, timestamps in reports.items()
            for timestamp in timestamps
        ]
        return calls

    def retrieve_data(self, reports: Optional[Dict[str, List[int]]] = None) -> Optional[List[Call]]:
        """Assemble timestamps before 'Call' object"""
        if reports is None:
            reports = self.unwanted_timestamps_removed_for_singles()
            if reports is None:
                logging.info("No reports to contstruct timestamps before call")
                return None
        calls = [
            Call(
                self.autopay_address,
                ["retrieveData(bytes32,uint256)(bytes)", HexBytes(query_id), timestamp],
                [[("current_values", query_id, timestamp), None]],
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
                logging.info("No reports to contstruct past tips call object")
                return None

        calls = [
            Call(
                self.autopay_address,
                ["getPastTips(bytes32)((uint256,uint256,uint256)[])", HexBytes(query_id)],
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
            logging.info("No reports to contstruct timestamps before call")
            return None
        past_tips_call = self.past_tips_call(reports)
        timestamps_before_call = self.timestamps_before_call(reports)
        if past_tips_call is None or timestamps_before_call is None:
            logging.info("Unable to construct past tips and timestamps before call")
            return None
        calls = past_tips_call + timestamps_before_call
        multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)()
        # remove values from dict since not needed
        return {key: multi_call[key] for key in multi_call if "before_values" not in key}

    def reward_claimed_status_call(self) -> Tuple[Optional[List[Call]], Optional[Dict[Tuple[str, str], List[int]]]]:
        feeds = self.get_valid_timestamps()
        if feeds is None:
            logging.info("No valid timestamps to check reward claimed status")
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
            logging.info("No reward claimed status call object constructed")
            return None
        response = Multicall(calls=calls, _w3=self.w3)()
        filtered_dict = {}

        for key in feeds:
            filtered_timestamps = [timestamp for claimed, timestamp in zip(response[key], feeds[key]) if not claimed]
            if filtered_timestamps:
                filtered_dict[key] = filtered_timestamps
        return filtered_dict


if __name__ == "__main__":
    from telliot_core.model.endpoints import RPCEndpoint
    import os
    from dotenv import load_dotenv

    load_dotenv()
    node = RPCEndpoint(
        network="mumbai",
        url=os.environ.get("NODE_URL"),
        chain_id=80001,
    )
    node.connect()

    class Account:
        address = "0xd5f1Cc896542C111c7Aa7D7fae2C3D654f34b927"

    tellor_autopay = Tellor360AutopayContract(node=node, account=Account)
    tellor_autopay.connect()
    apay_calls = AutopayCalls(autopay_contract=tellor_autopay)
    query_type = apay_calls.get_query_type(
        query_id="0x9026839f0ed5b30c73fd0a6046e3ade4e04c94c5e8c982089205109de74b0553"
    )
