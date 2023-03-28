import json
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from eth_utils.typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import HTTPProvider
from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt


@dataclass
class Args:
    _reporter: ChecksumAddress
    _time: int
    _queryId: HexBytes


@dataclass
class EventData:
    address: ChecksumAddress
    args: Args
    blockHash: HexBytes
    blockNumber: int
    event: str
    logIndex: int
    transactionHash: HexBytes
    transactionIndex: int


@dataclass
class FeedDetails:
    """Data types for feed details contract response"""

    reward: int
    balance: int
    startTime: int
    interval: int
    window: int
    priceThreshold: int
    rewardIncreasePerSecond: int
    feedsWithFundingIndex: int


@dataclass
class Tip:
    """Data type for tips struct in autopay contract"""

    amount: int
    timestamp: int


def fallback_input(_key: str) -> str:
    val = os.getenv(_key, None)
    if not val:
        return input(f"{_key}:\n")
    print(f"{_key} set!")
    return val


def one_time_tips(tips_lis: List[int], timestamp: int, timestamp_before: int) -> bool:
    """Check timestamps for one time tips"""
    count = len(tips_lis)
    if count > 0:
        mini = 0
        maxi = count
        while maxi - mini > 1:
            mid = int((maxi + mini) / 2)
            tip_mid = Tip(*tips_lis[mid])
            if tip_mid.timestamp > timestamp:
                maxi = mid
            else:
                mini = mid
        tips = Tip(*tips_lis[mini])
        if timestamp_before is None:
            return True
        conditions = (
            timestamp_before < tips.timestamp,
            timestamp > tips.timestamp,
            tips.amount > 0,
        )
        return all(conditions)
    return False


def is_timestamp_first_in_window(
    timestamp_before: int,
    timestamp_to_check: int,
    feed_start_timestamp: int,
    feed_window: int,
    feed_interval: int,
) -> bool:
    """
    Calculates to check if timestamp(timestamp_to_check) is first in window

    Return: bool
    """
    # Number of intervals since start time
    num_intervals = math.floor((timestamp_to_check - feed_start_timestamp) / feed_interval)
    # Start time of latest submission window
    current_window_start = feed_start_timestamp + (feed_interval * num_intervals)
    if timestamp_before is None:
        timestamp_before = 0
    eligible = [
        (timestamp_to_check - current_window_start) < feed_window,
        timestamp_before < current_window_start,
    ]
    return all(eligible)
