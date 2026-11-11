#!/usr/bin/env python3
"""eServices Lab controller (Python 3.8+, stdlib only). Introduces reversible security drift into the
simulated case-study domain and records ground truth for scoring DriftGuard.
  init | up | down | status | on <s> | off <s> | reset | mark <label> | truth | verify"""
import argparse, csv, http.client, json, os, shutil, socket, ssl, subprocess, sys, time, warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE, SCANS, GT = ROOT/"state.json", ROOT/"scans.json", ROOT/"ground_truth.csv"
TPL, CONF, CERTS = ROOT/"nginx/site.conf.tpl", ROOT/"nginx/conf.d/default.conf", ROOT/"certs"
HOST = "127.0.0.1"
HTTPS, HTTP, ADMIN = (int(os.environ.get(k, d)) for k, d in
                      (("LAB_HTTPS_PORT", 8443), ("LAB_HTTP_PORT", 8080), ("LAB_ADMIN_PORT", 8081)))
DEBUG = "/api/v1/admin/debug"
SCEN = {  # name: (category, expected finding)
    "tls-legacy": ("TLS/SSL", "Legacy TLS 1.0/1.1 accepted"),
    "cert-mismatch": ("TLS/SSL", "Certificate does not match hostname"),
    "http-plain": ("Network/Service", "Application served over plain HTTP, no redirect"),
    "port-open": ("Network/Service", "Unexpected legacy admin service on port %d" % ADMIN),
    "api-debug": ("API", "Debug endpoint %s publicly reachable" % DEBUG),
}
now = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
load = lambda: {k: bool(json.loads(STATE.read_text()).get(k)) for k in SCEN} if STATE.exists() else {k: False for k in SCEN}

def log(event, scenario="", action="", state=None):
    new = not GT.exists()
    with GT.open("a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["timestamp_utc", "event", "scenario", "action", "category", "expected_finding", "state_after"])
        w.writerow([now(), event, scenario, action, *SCEN.get(scenario, ("", "")), json.dumps(state if state is not None else load(), sort_keys=True)])

def compose(*a, check=True):
    return subprocess.run(["docker", "compose", *a], cwd=str(ROOT), check=check)

def render(s):
    proxy = "proxy_pass http://portal; proxy_set_header Host $host;"
    dbg = ("    location = %s { %s }" % (DEBUG, proxy)) if s["api-debug"] else ("    location = %s { return 403; }" % DEBUG)
    http_block = (dbg + "\n    location / { %s }" % proxy) if s["http-plain"] else "    return 301 https://$host:%d$request_uri;" % HTTPS
    out = TPL.read_text()
    for k, v in {"HTTP_BLOCK": http_block, "CERT": "mismatch" if s["cert-mismatch"] else "good",
                 "SSL_PROTOCOLS": "TLSv1 TLSv1.1 TLSv1.2 TLSv1.3" if s["tls-legacy"] else "TLSv1.2 TLSv1.3",
                 "SSL_CIPHERS": "    ssl_ciphers ALL:@SECLEVEL=0;" if s["tls-legacy"] else "", "DEBUG_LOCATION": dbg}.items():
        out = out.replace("{{%s}}" % k, v)
    CONF.parent.mkdir(parents=True, exist_ok=True)
    CONF.write_text(out)  # written in place: the directory is bind-mounted

def reload_nginx():
    if compose("exec", "-T", "nginx", "nginx", "-s", "reload", check=False).returncode:
        print("  (nginx not running yet - config applies on `up`)")

def set_admin(on):
    compose("--profile", "drift-port", *(["up", "-d", "legacy-admin"] if on else ["rm", "-sf", "legacy-admin"]), check=on)

def apply(s, prev=None):
    render(s); reload_nginx()
    if prev is None or prev["port-open"] != s["port-open"]: set_admin(s["port-open"])

def gen_certs():
    CERTS.mkdir(exist_ok=True)
    for name, subj, san in (("good", "/CN=localhost", "subjectAltName=DNS:localhost,DNS:eservices.test,IP:127.0.0.1"),
                            ("mismatch", "/CN=wrong-host.example", "subjectAltName=DNS:wrong-host.example")):
        if (CERTS/(name + ".crt")).exists(): continue
        local = shutil.which("openssl"); base = str(CERTS) if local else "/certs"
        args = ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365", "-keyout", f"{base}/{name}.key",
                "-out", f"{base}/{name}.crt", "-subj", subj, "-addext", san]
        subprocess.run((["openssl"] if local else ["docker", "run", "--rm", "-v", f"{CERTS}:/certs", "alpine/openssl"]) + args,
                       check=True, stderr=subprocess.DEVNULL)

def cmd_init(_):
    gen_certs(); s = load(); STATE.write_text(json.dumps(s)); render(s)
    if not GT.exists(): log("init", state=s)
    print("initialised")

def cmd_up(a):
    cmd_init(a); compose("up", "-d", "--build")
    for _ in range(40):
        try:
            c = http.client.HTTPSConnection(HOST, HTTPS, timeout=3, context=_ctx()); c.request("GET", "/health"); c.getresponse().read(); break
        except Exception: time.sleep(2)
    print("https://localhost:%d  http://localhost:%d" % (HTTPS, HTTP))

def cmd_down(_): compose("--profile", "drift-port", "down")

def cmd_status(_):
    s = load()
    for n, (c, f) in SCEN.items(): print("  [%s] %-14s %-16s %s" % ("X" if s[n] else " ", n, c, f))

def change(name, val):
    if name not in SCEN: sys.exit("unknown scenario; choose: " + ", ".join(SCEN))
    prev = load(); s = dict(prev, **{name: val}); STATE.write_text(json.dumps(s)); apply(s, prev)
    log("change", name, "introduced" if val else "remediated", s); print(name, "ON" if val else "OFF")

def cmd_reset(_):
    prev = load(); s = {k: False for k in SCEN}; STATE.write_text(json.dumps(s)); apply(s, prev); log("reset", state=s); print("reset")

def cmd_mark(a):
    sc = json.loads(SCANS.read_text()) if SCANS.exists() else []
    sc.append({"label": a.label, "timestamp_utc": now(), "state": load()}); SCANS.write_text(json.dumps(sc, indent=1))
    log("scan", state=load()); print("recorded scan", a.label)

def classify(h):
    out = []
    for i, p in enumerate(h):
        if i == 0: out.append("BASELINE" if p else "-")
        elif p and not h[i-1]: out.append("RECURRING" if any(h[:i-1]) else "NEW")
        elif p: out.append("PERSISTENT")
        else: out.append("FIXED" if h[i-1] else "-")
    return out

def cmd_truth(_):
    if not SCANS.exists(): sys.exit("no scans marked yet: run `lab.py mark <label>` after each DriftGuard scan")
    sc = json.loads(SCANS.read_text())
    print("  %-14s " % "scenario" + " ".join("%-11s" % x["label"] for x in sc))
    for n in SCEN: print("  %-14s " % n + " ".join("%-11s" % r for r in classify([bool(x["state"].get(n)) for x in sc])))

def _ctx():
    c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); c.check_hostname = False; c.verify_mode = ssl.CERT_NONE; return c

def p_tls():
    res = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for v in (ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_1):
            try:
                c = _ctx()
                try: c.set_ciphers("ALL:@SECLEVEL=0")
                except ssl.SSLError: pass
                c.minimum_version = c.maximum_version = v
                with socket.create_connection((HOST, HTTPS), timeout=5) as s, c.wrap_socket(s, server_hostname="localhost"): res.append(True)
            except (ValueError,): res.append(None)
            except (ssl.SSLError, OSError): res.append(False)
    return True if True in res else (None if all(r is None for r in res) else False)

def p_cert():
    c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    for n in ("good", "mismatch"): c.load_verify_locations(cafile=str(CERTS/(n + ".crt")))
    try:
        with socket.create_connection((HOST, HTTPS), timeout=5) as s, c.wrap_socket(s, server_hostname="localhost"): return False
    except ssl.SSLCertVerificationError as e: return "hostname" in str(e).lower() or e.verify_code == 62
    except (ssl.SSLError, OSError): return None

def p_http():
    try:
        c = http.client.HTTPConnection(HOST, HTTP, timeout=5); c.request("GET", "/"); st = c.getresponse().status
    except OSError: return None
    return False if 300 <= st < 400 else (True if 200 <= st < 300 else None)

def p_port():
    try:
        with socket.create_connection((HOST, ADMIN), timeout=3): return True
    except OSError: return False

def p_api():
    try:
        c = http.client.HTTPSConnection(HOST, HTTPS, timeout=5, context=_ctx()); c.request("GET", DEBUG); st = c.getresponse().status
    except OSError: return None
    return False if st == 403 else (None if st >= 500 else True)

PROBES = {"tls-legacy": p_tls, "cert-mismatch": p_cert, "http-plain": p_http, "port-open": p_port, "api-debug": p_api}

def verify_all():
    s, rows, ok = load(), [], True
    for n, p in PROBES.items():
        o = p(); res = "UNKNOWN" if o is None else ("PASS" if o == s[n] else "FAIL"); ok &= res == "PASS"; rows.append((n, s[n], o, res))
    return rows, ok

def cmd_verify(_):
    rows, ok = verify_all()
    for r in rows: print("%-14s expected=%-6s observed=%-6s %s" % r)
    print("\nLab matches ground truth." if ok else "\nNOT confirmed: mismatch or inconclusive probe (is the stack fully up?).")
    return 0 if ok else 1

if __name__ == "__main__":
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="c", required=True)
    for n, f in (("init", cmd_init), ("up", cmd_up), ("down", cmd_down), ("status", cmd_status), ("reset", cmd_reset), ("truth", cmd_truth), ("verify", cmd_verify)):
        sub.add_parser(n).set_defaults(f=f)
    for n, v in (("on", True), ("off", False)):
        q = sub.add_parser(n); q.add_argument("scenario"); q.set_defaults(f=lambda a, v=v: change(a.scenario, v))
    q = sub.add_parser("mark"); q.add_argument("label"); q.set_defaults(f=cmd_mark)
    a = p.parse_args(); sys.exit(a.f(a) or 0)
