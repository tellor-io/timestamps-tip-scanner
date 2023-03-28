import logging
from typing import Dict, List, Optional

from web3 import Web3
from web3.contract import Contract, ContractFunction
from eth_account.signers.local import LocalAccount
from web3.exceptions import ContractLogicError
from timestamps_tip_scanner.autopay_calls import AutopayCalls
from timestamps_tip_scanner.utils import one_time_tips

logger = logging.getLogger(__name__)


def timestamps_to_claim(apay: AutopayCalls) -> Optional[List[Dict[str, List[int]]]]:
    reports_dict = apay.read_reports()
    if reports_dict is None:
        logger.info("No reports found to check tips for")
        return None
    dic = apay.get_past_tips_and_timestamps_before()

    to_claim_lis = []
    for query_id, timestamps in reports_dict.items():
        tips_lis = dic[("past_tips", query_id)]
        to_claim: Dict[str, List[int]] = {query_id: []}
        for timestamp in timestamps:
            timestamp_before = dic[(query_id, timestamp)]
            is_valid = one_time_tips(
                tips_lis=tips_lis, timestamp=timestamp, timestamp_before=timestamp_before
            )
            if is_valid:
                to_claim[query_id].append(timestamp)
        if to_claim[query_id]:
            to_claim_lis.append(to_claim)
    return to_claim_lis


def claim_single_tips(w3: Web3, contract: Contract, account: LocalAccount) -> None:
    tip_eligible_reports = timestamps_to_claim(AutopayCalls(w3, account.address, contract.address))
    if not tip_eligible_reports:
        logger.info(f"No eligible timestamps to claim for {account.address}")
        return None
    for tip_eligible_report in tip_eligible_reports:
        for query_id, timestamps in tip_eligible_report.items():
            if not timestamps:
                logger.info(f"No eligible timestamps to claim for query id: {query_id}")
                continue
            function = contract.get_function_by_name("claimOneTimeTip")
            function_call: ContractFunction = function(_queryId=query_id, _timestamps=timestamps)
            try:
                gas = function_call.estimateGas({"from": account.address}, "latest")
            except ContractLogicError as e:
                logger.info(f"Contract logic error for {query_id}-{timestamps}, error: {e}")
                continue
            tx = function_call.buildTransaction(
                {
                    "gas": gas,
                    "nonce": w3.eth.get_transaction_count(account.address),
                    "gasPrice": w3.eth.gas_price,
                }
            )
            signed_tx = account.sign_transaction(tx)  # type: ignore
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            w3.eth.wait_for_transaction_receipt(tx_hash)
            w3.middleware_onion.clear()
            logger.info(f"Claimed tip for {query_id} and {timestamps}")
            logger.info(f"Tx hash: {tx_hash.hex()}")
