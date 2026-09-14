#!/usr/bin/env python3
"""Read one TEST PaymentIntent's refund list through a restricted read-only key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


parser = argparse.ArgumentParser()
parser.add_argument("--key-file", required=True)
parser.add_argument("--payment", required=True)
parser.add_argument("--label", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()

key = Path(args.key_file).read_text(encoding="utf-8").strip()
payment_record = json.loads(Path(args.payment).read_text(encoding="utf-8"))
payment_id = payment_record["paymentIntentId"]
if not key.startswith("rk_test_") or not payment_id.startswith("pi_"):
    raise SystemExit("A restricted Stripe TEST key and TEST PaymentIntent are required.")
if payment_record.get("livemode") is not False:
    raise SystemExit("The supplied payment record is not explicitly TEST mode.")


def get(path: str, params: dict[str, str | int] | None = None) -> dict:
    url = "https://api.stripe.com" + path
    if params:
        url += "?" + urlencode(params)
    request = Request(url, headers={"Authorization": f"Bearer {key}"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read())


refunds: list[dict] = []
starting_after = None
while True:
    params: dict[str, str | int] = {"payment_intent": payment_id, "limit": 100}
    if starting_after:
        params["starting_after"] = starting_after
    page = get("/v1/refunds", params)
    refunds.extend(page.get("data", []))
    if not page.get("has_more") or not page.get("data"):
        break
    starting_after = page["data"][-1]["id"]

result = {
    "label": args.label,
    "observedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    "source": "Stripe API /v1/refunds through a separate restricted read-only TEST key",
    "providerMode": "Stripe TEST mode",
    "paymentIntentId": payment_id,
    "count": len(refunds),
    "totalAmountCents": sum(int(item.get("amount", 0)) for item in refunds),
    "refunds": [
        {key: item.get(key) for key in ("id", "amount", "currency", "status", "livemode", "payment_intent", "created")}
        for item in refunds
    ],
}
out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"label": args.label, "paymentIntentSuffix": payment_id[-8:], "count": result["count"], "totalAmountCents": result["totalAmountCents"]}))
