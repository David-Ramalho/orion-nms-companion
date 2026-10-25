import threading
import time
import types
import unittest
from unittest.mock import Mock, patch
from companion.desktop import Desktop


def wait_for(predicate, timeout=2):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError("Worker did not reach expected state")


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.desktop = Desktop()
        self.desktop.transcribe = Mock(return_value="hello")
        self.streams = []
        def make_stream(**kwargs):
            stream = Mock()
            stream.callback = kwargs["callback"]
            self.streams.append(stream)
            return stream
        self.sound = patch.dict("sys.modules", {"sounddevice": types.SimpleNamespace(RawInputStream=make_stream)})
        self.sound.start()

    def tearDown(self):
        self.desktop.close()
        if self.desktop._worker:
            self.desktop._worker.join(2)
        self.sound.stop()

    def record(self):
        self.desktop.toggle_record()
        wait_for(lambda: bool(self.streams) and self.streams[-1].start.called)
        return self.streams[-1]

    def test_device_open_does_not_block_hotkey_and_stop_discards(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(**kwargs):
            entered.set()
            release.wait(2)
            return Mock()
        with patch.dict("sys.modules", {"sounddevice": types.SimpleNamespace(RawInputStream=blocked)}):
            self.desktop.toggle_record()
            self.assertTrue(entered.wait(1))
            self.desktop.emit("stop")
            self.assertEqual(self.desktop.since(0)[-1]["type"], "stop")
            release.set()
            wait_for(lambda: self.desktop.recording is None)
        self.desktop.transcribe.assert_not_called()

    def test_stop_cancels_recording_and_closes_once(self):
        stream = self.record()
        stream.callback(b"\x00\x00" * 200)
        self.desktop.emit("stop")
        wait_for(lambda: stream.close.called)
        stream.abort.assert_called_once()
        stream.close.assert_called_once()
        self.desktop.transcribe.assert_not_called()

    def test_profile_change_suppresses_inflight_transcription(self):
        entered, release = threading.Event(), threading.Event()
        def transcribe(*args):
            entered.set()
            release.wait(2)
            return "old profile text"
        self.desktop.transcribe = transcribe
        stream = self.record()
        stream.callback(b"\x00\x00" * 200)
        self.desktop.toggle_record()
        self.assertTrue(entered.wait(1))
        self.desktop.profile = "other"
        release.set()
        wait_for(lambda: not self.desktop._transcribing)
        self.assertFalse(any(e["type"] == "transcript" for e in self.desktop.since(0)))

    def test_audio_and_events_are_bounded(self):
        self.desktop.MAX_AUDIO_BYTES = 100
        stream = self.record()
        stream.callback(b"\x00" * 1000)
        wait_for(lambda: self.desktop.transcribe.called)
        audio = self.desktop.transcribe.call_args.args[0]
        self.assertEqual(len(audio), 144)  # 44-byte WAV header + bounded PCM
        for _ in range(200):
            self.desktop.emit("notice", text="bounded")
        self.assertEqual(len(self.desktop.since(0)), 100)

    def test_capture_single_flight_and_stale_result_suppressed(self):
        entered, release = threading.Event(), threading.Event()
        def capture(profile):
            entered.set()
            release.wait(2)
            return {"profile": profile}
        with patch("companion.capture.capture", side_effect=capture) as fn:
            self.desktop.scan()
            self.assertTrue(entered.wait(1))
            for _ in range(30):
                self.desktop.scan()
            self.desktop.profile = "other"
            release.set()
            wait_for(lambda: not self.desktop._capturing)
            fn.assert_called_once_with("default")
        self.assertFalse(any(e["type"] == "capture" for e in self.desktop.since(0)))

    def test_expired_timer_cannot_stop_next_recording(self):
        first = self.record()
        old_serial = self.desktop._record_serial
        self.desktop.toggle_record()
        wait_for(lambda: first.close.called)
        self.desktop.toggle_record()
        wait_for(lambda: len(self.streams) == 2 and self.streams[-1].start.called)
        second = self.streams[-1]
        self.desktop._enqueue(("finish", old_serial))
        time.sleep(.05)
        self.assertFalse(second.close.called)

    def test_record_rejected_while_transcription_inflight(self):
        entered, release = threading.Event(), threading.Event()
        def transcribe(*args):
            entered.set()
            release.wait(2)
            return "hello"
        self.desktop.transcribe = transcribe
        stream = self.record()
        stream.callback(b"\x00\x00" * 200)
        self.desktop.toggle_record()
        self.assertTrue(entered.wait(1))
        self.desktop.toggle_record()
        time.sleep(.05)
        self.assertEqual(len(self.streams), 1)
        release.set()
        wait_for(lambda: not self.desktop._transcribing)

    def test_shutdown_discards_audio(self):
        stream = self.record()
        stream.callback(b"\x00\x00" * 200)
        self.desktop.close()
        wait_for(lambda: stream.close.called)
        self.desktop.transcribe.assert_not_called()


class LauncherTests(unittest.TestCase):
    def test_occupied_port_is_reported_without_starting_server(self):
        import socket
        from launch import ensure_port_free
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            with self.assertRaisesRegex(RuntimeError, "ocupada"):
                ensure_port_free(listener.getsockname()[1])

    def test_instance_lock_is_released_when_handle_closes(self):
        import tempfile
        from pathlib import Path
        from launch import claim_instance
        with tempfile.TemporaryDirectory() as folder:
            first = claim_instance(Path(folder))
            try:
                with self.assertRaisesRegex(RuntimeError, "instancia"):
                    claim_instance(Path(folder))
            finally:
                first.close()
            second = claim_instance(Path(folder))
            second.close()


if __name__ == "__main__":
    unittest.main()
