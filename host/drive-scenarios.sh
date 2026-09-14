#!/bin/bash
# Host driver: run each isolated model-agent scenario, independently read back Stripe after each,
# then run the deterministic regression, then a final readback. Host-side readbacks use the probe key.
OUT="E:/CodexWorkspaces/artifacts/witnora/2026-09-14-agent-isolation"
DEP="E:/CodexWorkspaces/artifacts/witnora/2026-09-10-stripe-governed"
LAUNCH=/mnt/e/CodexWorkspaces/artifacts/witnora/2026-09-14-agent-isolation/host/run-agent-wsl.sh
export WITNORA_GATEWAY_TOKEN=$(node -e "console.log(JSON.parse(require('fs').readFileSync('$DEP/gateway/secrets.json','utf8')).gatewayToken)")
export WSLENV=OPENAI_API_KEY/u:WITNORA_GATEWAY_TOKEN/u
PI=$(node -e "console.log(require('$OUT/evidence/payment-A2.json').paymentIntentId)")
echo "target PI=$PI"
for S in A B C; do
  echo "======================= MODEL AGENT SCENARIO $S ======================="
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-48G -u root -- bash "$LAUNCH" "$S" "$PI" 500 172.23.240.1 gpt-4o run 2>&1 | tr -d '\0'
  echo "--- independent readback after $S ---"
  node "$OUT/scripts/readback.mjs" --pi "$PI" --label "A2-after-$S"
done
echo "======================= DETERMINISTIC REGRESSION ======================="
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-48G -u root -- bash "$LAUNCH" regression "$PI" 500 172.23.240.1 gpt-4o regression 2>&1 | tr -d '\0'
node "$OUT/scripts/readback.mjs" --pi "$PI" --label "A2-after-regression"
echo "======================= FINAL READBACK ======================="
node "$OUT/scripts/readback.mjs" --pi "$PI" --label "A2-final"
echo "DONE-ALL-SCENARIOS"
