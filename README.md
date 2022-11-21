### Scan your address for timestamps that can claim tips in Autopay

Concepts and a chunk of the code came from [this](https://web3py.readthedocs.io/en/stable/examples.html#example-code) example, refactored to use as a timestamp scanner


Steps:
```c
git clone https://github.com/tellor-io/timestamps-tip-scanner.git
cd timestamps-tip-scanner
echo "MUMBAI_NODE = https://polygon-mumbai.g.alchemy.com/v2/<put_your_api_key_here>" >> .env
```
```c
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
To fetch timestamps, run:
```c
python src/timestamps_tip_scanner/run.py mumbai <wallet>
```
To start at a certain block use the optional flag ```--start-block <num>```

:warning: Disclaimer - Code hasn't been fully tested so use at own risk!

