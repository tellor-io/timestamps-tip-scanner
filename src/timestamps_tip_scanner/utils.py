import os
import math
import json
from web3 import HTTPProvider
from web3 import Web3
from dataclasses import dataclass
from web3.contract import Contract


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


def fallback_input(_key: str):
    val = os.getenv(_key, None)
    if not val:
        return input(f"{_key}:\n")
    print(f"{_key} set!")
    return val


def one_time_tips(tips_lis: tuple, timestamp: int, timestamp_before: int):
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
    num_intervals = math.floor(
        (timestamp_to_check - feed_start_timestamp) / feed_interval
    )
    # Start time of latest submission window
    current_window_start = feed_start_timestamp + (feed_interval * num_intervals)
    if timestamp_before is None:
        timestamp_before = 0
    eligible = [
        (timestamp_to_check - current_window_start) < feed_window,
        timestamp_before < current_window_start,
    ]
    return all(eligible)


def evm_transaction(
    contract_factory: Contract,
    func_name: str,
    w3: Web3,
    wallet_address: str,
    private_key: str,
    gas_limit: int,
    **kwargs,
):
    gas = gas_limit
    gas_multiplier = int(os.getenv("GAS_MULTIPLIER", 2))

    wallet_nonce = w3.eth.get_transaction_count(wallet_address)
    txn_build = contract_factory.get_function_by_name(func_name)(
        **kwargs
    ).buildTransaction(
        dict(
            nonce=int(wallet_nonce),
            gasPrice=int(w3.eth.gas_price * gas_multiplier),
            gas=gas,
        )
    )
    signed_txn = w3.eth.account.signTransaction(txn_build, private_key)
    # Send the transaction
    transaction_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    transaction_hash = transaction_hash.hex()
    print(f"{func_name} txn: {transaction_hash}")
    receipt = w3.eth.wait_for_transaction_receipt(transaction_hash, timeout=480)
    return receipt


def autopay_factory(address: str, w3: Web3):
    with open("abi/autopay.json") as f:
        autopay_abi = json.load(f)

    return w3.eth.contract(address=address, abi=autopay_abi)


def w3_instance(node_url):

    provider = HTTPProvider(node_url)

    # Remove the default JSON-RPC retry middleware
    # as it correctly cannot handle eth_getLogs block range
    # throttle down.
    provider.middlewares.clear()

    return Web3(provider)
