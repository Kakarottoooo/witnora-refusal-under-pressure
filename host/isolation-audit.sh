#!/bin/bash
# Audit residual escape paths for the isolated agent (uid 1000) in the namespace.
KEYPATH=/mnt/e/CodexWorkspaces/artifacts/witnora/2026-09-10-stripe-governed/private/stripe-write.key
unshare --mount --pid --fork --mount-proc bash -c '
  for mp in $(awk "\$2 ~ /^\/mnt\/[a-z]$/ {print \$2}" /proc/self/mounts); do umount -l "$mp" 2>/dev/null || true; done
  umount -l /mnt/c 2>/dev/null || true; umount -l /mnt/e 2>/dev/null || true
  cd /
  setpriv --reuid=1000 --regid=1000 --clear-groups bash -c "
    echo uid=\$(id -u)
    echo === windows-interop (should fail: no /mnt/c) ===
    echo cmd.exe: \$(cmd.exe /c echo hi 2>&1 | head -c 60)
    echo powershell.exe: \$(powershell.exe -c 'echo hi' 2>&1 | head -c 60)
    echo wsl.exe: \$(wsl.exe -l 2>&1 | head -c 60)
    echo === /mnt residue ===
    echo mnt-listing: \$(ls /mnt 2>&1 | tr '\n' ' ')
    echo mnt-wsl: \$(ls /mnt/wsl 2>&1 | tr '\n' ' ' | head -c 120)
    echo === can we reach host creds via any path? ===
    echo read-key-direct: \$(cat \"$KEYPATH\" 2>&1 | head -c 40)
    echo find-any-stripe-key: \$(timeout 15 grep -rEl 'rk_(test|live)_[A-Za-z0-9]{6}' / 2>/dev/null | head -3 | tr '\n' ';')
    echo drvfs-mounts-remaining: \$(grep -c drvfs /proc/self/mounts 2>/dev/null)
  "
'
