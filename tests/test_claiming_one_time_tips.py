from unittest.mock import patch

from brownie import accounts
from brownie import chain
from hexbytes import HexBytes
from telliot_feeds.feeds import btc_usd_median_feed
from telliot_feeds.feeds import eth_usd_median_feed
from telliot_feeds.feeds import ric_usd_median_feed
from telliot_feeds.feeds import trb_usd_median_feed
from web3 import Web3

from timestamps_tip_scanner.autopay_calls import AutopayCalls
from timestamps_tip_scanner.claims.single_tips import claim_single_tips
from timestamps_tip_scanner.claims.single_tips import timestamps_to_claim
from timestamps_tip_scanner.timestamps_scanner import run


def test_single_tip(tellor_autopay, contracts, caplog):
    feed = eth_usd_median_feed
    keys = contracts.keys
    contracts.autopay.tip(feed.query.query_id, Web3.toWei(1, "ether"), feed.query.query_data, {"from": keys.reporter1})
    assert contracts.token.balanceOf(tellor_autopay.address) == Web3.toWei(1, "ether")

    chain.mine(10, timedelta=1)
    contracts.tellorflex.submitValue(
        feed.query.query_id, Web3.toHex(1800), 0, feed.query.query_data, {"from": keys.reporter1}
    )
    submission_timestamp = chain.time()
    # run the scanner to fetch reported timestamps
    run(
        w3=tellor_autopay.node._web3,
        tellorflex_contract=contracts.tellorflex,
        reporter=keys.reporter1.address,
        chain_id=1337,
        starting_block=0,
    )
    with patch("timestamps_tip_scanner.autopay_calls.time", chain.time), patch(
        "timestamps_tip_scanner.jsonified_state.time", chain.time
    ), patch("timestamps_tip_scanner.event_scanner.time", chain.time):
        # attempt to claim before 12 hour wait period
        tellor_autopay.account = keys.reporter1
        _ = claim_single_tips(tellor_autopay)
        assert "No eligible timestamps to claim for 0x33A4622B82D4c04a53e170c638B944ce27cffce3" in caplog.text
        # bypass the 12 hour wait period before claiming a tip
        chain.sleep(43201)
        _ = claim_single_tips(tellor_autopay)
        assert (
            "Claimed tip for 0x83a7f3d48786ac2667503a61e8c415438ed2922eb86a2906e4ee66d9a2ce4992 "
            f"and [{submission_timestamp}]"
        ) in caplog.text
        assert f"{keys.reporter1.address} claim transaction status: 1" in caplog.text


def test_multiple_reporters_submissions(tellor_autopay, contracts, caplog):
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
                w3=tellor_autopay.node._web3,
                tellorflex_contract=contracts.tellorflex,
                reporter=accounts[i].address,
                chain_id=1337,
                starting_block=0,
            )
            tellor_autopay.account = getattr(keys, f"reporter{i}")
            _ = claim_single_tips(tellor_autopay)
            assert f"{accounts[i].address} claim transaction status: 1" in caplog.text


def test_single_reporter_multiple_tips(contracts, tellor_autopay, caplog):
    """Test that multiple tips can be claimed"""
    tellorflex = contracts.tellorflex
    autopay = contracts.autopay
    keys = contracts.keys
    w3 = tellor_autopay.node._web3
    tellor_autopay.account = keys.reporter1
    # tip 1 and submission
    query = btc_usd_median_feed.query
    autopay.tip(query.query_id, Web3.toWei(1, "ether"), query.query_data, {"from": keys.user})
    # advance block chain
    chain.mine(timedelta=1)
    tellorflex.submitValue(query.query_id, Web3.toHex(1800), 0, query.query_data, {"from": keys.reporter1})

    # tip 2 and submission
    query = eth_usd_median_feed.query
    autopay.tip(query.query_id, Web3.toWei(1, "ether"), query.query_data, {"from": keys.user})
    # bypass 12 hour wait period
    chain.sleep(43201)
    tellorflex.submitValue(query.query_id, Web3.toHex(1800), 0, query.query_data, {"from": keys.reporter1})
    # advance block chain
    chain.mine(timedelta=1)
    # tip 3 and submission
    query = ric_usd_median_feed.query
    autopay.tip(query.query_id, Web3.toWei(1, "ether"), query.query_data, {"from": keys.user})
    # bypass 12 hour wait period
    chain.sleep(43201)
    tellorflex.submitValue(query.query_id, Web3.toHex(1800), 0, query.query_data, {"from": keys.reporter1})
    # advance block chain
    chain.mine(timedelta=1)
    # scan for reported timestamps
    scan = run(
        w3=w3,
        tellorflex_contract=contracts.tellorflex,
        reporter=keys.reporter1.address,
        chain_id=1337,
        starting_block=0,
    )
    reports = scan.state["localhost"][keys.reporter1.address]
    assert reports["last_scanned_block"] == w3.eth.blockNumber - 1
    assert HexBytes(btc_usd_median_feed.query.query_id).hex() in reports
    assert HexBytes(eth_usd_median_feed.query.query_id).hex() in reports
    assert HexBytes(ric_usd_median_feed.query.query_id).hex() in reports
    # hack time to be same as block timestamp
    with patch("timestamps_tip_scanner.autopay_calls.time", chain.time), patch(
        "timestamps_tip_scanner.jsonified_state.time", chain.time
    ), patch("timestamps_tip_scanner.event_scanner.time", chain.time):
        # claim single tips
        # bypass 12 hour wait period
        chain.sleep(43201)
        tips_to_claim = timestamps_to_claim(AutopayCalls(tellor_autopay))
        assert HexBytes(btc_usd_median_feed.query.query_id).hex() in tips_to_claim[0]
        assert HexBytes(eth_usd_median_feed.query.query_id).hex() in tips_to_claim[1]
        assert HexBytes(ric_usd_median_feed.query.query_id).hex() in tips_to_claim[2]
        _ = claim_single_tips(tellor_autopay)

        assert f"Claimed tip for {HexBytes(btc_usd_median_feed.query.query_id).hex()}" in caplog.text
        assert f"Claimed tip for {HexBytes(eth_usd_median_feed.query.query_id).hex()}" in caplog.text
        assert f"Claimed tip for {HexBytes(ric_usd_median_feed.query.query_id).hex()}" in caplog.text
