import logging

from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract import Contract
from web3.contract import ContractFunction
from web3.exceptions import ContractLogicError

from timestamps_tip_scanner.autopay_calls import AutopayCalls

logger = logging.getLogger(__name__)


def claim_tips(w3: Web3, autopay_contract: Contract, account: LocalAccount) -> None:
    """Claim tips for eligible feed tips in Autopay contract"""
    autopay = AutopayCalls(w3=w3, wallet=account.address, autopay_address=autopay_contract.address)
    claim_tip_params = autopay.reward_claimed_status_check()
    if not claim_tip_params:
        logger.info(f"No eligible timestamps to claim for {account.address}")
        return None
    for feed_id, query_id in claim_tip_params:
        timestamps = claim_tip_params[(feed_id, query_id)]
        function = autopay_contract.get_function_by_name("claimTip")
        function_call: ContractFunction = function(_feedId=feed_id, _queryId=query_id, _timestamps=timestamps)
        try:
            gas = function_call.estimateGas({"from": account.address}, "latest")
        except ContractLogicError as e:
            logger.info(f"Contract logic error for {feed_id}-{query_id}-{timestamps}, error: {e}")
            continue
        tx = function_call.buildTransaction(
            {
                "gas": gas,  # type: ignore
                "nonce": w3.eth.get_transaction_count(account.address),
                "gasPrice": w3.eth.gas_price,
            }
        )
        signed_tx = account.sign_transaction(tx)  # type: ignore
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        w3.middleware_onion.clear()
        logger.info(f"Claimed tip for {feed_id}-{query_id} and {timestamps}")
        logger.info(f"Tx hash: {tx_hash.hex()}")
