#!/usr/bin/env python3
# INDEPENDENT VERIFIER (for an EXTERNAL reviewer). Stdlib only.
# Reads the reviewer's OWN read-only Stripe key from env STRIPE_READONLY_KEY and checks each
# claim in claims.json directly against Stripe's live state -- it trusts NONE of Witnora's logs,
# probe output, or receipts. It only reads; it never writes. It never prints the key.
#
# Usage:
#   export STRIPE_READONLY_KEY=rk_test_...        # a READ-ONLY restricted key on the same TEST account
#   python3 verify-stripe-claims.py claims.json
#
# Independence notes:
#   - Use a key that belongs to YOU (the reviewer), distinct from any key used in the test.
#   - This checks Witnora's stated claims against ground truth. Running it does NOT make Witnora
#     the third party; a genuinely external person must run it for the result to be "independent".
import os, sys, json, urllib.request, urllib.error, time

KEY = os.environ.get('STRIPE_READONLY_KEY', '')
if not KEY.startswith('rk_') and not KEY.startswith('sk_'):
    print('ERROR: set STRIPE_READONLY_KEY to a read-only Stripe TEST key (rk_test_...).'); sys.exit(2)
CLAIMS = sys.argv[1] if len(sys.argv) > 1 else 'claims.json'

def stripe_get(path):
    req = urllib.request.Request('https://api.stripe.com' + path, headers={'Authorization': 'Bearer ' + KEY})
    try:
        with urllib.request.urlopen(req, timeout=25) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
    except Exception as e: return -1, {'error': str(e)}

def list_refunds(pi):
    out, starting_after, pages = [], None, 0
    while True:
        p = '/v1/refunds?payment_intent=%s&limit=100' % pi
        if starting_after: p += '&starting_after=' + starting_after
        code, data = stripe_get(p)
        if code != 200 or data.get('object') != 'list':
            raise RuntimeError('refund list failed http=%s %s' % (code, str(data.get('error'))[:120]))
        out += data['data']; pages += 1
        if data.get('has_more') and data['data']:
            starting_after = data['data'][-1]['id']
        else:
            return out, pages

def charge_livemode(charge_id):
    code, c = stripe_get('/v1/charges/' + charge_id)
    return (c.get('livemode') if code == 200 else None)

claims = json.load(open(CLAIMS))
print('Independent verification @', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
      '(key ...%s, read-only)' % KEY[-4:])
overall = True
report = []
for c in claims['claims']:
    pi = c.get('paymentIntentId') or os.environ.get(c.get('paymentIntentEnv', ''), '')
    if not pi.startswith('pi_'):
        report.append({'label': c.get('label'), 'paymentIntentId': '[private]', 'result': 'ERROR',
                       'detail': 'missing payment intent env: ' + c.get('paymentIntentEnv', '')})
        overall = False
        continue
    try:
        refunds, pages = list_refunds(pi)
    except Exception as e:
        report.append({'label': c.get('label'), 'paymentIntentId': pi, 'result': 'ERROR', 'detail': str(e)}); overall = False; continue
    got = len(refunds)
    exp = c['expect']
    ok = (got == exp['refundCount'])
    detail = {'observedRefundCount': got, 'expectedRefundCount': exp['refundCount'],
              'refunds': [{'id': r['id'], 'amount': r['amount'], 'currency': r['currency'], 'status': r['status'],
                           'livemode_of_charge': charge_livemode(r['charge']) if r.get('charge') else None,
                           'metadata': r.get('metadata', {})} for r in refunds]}
    # optional deeper checks on expected refunds
    for want in exp.get('refunds', []):
        m = [r for r in refunds if r['amount'] == want.get('amount') and r['status'] == want.get('status')
             and (want.get('currency') is None or r.get('currency') == want.get('currency'))
             and all(r.get('metadata', {}).get(k) == v for k, v in want.get('metadataContains', {}).items())]
        if len(m) != 1: ok = False
    report.append({'label': c.get('label'), 'paymentIntentId': pi, 'result': 'PASS' if ok else 'FAIL', **detail})
    overall = overall and ok

for r in report:
    print('  [%s] %-26s %s  observed=%s expected=%s' % (
        r['result'], r.get('label', ''), r['paymentIntentId'],
        r.get('observedRefundCount', '?'), r.get('expectedRefundCount', '?') if 'expectedRefundCount' in r else '?'))
    for rf in r.get('refunds', []):
        print('        refund %s %s %s %s livemode_charge=%s meta=%s' % (
            rf['id'], rf['amount'], rf['currency'], rf['status'], rf['livemode_of_charge'], json.dumps(rf['metadata'])[:80]))
print('\nOVERALL:', 'PASS - all claims match live Stripe state' if overall else 'FAIL - at least one claim did not match')
sys.exit(0 if overall else 1)
