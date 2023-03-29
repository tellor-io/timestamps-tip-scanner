# import asyncio
from typing import Optional

import click
from chained_accounts import find_accounts
from eth_utils import to_checksum_address
from eth_utils.typing import ChecksumAddress
from telliot_core.apps.telliot_config import TelliotConfig
from telliot_core.directory import contract_directory

from timestamps_tip_scanner.timestamps_scanner import run


cfg = TelliotConfig()


@click.command()
@click.argument("chain_id", type=int)
@click.option("--account", "-a", help="Account name, required if address not selected")
@click.option("--start-block", "-sb", type=int, default=None, help="block num to start scanning from.")
@click.option("--address", "-addy", help="wallet address, required if account not selected")
def scan(chain_id: int, account: str, address: ChecksumAddress, start_block: Optional[int]) -> None:
    """
    CHAIN ID: desired chain to scan

    ACCOUNT: chained account name to use

    ADDRESS: wallet address

    START BLOCK: block num to start scanning from.
    """
    if not address and not account:
        raise click.BadOptionUsage(option_name="address/account", message="address or account name required")

    if account and address:
        raise click.BadOptionUsage(
            option_name="address/account",
            message="address and account name cannot be used together, please select one or the other",
        )

    if address:
        address = to_checksum_address(address)

    if account:
        accounts = find_accounts(account)
        if not accounts:
            click.echo(
                f"No account found named: '{account}'.\n"
                "Either use -addy flag or add one with the account subcommand.\n"
                "For more info run: `telliot account add --help`"
            )
            raise click.BadOptionUsage(option_name="address/account", message="address or account name required")
        address = to_checksum_address(accounts[0].address)

    cfg.main.chain_id = chain_id

    endpoints = cfg.endpoints.find(chain_id=chain_id)
    if not endpoints:
        raise click.BadArgumentUsage(message="No endpoints found for chain-id")
    endpoint = endpoints[0]
    if not endpoint.connect():
        raise click.BadArgumentUsage(
            f"Could not connect to endpoint for {chain_id}\n"
            "Please check your ~/telliot/endpoints.yaml file and try again"
        )

    w3 = endpoint._web3

    contract_info = contract_directory.find(chain_id=chain_id, name="tellor360-oracle")
    if not contract_info:
        raise click.BadArgumentUsage(
            f"Tellorflex not found in telliot on chain_id {chain_id}\nCheck supported tellor chain ids"
        )

    tellorflex_address = contract_info[0].address[chain_id]
    abi = contract_info[0].get_abi(chain_id=chain_id)
    tellorflex_contract = w3.eth.contract(address=tellorflex_address, abi=abi)

    run(w3=w3, reporter=address, tellorflex_contract=tellorflex_contract, chain_id=chain_id, starting_block=start_block)
