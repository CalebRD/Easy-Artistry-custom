# helper_local_sd.py
import subprocess, time, requests, psutil

def start_sd(port=7860) -> subprocess.Popen:
    proc = subprocess.Popen(
        ["python", "program_main\serve_local_sd.py", "--port", str(port)]
    )
    _wait_ready(port)
    return proc

def _wait_ready(port, timeout=90):
    url = f"http://127.0.0.1:{port}/sdapi/v1/sd-models"
    for _ in range(timeout):
        try:
            requests.get(url, timeout=2)
            return
        except requests.exceptions.RequestException:
            time.sleep(1)
    raise TimeoutError("WebUI start timeout")

def stop_sd(proc: subprocess.Popen, port=7860):
    try:
        requests.post(f"http://127.0.0.1:{port}/shutdown", timeout=2)
    except requests.exceptions.RequestException:
        pass
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    # double-check if any process is still using the port
    for p in psutil.process_iter(["pid", "connections"]):
        for c in p.info["connections"]:
            if c.laddr.port == port:
                p.kill()
 
# ==================== demo ====================
if __name__ == "__main__":
    proc = start_sd(7860)                      # launch WebUI
    print("WebUI started, waiting for it to be ready,enter 'stop' to quit.")
    try:
        # simple interactive loop
        while True:
            cmd = input(">>> type 'stop' to quit: ").strip().lower()
            if cmd in {"stop", "exit", "q"}:
                break                          # leave the loop
    except KeyboardInterrupt:                  # allow Ctrl‑C as well
        pass
    finally:
        stop_sd(proc, 7860)                    # graceful shutdown
