import os
from typing import Optional

from dotenv import load_dotenv
from eth_utils import to_checksum_address
from telliot_core.apps.telliot_config import TelliotConfig
from telliot_core.directory import contract_directory
from telliot_core.model.endpoints import RPCEndpoint
from web3 import Web3

from timestamps_tip_scanner.autopay_calls import AutopayCalls
from timestamps_tip_scanner.timestamps_scanner import run


print(f"env loaded: {load_dotenv()}")
node_url = os.getenv("NODE_URL", None)
cfg = TelliotConfig()


def w3_connection(chain_id: int) -> Web3:
    cfg.main.chain_id = chain_id
    endpoint = RPCEndpoint(chain_id=chain_id, url=node_url)
    if not endpoint.connect():
        raise Exception(f"Could not connect to endpoint {endpoint}")
    w3 = endpoint._web3
    return w3


def fetch_contract(chain_id: int, name: str):
    return contract_directory.find(chain_id=chain_id, name=name)[0]


def autopay(chain_id: int, wallet: str):
    w3 = w3_connection(chain_id)
    autopay_address = fetch_contract(chain_id, "tellor360-autopay").address[chain_id]
    return AutopayCalls(w3=w3, wallet=wallet, autopay_address=autopay_address)


def fetch_data(chain_id: int, address: str, starting_block: Optional[int]):
    w3 = w3_connection(chain_id=chain_id)
    contract_info = fetch_contract(chain_id, "tellor360-oracle")
    if not contract_info:
        raise Exception(f"Tellorflex not found in telliot on chain_id {chain_id}\nCheck supported tellor chain ids")
    abi = contract_info.get_abi(chain_id=chain_id)
    tellorflex_contract = w3.eth.contract(address=contract_info.address[chain_id], abi=abi)
    return run(
        w3=w3,
        tellorflex_contract=tellorflex_contract,
        chain_id=chain_id,
        reporter=to_checksum_address(address),
        starting_block=starting_block,
    )
