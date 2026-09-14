#!/bin/bash
HOSTIP=$(ip route show default | cut -d' ' -f3 | head -1)
echo "host_ip=$HOSTIP"
python3 --version 2>/dev/null && echo "python3 present" || echo "python3 MISSING"
python3 -c 'import urllib.request,json,subprocess; print("stdlib-ok")' 2>/dev/null || echo "NO-STDLIB"
echo -n "curl host:18792/ -> "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 "http://$HOSTIP:18792/" || echo UNREACHABLE
echo -n "curl host:18792/v1/actions -> "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 "http://$HOSTIP:18792/v1/actions" || echo UNREACHABLE
