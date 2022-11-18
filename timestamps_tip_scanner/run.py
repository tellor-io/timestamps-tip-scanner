import asyncio
import click

from timestamps_tip_scanner.call import call
from timestamps_tip_scanner.timestamps_scanner import run


@click.command()
@click.argument('network')
@click.argument('address')
@click.option('--start-block', default=None, help='block num to start scanning from.')
def scan(network, address, start_block):
    """NETWORK: which network to scan

    ADDRESS: wallet address
    """

    run(network, address, start_block)
    asyncio.run(call(network, address))

if __name__ == '__main__':
    scan()