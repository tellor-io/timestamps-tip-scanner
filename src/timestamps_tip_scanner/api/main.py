import json
import time
from typing import Any
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from timestamps_tip_scanner.api.utils import autopay
from timestamps_tip_scanner.api.utils import fetch_data
from timestamps_tip_scanner.claims.single_tips import timestamps_to_claim
from timestamps_tip_scanner.constants import CHAIN_ID_MAPPING
from timestamps_tip_scanner.constants import REPORTS_FILENAME


app = FastAPI()


def reports_file(chain_id: int, address: str) -> Any:
    try:
        with open(REPORTS_FILENAME, "r") as f:
            reports = json.load(f)
    except FileNotFoundError:
        return None
    report_chain = reports.get(CHAIN_ID_MAPPING[chain_id]["name"])
    if not report_chain:
        return None
    report_address = report_chain.get(address)
    if not report_address:
        return None
    last_scan = report_address.get("last_scanned_time")
    if not last_scan:
        return None
    if int(time.time()) - last_scan > 60 * 10:  # if last scan was more than 10 minutes ago scan again
        return None
    return reports


@app.get("/", response_class=HTMLResponse)
def guide() -> str:
    return """<pre>Endpoints:
    /reports/{chain_id}?address={address}&starting_block={starting_block}
    /feed_tips/{chain_id}?address={address}&starting_block={starting_block}
    /tips/{chain_id}?address={address}&starting_block={starting_block}</pre>"""


@app.get("/reports/{chain_id}", response_class=HTMLResponse)
def reports(chain_id: int, address: str, starting_block: Optional[int] = None) -> str:
    data = fetch_data(chain_id, address, starting_block).serve()
    data_formatted = json.dumps(data, indent=4)
    content = f"<pre>{data_formatted}</pre>"
    return content


@app.get("/feed_tips/{chain_id}", response_class=HTMLResponse)
def feed_tips(chain_id: int, address: str, starting_block: Optional[int] = None) -> str:
    if reports_file(chain_id, address) is None:
        _ = fetch_data(chain_id, address, starting_block)
    apay = autopay(chain_id, address)
    data = apay.reward_claimed_status_check()
    if data is None:
        return "<pre>{}</pre>"
    return f"<pre>{data}</pre>"


@app.get("/tips/{chain_id}", response_class=HTMLResponse)
def one_time_tips(chain_id: int, address: str, starting_block: Optional[int] = None) -> str:
    if reports_file(chain_id, address) is None:
        _ = fetch_data(chain_id, address, starting_block)
    apay = autopay(chain_id, address)
    return f"<pre>{timestamps_to_claim(apay=apay)}</pre>"
