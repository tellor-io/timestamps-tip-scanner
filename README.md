### Scan your address for timestamps that can claim tips in Autopay

Concepts and a chunk of the code came from [this](https://web3py.readthedocs.io/en/stable/examples.html#example-code) example, refactored to use as a timestamp scanner


Steps:
```shell
python3 -m venv venv
source venv/bin/activate
pip install -e .
```
First fetch timestamps:
```shell
scanner scan <CHAIN-ID> <ACCOUNT-NAME> or <PUBLIC-KEY> <--start-block>
```
Claim one time tips:
```shell
scanner claim-one-time-tip <CHAIN-ID> <ACCOUNT-NAME> or <PRIVATE-KEY>
```
Claim feed tips:
```shell
scanner claim-tip <CHAIN-ID> <ACCOUNT-NAME> or <PRIVATE-KEY>
```
######Supported Networks:
- 137 (polygon)
- 80001 (mumbai)

######API
```
uvicorn timestamps_tip_scanner.api.main:app --reload
```
######Enpoints
```
/reports/{chain_id}?address={address}&starting_block={starting_block}
/feed_tips/{chain_id}?address={address}
/tips/{chain_id}?address={address}
```
:warning: Disclaimer - Code hasn't been fully tested so use at own risk!
