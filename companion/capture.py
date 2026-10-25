from __future__ import annotations
import ctypes
import io
import json
import os
import subprocess
import uuid
from pathlib import Path
from .config import DATA_DIR

def game_rectangle():
    if os.name != "nt":
        raise ValueError("A captura automática exige Windows. Use o envio de imagem.")
    from ctypes import wintypes
    user = ctypes.windll.user32
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowTextW.argtypes = [wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user.GetWindowRect.argtypes = [wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    matches = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def inspect(hwnd, _):
        title = ctypes.create_unicode_buffer(512)
        user.GetWindowTextW(hwnd,title,512)
        if user.IsWindowVisible(hwnd) and ("no man's sky" in title.value.casefold() or "no man’s sky" in title.value.casefold()):
            rect = wintypes.RECT()
            if user.GetWindowRect(hwnd,ctypes.byref(rect)) and rect.right>rect.left and rect.bottom>rect.top:
                matches.append((rect.left,rect.top,rect.right,rect.bottom))
        return True
    callback = callback_type(inspect)
    user.EnumWindows(callback,0)
    if not matches:
        raise ValueError("Janela de No Man's Sky não encontrada. Use modo sem bordas ou envie uma imagem.")
    return matches[0]

def image_path(profile, ident):
    if not ident or not all(c in "0123456789abcdef" for c in ident) or len(ident)!=32:
        raise ValueError("Imagem inválida.")
    return DATA_DIR / "captures" / profile / (ident+".png")

def save_image(profile, raw=None):
    from PIL import Image, ImageGrab
    if raw is None:
        image = ImageGrab.grab(bbox=game_rectangle(),all_screens=True)
    else:
        if len(raw)>12*1024*1024:
            raise ValueError("Envie uma imagem de até 12 MB.")
        image = Image.open(io.BytesIO(raw))
        if image.width*image.height>25_000_000:
            raise ValueError("Imagem grande demais.")
        image.load()
    image.thumbnail((2560,1440))
    ident = uuid.uuid4().hex
    path = image_path(profile,ident)
    path.parent.mkdir(parents=True,exist_ok=True)
    image.convert("RGB").save(path)
    return ident,path

def windows_ocr(path):
    if os.name != "nt":
        return {"text":"","error":"OCR automático disponível no Windows; preencha a observação manualmente."}
    script = Path(__file__).with_name("windows_ocr.ps1")
    try:
        code = script.read_text(encoding="utf-8").split("\n",1)[1]
        env = {**os.environ,"ORION_OCR_IMAGE":str(path.resolve())}
        result = subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command","$ImagePath=$env:ORION_OCR_IMAGE\n"+code],env=env,capture_output=True,timeout=25,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if result.returncode:
            raise ValueError("OCR do Windows indisponível. Instale o pacote de idioma OCR do Windows ou preencha a observação.")
        return {"text":json.loads(result.stdout.decode("utf-8-sig"))["text"],"error":None}
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return {"text":"","error":"OCR não respondeu. A imagem foi salva; descreva o que vê e confirme."}

def capture(profile, raw=None):
    ident,path = save_image(profile,raw)
    return {"id":ident,"profile":profile,"image_url":f"/api/captures/{ident}?profile={profile}","source":"screenshot","requires_review":True,**ocr(path)}

_ocr_engine = None
_ocr_lock = __import__("threading").Lock()

def ocr(path):
    native = windows_ocr(path)
    if not native.get("error"):
        native["engine"] = "Windows OCR"
        return native
    try:
        global _ocr_engine
        with _ocr_lock:
            from rapidocr_onnxruntime import RapidOCR
            if _ocr_engine is None:
                _ocr_engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
            result,_ = _ocr_engine(str(path))
        rows = result or []
        return {"text":"\n".join(str(row[1]) for row in rows), "error":None,
                "engine":"RapidOCR CPU","confidence":round(sum(float(row[2]) for row in rows)/len(rows),3) if rows else None}
    except Exception:
        return native
