****WIP****

- ideas and a chunk of the code came from this example, refactored to use as a tip scanner:
https://web3py.readthedocs.io/en/stable/examples.html#example-code

#### returns a json file that looks like this:
```json
{
    "last_scanned_block": 27636952,
    "0xdedC604896bE034283365D65118Cce2942F99392": {
        "0xd913406746edf7891a09ffb9b26a12553bbf4d25ecf8e530ec359969fe6a7a9c": [
            1660588046,
            1660589851,
            1660591667,
            1660593476,
            1660595297,
            1660597107,
            1660598917
        ]
    }
}
```

Example: 
```json
{
    "single_tips": {
        "0xd913406746edf7891a09ffb9b26a12553bbf4d25ecf8e530ec359969fe6a7a9c": [
            1660589851,
            1660591667,
            1660593476,
            1660595297,
            1660597107,
            1660598917
        ]
    }
}
```
```json
{"feed_tips": {"query id": {"feed id": ["timestamps"]}}}
{
    "feed_tips": {
        "0xb9d5e25dabd5f0a48f45f5b6b524bac100df05eaf5311f3e5339ac7c3dd0a37e": {
            "267c686e0ad022fe8f3a726094f00beb129ce69faf79d6856fedcc8f0e5cd14b": [ 
                1660235590
            ]
        },
        "0x7239909c0aa5d3e89efb2dce06c80811e93ab18413110b8c0435ee32c52cc4fb": {
            "45ec950951300395e0c6d7b0d16995f8d559ec80c7fcfce81ca46cc79da23eb6": [
                1660401075,
                1660242252,
                1660486022,
                1660313159
            ]
        }
    }
}

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
NODE_URI = https://polygon-mumbai.infura.io/v3/<put_your_api_key_here>
AUTOPAY_ADDRESS = "0x7B49420008BcA14782F2700547764AdAdD54F813"
TELLORFLEX_ADDRESS = "0x840c23e39F9D029fFa888F47069aA6864f0401D7"
REPORTER = <wallet address>
BATCH_SIZE = <scan batch size number>
PRIVATE_KEY = <required to claim tips>
```
```
python3 -m venv venv
source venv/bin/activate
```
```
pip install -r requirements-dev.txt
```
To fetch a reports' timestamp, run:
```
python src/timestamps_tip_scanner.py
```
Then to filter tip eligible ones, run:
```
python src/call.py
```
To claim tips
```
python src/claim_tips.py
```

- to start at a certain block edit report_timestamps.json with the block you want to start with
  
```json
{"last_scanned_block": "add block number here"
```

