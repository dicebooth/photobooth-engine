"""
Self-signed TLS certificate for the web portal.
Browsers expose the camera (used by the QR scanner) only on HTTPS pages, so the portal is served over TLS.
The certificate is created once with the openssl CLI and then reused: phones that already accepted it
are not asked again.
"""
import os
import subprocess

CERT_DIR = "web-cert"
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"
CERT_VALIDITY_DAYS = 825


def ensure_certificate(ips: list, cert_dir: str = CERT_DIR) -> tuple:
    """
    Method which returns the portal certificate, generating it if missing.
    :param ips: IP addresses to include in the certificate subject alternative names
    :param cert_dir: folder where certificate and key are stored
    :return: (certificate path, key path)
    """

    cert_path = os.path.join(cert_dir, CERT_FILE)
    key_path = os.path.join(cert_dir, KEY_FILE)
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    os.makedirs(cert_dir, exist_ok=True)
    alt_names = ",".join(["DNS:localhost", "IP:127.0.0.1"] + [f"IP:{ip}" for ip in ips if ip != "127.0.0.1"])
    try:
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
             "-days", str(CERT_VALIDITY_DAYS), "-subj", "/CN=Photobooth",
             "-keyout", key_path, "-out", cert_path, "-addext", f"subjectAltName={alt_names}"],
            check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("openssl not found: install it or start the portal with --web-http")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"unable to create the portal certificate: {e.stderr.strip()}")

    os.chmod(key_path, 0o600)
    return cert_path, key_path
