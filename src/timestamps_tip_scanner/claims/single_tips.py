import logging
from typing import Dict
from typing import List
from typing import Optional

from telliot_core.tellor.tellor360.autopay import Tellor360AutopayContract

from timestamps_tip_scanner.autopay_calls import AutopayCalls
from timestamps_tip_scanner.utils import gas_estimate
from timestamps_tip_scanner.utils import one_time_tips


def timestamps_to_claim(apay: AutopayCalls) -> Optional[List[Dict[str, List[int]]]]:
    reports_dict = apay.unwanted_timestamps_removed_for_singles()
    if reports_dict is None:
        logging.info("No reports found to check tips for")
        return None
    dic = apay.get_past_tips_and_timestamps_before()
    if dic is None:
        logging.info("No past tips found to check timestamps for")
        return None
    to_claim_lis = []
    for query_id, timestamps in reports_dict.items():
        tips_lis = dic[("past_tips", query_id)]
        to_claim: Dict[str, List[int]] = {query_id: []}
        for timestamp in timestamps:
            timestamp_before = dic[("timestamps", query_id, timestamp)]
            is_valid = one_time_tips(tips_lis=tips_lis, timestamp=timestamp, timestamp_before=timestamp_before)
            if is_valid:
                to_claim[query_id].append(timestamp)
        if to_claim[query_id]:
            to_claim_lis.append(to_claim)
    return to_claim_lis


def claim_single_tips(tellor_autopay: Tellor360AutopayContract) -> None:
    """Claim tips for eligible OneTimeTips in Autopay contract"""
    account = tellor_autopay.account.local_account
    w3 = tellor_autopay.node._web3
    tip_eligible_reports = timestamps_to_claim(AutopayCalls(tellor_autopay))
    if not tip_eligible_reports:
        logging.info(f"No eligible timestamps to claim for {account.address}")
        return None
    for tip_eligible_report in tip_eligible_reports:
        for query_id, timestamps in tip_eligible_report.items():
            function = tellor_autopay.contract.get_function_by_name("claimOneTimeTip")
            function_call = function(_queryId=query_id, _timestamps=timestamps)
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
            logging.info(f"Claimed tip for {query_id} and {timestamps}")
            logging.info(f"Tx hash: {tx_hash.hex()}")
            logging.info(f"{account.address} claim transaction status: {receipt['status']}")
