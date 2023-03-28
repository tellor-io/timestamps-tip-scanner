import os
import click
from eth_account import Account
from telliot_core.directory import contract_directory
from telliot_core.apps.telliot_config import TelliotConfig
from chained_accounts import find_accounts
from telliot_core.utils.key_helpers import lazy_unlock_account

from timestamps_tip_scanner.claims.feed_tips import claim_tips

cfg = TelliotConfig()


@click.command()
@click.argument("chain_id", type=int)
@click.option("--account", "-a", help="Account name, required if address not selected")
@click.option("--private-key", "-pk", help="private key, required if account not selected")
def claim(chain_id: int, account: str, private_key: str) -> None:
    """
    CHAIN ID: desired chain to scan

    ACCOUNT: chained account name to use

    PRIVATE KEY: private key to use
    """
    private_key = os.getenv("PRIVATE_KEY")  # type: ignore
    if not private_key and not account:
        raise click.BadOptionUsage(option_name="private_key/account", message="private key or account name required")

    if private_key:
        acct = Account.from_key(private_key)

    elif account:
        accounts = find_accounts(account)
        if not accounts:
            click.echo(
                f"No account found named: '{account}'.\n"
                "Either use -pk flag or add one with the account subcommand.\n"
                "For more info run: `telliot account add --help`"
            )
            raise click.BadOptionUsage(
                option_name="private_key/account", message="private key or account name required"
            )
        lazy_unlock_account(accounts[0])
        acct = accounts[0].local_account

    cfg.main.chain_id = chain_id
    endpoints = cfg.endpoints.find(chain_id=chain_id)
    if not endpoints:
        click.echo(f"No endpoints found for chain id: {chain_id}")
        raise click.BadOptionUsage(option_name="chain_id", message="chain id not found")

    endpoint = endpoints[0]
    w3 = endpoint._web3
    contract_info = contract_directory.find(chain_id=chain_id, name="tellor360-autopay")
    if not contract_info:
        raise click.BadArgumentUsage(
            f"Tellorflex not found in telliot on chain_id {chain_id}"
            "Check supported tellor chain ids")

    autopay_address = contract_info[0].address[chain_id]
    abi = contract_info[0].get_abi(chain_id=chain_id)
    autopay_contract = w3.eth.contract(address=autopay_address, abi=abi)
    claim_tips(w3, autopay_contract, acct)
