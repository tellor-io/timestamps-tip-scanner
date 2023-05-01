### Scan timestamps for Autopay tips

Steps:
```shell
python3 -m venv venv
source venv/bin/activate
pip install -e .
```
pre-requisite
```shell
# register address to keyfile
chained add <choose-acct-name> <private-key>
```
First scan oracle for your reports:
```shell
scanner scan <chain-id> -a <acct-name> --start-block <block-number>
```
Then, to claim tips:
- one time tips:
```shell
scanner claim-one-time-tip <chain-id> <acct-name>
```
- feed tips:
```shell
scanner claim-tip <chain-id> -a <acct-name>
```
###### Supported Networks:
- 137 (polygon)
- 80001 (mumbai)

###### API
```
uvicorn timestamps_tip_scanner.api.main:app --reload
```
###### Enpoints
```
/reports/{chain_id}?address={address}&starting_block={starting_block}
/feed_tips/{chain_id}?address={address}
/tips/{chain_id}?address={address}
```
:warning: Disclaimer - Code hasn't been fully tested so use at own risk!
