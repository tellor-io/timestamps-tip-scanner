import logging
import os
from dataclasses import dataclass
from typing import List
from typing import Optional

from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3.contract import ContractFunction
from web3.exceptions import ContractLogicError

logger = logging.getLogger(__name__)


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
    cumulative: int


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


def gas_estimate(function_call: ContractFunction, account: LocalAccount) -> Optional[int]:
    """See if a transaction will by trying to estimate gas for a transaction"""
    try:
        return function_call.estimateGas({"from": account.address}, "latest")
    except ContractLogicError as e:
        logger.info(f"Contract logic error {function_call}: {e}")
        return None
