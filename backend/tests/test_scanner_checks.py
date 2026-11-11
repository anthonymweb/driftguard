import unittest

from driftguard.scanner.checks import (
    CATALOGUE,
    api_debug,
    cert_mismatch,
    http_plain,
    port_open,
    tls_legacy,
)


def ctx(target="eservices-lab", approved_ports=None, hostname="eservices-lab", url="https://eservices-lab:8443"):
    return {
        "target": target,
        "approved_ports": approved_ports or [],
        "hostname": hostname,
        "url": url,
    }


class CatalogueShapeTests(unittest.TestCase):
    def test_catalogue_contains_five_checks_in_orderable_structure(self):
        ids = {c.id for c in CATALOGUE}
        self.assertEqual(ids, {"tls-legacy", "cert-mismatch", "port-open", "http-plain", "api-debug"})
        for c in CATALOGUE:
            self.assertIn(c.area, {"TLS", "Network", "API"})
            self.assertTrue(c.title)
            self.assertTrue(c.severity)
            self.assertTrue(callable(c.run))

    def test_check_metadata(self):
        by_id = {c.id: c for c in CATALOGUE}
        self.assertEqual((by_id["tls-legacy"].area, by_id["tls-legacy"].severity), ("TLS", "high"))
        self.assertEqual((by_id["cert-mismatch"].area, by_id["cert-mismatch"].severity), ("TLS", "medium"))
        self.assertEqual((by_id["port-open"].area, by_id["port-open"].severity), ("Network", "high"))
        self.assertEqual((by_id["http-plain"].area, by_id["http-plain"].severity), ("Network", "medium"))
        self.assertEqual((by_id["api-debug"].area, by_id["api-debug"].severity), ("API", "high"))


class TlsLegacyTests(unittest.TestCase):
    def test_detects_tls10_or_tls11_offered(self):
        obs = {"testssl": {"protocols": {"TLS1": True, "TLS1_1": False, "TLS1_2": True, "TLS1_3": True}}}
        items = tls_legacy.run(obs, ctx())
        self.assertEqual(len(items), 1)
        ev = items[0]
        self.assertEqual(ev["fingerprint"], "eservices-lab/TLS/tls-legacy")
        self.assertEqual(ev["category"], "TLS")
        self.assertEqual(ev["severity"], "high")
        self.assertEqual(ev["title"], "Legacy TLS protocol accepted")
        self.assertIn("resource", ev)
        self.assertTrue(ev["details"].get("TLS1"))

        obs2 = {"testssl": {"protocols": {"TLS1": False, "TLS1_1": True, "TLS1_2": True}}}
        items2 = tls_legacy.run(obs2, ctx(target="svc"))
        self.assertEqual(items2[0]["fingerprint"], "svc/TLS/tls-legacy")
        self.assertTrue(items2[0]["details"].get("TLS1_1"))

    def test_no_finding_when_only_modern_tls(self):
        obs = {"testssl": {"protocols": {"TLS1": False, "TLS1_1": False, "TLS1_2": True, "TLS1_3": True}}}
        self.assertEqual(tls_legacy.run(obs, ctx()), [])

    def test_no_finding_when_observation_missing(self):
        self.assertEqual(tls_legacy.run({}, ctx()), [])


class CertMismatchTests(unittest.TestCase):
    def test_detects_mismatched_certificate(self):
        obs = {"testssl": {"cert": {"cert_commonName": "wrong.example", "cert_subjectAltName": "DNS:wrong.example"}}}
        items = cert_mismatch.run(obs, ctx(hostname="eservices-lab"))
        self.assertEqual(len(items), 1)
        ev = items[0]
        self.assertEqual(ev["fingerprint"], "eservices-lab/TLS/cert-mismatch")
        self.assertEqual(ev["category"], "TLS")
        self.assertEqual(ev["severity"], "medium")
        self.assertEqual(ev["title"], "Certificate hostname mismatch")
        self.assertEqual(ev["resource"], "eservices-lab")
        self.assertIn("cert", ev["details"])

    def test_no_finding_when_certificate_matches_hostname(self):
        obs = {"testssl": {"cert": {"cert_commonName": "eservices-lab", "cert_subjectAltName": "DNS:eservices-lab"}}}
        self.assertEqual(cert_mismatch.run(obs, ctx(hostname="eservices-lab")), [])

    def test_no_finding_when_san_matches(self):
        obs = {"testssl": {"cert": {"cert_subjectAltName": "DNS:other, DNS:eservices-lab.local"}}}
        self.assertEqual(cert_mismatch.run(obs, ctx(hostname="eservices-lab.local")), [])

    def test_no_finding_when_observation_missing(self):
        self.assertEqual(cert_mismatch.run({}, ctx()), [])

    def test_unrelated_certificate_field_containing_the_hostname_does_not_match(self):
        # Only the CN and the SANs name the host. A certificate that merely
        # mentions the hostname in some other field has not matched it.
        obs = {"testssl": {"cert": {
            "cert_commonName": "wrong.example",
            "cert_subjectAltName": "DNS:wrong.example",
            "cert_issuer": "CN=eservices-lab, O=Unrelated Field",
        }}}
        items = cert_mismatch.run(obs, ctx(hostname="eservices-lab"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["fingerprint"], "eservices-lab/TLS/cert-mismatch")

    def test_wildcard_certificate_matches_a_single_label_subdomain(self):
        obs = {"testssl": {"cert": {"cert_subjectAltName": "DNS:*.example.test"}}}
        self.assertEqual(cert_mismatch.run(obs, ctx(hostname="www.example.test")), [])
        # a wildcard covers one label only, not a deeper name
        self.assertEqual(len(cert_mismatch.run(obs, ctx(hostname="a.b.example.test"))), 1)


class PortOpenTests(unittest.TestCase):
    def test_reports_unapproved_open_port(self):
        obs = {"nmap": {"open_ports": [{"port": 8081, "state": "open", "service": "http", "version": ""}]}}
        items = port_open.run(obs, ctx(approved_ports=[8443, 8080]))
        self.assertEqual(len(items), 1)
        ev = items[0]
        self.assertEqual(ev["fingerprint"], "eservices-lab/Network/port-open")
        self.assertEqual(ev["category"], "Network")
        self.assertEqual(ev["severity"], "high")
        self.assertEqual(ev["title"], "Unexpected open port")
        self.assertEqual(ev["resource"], "8081")
        self.assertEqual(ev["details"]["port"], 8081)

    def test_approved_port_produces_no_finding(self):
        obs = {"nmap": {"open_ports": [{"port": 8443, "state": "open", "service": "https", "version": ""}]}}
        self.assertEqual(port_open.run(obs, ctx(approved_ports=[8443, 8080])), [])

    def test_mixed_ports_only_reports_unapproved(self):
        obs = {"nmap": {"open_ports": [
            {"port": 8443, "state": "open", "service": "https", "version": ""},
            {"port": 8081, "state": "open", "service": "http", "version": "nginx"},
        ]}}
        items = port_open.run(obs, ctx(approved_ports=[8443]))
        self.assertEqual([i["resource"] for i in items], ["8081"])
        self.assertEqual(items[0]["fingerprint"], "eservices-lab/Network/port-open")

    def test_no_finding_when_no_open_ports(self):
        obs = {"nmap": {"open_ports": []}}
        self.assertEqual(port_open.run(obs, ctx(approved_ports=[8443])), [])

    def test_no_finding_when_observation_missing(self):
        self.assertEqual(port_open.run({}, ctx(approved_ports=[8443])), [])


class HttpPlainTests(unittest.TestCase):
    def test_detects_plain_http_without_https_redirect(self):
        obs = {"httpx": {"status_code": 200, "scheme": "http", "location": None, "final_url": "http://svc:8080/"}}
        items = http_plain.run(obs, ctx(target="democommerce", url="http://democommerce:8080"))
        self.assertEqual(len(items), 1)
        ev = items[0]
        self.assertEqual(ev["fingerprint"], "democommerce/Network/http-plain")
        self.assertEqual(ev["category"], "Network")
        self.assertEqual(ev["severity"], "medium")
        self.assertEqual(ev["title"], "Plain HTTP without redirect to HTTPS")
        self.assertEqual(ev["resource"], "http://democommerce:8080")
        self.assertEqual(ev["details"]["status_code"], 200)

    def test_no_finding_when_redirects_to_https(self):
        obs = {"httpx": {"status_code": 301, "scheme": "http", "location": "https://svc/", "final_url": "http://svc/"}}
        self.assertEqual(http_plain.run(obs, ctx(url="http://svc/")), [])

    def test_no_finding_when_already_https(self):
        obs = {"httpx": {"status_code": 200, "scheme": "https", "location": None, "final_url": "https://svc/"}}
        self.assertEqual(http_plain.run(obs, ctx(url="https://svc/")), [])

    def test_no_finding_when_observation_missing(self):
        self.assertEqual(http_plain.run({}, ctx()), [])


class ApiDebugTests(unittest.TestCase):
    def test_detects_sensitive_path_answering_without_auth(self):
        obs = {"gobuster": {"found": [{"path": "/api/v1/admin/debug", "status": 200, "size": 123}]}}
        items = api_debug.run(obs, ctx())
        self.assertEqual(len(items), 1)
        ev = items[0]
        self.assertEqual(ev["fingerprint"], "eservices-lab/API/api-debug")
        self.assertEqual(ev["category"], "API")
        self.assertEqual(ev["severity"], "high")
        self.assertEqual(ev["title"], "Sensitive or administrative path exposed")
        self.assertEqual(ev["resource"], "/api/v1/admin/debug")
        self.assertEqual(ev["details"]["status"], 200)

    def test_no_finding_for_404_path(self):
        obs = {"gobuster": {"found": [{"path": "/api/v1/admin/debug", "status": 404, "size": 0}]}}
        self.assertEqual(api_debug.run(obs, ctx()), [])

    def test_no_finding_for_a_redirect_to_a_sign_in_page(self):
        # A 3xx discloses nothing: it is the server sending the visitor
        # somewhere else (a sign-in page), not the sensitive content.
        obs = {"gobuster": {"found": [{"path": "/admin", "status": 302, "size": 0}]}}
        self.assertEqual(api_debug.run(obs, ctx()), [])

    def test_no_finding_for_auth_required(self):
        obs = {"gobuster": {"found": [{"path": "/api/v1/admin/debug", "status": 401, "size": 0}]}}
        self.assertEqual(api_debug.run(obs, ctx()), [])
        obs2 = {"gobuster": {"found": [{"path": "/api/v1/admin/debug", "status": 403, "size": 0}]}}
        self.assertEqual(api_debug.run(obs2, ctx()), [])

    def test_no_finding_when_none_found(self):
        obs = {"gobuster": {"found": []}}
        self.assertEqual(api_debug.run(obs, ctx()), [])

    def test_no_finding_when_observation_missing(self):
        self.assertEqual(api_debug.run({}, ctx()), [])


if __name__ == "__main__":
    unittest.main()
