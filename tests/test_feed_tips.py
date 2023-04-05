from unittest.mock import patch

import pytest
from brownie import chain
from telliot_feeds.feeds import matic_usd_median_feed
from web3 import Web3

from timestamps_tip_scanner.claims.feed_tips import claim_tips
from timestamps_tip_scanner.timestamps_scanner import run


startTime = chain.time()
window = 180
interval = 3600
reward = int(0.5 * 1e18)
priceThreshold = 50
rewardIncreasePerSecond = int(0.01 * 1e18)
amount = int(1e18)
feed = matic_usd_median_feed


@pytest.fixture(scope="function")
def setupDataFeed(contracts):
    contracts.autopay.setupDataFeed(
        feed.query.query_id,
        reward,
        startTime,
        interval,
        window,
        priceThreshold,
        rewardIncreasePerSecond,
        feed.query.query_data,
        amount,
        {"from": contracts.keys.user},
    )


def test_claim_feed_tips(w3, autopay_contract, setupDataFeed, contracts, caplog):
    """Test claiming feed tips after submitting a report"""
    with patch("timestamps_tip_scanner.autopay_calls.time", chain.time), patch(
        "timestamps_tip_scanner.jsonified_state.time", chain.time
    ), patch("timestamps_tip_scanner.event_scanner.time", chain.time):
        keys = contracts.keys
        # submit value from reporter-1
        contracts.tellorflex.submitValue(
            feed.query.query_id, Web3.toHex(1800), 0, feed.query.query_data, {"from": keys.reporter1}
        )
        chain.mine(timedelta=1)
        # submit value from reporter-2
        contracts.tellorflex.submitValue(
            feed.query.query_id, Web3.toHex(1800), 0, feed.query.query_data, {"from": keys.reporter2}
        )
        # bypass wait period to claim
        chain.sleep(43202)
        #  run scanner to fetch reported timestamps
        run(
            w3=w3,
            tellorflex_contract=contracts.tellorflex,
            reporter=keys.reporter1.address,
            chain_id=1337,
            starting_block=0,
        )
        # claim eligible tip should be 1
        claim_tips(
            w3=w3,
            autopay_contract=autopay_contract,
            account=keys.reporter1,
        )
        assert f"{keys.reporter1.address} claim transaction status: 1" in caplog.text
        # try to claim same reporter again should not be eligible
        claim_tips(
            w3=w3,
            autopay_contract=autopay_contract,
            account=keys.reporter1,
        )
        assert f"No eligible timestamps to claim for {keys.reporter1.address}" in caplog.text
        # try to claim for second reporter in with same window report should not be eligible
        run(
            w3=w3,
            tellorflex_contract=contracts.tellorflex,
            reporter=keys.reporter2.address,
            chain_id=1337,
            starting_block=0,
        )
        claim_tips(
            w3=w3,
            autopay_contract=autopay_contract,
            account=keys.reporter2,
        )
        assert f"No eligible timestamps to claim for {keys.reporter2.address}" in caplog.text
