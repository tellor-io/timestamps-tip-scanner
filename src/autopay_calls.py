import asyncio
from concurrent.futures import ThreadPoolExecutor
from eth_typing.evm import ChecksumAddress

from web3 import Web3
from multicall import multicall, Multicall, Call
from multicall.constants import Network, MULTICALL2_ADDRESSES, MULTICALL_ADDRESSES
from typing import Any, Dict

# add testnet support for multicall that aren't avaialable in the package
Network.Mumbai = 80001
MULTICALL_ADDRESSES[Network.Mumbai] = MULTICALL2_ADDRESSES[
    Network.Mumbai
] = "0x35583BDef43126cdE71FD273F5ebeffd3a92742A"
Network.ArbitrumRinkeby = 421611
MULTICALL_ADDRESSES[Network.ArbitrumRinkeby] = MULTICALL2_ADDRESSES[
    Network.ArbitrumRinkeby
] = "0xf609687230a65E8bd14caceDEfCF2dea9c15b242"
Network.OptimismKovan = 69
MULTICALL_ADDRESSES[Network.OptimismKovan] = MULTICALL2_ADDRESSES[
    Network.OptimismKovan
] = "0xf609687230a65E8bd14caceDEfCF2dea9c15b242"


async def run_in_subprocess(coro: Any, *args: Any, **kwargs: Any) -> Any:
    """Use ThreadPoolExecutor to execute tasks"""
    return await asyncio.get_event_loop().run_in_executor(
        ThreadPoolExecutor(16), coro, *args, **kwargs
    )


# Multicall interface uses ProcessPoolExecutor which leaks memory and breaks when used for the tip listener
# switching to use ThreadPoolExecutor instead seems to fix that
multicall.run_in_subprocess = run_in_subprocess


class AutopayCalls:
    def __init__(
        self, query_ids: Dict[str, int], w3: Web3, autopay_address: ChecksumAddress
    ) -> None:
        self.w3 = w3
        self.query_ids = query_ids
        self.autopay_address = autopay_address

    # {"last_scanned_block": {EOA: {"query_id": [timestamps]}}
    async def get_feed_ids(self):
        """Returns feed ids for every query id"""
        if self.query_ids:
            calls = [
                Call(
                    self.autopay_address,
                    ["getCurrentFeeds(bytes32)(bytes32[])", bytes.fromhex(query_id[2:])],
                    [[query_id, None]],
                )

                for query_id in self.query_ids
                
            ]
            multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)
            data = await multi_call.coroutine()

            return data
        else:
            return None

    async def get_feed_details(self) -> Any:
        """Returns feed details for all feed Ids"""
        # store them like this {(query_id, feed_id): details}
        feed_ids: dict = await self.get_feed_ids()
        if feed_ids:
            calls = [
                Call(
                    self.autopay_address,
                    [
                        "getDataFeed(bytes32)((uint256,uint256,uint256,uint256,uint256,uint256,uint256))",
                        feed_id,
                    ],
                    [[(query_id, feed_id), None]],
                )
                for query_id, feeds in feed_ids.items()
                for feed_id in feeds
                if len(feeds) > 0
            ]
            multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)
            data = await multi_call.coroutine()
            return data
        else:
            return None

    async def get_timestamps_before(self) -> Any:
        """Get timestamps before"""
        if self.query_ids:
            calls = [
                Call(
                    self.autopay_address,
                    [
                        "getDataBefore(bytes32,uint256)(bool,bytes,uint256)",
                        bytes.fromhex(query_id[2:]),
                        timestamp,
                    ],
                    [
                        ["disregard", None],
                        ["disregard", None],
                        [(query_id, timestamp), None],
                    ],
                )
                for query_id, timestamps in self.query_ids.items()
                for timestamp in timestamps
            ]
            multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)
            data = await multi_call.coroutine()
            data.pop("disregard")
            return data
        else:
            return None

    async def get_past_tips(self) -> Any:
        """get past tips from autopay"""
        if self.query_ids:
            calls = [
                Call(
                    self.autopay_address,
                    [
                        "getPastTips(bytes32)((uint256,uint256)[])",
                        bytes.fromhex(query_id[2:]),
                    ],
                    [[query_id, None]],
                )
                for query_id in self.query_ids
            ]
            multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)
            data = await multi_call.coroutine()
            return data
        return None

    async def get_reward_claimed_status(self, timestamps: list) -> Any:
        """check if a reported timestamp has already claimed"""
        calls = [
            Call(
                self.autopay_address,
                [
                    "getRewardClaimedStatus(bytes32,bytes32,uint256)(bool)",
                    int(timestamp),
                ],
                [[timestamp, None]],
            )
            for timestamp in timestamps
        ]
        multi_call = Multicall(calls=calls, _w3=self.w3, require_success=True)
        data = await multi_call.coroutine()
        return data


if __name__ == "__main__":
    print(__name__)
