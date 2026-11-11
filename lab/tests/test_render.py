# tests/test_render.py
import unittest

from domain import ROOT
from domain.render import render

REFERENCE_TEMPLATE = ROOT / "eservices-lab" / "nginx" / "site.conf.tpl"


class RenderTests(unittest.TestCase):
    def test_substitutes_all_placeholders(self):
        template = ("{{HTTP_BLOCK}}\n"
                    "    ssl_certificate     /etc/nginx/certs/{{CERT}}.crt;\n"
                    "    ssl_protocols {{SSL_PROTOCOLS}};\n"
                    "{{SSL_CIPHERS}}\n")
        out = render(template, {
            "HTTP_BLOCK": "return 301 https://$host$request_uri;",
            "CERT": "localhost",
            "SSL_PROTOCOLS": "TLSv1.2 TLSv1.3",
            "SSL_CIPHERS": "    ssl_ciphers ALL:@SECLEVEL=0;",
        })
        self.assertEqual(
            out,
            "return 301 https://$host$request_uri;\n"
            "    ssl_certificate     /etc/nginx/certs/localhost.crt;\n"
            "    ssl_protocols TLSv1.2 TLSv1.3;\n"
            "    ssl_ciphers ALL:@SECLEVEL=0;\n")
        self.assertNotIn("{{", out)

    def test_rejects_leftover_placeholder(self):
        with self.assertRaises(ValueError):
            render("{{A}} {{B}}", {"A": "1"})

    def test_leaves_nginx_variables_untouched(self):
        self.assertIn("$host", render("return 301 https://$host$request_uri;", {}))

    def test_reference_template_renders_every_placeholder(self):
        # the shared site.conf.tpl carries HTTP_BLOCK, CERT (twice), SSL_PROTOCOLS,
        # SSL_CIPHERS and DEBUG_LOCATION — all five must resolve in one pass
        out = render(REFERENCE_TEMPLATE.read_text(), {
            "HTTP_BLOCK": "return 301 https://$host$request_uri;",
            "CERT": "localhost",
            "SSL_PROTOCOLS": "TLSv1.2 TLSv1.3",
            "SSL_CIPHERS": "    ssl_ciphers ALL:@SECLEVEL=0;",
            "DEBUG_LOCATION": "    location = /api/v1/admin/debug { return 403; }",
        })
        self.assertNotIn("{{", out)
        self.assertIn("ssl_certificate     /etc/nginx/certs/localhost.crt;", out)
        self.assertIn("return 301 https://$host$request_uri;", out)


if __name__ == "__main__":
    unittest.main()
