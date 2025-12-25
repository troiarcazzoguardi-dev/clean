#!/usr/bin/env python3
import subprocess
import sys

def run(cmd):
    """Esegue un comando shell e stampa output live"""
    print(f"$ {' '.join(cmd)}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        print(f"✖ ERROR: comando fallito -> {' '.join(cmd)}")
        sys.exit(process.returncode)

def main():
    # Controlla permessi root
    import os
    if os.geteuid() != 0:
        print("❌ Devi eseguire questo script come root")
        sys.exit(1)

    print("🛠️  GRUB invisibile - reinstallazione su /dev/vda3")
    
    # 1️⃣ Forza reinstallazione GRUB sul disco principale
    run(["grub-install", "/dev/vda3"])
    run(["update-grub"])

    # 2️⃣ Scrive /etc/default/grub per nascondere il menu
    grub_conf = """GRUB_TIMEOUT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_HIDDEN_TIMEOUT=0
GRUB_DISABLE_RECOVERY=true
GRUB_DISABLE_SUBMENU=true
GRUB_FORCE_HIDDEN_MENU=true
GRUB_RECORDFAIL_TIMEOUT=0
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=0 systemd.show_status=false vt.global_cursor_default=0"
"""
    with open("/etc/default/grub", "w") as f:
        f.write(grub_conf)
    print("✔ /etc/default/grub aggiornato")

    # 3️⃣ Aggiorna GRUB con le nuove impostazioni
    run(["update-grub"])

    print("\n✅ GRUB reinstallato e menu nascosto con successo!")

if __name__ == "__main__":
    main()
