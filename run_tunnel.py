import subprocess
import time
import re
import sys
import os

print("[Tunnel Manager] Starting localhost.run SSH tunnel on 127.0.0.1:5000...")
cmd = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=5",
    "-R", "80:127.0.0.1:5000",
    "nokey@localhost.run"
]

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

public_url = None
start_time = time.time()

while time.time() - start_time < 30:
    line = proc.stdout.readline()
    if not line:
        time.sleep(0.5)
        continue
    print(line.strip())
    match = re.search(r'(https://[a-zA-Z0-9\.\-]+\.lhr\.life)', line)
    if match:
        public_url = match.group(1)
        print("\n" + "="*60)
        print(f">>> PUBLIC LIVE WEBSITE URL: {public_url}")
        print("="*60 + "\n")
        with open("public_url.txt", "w", encoding="utf-8") as f:
            f.write(public_url + "\n")
        sys.stdout.flush()
        break

if not public_url:
    print("[Tunnel Manager] Could not extract public URL within timeout.")

# Keep process alive
proc.wait()
