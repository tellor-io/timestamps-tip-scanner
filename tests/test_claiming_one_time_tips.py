from unittest.mock import patch

from brownie import accounts
from brownie import chain
from telliot_feeds.feeds import btc_usd_median_feed
from telliot_feeds.feeds import eth_usd_median_feed
from telliot_feeds.feeds import ric_usd_median_feed
from telliot_feeds.feeds import trb_usd_median_feed
from web3 import Web3

from timestamps_tip_scanner.claims.single_tips import claim_single_tips
from timestamps_tip_scanner.timestamps_scanner import run


def test_single_tip(w3, autopay_contract, contracts, caplog):
    spec = eth_usd_median_feed
    keys = contracts.keys
    contracts.autopay.tip(spec.query.query_id, Web3.toWei(1, "ether"), spec.query.query_data, {"from": keys.reporter1})
    assert contracts.token.balanceOf(autopay_contract.address) == Web3.toWei(1, "ether")

    chain.mine(10, timedelta=1)
    contracts.tellorflex.submitValue(
        spec.query.query_id, Web3.toHex(1800), 0, spec.query.query_data, {"from": keys.reporter1}
    )
    submission_timestamp = chain.time()
    # run the scanner to fetch reported timestamps
    run(
        w3=w3,
        tellorflex_contract=contracts.tellorflex,
        reporter=keys.reporter1.address,
        chain_id=1337,
        starting_block=0,
    )
    with patch("timestamps_tip_scanner.autopay_calls.time", chain.time), patch(
        "timestamps_tip_scanner.jsonified_state.time", chain.time
    ), patch("timestamps_tip_scanner.event_scanner.time", chain.time):
        # attempt to claim before 12 hour wait period
        _ = claim_single_tips(w3, autopay_contract, keys.reporter1)
        assert "No eligible timestamps to claim for 0x33A4622B82D4c04a53e170c638B944ce27cffce3" in caplog.text
        # bypass the 12 hour wait period before claiming a tip
        chain.sleep(43201)
        _ = claim_single_tips(w3, autopay_contract, keys.reporter1)
        assert (
            "Claimed tip for 0x83a7f3d48786ac2667503a61e8c415438ed2922eb86a2906e4ee66d9a2ce4992 "
            f"and [{submission_timestamp}]"
        ) in caplog.text
        assert f"{keys.reporter1.address} claim transaction status: 1" in caplog.text


def test_multiple_reporters_submissions(w3, autopay_contract, contracts, caplog):
    keys = contracts.keys
    with patch("timestamps_tip_scanner.autopay_calls.time", chain.time), patch(
        "timestamps_tip_scanner.jsonified_state.time", chain.time
    ), patch("timestamps_tip_scanner.event_scanner.time", chain.time):
        i = 1
        for feed in (eth_usd_median_feed, trb_usd_median_feed, ric_usd_median_feed, btc_usd_median_feed):

            contracts.autopay.tip(
                feed.query.query_id, Web3.toWei(1, "ether"), feed.query.query_data, {"from": keys.user}
            )
            chain.mine(10, timedelta=1)
            contracts.tellorflex.submitValue(
                feed.query.query_id, Web3.toHex(1800), 0, feed.query.query_data, {"from": accounts[i]}
            )
            i += 1
        # run the scanner to fetch reported timestamps
        chain.sleep(86340)
        for i in range(1, 5):
            chain.mine(10, timedelta=1)
            run(
                w3=w3,
                tellorflex_contract=contracts.tellorflex,
                reporter=accounts[i].address,
                chain_id=1337,
                starting_block=0,
            )
            _ = claim_single_tips(w3, autopay_contract, getattr(keys, f"reporter{i}"))
            assert f"{accounts[i].address} claim transaction status: 1" in caplog.text
