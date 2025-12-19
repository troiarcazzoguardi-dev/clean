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
# 1. Install hping3 + dipendenze
# =============================
run("apt update")
run("apt install -y hping3 git curl build-essential libssl-dev zlib1g-dev libncurses5-dev libffi-dev libreadline-dev")

# =============================
# 2. setcap su hping3
# =============================
HPING = "/usr/sbin/hping3"
if os.path.exists(HPING):
    run(f"setcap cap_net_raw+ep {HPING}")

# =============================
# 3. PATH globale (niente /sbin/)
# =============================
with open("/root/.bashrc", "a") as f:
    f.write("\nexport PATH=$PATH:/sbin:/usr/sbin\n")

# =============================
# 4. Disabilita Ctrl+Alt+Del / Power / Suspend
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

# logind.conf
logind = "/etc/systemd/logind.conf"
lines = []
if os.path.exists(logind):
    with open(logind, "r") as f:
        lines = f.readlines()

def set_conf(key, value):
    global lines
    found = False
    for i,l in enumerate(lines):
        if l.strip().startswith(key):
            lines[i] = f"{key}={value}\n"
            found = True
    if not found:
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
# 5. Install Python 3.10 ufficiale
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
# 7. Clone bot + avvio nohup
# =============================
run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")
run("cd /root/bott && nohup /usr/local/bin/python3.10 bott.py > bot.log 2>&1 &")

print("\n[✓] TUTTO COMPLETATO")