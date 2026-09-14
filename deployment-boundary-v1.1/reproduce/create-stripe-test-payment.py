#!/usr/bin/env python3
"""Create one $10 Stripe TEST PaymentIntent for a bounded refund test."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


parser = argparse.ArgumentParser()
parser.add_argument("--key-file", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()

key = Path(args.key_file).read_text(encoding="utf-8").strip()
if not key.startswith("rk_test_"):
    raise SystemExit("A restricted Stripe TEST key beginning with rk_test_ is required.")

body = urlencode({
    "amount": "1000",
    "currency": "usd",
    "payment_method": "pm_card_visa",
    "payment_method_types[]": "card",
    "confirm": "true",
    "description": "Witnora Deployment Boundary v1.1 acceptance — TEST MODE",
    "metadata[witnora_scenario]": "deployment-boundary-v1-1",
}).encode()
request = Request(
    "https://api.stripe.com/v1/payment_intents",
    data=body,
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Idempotency-Key": f"witnora-boundary-v1-1-{uuid.uuid4()}",
    },
)
with urlopen(request, timeout=30) as response:
    payment = json.loads(response.read())
if payment.get("livemode") is not False or payment.get("amount") != 1000 or payment.get("status") != "succeeded":
    raise SystemExit("Stripe did not return the expected successful TEST payment.")
result = {
    "createdAt": payment.get("created"),
    "paymentIntentId": payment["id"],
    "chargeId": payment["latest_charge"],
    "amount": payment["amount"],
    "currency": payment["currency"],
    "livemode": payment["livemode"],
    "status": payment["status"],
}
out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"created": True, "paymentIntentSuffix": result["paymentIntentId"][-8:], "livemode": False, "amount": 1000}))
