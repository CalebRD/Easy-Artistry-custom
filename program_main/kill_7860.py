# kill_7860.py
import psutil
for p in psutil.process_iter(["pid", "connections"]):
    for c in p.info["connections"]:
        if c.laddr and c.laddr.port == 7860:
            print("Killing PID", p.pid)
            p.kill()
