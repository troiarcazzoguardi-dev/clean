#!/usr/bin/env python3
import os
import subprocess
import sys
import time

COMMANDS = [
    ("Stop ClamAV services",
     ["systemctl", "stop", "clamav-daemon", "clamav-freshclam"]),

    ("Purge all ClamAV packages",
     ["apt", "purge", "clamav*", "-y"]),

    ("Remove leftover directories",
     ["rm", "-rf", "/var/lib/clamav", "/etc/clamav"]),

    ("Reconfigure dpkg",
     ["dpkg", "--configure", "-a"]),

    ("Fix broken packages",
     ["apt", "--fix-broken", "install", "-y"]),

    ("Update package list",
     ["apt", "update"]),

    ("Reinstall ClamAV",
     ["apt", "install", "clamav", "clamav-daemon", "-y"]),

    ("Update virus database",
     ["freshclam"]),

    ("Start ClamAV services",
     ["systemctl", "start", "clamav-daemon", "clamav-freshclam"]),
]


def run_command(title, cmd):
    print(f"\n\033[1;34m▶ {title}\033[0m")
    print(f"\033[90m$ {' '.join(cmd)}\033[0m\n")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if process.returncode != 0:
        print(f"\n\033[1;31m✖ ERROR in step: {title}\033[0m")
        sys.exit(process.returncode)

    print(f"\033[1;32m✔ Done: {title}\033[0m")


def main():
    if os.geteuid() != 0:
        print("❌ This script must be run as root (use sudo)")
        sys.exit(1)

    print("\n🛠️  ClamAV / DPKG Auto-Repair Tool")
    print("=================================")

    for title, cmd in COMMANDS:
        run_command(title, cmd)
        time.sleep(1)

    print("\n\033[1;32m✅ SYSTEM FIXED — dpkg & ClamAV OK\033[0m\n")


if __name__ == "__main__":
    main()
