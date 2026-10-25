"""Double-click launcher: isolated packages/data and optional Windows subtitle HUD."""
from pathlib import Path
import hashlib
import os
import socket
import subprocess
import sys
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent
_instance_lock = None


def claim_instance(runtime):
    """Hold an OS lock until this launcher exits, including dependency setup."""
    handle = (runtime / "launcher.lock").open("a+b")
    try:
        handle.seek(0)
        if not handle.read(1):
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError("Outra instancia do Orion ja esta iniciando ou em execucao. Use a janela existente.")
    return handle


def ensure_port_free(port=8765):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(f"A porta local {port} esta ocupada. Use o Orion existente ou feche o servico nessa porta antes de iniciar.")

def main():
    global _instance_lock
    os.chdir(ROOT)
    runtime = Path(os.environ.get("NMS_COMPANION_RUNTIME",ROOT/".runtime")).resolve()
    runtime.mkdir(parents=True,exist_ok=True)
    _instance_lock = claim_instance(runtime)
    ensure_port_free()
    packages = runtime/"packages"
    # Reuse this development checkout's already installed dependencies.
    if not os.environ.get("NMS_COMPANION_RUNTIME") and (ROOT/".packages"/"flask").exists():
        packages=ROOT/".packages"
    temp = runtime/"tmp";temp.mkdir(exist_ok=True)
    os.environ.update(TEMP=str(temp),TMP=str(temp),DOTNET_BUNDLE_EXTRACT_BASE_DIR=str(runtime/"dotnet"),HF_HOME=str(runtime/"huggingface"))
    requirements=ROOT/"requirements.txt"
    digest=hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp=runtime/"requirements.sha256"
    if not stamp.exists() or stamp.read_text().strip()!=digest:
        print("Preparando dependências do Orion…")
        subprocess.run([sys.executable,"-m","pip","install","--upgrade","--target",str(packages),"--cache-dir",str(runtime/"pip-cache"),"-r",str(requirements)],check=True)
        stamp.write_text(digest)
    mapping=ROOT/".runtime"/"helpers"/"nms-keymap.json"
    if not mapping.exists():
        import runpy
        try:
            runpy.run_path(str(ROOT/"setup-reader.py"))["setup"]()
        except Exception:
            print("Mapa de saves indisponível; diário e conversa continuam utilizáveis.")
    os.environ["PYTHONPATH"]=str(packages)+os.pathsep+str(ROOT)
    os.environ.setdefault("NMS_COMPANION_DATA",str(runtime/"userdata"))
    os.environ["ORION_DESKTOP"]="1" if "--desktop" in sys.argv else "0"
    timer=threading.Timer(2,lambda:webbrowser.open("http://127.0.0.1:8765"));timer.daemon=True;timer.start()
    try:
        subprocess.run([sys.executable,"-m","companion.app"],check=True)
    finally:
        timer.cancel()
        _instance_lock.close()
        _instance_lock = None

if __name__=="__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print("Não foi possível iniciar o Orion:",exc)
        input("Pressione Enter para fechar…")
