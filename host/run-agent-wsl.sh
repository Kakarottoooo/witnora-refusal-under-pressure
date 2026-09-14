#!/bin/bash
# Launch the model agent inside an isolated WSL mount+pid namespace as a NON-root uid.
# Args: SCENARIO PI AMOUNT HOSTIP MODEL MODE(dry|run)
# Secrets OPENAI_API_KEY and WITNORA_GATEWAY_TOKEN arrive via WSLENV (not on the cmdline).
set -e
SCEN="$1"; PI="$2"; AMT="$3"; HOSTIP="$4"; MODEL="$5"; MODE="${6:-run}"
SRC=/mnt/e/CodexWorkspaces/artifacts/witnora/2026-09-14-agent-isolation/agent/agent-harness.py
KEYPATH=/mnt/e/CodexWorkspaces/artifacts/witnora/2026-09-10-stripe-governed/private/stripe-write.key
mkdir -p /opt/agent/logs
cp "$SRC" /opt/agent/agent-harness.py
cp /mnt/e/CodexWorkspaces/artifacts/witnora/2026-09-14-agent-isolation/agent/regression.py /opt/agent/regression.py
cp /mnt/e/CodexWorkspaces/artifacts/witnora/2026-09-14-agent-isolation/agent/audit.py /opt/agent/audit.py
chmod 0755 /opt/agent /opt/agent/agent-harness.py /opt/agent/regression.py /opt/agent/audit.py
chmod 0777 /opt/agent/logs
# gw helper: lets the agent use the sanctioned gateway channel without ever seeing the token value.
cat > /opt/agent/gw <<'GWEOF'
#!/bin/bash
M="${1:-GET}"; P="$2"; D="$3"
if [ -n "$D" ]; then curl -s -X "$M" "$WITNORA_GATEWAY_URL$P" -H "Authorization: Bearer $WITNORA_GATEWAY_TOKEN" -H "content-type: application/json" -d "$D"
else curl -s -X "$M" "$WITNORA_GATEWAY_URL$P" -H "Authorization: Bearer $WITNORA_GATEWAY_TOKEN"; fi
GWEOF
chmod 0755 /opt/agent/gw
LOG=/opt/agent/logs/agent-log-$SCEN.jsonl

# Export config for the harness (inherited through unshare + setpriv).
export TARGET_PAYMENT_INTENT="$PI" TARGET_AMOUNT="$AMT" AGENT_MODEL="$MODEL" AGENT_SCENARIO="$SCEN" AGENT_LOG="$LOG"
export WITNORA_GATEWAY_URL="http://$HOSTIP:18792"
export AGENT_MAX_CALLS="${AGENT_MAX_CALLS:-25}" AGENT_MAX_MS="${AGENT_MAX_MS:-600000}"
export PATH="/opt/agent:$PATH"

echo "== launcher: setpriv=$(command -v setpriv || echo MISSING) python3=$(command -v python3)"
echo "== env presence: OPENAI_API_KEY=${#OPENAI_API_KEY}ch WITNORA_GATEWAY_TOKEN=${#WITNORA_GATEWAY_TOKEN}ch"

unshare --mount --pid --fork --mount-proc bash -c '
  # Unmount ONLY Windows drive-letter mounts (drvfs) that expose host files/creds.
  # Keep /mnt/wsl (holds resolv.conf and WSL networking) so DNS/internet still work.
  for mp in $(awk "\$2 ~ /^\/mnt\/[a-z]$/ {print \$2}" /proc/self/mounts); do umount -l "$mp" 2>/dev/null || true; done
  umount -l /mnt/c 2>/dev/null || true
  umount -l /mnt/e 2>/dev/null || true
  if ls "'"$KEYPATH"'" >/dev/null 2>&1; then echo "ISOLATION_FAIL: host write key VISIBLE in namespace"; exit 90; fi
  echo "== isolation OK: host write key NOT visible; whoami-before-drop=$(whoami); dns=$(getent hosts api.openai.com >/dev/null 2>&1 && echo resolves || echo NO-DNS)"
  cd /opt/agent 2>/dev/null || cd /
  if [ "'"$MODE"'" = "dry" ]; then
    setpriv --reuid=1000 --regid=1000 --clear-groups bash -c "
      echo agent-uid=\$(id -u)
      echo can-read-host-key=\$(cat \"'"$KEYPATH"'\" 2>&1 | head -c 40)
      echo remount-blocked=\$(mount -t drvfs E: /mnt/e 2>&1 | head -c 50)
      echo openai-dns+https=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.openai.com/v1/models || echo FAIL)
      echo gateway-reach=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \$WITNORA_GATEWAY_URL/v1/actions || echo FAIL)
      echo stripe-reach=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.stripe.com/v1 || echo FAIL)"
    exit 0
  fi
  if [ "'"$MODE"'" = "regression" ]; then
    setpriv --reuid=1000 --regid=1000 --clear-groups python3 /opt/agent/regression.py
  elif [ "'"$MODE"'" = "audit" ]; then
    setpriv --reuid=1000 --regid=1000 --clear-groups python3 /opt/agent/audit.py
  else
    setpriv --reuid=1000 --regid=1000 --clear-groups python3 /opt/agent/agent-harness.py
  fi
'
