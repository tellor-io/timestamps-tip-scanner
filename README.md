****WIP****
-- still needs to scan for feed tips
-- also this only works with polygon-mumbai for now but will be edited to work with all EVM chains once we decide we like it.

- ideas and a chunk of the code came from this example, refactored to use as a tip scanner:
https://web3py.readthedocs.io/en/stable/examples.html#example-code

#### returns a json file that looks like this:
```json
{
    "last_scanned_block": 26339243,
    "reporter": {
        "reporter address": {
            "today's date": {
                "query id": {
                    "list of total submissions for the batch of blocks scanned today": [
                        1650770213],
                    "one time eligible timestamps": [
                        1650766071
                    ]
                }
            }
        }
    }
}
```

Example: 
```json
{
    "last_scanned_block": 26339243,
    "reporter": {
        "0xdedC604896bE034283365D65118Cce2942F99392": {
            "May-16-2022": {,
                "0xb9d5e25dabd5f0a48f45f5b6b524bac100df05eaf5311f3e5339ac7c3dd0a37e": {
                    "all_submissions": [
                        1651135148,
                        1651156177,
                        1651166664,
                        1651180563,
                        1651190980,
                        1651236210,
                        1651239687,
                        1651255325,
                        1651265755,
                        1651323102
                    ],
                    "one_time_tips": [
                        1650778883
                    ]
                }
            }
        }
    }
}
```

Run commands:
```
git clone https://github.com/tellor-io/timestamps-tip-scanner.git
```
```
cd timestamps-tip-scanner
```
```
touch .env
vi .env
NODE_API = https://polygon-mumbai.infura.io/v3/<put_your_api_key_here>
```
```
python3 -m venv venv
source venv/bin/activate
```
```
pip install -r requirements-dev.txt
```
```
python src/timestamps_tip_scanner.py
```

- to start at a certain block edit record.json with the block you want to start with
  
```json
{"last_scanned_block": "add block number here"
```

