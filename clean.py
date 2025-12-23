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
# 3. PATH
# =============================
with open("/root/.bashrc", "a") as f:
    f.write("\nexport PATH=$PATH:/sbin:/usr/sbin\n")

# =============================
# 4. POWER / REBOOT LOCK
# =============================
for t in [
    "ctrl-alt-del.target",
    "poweroff.target",
    "reboot.target",
    "suspend.target",
    "hibernate.target"
]:
    run(f"systemctl mask {t}")

# =============================
# 5. GRUB PASSWORD **PLAINTEXT**
# =============================
GRUB_PASSWORD = "kali55757"
GRUB_CUSTOM = "/etc/grub.d/40_custom"

print("[+] Impostazione password GRUB IN CHIARO (no hash)")

with open(GRUB_CUSTOM, "w") as f:
    f.write(f"""set superusers="root"
password root {GRUB_PASSWORD}
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
# 7. Bot
# =============================
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15", fatal=True)

run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 8. systemd service
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

[Install]
WantedBy=multi-user.target
""")

run("systemctl daemon-reload")
run("systemctl enable bott")
run("systemctl start bott")

print("\n[✓] COMPLETATO: GRUB CON PASSWORD IN CHIARO – SISTEMA AVVIATO")
