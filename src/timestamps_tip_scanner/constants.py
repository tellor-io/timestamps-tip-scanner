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
    1: {
        "name": "mainnet",
        "explorer_api": (
            "https://api.etherscan.io/api?module=block&action=getblocknobytime"
            f"&timestamp={start_timestamp}&closest=before"
        ),
    },
    5: {
        "name": "goerli",
        "explorer_api": (
            "https://api-goerli.etherscan.io/api?module=block&action=getblocknobytime"
            f"&timestamp={start_timestamp}&closest=before"
        ),
    },
    11155111: {
        "name": "sepolia",
        "explorer_api": (
            "https://api-sepolia.etherscan.io/api?module=block&action=getblocknobytime"
            f"&timestamp={start_timestamp}&closest=before"
        ),
    },
}

QUERYDATASTORAGEMAPPING = {
    1: "0x96918F58e0D34DC1f69d0ef724D5207C28919010",
    5: "0x96918F58e0D34DC1f69d0ef724D5207C28919010",
    137: "0x96918F58e0D34DC1f69d0ef724D5207C28919010",
    80001: "0x96918F58e0D34DC1f69d0ef724D5207C28919010",
    11155111: "0x49eE5818fcA3016728827ba473c44f9024A6EC88",
}

REPORTS_FILENAME = "new_report_timestamps.json"
TWELVE_HOURS = 43200
FOUR_WEEKS = 4 * 7 * 24 * 60 * 60  # 4 weeks in seconds
