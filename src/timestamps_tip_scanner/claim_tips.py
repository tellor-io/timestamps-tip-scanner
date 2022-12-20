import os
import ast
from timestamps_tip_scanner.utils import fallback_input
from timestamps_tip_scanner.utils import autopay_factory
from timestamps_tip_scanner.utils import evm_transaction
from timestamps_tip_scanner.utils import w3_instance
from dotenv import load_dotenv
from dataclasses import dataclass

print(f"env loaded: {load_dotenv()}")


@dataclass
class ClaimTips:
    reporter: str = None
    pk: str = None
    autopay_address: str = None
    contract: str = None
    query_id: str = None
    timestamps: list = None

    def __post_init__(self) -> None:
        self.reporter, self.w3 = w3_instance()
        self.pk = fallback_input("PRIVATE_KEY")
        self.autopay_address = fallback_input("AUTOPAY_ADDRESS")
        self.contract = autopay_factory(self.autopay_address, self.w3)
        print("Enter query id (example: 0x40aa71e5205fdc7bdb7d65f7ae41daca3820c5d3a8f62357a99eda3aa27244a3):")
        self.query_id = input()
        print("Enter list of timestamps (example: [1660320062]):")
        self.timestamps = input()
        self.timestamps = list(ast.literal_eval(self.timestamps))

    def claim_one_time_tip(self):
        return evm_transaction(
            contract_factory=self.contract,
            func_name="claimOneTimeTip",
            w3=self.w3,
            wallet_address=self.reporter,
            private_key=self.pk,
            _queryId=self.query_id,
            _timestamps=self.timestamps,
        )

    def claim_feed_tips(self):
        print("Enter feed id (example: 0x7758ba9b140c3b91500e0a61f383147cd01e4a548be6ecb357f355f279271881):")
        feed_id = input()
        return evm_transaction(
            contract_factory=self.contract,
            func_name="claimTip",
            w3=self.w3,
            wallet_address=self.reporter,
            private_key=self.pk,
            gas_limit=int(len(self.timestamps) * 100000 + 200000),
            _feedId=feed_id,
            _queryId=self.query_id,
            _timestamps=self.timestamps,
        )


def claim_txns():

    print(
        "Make a selection:\nEnter (1) for claiming one time tips\nEnter (2) for claiming feed tips"
    )

    choice = None
    while choice is None:
        user_input = input()
        try:
            user_input = int(user_input)
            claim = ClaimTips()
        except ValueError:
            print("Please choose a number between 1 and 2")
            continue
        if user_input == 1:
            choice = claim.claim_one_time_tip()
        elif user_input == 2:
            choice = claim.claim_feed_tips()

    if choice["status"] == 1:
        print("Transaction Succeeded!")
    elif choice["status"] == 0:
        print("Transaction Failed!")
    return choice


claim_txns()
