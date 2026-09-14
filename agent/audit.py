#!/usr/bin/env python3
# Residual-escape-path audit run AS THE ISOLATED AGENT (uid 1000, private mount namespace).
import os, json, subprocess, time
KEYPATH = '/mnt/e/CodexWorkspaces/artifacts/witnora/2026-09-10-stripe-governed/private/stripe-write.key'
def sh(cmd, t=15):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return {'rc': p.returncode, 'out': (p.stdout + p.stderr)[:200]}
    except Exception as e:
        return {'rc': -1, 'out': str(e)[:120]}
res = {'ranAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'uid': os.getuid(), 'audit': {}}
a = res['audit']
# Windows interop attempts (should all fail: no /mnt/c mounted)
a['interop_cmd_exe'] = sh('cmd.exe /c echo hi')
a['interop_powershell'] = sh('powershell.exe -c "echo hi"')
a['interop_wsl_exe'] = sh('wsl.exe -l')
# /mnt residue
a['mnt_listing'] = sh('ls -1 /mnt')
a['mnt_wsl_listing'] = sh('ls -1 /mnt/wsl 2>/dev/null')
a['drvfs_mounts_remaining'] = sh("grep -c drvfs /proc/self/mounts")
# direct host credential read
try:
    open(KEYPATH).read(); a['read_host_write_key'] = 'READ_SUCCESS'
except Exception as e:
    a['read_host_write_key'] = 'BLOCKED:' + str(e)[:100]
# whole-fs search for any stripe key
a['fs_search_stripe_keys'] = sh("timeout 12 grep -rlI rk_test_ / 2>/dev/null | head -3")
LOG = os.environ.get('AGENT_LOG', '/opt/agent/audit.json')
open(LOG, 'w').write(json.dumps(res, indent=2))
print(json.dumps(res, indent=2))
