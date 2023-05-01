from unittest.mock import patch

from brownie import chain
from telliot_feeds.feeds import matic_usd_median_feed
from web3 import Web3

from timestamps_tip_scanner.claims.feed_tips import claim_tips
from timestamps_tip_scanner.timestamps_scanner import run

window = 180
interval = 3600
reward = int(0.5 * 1e18)
priceThreshold = 50
rewardIncreasePerSecond = int(0.01 * 1e18)
amount = int(10e18)
feed = matic_usd_median_feed


def test_claim_feed_tips(tellor_autopay, contracts, caplog):
    """Test claiming feed tips after submitting a report"""

    # setup a datafeed
    contracts.autopay.setupDataFeed(
        feed.query.query_id,
        reward,
        chain.time(),  # startTime
        interval,
        window,
        priceThreshold,
        rewardIncreasePerSecond,
        feed.query.query_data,
        amount,
        {"from": contracts.keys.user.address},
    ), "setupDataFeed"
    # mock.patch time to be chain.time
    with patch("timestamps_tip_scanner.autopay_calls.time", chain.time), patch(
        "timestamps_tip_scanner.jsonified_state.time", chain.time
    ), patch("timestamps_tip_scanner.event_scanner.time", chain.time):
        keys = contracts.keys

        # submit value from reporter-1
        contracts.tellorflex.submitValue(
            feed.query.query_id, Web3.toHex(1800), 0, feed.query.query_data, {"from": keys.reporter1}
        )
        # advance chain by 1 block
        chain.mine(timedelta=1)
        # submit value from reporter-2
        contracts.tellorflex.submitValue(
            feed.query.query_id, Web3.toHex(1800), 0, feed.query.query_data, {"from": keys.reporter2}
        )
        # bypass wait period to claim
        chain.sleep(43202)
        #  run scanner to fetch reported timestamps
        run(
            w3=tellor_autopay.node._web3,
            tellorflex_contract=contracts.tellorflex,
            reporter=keys.reporter1.address,
            chain_id=1337,
            starting_block=0,
        )
        # set Tellor360Autopay account to reporter-1
        tellor_autopay.account = keys.reporter1
        # claim tips for reporter-1 should be 1 and successful
        claim_tips(
            autopay_contract=tellor_autopay,
        )
        assert f"{keys.reporter1.address} claim transaction status: 1" in caplog.text
        # try to claim same reporter again should not be eligible
        claim_tips(
            autopay_contract=tellor_autopay,
        )
        assert f"No eligible timestamps to claim for {keys.reporter1.address}" in caplog.text
        # try to claim for second reporter in with same window report should not be eligible
        run(
            w3=tellor_autopay.node._web3,
            tellorflex_contract=contracts.tellorflex,
            reporter=keys.reporter2.address,
            chain_id=1337,
            starting_block=0,
        )
        tellor_autopay.account = keys.reporter2
        claim_tips(
            autopay_contract=tellor_autopay,
        )
        assert f"No eligible timestamps to claim for {keys.reporter2.address}" in caplog.text

        # submit value from reporter-2 that meets the threshold
        contracts.tellorflex.submitValue(
            feed.query.query_id, Web3.toHex(1), 0, feed.query.query_data, {"from": keys.reporter2}
        )
        # bypass wait period to claim
        chain.sleep(43201)
        run(
            w3=tellor_autopay.node._web3,
            tellorflex_contract=contracts.tellorflex,
            reporter=keys.reporter2.address,
            chain_id=1337,
            starting_block=0,
        )
        claim_tips(
            autopay_contract=tellor_autopay,
        )
        assert f"{keys.reporter2.address} claim transaction status: 1" in caplog.text
