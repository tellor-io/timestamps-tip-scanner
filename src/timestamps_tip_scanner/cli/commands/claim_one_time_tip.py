import os
from typing import Optional

import click
from chained_accounts import find_accounts
from eth_account import Account
from telliot_core.apps.telliot_config import TelliotConfig
from telliot_core.tellor.tellor360.autopay import Tellor360AutopayContract
from telliot_core.utils.key_helpers import lazy_unlock_account

from timestamps_tip_scanner.claims.single_tips import claim_single_tips

cfg = TelliotConfig()


@click.command()
@click.argument("chain_id", type=int)
@click.option("--account", "-a", help="Account name, required if address not selected")
@click.option("--private-key", "-pk", help="private key, required if account not selected")
def claim_one_time_tip(chain_id: int, account: str, private_key: Optional[str]) -> None:
    """
    CHAIN ID: desired chain where to claim one time tips

    ACCOUNT: chained account name to use

    PRIVATE KEY: private key to use
    """
    private_key = os.getenv("PRIVATE_KEY")
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
        acct = accounts[0]
        lazy_unlock_account(acct)

    cfg.main.chain_id = chain_id
    endpoints = cfg.endpoints.find(chain_id=chain_id)
    if not endpoints:
        click.echo(f"No endpoints found for chain id: {chain_id}")
        raise click.BadOptionUsage(option_name="chain_id", message="chain id not found")

    endpoint = endpoints[0]
    if not endpoint.connect():
        raise click.BadArgumentUsage(
            f"Could not connect to endpoint for {chain_id}\n"
            "Please check your ~/telliot/endpoints.yaml file and try again"
        )
    autopay_contract = Tellor360AutopayContract(node=endpoint, account=acct)
    if not autopay_contract.connect():
        raise click.BadArgumentUsage(f"Could not connect to autopay contract for {chain_id}\n")
    claim_single_tips(autopay_contract)
