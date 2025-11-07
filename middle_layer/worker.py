# -*- coding: utf-8 -*-
# middle_layer/worker.py
# JSON-Lines (一行一个 JSON) 协议的本机 Worker。
# C# 子进程启动本脚本；stdin 收请求、stdout 回响应。

import sys, os, json, traceback, contextlib
from pathlib import Path

# ---------- 让 Python 能 import backend 目录 ----------
PROJ_ROOT = Path(__file__).resolve().parents[1]           # .../Easy-Artistry-custom
BACKEND   = PROJ_ROOT / "backend"
os.chdir(PROJ_ROOT.as_posix())                            # 相对路径在项目根
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ---------- 导入你的门面函数 ----------
from backend.backend_main import generate_image_from_prompt  # 现有统一入口

# ---------- 方法注册表（后续功能只需在此注册即可） ----------
REGISTRY = {}
def register(ns: str, table: dict):
    for name, fn in table.items():
        REGISTRY[f"{ns}.{name}"] = fn

register("images", {
    "generate": generate_image_from_prompt,   # 现在只接这一个主功能
})

def dispatch(method: str, params: dict):
    fn = REGISTRY.get(method)
    if not fn:
        raise ValueError(f"Unknown method: {method}")
    return fn(**(params or {}))

# 避免 backend 里的 print 污染协议：把 stdout 暂时重定向到 stderr
@contextlib.contextmanager
def redirect_print_to_stderr():
    old = sys.stdout
    try:
        sys.stdout = sys.stderr
        yield
    finally:
        sys.stdout = old

def handle_one(line: str):
    req = json.loads(line)
    rid = req.get("id")
    try:
        with redirect_print_to_stderr():
            result = dispatch(req.get("method"), req.get("params") or {})
        out = {"id": rid, "result": result}
    except Exception:
        out = {
            "id": rid,
            "error": {
                "code": "E_RUNTIME",
                "message": "backend error",
                "trace": traceback.format_exc()
            }
        }
    sys.__stdout__.write(json.dumps(out, ensure_ascii=False) + "\n")
    sys.__stdout__.flush()

def main():
    # -u/无缓冲由 C# 进程负责；这里也保证按行处理。
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if not line.strip():
            continue
        handle_one(line)

if __name__ == "__main__":
    main()
