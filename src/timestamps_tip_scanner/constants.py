import os
from datetime import datetime
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()
start_timestamp = int(datetime
                    .today()
                    .replace(hour=00, minute=00, second=0, microsecond=0)
                    .timestamp())

@dataclass
class Network:
    oracle_address: str
    autopay_address: str
    api_node: str
    api_scan: str
    api_key: str = None

Networks = {
    "mumbai": Network(
        oracle_address="0x8f55D884CAD66B79e1a131f6bCB0e66f4fD84d5B",
        autopay_address="0x1775704809521D4D7ee65B6aFb93816af73476ec",
        api_node=os.getenv("MUMBAI_NODE"),
        api_scan=f"https://api-testnet.polygonscan.com/api?module=block&action=getblocknobytime&timestamp={start_timestamp}&closest=before")
, "polygon": Network(
        oracle_address="0x8f55D884CAD66B79e1a131f6bCB0e66f4fD84d5B",
        autopay_address="0x1775704809521D4D7ee65B6aFb93816af73476ec",
        api_node=os.getenv("POLYGON_NODE"),
        api_scan=f"https://api.polygonscan.com/api?module=block&action=getblocknobytime&timestamp={start_timestamp}&closest=before")}