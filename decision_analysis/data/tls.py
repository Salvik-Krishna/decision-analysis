"""
TLS / CA-bundle helper.

Some Python builds (notably the MSYS2/UCRT64 interpreter on Windows) ship
without a usable default CA bundle, so HTTPS verification of public endpoints
(SEC EDGAR, Yahoo Finance) fails with CERTIFICATE_VERIFY_FAILED.  This module
locates a system CA bundle and wires it up *without* disabling verification.

Usage
-----
    from decision_analysis.data.tls import configure_tls
    ctx = configure_tls()          # also exports SSL_CERT_FILE for stdlib urlopen
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from typing import Optional

# Common locations for a PEM CA bundle, in priority order.
_CANDIDATES = [
    os.environ.get("SSL_CERT_FILE", ""),
    os.environ.get("REQUESTS_CA_BUNDLE", ""),
    r"C:\msys64\usr\ssl\certs\ca-bundle.crt",
    r"C:\msys64\usr\ssl\cert.pem",
    r"C:\msys64\etc\pki\ca-trust\extracted\pem\tls-ca-bundle.pem",
    "/c/msys64/usr/ssl/certs/ca-bundle.crt",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
]


def find_ca_bundle() -> Optional[str]:
    """Return the path to a usable PEM CA bundle, or None."""
    # If the default context already verifies, no override is needed.
    try:
        if ssl.create_default_context().cert_store_stats().get("x509_ca", 0) > 0:
            return os.environ.get("SSL_CERT_FILE") or None
    except Exception:
        pass

    for cand in _CANDIDATES:
        if cand and Path(cand).is_file():
            return cand
    return None


def configure_tls() -> ssl.SSLContext:
    """
    Build a *verified* SSL context using a discovered CA bundle, and export
    SSL_CERT_FILE so stdlib ``urlopen`` calls that don't take a context (e.g.
    the EDGAR scraper) also verify correctly.
    """
    bundle = find_ca_bundle()
    if bundle:
        os.environ["SSL_CERT_FILE"] = bundle
        os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)
        return ssl.create_default_context(cafile=bundle)
    # Fall back to the platform default (still verified).
    return ssl.create_default_context()
