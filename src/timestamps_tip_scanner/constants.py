from datetime import datetime


start_timestamp = int(datetime.today().replace(hour=00, minute=00, second=0, microsecond=0).timestamp())

CHAIN_ID_MAPPING = {
    80001: {
        "name": "mumbai",
        "explorer_api": (
            "https://api-testnet.polygonscan.com/api?module=block"
            f"&action=getblocknobytime&timestamp={start_timestamp}&closest=before"
        ),
    },
    137: {
        "name": "polygon",
        "explorer_api": (
            "https://api.polygonscan.com/api?module=block&action=getblocknobytime"
            f"&timestamp={start_timestamp}&closest=before"
        ),
    },
}
REPORTS_FILENAME = "new_report_timestamps.json"
