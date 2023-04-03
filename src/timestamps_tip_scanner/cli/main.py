import click

from timestamps_tip_scanner.cli.commands.claim_one_time_tip import claim_one_time_tip
from timestamps_tip_scanner.cli.commands.claim_tip import claim_tip
from timestamps_tip_scanner.cli.commands.scan import scan
from timestamps_tip_scanner.logger import setup_logger

setup_logger()


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Timestamps Tip Scanner"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


main.add_command(scan)
main.add_command(claim_one_time_tip)
main.add_command(claim_tip)
