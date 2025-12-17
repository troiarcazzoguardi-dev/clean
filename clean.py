#!/usr/bin/env python3
import subprocess
import os

print("Pulizia /var in corso...")

# 1. Log systemd
print("Pulizia log systemd...")
subprocess.run(["journalctl", "--vacuum-size=500M"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["journalctl", "--vacuum-time=7d"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 2. Log tradizionali
print("Pulizia log tradizionali /var/log...")
log_files = [f for f in os.listdir("/var/log") if f.endswith(".log") or f.endswith(".log.1") or f.endswith(".gz")]
for lf in log_files:
    path = os.path.join("/var/log", lf)
    try:
        if lf.endswith(".log"):
            open(path, "w").close()  # tronca il file
        else:
            os.remove(path)          # rimuove i log compressi
    except:
        pass

# 3. Cache APT
print("Pulizia cache APT...")
subprocess.run(["apt", "clean"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["apt", "autoclean"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 4. Temp files
print("Pulizia /var/tmp...")
subprocess.run(["rm", "-rf", "/var/tmp/*"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 5. Spool mail/cron
print("Pulizia /var/spool...")
subprocess.run(["rm", "-rf", "/var/spool/cron/*"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["rm", "-rf", "/var/spool/mail/*"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 6. Controllo finale
print("Spazio occupato in /var dopo pulizia:")
subprocess.run(["du", "-sh", "/var"])

print("Pulizia completata.")
