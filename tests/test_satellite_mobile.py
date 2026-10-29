"""Page mobile du satellite et choix du certificat TLS."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from core import satellite, tls_lan


class PageMobileTests(unittest.TestCase):
    def test_page_servie_sur_le_listener_lan_seulement(self):
        client = TestClient(satellite._app_lan())
        r = client.get("/mobile")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Jarvis", r.text)
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertEqual(r.headers["x-frame-options"], "DENY")

    def test_la_page_ne_contient_aucun_secret(self):
        texte = (Path(satellite.__file__).parent.parent / "web" / "mobile.html").read_text(encoding="utf-8")
        for interdit in ("gsk_", "sk-"):
            self.assertNotIn(interdit, texte)

    def test_certificat_tailscale_utilise_si_present(self):
        with TemporaryDirectory() as d:
            crt, cle = Path(d, "a.crt"), Path(d, "a.key")
            crt.write_text("x"); cle.write_text("y")
            valeurs = {"satellite_lan.certificat_tailscale": str(crt),
                       "satellite_lan.cle_tailscale": str(cle)}
            with patch("core.config.reglage", lambda k, d=None: valeurs.get(k, d)):
                self.assertEqual(tls_lan.certificat_tls(), (crt, cle))

    def test_repli_auto_signe_si_fichiers_absents(self):
        valeurs = {"satellite_lan.certificat_tailscale": "/nope.crt",
                   "satellite_lan.cle_tailscale": "/nope.key"}
        with patch("core.config.reglage", lambda k, d=None: valeurs.get(k, d)), \
             patch.object(tls_lan, "assurer_certificat", return_value=("auto", "cle")):
            self.assertEqual(tls_lan.certificat_tls(), ("auto", "cle"))


if __name__ == "__main__":
    unittest.main()
