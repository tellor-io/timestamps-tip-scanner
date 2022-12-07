### Scan your address for timestamps that can claim tips in Autopay

Concepts and a chunk of the code came from [this](https://web3py.readthedocs.io/en/stable/examples.html#example-code) example, refactored to use as a timestamp scanner


Steps:
```cli
git clone https://github.com/tellor-io/timestamps-tip-scanner.git
cd timestamps-tip-scanner
echo "MUMBAI_NODE = https://polygon-mumbai.g.alchemy.com/v2/<put_your_api_key_here>" >> .env
```
```cli
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```
To fetch timestamps, run:
```cli
python src/timestamps_tip_scanner/run.py network <wallet>
```
Supported Networks:
- polygon
- mumbai

To start at a certain block use the optional flag ```--start-block <num>```

:warning: Disclaimer - Code hasn't been fully tested so use at own risk!

