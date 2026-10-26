"""Windows hotkeys and subtitle HUD. Audio work never runs on a UI thread."""
from __future__ import annotations
import ctypes
import io
import os
import queue
import threading
import wave
from collections import deque

from .config import load_config


class Desktop:
    MAX_AUDIO_BYTES = 16000 * 2 * 60

    def __init__(self):
        self.events = deque(maxlen=100)
        self.lock = threading.Lock()
        self._state = threading.RLock()
        self.seq = 0
        self._profile = "default"
        self.recording = None
        self.record_profile = None
        self.frames = []
        self._audio_bytes = 0
        self._epoch = 0
        self._record_serial = 0
        self._timer = None
        self._commands = queue.Queue(maxsize=8)
        self._worker = None
        self._transcribing = False
        self._capturing = False
        self.stopped = threading.Event()
        self.transcribe = None
        self.hotkeys = {}
        self.hotkey_errors = {}
        self.subtitle = "Ori pronto · F8 falar · F9 parar · F10 capturar"
        self.notice = ""
        self.started = False
        self.interrupt = None

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, value):
        self.set_profile(value)

    def set_profile(self, value):
        with self._state:
            if value == self._profile:
                return
            self._profile = value
            self._epoch += 1
        if self.interrupt:
            self.interrupt()
        self._enqueue("cancel")

    def emit(self, kind, profile=None, **data):
        if kind == "stop":
            with self._state:
                self._epoch += 1
            if self.interrupt:
                self.interrupt()
            self._enqueue("cancel")
        with self.lock:
            self.seq += 1
            self.events.append({"id": self.seq, "type": kind,
                                "profile": profile or self.profile, **data})

    def since(self, cursor):
        with self.lock:
            return [dict(e) for e in self.events if e["id"] > cursor]

    def _enqueue(self, command, epoch=None):
        if self.stopped.is_set():
            return
        with self._state:
            if self._worker is None:
                self._worker = threading.Thread(target=self._audio_worker, daemon=True)
                self._worker.start()
            try:
                self._commands.put_nowait((command, self._epoch if epoch is None else epoch))
            except queue.Full:
                # Cancel/close also invalidate epochs; the worker checks them even
                # when the bounded command queue cannot accept another message.
                pass

    def toggle_record(self):
        self._enqueue("toggle")

    def _audio_worker(self):
        while not self.stopped.is_set():
            try:
                command, epoch = self._commands.get(timeout=.1)
            except queue.Empty:
                command, epoch = "check", self._epoch
            try:
                if self.recording is not None and self._record_epoch != self._epoch:
                    self._finish_record(False)
                if epoch != self._epoch:
                    continue
                if command == "cancel":
                    self._finish_record(False)
                elif isinstance(command, tuple) and command[0] == "finish":
                    if command[1] == self._record_serial:
                        self._finish_record(True)
                elif command == "toggle":
                    if self.recording is not None:
                        self._finish_record(True)
                    elif not self._transcribing:
                        self._begin_record(epoch)
            except Exception as exc:
                self.emit("notice", text=f"Microfone indisponível: {exc}")
        self._finish_record(False)

    def _begin_record(self, epoch):
        import sounddevice as sd
        nms_mode = bool(load_config().get("nms_mode"))
        recording_limit_seconds = 20 if nms_mode else self.MAX_AUDIO_BYTES // (16000 * 2)
        max_audio_bytes = 16000 * 2 * recording_limit_seconds
        if self.interrupt:
            self.interrupt()
        # Stop browser speech without invalidating this newly requested recording.
        with self.lock:
            self.seq += 1
            self.events.append({"id": self.seq, "type": "stop", "profile": self.profile})
        profile = self.profile
        self._record_serial += 1
        serial = self._record_serial
        frames = []
        self.frames = frames
        self._audio_bytes = 0
        def callback(data, *_):
            with self._state:
                if epoch != self._epoch or self.stopped.is_set():
                    return
                remaining = max_audio_bytes - self._audio_bytes
                chunk = bytes(data)[:max(0, remaining)]
                if chunk:
                    frames.append(chunk)
                    self._audio_bytes += len(chunk)
                if self._audio_bytes >= max_audio_bytes:
                    self._enqueue(("finish", serial), epoch)
        stream = None
        try:
            stream = sd.RawInputStream(samplerate=16000, channels=1,
                                       dtype="int16", callback=callback)
            self.recording = stream
            self.record_profile = profile
            self._record_epoch = epoch
            stream.start()
            if epoch != self._epoch or self.stopped.is_set():
                self._finish_record(False)
                return
            self.emit("notice", profile, text=f"Gravando · F8 envia · F9 cancela · limite {recording_limit_seconds} s")
            self._timer = threading.Timer(recording_limit_seconds, lambda: self._enqueue(("finish", serial), epoch))
            self._timer.daemon = True
            self._timer.start()
        except Exception:
            self._finish_record(False)
            raise

    def _finish_record(self, submit):
        stream, self.recording = self.recording, None
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if stream is None:
            return
        try:
            # abort discards pending input; it does not wait for queued audio.
            stream.abort()
        except Exception as exc:
            self.emit("notice", text=f"Erro ao parar microfone: {exc}")
        finally:
            try:
                stream.close()
            except Exception as exc:
                self.emit("notice", text=f"Erro ao fechar microfone: {exc}")
        with self._state:
            audio = b"".join(self.frames) if submit else b""
            self.frames = []
            self._audio_bytes = 0
            epoch, profile = self._record_epoch, self.record_profile
            if not audio or epoch != self._epoch or self.stopped.is_set() or self._transcribing:
                return
            self._transcribing = True
        self.emit("notice", profile, text="Transcrevendo no computador.")
        def process():
            try:
                output = io.BytesIO()
                with wave.open(output, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    wav.writeframes(audio)
                text = self.transcribe(output.getvalue(), ".wav")
                with self._state:
                    if text and epoch == self._epoch and not self.stopped.is_set():
                        self.emit("transcript", profile, text=text)
            except Exception as exc:
                if epoch == self._epoch and not self.stopped.is_set():
                    self.emit("notice", profile, text=str(exc))
            finally:
                with self._state:
                    self._transcribing = False
        threading.Thread(target=process, daemon=True).start()

    def scan(self):
        with self._state:
            if self.stopped.is_set() or self._capturing:
                return
            self._capturing = True
            profile, epoch = self.profile, self._epoch
        def process():
            try:
                from .capture import capture
                result = capture(profile)
                with self._state:
                    if epoch == self._epoch and not self.stopped.is_set():
                        self.emit("capture", profile, scan=result)
            except Exception as exc:
                if epoch == self._epoch and not self.stopped.is_set():
                    self.emit("notice", profile, text=str(exc))
            finally:
                with self._state:
                    self._capturing = False
        threading.Thread(target=process, daemon=True).start()

    def start(self, transcribe):
        self.transcribe = transcribe
        if self.started or self.stopped.is_set() or os.name != "nt":
            return
        self.started = True
        threading.Thread(target=self._hotkeys, daemon=True).start()

    @staticmethod
    def _winapi():
        from ctypes import wintypes
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user.RegisterHotKey.restype = wintypes.BOOL
        user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user.UnregisterHotKey.restype = wintypes.BOOL
        user.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user.GetMessageW.restype = ctypes.c_int
        user.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.PostThreadMessageW.restype = wintypes.BOOL
        return user

    def _hotkeys(self):
        from ctypes import wintypes
        registered = []
        user = self._winapi()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentThreadId.restype = wintypes.DWORD
        kernel.GetCurrentThreadId.argtypes = []
        self.hotkey_thread = kernel.GetCurrentThreadId()
        try:
            for ident, vk, name in ((1, 0x77, "F8"), (2, 0x78, "F9"), (3, 0x79, "F10")):
                ok = bool(user.RegisterHotKey(None, ident, 0x4000, vk))
                self.hotkeys[name] = ok
                if ok:
                    registered.append(ident)
                else:
                    self.hotkey_errors[name] = ctypes.get_last_error()
                    self.emit("notice", text=f"Atalho {name} indisponível (Windows {self.hotkey_errors[name]}).")
            msg = wintypes.MSG()
            while not self.stopped.is_set():
                status = user.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if status <= 0:
                    if status == -1:
                        self.emit("notice", text=f"Erro nos atalhos: Windows {ctypes.get_last_error()}")
                    break
                if msg.message == 0x312:
                    if msg.wParam == 1:
                        self.toggle_record()
                    elif msg.wParam == 2:
                        self.emit("stop")
                    elif msg.wParam == 3:
                        self.scan()
        finally:
            for ident in registered:
                user.UnregisterHotKey(None, ident)
            self.hotkey_thread = None

    def close(self):
        with self._state:
            self._epoch += 1
            self.stopped.set()
        if self.interrupt:
            self.interrupt()
        if self._timer:
            self._timer.cancel()
        thread_id = getattr(self, "hotkey_thread", None)
        if os.name == "nt" and thread_id:
            user = self._winapi()
            if not user.PostThreadMessageW(thread_id, 0x12, 0, 0):
                self.hotkey_errors["shutdown"] = ctypes.get_last_error()


service = Desktop()


def hud():
    import tkinter as tk
    root = tk.Tk()
    root.title("Orion · Legendas")
    root.geometry("660x155+40+40")
    root.configure(bg="#101b25")
    root.attributes("-topmost", True)
    text = tk.StringVar(value=service.subtitle)
    tk.Label(root, text="ORION  /  EXOSUIT LINK", bg="#101b25", fg="#68dcca", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
    tk.Label(root, textvariable=text, bg="#101b25", fg="#eef3f5", font=("Segoe UI", 12), wraplength=625, justify="left").pack(fill="both", expand=True, padx=14)
    controls = tk.Frame(root, bg="#101b25")
    controls.pack(fill="x", padx=10, pady=8)
    tk.Button(controls, text="F8 · Falar/enviar", command=service.toggle_record).pack(side="left")
    tk.Button(controls, text="F9 · Parar", command=lambda: service.emit("stop")).pack(side="left", padx=4)
    tk.Button(controls, text="F10 · Captura", command=service.scan).pack(side="left")
    timer = None
    closed = False
    def close_window():
        nonlocal closed
        if closed:
            return
        closed = True
        if timer is not None:
            root.after_cancel(timer)
        service.close()
        root.destroy()
    def tick():
        nonlocal timer
        if closed:
            return
        if service.stopped.is_set():
            close_window()
            return
        text.set(service.subtitle[-500:])
        timer = root.after(250, tick)
    root.protocol("WM_DELETE_WINDOW", close_window)
    timer = root.after(250, tick)
    try:
        root.mainloop()
    finally:
        service.close()
