from collections import namedtuple
from dataclasses import dataclass

import pytest
from brownie import accounts
from brownie import Autopay
from brownie import chain
from brownie import Governance
from brownie import multicall
from brownie import QueryDataStorage
from brownie import TellorFlex
from brownie import Token
from brownie import web3
from chained_accounts import ChainedAccount
from eth_account import Account
from hexbytes import HexBytes
from multicall.constants import MULTICALL2_ADDRESSES
from multicall.constants import Network
from multicall.constants import NO_STATE_OVERRIDE
from telliot_core.directory import ContractInfo
from telliot_core.model.endpoints import RPCEndpoint
from telliot_core.tellor.tellor360.autopay import contract_directory
from telliot_core.tellor.tellor360.autopay import Tellor360AutopayContract

from timestamps_tip_scanner.constants import CHAIN_ID_MAPPING
from timestamps_tip_scanner.jsonified_state import JSONifiedState
from timestamps_tip_scanner.logger import setup_logger

CHAIN_ID_MAPPING[1337] = {"name": "localhost"}
setup_logger()

contract = namedtuple("contract", "tellorflex autopay token querydatastorage keys")


@pytest.fixture(scope="module", autouse=True)
def reset_chain(chain):
    chain.reset()


@pytest.fixture(scope="function", autouse=True)
def remove_jsonified_state_file():
    JSONifiedState.delete_file()


@pytest.fixture(scope="function")
def contracts():
    """Deploy all contracts in tellor and return contract instances"""
    # mock token contract
    token = accounts[0].deploy(Token)
    # oracle contract
    tellorflex = accounts[0].deploy(
        TellorFlex,
        token.address,
        43200,
        web3.toWei(100, "ether"),
        web3.toWei(15, "ether"),
        web3.toWei(10, "ether"),
        HexBytes("0x5c13cd9c97dbb98f2429c101a2a8150e6c7a0ddaff6124ee176a3a411067ded0"),
    )
    # governance contract
    governance = accounts[0].deploy(Governance, tellorflex.address, token.address)
    # query data storage contract (store query data to query id mapping)
    querydatastorage = accounts[0].deploy(QueryDataStorage)
    # autopay contract
    autopay = accounts[0].deploy(Autopay, tellorflex.address, querydatastorage.address, 20)
    # multicall contract for making multicalls to fetch data from contracts in batch
    multi_call = multicall.deploy({"from": accounts[0]})
    # set Brownie network to be supported by multicall package
    Network.Brownie = 1337
    MULTICALL2_ADDRESSES[Network.Brownie] = multi_call.address
    NO_STATE_OVERRIDE.append(Network.Brownie)
    # advance block cause erros get blurted even when deployments are successful
    chain.mine(1)
    # initialize oracle by passing governance address
    tellorflex.init(governance.address)

    for acct in range(1, 7):
        # mint tokens to five accounts
        token.mint(accounts[acct], web3.toWei(10000, "ether"), {"from": accounts[0]})
        # approve tellorflex spending for all five accounts
        token.approve(tellorflex.address, web3.toWei(10000, "ether"), {"from": accounts[acct]})
        # deposit stake for all five accounts
        tellorflex.depositStake(web3.toWei(9000, "ether"), {"from": accounts[acct]})
        # approve autopay spending for all five accounts
        token.approve(autopay.address, web3.toWei(10000, "ether"), {"from": accounts[acct]})
        # assert remaining balance
        assert token.balanceOf(accounts[acct]) == web3.toWei(1000, "ether")

    return contract(tellorflex, autopay, token, querydatastorage, BrownieAccounts())


class CustomAccount:
    """Wrapper class for brownie and eth_account accounts for easy access to both"""

    def __init__(self, private_key):
        # both return LocalAccount but have different methods
        self.local_account = Account.from_key(private_key)
        self.brownie_account = accounts.add(private_key)

    def __getattr__(self, name):
        if hasattr(self.local_account, name):
            return getattr(self.local_account, name)
        if hasattr(self.brownie_account, name):
            return getattr(self.brownie_account, name)


@dataclass
class BrownieAccounts:
    # default "brownie" mnemonic accounts
    owner = CustomAccount("0xbbfbee4961061d506ffbb11dfea64eba16355cbf1d9c29613126ba7fec0aed5d")
    reporter1 = CustomAccount("0x804365e293b9fab9bd11bddd39082396d56d30779efbb3ffb0a6089027902c4a")
    reporter2 = CustomAccount("0x1f52464c2fb44e9b7e0808f2c5fe56d87b73eb3bca0e72c66f9f74d7c6c9a81f")
    reporter3 = CustomAccount("0x905e216d8acdabbd095f11162327c5e6e80cc59a51283732cd4fe1299b33b7a6")
    reporter4 = CustomAccount("0xe21bbdc4c57125bec3e05467423dfc3da8754d862140550fc7b3d2833ad1bdeb")
    reporter5 = CustomAccount("0xb591fb79dd7065964210e7e527c87f97523da07ef8d16794f09750d5eef959b5")
    # accounts[6]
    user = CustomAccount("0xfe613f76efbfd03a16624ed8d96777966770f353e83d6f7611c11fdfcdfa48d1")


@pytest.fixture(scope="function")
def tellor_autopay(contracts):
    entry_name = "tellor360-autopay"  # Replace this with the actual name of the contract you want to modify
    original_entry = contract_directory.entries[entry_name]

    modified_entry = ContractInfo(
        name=original_entry.name,
        org=original_entry.org,
        address={**original_entry.address, 1337: contracts.autopay.address},
        abi_file=original_entry.abi_file,
    )
    contract_directory.entries[entry_name] = modified_entry
    account = ChainedAccount("timestamps_tip_scanner_account_0")
    node = RPCEndpoint(
        url="http://localhost:8545",
        network="brownie",
        chain_id=1337,
    )
    node.connect()
    autopay = Tellor360AutopayContract(node=node, account=account)

    autopay.connect()
    return autopay


@pytest.fixture(scope="module", autouse=True)
def accts():
    accounts = [
        "timestamps_tip_scanner_account_0",
        "timestamps_tip_scanner_account_1",
        "timestamps_tip_scanner_account_2",
        "timestamps_tip_scanner_account_3",
        "timestamps_tip_scanner_account_4",
        "timestamps_tip_scanner_account_5",
        "timestamps_tip_scanner_account_6",
    ]
    for acct in accounts:
        account = ChainedAccount(acct)
        if account.keyfile.exists():
            continue
        ChainedAccount.add(acct, 1337, PKMAPPING[acct], "")

    yield
    # delete accounts after tests are finished
    for acct in accounts:
        account = ChainedAccount(acct)
        if not account.keyfile.exists():
            continue
        account.delete()


PKMAPPING = {
    "timestamps_tip_scanner_account_0": "0xbbfbee4961061d506ffbb11dfea64eba16355cbf1d9c29613126ba7fec0aed5d",
    "timestamps_tip_scanner_account_1": "0x804365e293b9fab9bd11bddd39082396d56d30779efbb3ffb0a6089027902c4a",
    "timestamps_tip_scanner_account_2": "0x1f52464c2fb44e9b7e0808f2c5fe56d87b73eb3bca0e72c66f9f74d7c6c9a81f",
    "timestamps_tip_scanner_account_3": "0x905e216d8acdabbd095f11162327c5e6e80cc59a51283732cd4fe1299b33b7a6",
    "timestamps_tip_scanner_account_4": "0xe21bbdc4c57125bec3e05467423dfc3da8754d862140550fc7b3d2833ad1bdeb",
    "timestamps_tip_scanner_account_5": "0xb591fb79dd7065964210e7e527c87f97523da07ef8d16794f09750d5eef959b5",
    "timestamps_tip_scanner_account_6": "0xfe613f76efbfd03a16624ed8d96777966770f353e83d6f7611c11fdfcdfa48d1",
}
