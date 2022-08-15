****WIP****
-- also this only works with polygon-mumbai for now but will be edited to work with all EVM chains once we decide we like it.

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
AUTOPAY_ADDRESS = "0x7B49420008BcA14782F2700547764AdAdD54F813"
TELLORFLEX_ADDRESS = "0x840c23e39F9D029fFa888F47069aA6864f0401D7"
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
python src/Call.py
```

- to start at a certain block edit report_timestamps.json with the block you want to start with
  
```json
{"last_scanned_block": "add block number here"
```

