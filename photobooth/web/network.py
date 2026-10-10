"""
Helpers to find how the portal can be reached from the local network and print it on the terminal.
"""
import ipaddress
import re
import socket
import subprocess


def _interface_ips() -> list:
    """
    Method which lists the IPv4 addresses of all network interfaces, using 'ip' (Linux) or 'ifconfig' (macOS).
    :return: list of IPv4 addresses as strings
    """

    for cmd in (["ip", "-4", "-o", "addr", "show"], ["ifconfig"]):
        try:
            output = subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        ips = re.findall(r"inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)", output)
        if ips:
            return ips
    return []


def _default_route_ip() -> str:
    """
    Method which returns the IP address of the interface used for the default route.
    No packet is actually sent: connecting a UDP socket only selects the outgoing interface.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def get_lan_ips() -> list:
    """
    Method which returns the addresses the portal can be reached at, best candidate first.
    Private LAN addresses (192.168.x.x, 10.x.x.x, 172.16-31.x.x) are preferred over VPN ones (e.g. Tailscale 100.x.x.x),
    since the default route may go through a VPN while the smartphone is on the local Wi-Fi.
    :return: list of IPv4 addresses, ['127.0.0.1'] if no network is available
    """

    candidates = []
    for ip in _interface_ips() + [_default_route_ip()]:
        addr = ipaddress.ip_address(ip)
        if addr.is_loopback or addr.is_link_local or ip in candidates:
            continue
        candidates.append(ip)

    candidates.sort(key=lambda ip: not ipaddress.ip_address(ip).is_private)
    return candidates or ["127.0.0.1"]


def print_connection_info(host: str, port: int, token: str, https: bool):
    """
    Method which prints the portal address and, if the qrcode package is installed, a QR code to scan with the smartphone.
    :param host: address the server is bound to
    :param port: server port
    :param token: access token required by the portal API
    :param https: whether the portal is served over HTTPS
    """

    ips = get_lan_ips() if host in ("0.0.0.0", "") else [host]
    ip = ips[0]
    url = f"{'https' if https else 'http'}://{ip}:{port}/?t={token}"

    lines = [
        "WEB PORTAL ATTIVO",
        "Collega lo smartphone alla stessa rete Wi-Fi e apri:",
        f"  {url}",
        "",
        f"  IP:     {ip}",
        f"  Porta:  {port}",
        f"  Token:  {token}",
        f"  Host:   {socket.gethostname()}",
    ]
    if len(ips) > 1:
        lines.append(f"  Altri indirizzi: {', '.join(ips[1:])}")
    if https:
        lines += [
            "",
            "Certificato self-signed: al primo accesso il browser mostra un avviso.",
            "Su iPhone: 'Mostra dettagli' > 'visita questo sito web' > conferma.",
        ]
    width = max(len(line) for line in lines) + 4
    print()
    print("=" * width)
    for line in lines:
        print(f"  {line}")
    print("=" * width)

    try:
        import qrcode
        qr = qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make(fit=True)
        # invert=True renders dark modules as spaces: scannable on dark terminal themes
        qr.print_ascii(invert=True)
    except ImportError:
        print("(installa il pacchetto 'qrcode' per mostrare il codice QR: pip install qrcode)")

    if ip.startswith("127."):
        print("ATTENZIONE: nessuna rete locale rilevata, il portale e' raggiungibile solo da questo computer.")
    print()
