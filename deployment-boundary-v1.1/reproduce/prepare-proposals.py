#!/usr/bin/env python3
"""Bind two $5 refund proposals to one freshly created Stripe TEST payment."""

from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--template", required=True)
parser.add_argument("--payment", required=True)
parser.add_argument("--out-dir", required=True)
args = parser.parse_args()

template = json.loads(Path(args.template).read_text(encoding="utf-8"))
payment = json.loads(Path(args.payment).read_text(encoding="utf-8"))
if payment.get("livemode") is not False or payment.get("status") != "succeeded":
    raise SystemExit("The payment must be a successful Stripe TEST object.")

out_dir = Path(args.out_dir)
out_dir.mkdir(parents=True, exist_ok=True)
for label in ("rejected", "approved"):
    proposal = copy.deepcopy(template)
    payment_id = payment["paymentIntentId"]
    proposal["externalId"] = f"stripe-boundary-v1-1-{label}-{int(time.time() * 1000)}"
    proposal["expectedState"].update({"paymentIntentId": payment_id, "amount": 500, "livemode": False})
    proposal["executionIntent"]["allowedResource"] = f"payment-intents/{payment_id}"
    proposal["executionIntent"]["approvedParameters"].update({"paymentIntentId": payment_id, "amount": 500})
    proposal["executionIntent"]["outcomePredicate"]["expectedState"] = copy.deepcopy(proposal["expectedState"])
    (out_dir / f"proposal-{label}.json").write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    time.sleep(0.002)
print(json.dumps({"prepared": ["rejected", "approved"], "paymentIntentSuffix": payment["paymentIntentId"][-8:]}))
