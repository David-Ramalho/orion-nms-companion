import json
import threading
import unittest
from unittest.mock import patch
from companion.providers import ollama_stream, gemini_stream, stream_reply, model_details, ollama_models, ProviderError

class Response:
    def __init__(self, lines):
        self.lines = lines
        self.closed = False
    def __iter__(self):
        return iter(self.lines)
    def read(self, *args):
        return b"".join(self.lines)
    def close(self):
        self.closed = True
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()

class ProviderTests(unittest.TestCase):
    def test_ollama_bounded_options_and_cleanup(self):
        response = Response([b'{"message":{"thinking":"private","content":"Hello"}}', b'{"done":true}'])
        with patch('companion.providers._request', return_value=response) as request:
            self.assertEqual(list(ollama_stream({'ollama_model':'test', 'ollama_num_ctx':32768}, [])), ['Hello'])
        payload = request.call_args.args[1]
        self.assertEqual(payload['keep_alive'], '5m')
        self.assertFalse(payload['think'])
        self.assertEqual(payload['options'], {'num_ctx':32768,'num_predict':512,'temperature':0.7})
        self.assertEqual(request.call_args.kwargs['timeout'], 180)
        self.assertTrue(response.closed)

    def test_cancellation_closes_response(self):
        stop = threading.Event()
        response = Response([b'{"message":{"content":"one"}}', b'{"message":{"content":"two"}}'])
        with patch('companion.providers._request', return_value=response):
            stream = ollama_stream({'ollama_model':'test'}, [], stop)
            self.assertEqual(next(stream), 'one')
            stop.set()
            self.assertEqual(list(stream), [])
        self.assertTrue(response.closed)

    def test_parse_failure_closes_response(self):
        response = Response([b'broken json'])
        with patch('companion.providers._request', return_value=response):
            with self.assertRaises(ProviderError):
                list(ollama_stream({'ollama_model':'test'}, []))
        self.assertTrue(response.closed)

    def test_cancelled_turn_never_connects(self):
        stop = threading.Event()
        stop.set()
        with patch('companion.providers._request') as request:
            self.assertEqual(list(ollama_stream({}, [], stop)), [])
            request.assert_not_called()

    def test_no_implicit_cloud_fallback(self):
        with patch('companion.providers.ollama_stream', side_effect=ProviderError('offline')), patch('companion.providers.gemini_stream') as cloud:
            with self.assertRaises(ProviderError):
                list(stream_reply({'provider_mode':'auto','cloud_fallback':True,'cloud_consent':False}, []))
            cloud.assert_not_called()

    def test_gemini_omits_thought_parts(self):
        packet = {'candidates':[{'content':{'parts':[{'text':'hidden','thought':True},{'text':'visible'}]}}]}
        response = Response([('data: '+json.dumps(packet)).encode()])
        with patch('urllib.request.urlopen', return_value=response):
            self.assertEqual(list(gemini_stream({'gemini_model':'test'}, [], 'key')), ['visible'])
        self.assertTrue(response.closed)

    def test_per_model_options_override_without_losing_32k(self):
        response = Response([b'{"message":{"content":"Hi"}}', b'{"done":true}'])
        config = {'ollama_model':'liquid32k', 'ollama_model_settings':{
            'liquid32k': {'ollama_num_ctx':32768,'ollama_temperature':0.05,'provider_timeout':300},
            'other': {'ollama_num_ctx':4096}}}
        with patch('companion.providers._request', return_value=response) as request:
            list(ollama_stream(config, []))
        self.assertEqual(request.call_args.args[1]['options']['num_ctx'], 32768)
        self.assertEqual(request.call_args.args[1]['options']['temperature'], 0.05)
        self.assertEqual(request.call_args.kwargs['timeout'], 300)

    def test_automatic_context_and_threads_are_omitted(self):
        response = Response([b'{"message":{"content":"Hi"}}'])
        with patch('companion.providers._request', return_value=response) as request:
            list(ollama_stream({'ollama_model':'x','ollama_num_ctx':0,'ollama_num_thread':0}, []))
        options = request.call_args.args[1]['options']
        self.assertNotIn('num_ctx', options)
        self.assertNotIn('num_thread', options)

    def test_timeout_does_not_claim_server_offline(self):
        with patch('companion.providers._request', side_effect=TimeoutError('timed out')):
            with self.assertRaises(ProviderError) as caught:
                list(ollama_stream({'ollama_model':'x'}, []))
        self.assertIn('180s', str(caught.exception))
        self.assertIn('nao confirma', str(caught.exception))

    def test_show_distinguishes_maximum_and_modelfile_default(self):
        packet = {'model_info':{'lfm2.context_length':128000},
                  'parameters':'num_ctx 32768\ntemperature 0.05',
                  'details':{'family':'lfm2','parameter_size':'1.2B','quantization_level':'Q4_K_M'},
                  'capabilities':['completion','thinking']}
        with patch('companion.providers._request', return_value=Response([json.dumps(packet).encode()])):
            details = model_details({'ollama_model':'liquid'})
        self.assertEqual(details['context_length'],128000)
        self.assertEqual(details['default_context_length'],32768)
        self.assertEqual(details['effective_settings']['ollama_num_ctx'],32768)
        self.assertEqual(details['model_defaults']['temperature'],0.05)

    def test_cancel_interrupts_cold_model_wait_before_headers(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        entered = threading.Event()
        release = threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length', '0')))
                entered.set()
                release.wait(3)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        stop = threading.Event()
        errors = []
        def consume():
            try:
                list(ollama_stream({'ollama_model':'x','ollama_url':f'http://127.0.0.1:{server.server_port}'}, [], stop))
            except Exception as exc:
                errors.append(exc)
        worker = threading.Thread(target=consume, daemon=True)
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            stop.set()
            worker.join(1.5)
            self.assertFalse(worker.is_alive(), 'Cancellation waited for the 180-second socket timeout')
            self.assertEqual(errors, [])
        finally:
            release.set()
            server.shutdown()
            server.server_close()

    def test_inline_liquid_reasoning_hidden_across_packet_boundaries(self):
        chunks = ['<th', 'ink>private', ' hidden', '</thi', 'nk>OK', ' visible']
        response = Response([json.dumps({'message':{'content':chunk}}).encode() for chunk in chunks])
        with patch('companion.providers._request', return_value=response):
            visible = ''.join(ollama_stream({'ollama_model':'liquid'}, []))
        self.assertEqual(visible,'OK visible')
        self.assertTrue(response.closed)

    def test_unfinished_reasoning_is_never_emitted(self):
        response = Response([b'{"message":{"content":"<think>private"}}',b'{"done":true}'])
        with patch('companion.providers._request', return_value=response):
            with self.assertRaises(ProviderError) as caught:
                list(ollama_stream({'ollama_model':'liquid'}, []))
        self.assertIn('sem texto', str(caught.exception))

    def test_normal_angle_brackets_remain_visible(self):
        response = Response([b'{"message":{"content":"A < B and <th"}}',b'{"message":{"content":"is> is text"}}'])
        with patch('companion.providers._request', return_value=response):
            self.assertEqual(''.join(ollama_stream({'ollama_model':'x'}, [])), 'A < B and <this> is text')

    def test_custom_installed_model_name_is_forwarded_without_allowlist(self):
        response = Response([b'{"message":{"content":"Hello"}}'])
        name = 'artist/Special_Echo-v2:Q4_32K'
        with patch('companion.providers._request', return_value=response) as request:
            self.assertEqual(''.join(ollama_stream({'ollama_model':name}, [])), 'Hello')
        self.assertEqual(request.call_args.args[1]['model'], name)
        self.assertFalse(request.call_args.args[1]['think'])

    def test_embedding_only_model_error_explains_incompatible_capability(self):
        import io
        import urllib.error
        error = urllib.error.HTTPError('http://localhost/api/chat',400,'Bad Request',{},
                                      io.BytesIO(b'{"error":"model does not support chat"}'))
        with patch('companion.providers._request', side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                list(ollama_stream({'ollama_model':'embedding-only'}, []))
        self.assertIn('embeddings', str(caught.exception))
        self.assertNotIn('offline', str(caught.exception))

if __name__ == '__main__':
    unittest.main()
