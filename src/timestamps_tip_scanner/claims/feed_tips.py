import logging

import click
from telliot_core.tellor.tellor360.autopay import Tellor360AutopayContract

from timestamps_tip_scanner.autopay_calls import AutopayCalls
from timestamps_tip_scanner.utils import gas_estimate

logger = logging.getLogger(__name__)


def claim_tips(autopay_contract: Tellor360AutopayContract) -> None:
    """Claim tips for eligible feed tips in Autopay contract"""
    account = autopay_contract.account.local_account
    autopay = AutopayCalls(autopay_contract=autopay_contract)
    w3 = autopay_contract.node._web3
    claim_tip_params = autopay.reward_claimed_status_check()
    if not claim_tip_params:
        logger.info(f"No eligible timestamps to claim for {account.address}")
        return None
    for feed_id, query_id in claim_tip_params:
        timestamps = claim_tip_params[(feed_id, query_id)]
        function = autopay_contract.contract.get_function_by_name("claimTip")
        function_call = function(_feedId=feed_id, _queryId=query_id, _timestamps=timestamps)
        gas = gas_estimate(function_call, account)
        if not gas:
            continue
        tx = function_call.buildTransaction(
            {
                "gas": int(gas * 1.2),
                "nonce": w3.eth.get_transaction_count(account.address),
                "gasPrice": w3.eth.gas_price,
            }
        )
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Claimed tip for {feed_id}-{query_id} and {timestamps}")
        click.echo(f"Tx hash: {tx_hash.hex()}")
        logging.info(f"{account.address} claim transaction status: {receipt['status']}")
