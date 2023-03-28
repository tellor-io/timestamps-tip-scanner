import click

from timestamps_tip_scanner.cli.commands.scan import scan
from timestamps_tip_scanner.cli.commands.single_claims import single_claims


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Timestamps Tip Scanner"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


main.add_command(scan)
main.add_command(single_claims)
