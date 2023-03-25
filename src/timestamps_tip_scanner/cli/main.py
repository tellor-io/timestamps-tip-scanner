import click
from timestamps_tip_scanner.cli.commands.scan import scan


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Timestamps Tip Scanner"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


main.add_command(scan)
