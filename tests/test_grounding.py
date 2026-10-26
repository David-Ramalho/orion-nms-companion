"""Behavioral checks for exact save reports that never depend on model numeracy."""
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from companion import memory, grounding
from companion.app import app

module = importlib.import_module("companion.app")
CONFIG = {"provider_mode":"auto","system_prompt":"Be brief","cloud_consent":False,
          "cloud_fallback":False,"ollama_model":"fixture"}
QUESTION = ("Using only my save, list my Units, Nanites, Quicksilver, base count and readable inventory count. "
            "Then suggest three activities, clearly separating saved facts from your ideas.")


class GroundingTests(unittest.TestCase):
    def setUp(self):
        parent=Path(__file__).parent/".runtime"
        parent.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=parent)
        self.old=memory.DB_PATH
        memory.DB_PATH=Path(self.temp.name)/"memory.sqlite3"
        self.client=app.test_client()
        app.testing=True
        self.payload={"Units":987654321,"Nanites":43210,"Specials":2468,
                      "bases":[{"Name":"Fixture Observatory"},{"Name":"Fixture Harbor"}],
                      "inventory":[{"item":"FUEL1","amount":10,"container":"Inventory"} for _ in range(7)]}
        memory.store_snapshot("default","fixture","fixture-save.json","2026-01-01T12:00:00Z",self.payload)

    def tearDown(self):
        memory.DB_PATH=self.old
        self.temp.cleanup()

    def request_report(self,text=QUESTION,profile="default",locale="en"):
        with patch.object(module,"load_config",return_value=CONFIG), \
             patch.object(module,"get_key",side_effect=AssertionError("Report must not read cloud credentials")), \
             patch.object(module.providers,"ollama_models",side_effect=AssertionError("Report must work offline")), \
             patch.object(module.providers,"ollama_stream",return_value=iter(["wrong: 100 units"])) as llm, \
             patch.object(module.providers,"gemini_stream",side_effect=AssertionError("No cloud call")):
            response=self.client.post("/api/chat/stream?profile="+profile,
                                      json={"text":text,"ui_locale":locale,"response_mode":"facts"},buffered=True)
        self.assertEqual(response.status_code,200)
        llm.assert_not_called()
        records=[json.loads(line) for line in response.data.splitlines()]
        return records,records[-1].get("text","")

    def test_default_save_question_calls_selected_ai_with_verified_reference(self):
        cfg={**CONFIG,"provider_mode":"ollama","ollama_model":"chosen-custom-model"}
        with patch.object(module,"load_config",return_value=cfg), \
             patch.object(module,"get_key",return_value=None), \
             patch.object(module.providers,"ollama_stream",return_value=iter(["An actual model answer."])) as llm:
            response=self.client.post("/api/chat/stream",json={"text":QUESTION},buffered=True)
        records=[json.loads(line) for line in response.data.splitlines()]
        llm.assert_called_once()
        self.assertEqual(llm.call_args.args[0]["ollama_model"],"chosen-custom-model")
        prompt=llm.call_args.args[1][0]["content"]
        for number in ("987654321","43210","2468"):
            self.assertIn(number,prompt)
        self.assertEqual(records[0]["provider"],"Ollama")
        self.assertEqual(records[0]["model"],"chosen-custom-model")
        self.assertEqual(records[0]["verified_save"]["currencies"],{"Units":987654321,"Nanites":43210,"Quicksilver":2468})
        self.assertEqual(records[0]["verified_save"]["inventory_count"],7)
        self.assertEqual(records[-1]["text"],"An actual model answer.")
        self.assertNotIn("formatted by the app",records[-1]["text"])

    def test_default_save_chat_does_not_silently_fall_back_to_fixed_report(self):
        cfg={**CONFIG,"provider_mode":"ollama"}
        with patch.object(module,"load_config",return_value=cfg), \
             patch.object(module,"get_key",return_value=None), \
             patch.object(module.providers,"ollama_stream",side_effect=module.providers.ProviderError("fixture offline")):
            response=self.client.post("/api/chat/stream",json={"text":QUESTION},buffered=True)
        records=[json.loads(line) for line in response.data.splitlines()]
        self.assertEqual(records[0]["provider"],"Ollama")
        self.assertEqual(records[0]["verified_save"]["base_count"],2)
        self.assertEqual(records[-1]["type"],"error")
        self.assertEqual(records[-1]["message"],"fixture offline")

    def test_auto_connection_failure_still_provides_reference(self):
        with patch.object(module,"load_config",return_value=CONFIG), \
             patch.object(module,"get_key",return_value=None), \
             patch.object(module.providers,"ollama_models",side_effect=module.providers.ProviderError("offline")):
            response=self.client.post("/api/chat/stream",json={"text":QUESTION},buffered=True)
        records=[json.loads(line) for line in response.data.splitlines()]
        self.assertEqual(records[-1]["type"],"error")
        self.assertEqual(records[-1]["verified_save"]["currencies"]["Units"],987654321)
        self.assertEqual(records[-1]["verified_save"]["base_count"],2)

    def test_verified_reference_does_not_leak_across_profiles(self):
        other=memory.add_profile("No snapshot")
        cfg={**CONFIG,"provider_mode":"ollama"}
        with patch.object(module,"load_config",return_value=cfg), \
             patch.object(module,"get_key",return_value=None), \
             patch.object(module.providers,"ollama_stream",return_value=iter(["No save is linked."])):
            response=self.client.post("/api/chat/stream?profile="+other,json={"text":QUESTION},buffered=True)
        records=[json.loads(line) for line in response.data.splitlines()]
        self.assertIsNone(records[0]["verified_save"])

    def test_facts_mode_is_explicit_even_without_save_keywords(self):
        records,text=self.request_report(text="Please.")
        self.assertEqual(records[0]["provider"],"Save reader")
        self.assertIn("987,654,321",text)

    def test_ai_context_and_reference_share_one_snapshot(self):
        cfg={**CONFIG,"provider_mode":"ollama"}
        snap={"payload":self.payload,"observed_at":"2026-01-01T12:00:00Z","source":"fixture-save.json"}
        with patch.object(module,"load_config",return_value=cfg), \
             patch.object(module,"get_key",return_value=None), \
             patch.object(memory,"latest_snapshot",return_value=snap) as latest, \
             patch.object(module.providers,"ollama_stream",return_value=iter(["AI reply"])) as llm:
            response=self.client.post("/api/chat/stream",json={"text":QUESTION},buffered=True)
        latest.assert_called_once_with("default")
        records=[json.loads(line) for line in response.data.splitlines()]
        self.assertEqual(records[0]["verified_save"]["currencies"]["Units"],987654321)
        self.assertIn("987654321",llm.call_args.args[1][0]["content"])

    def test_invalid_response_mode_is_rejected(self):
        response=self.client.post("/api/chat/stream",json={"text":QUESTION,"response_mode":"invented"})
        self.assertEqual(response.status_code,400)
        self.assertFalse(module._turn_lock.locked())

    def test_report_uses_exact_save_values_even_if_provider_would_be_wrong(self):
        records,text=self.request_report()
        self.assertEqual(records[0]["provider"],"Save reader")
        self.assertEqual(records[0]["model"],"")
        for expected in ("Units: 987,654,321","Nanites: 43,210","Quicksilver: 2,468",
                         "Base count: 2","Readable inventory entries: 7"):
            self.assertIn(expected,text)
        self.assertIn("Activity ideas — app suggestions, not saved missions",text)
        self.assertIn("1. Revisit",text)
        self.assertIn("3. Record",text)
        self.assertNotIn("100 units",text)
        self.assertEqual(memory.history()[-1]["content"],text)

    def test_portuguese_question_controls_report_language(self):
        _,text=self.request_report("Mostre os dados do meu save: unidades, nanites, quicksilver e quantas bases tenho.",locale="en")
        self.assertIn("Unidades: 987.654.321",text)
        self.assertIn("Entradas legíveis de inventário: 7",text)
        self.assertNotIn("Activity ideas",text)

    def test_missing_currencies_are_unknown_not_defaulted(self):
        memory.store_snapshot("default","missing","fixture-save.json","fixture",{"bases":[],"inventory":[]})
        _,text=self.request_report("Show my save statistics")
        self.assertIn("Units: Unknown",text)
        self.assertIn("Nanites: Unknown",text)
        self.assertIn("Quicksilver: Unknown",text)
        self.assertIn("Base count: 0",text)

    def test_other_profile_cannot_read_selected_save(self):
        other=memory.add_profile("Other fixture")
        _,text=self.request_report(profile=other)
        self.assertIn("No save has been read for this character",text)
        self.assertNotIn("987",text)

    def test_other_profile_gets_its_own_values(self):
        other=memory.add_profile("Other fixture")
        memory.store_snapshot(other,"other","other.json","fixture",
                              {"Units":123,"Nanites":456,"Specials":789,"bases":[],"inventory":[]})
        _,text=self.request_report(profile=other)
        self.assertIn("Units: 123",text)
        self.assertNotIn("987",text)

    def test_clear_during_app_report_cannot_restore_reply(self):
        def chunks(report):
            yield report.splitlines(keepends=True)[0]
            self.client.post("/api/memory/clear-history",json={})
            yield report
        with patch.object(grounding,"report_chunks",side_effect=chunks):
            records,_=self.request_report()
        self.assertEqual(records[-1]["type"],"cancelled")
        self.assertEqual(memory.history(),[])
        self.assertFalse(module._turn_lock.locked())

    def test_general_game_advice_still_uses_selected_model(self):
        cfg={**CONFIG,"provider_mode":"ollama"}
        with patch.object(module,"load_config",return_value=cfg), \
             patch.object(module,"get_key",return_value=None), \
             patch.object(module.providers,"ollama_stream",return_value=iter(["A model suggestion."])) as llm:
            response=self.client.post("/api/chat/stream",json={"text":"How do I farm Units in NMS?"},buffered=True)
        self.assertIn(b"A model suggestion.",response.data)
        llm.assert_called_once()

    def test_personal_identity_is_not_inherited_from_other_apps(self):
        cfg={**CONFIG,"provider_mode":"ollama"}
        with patch.object(module,"load_config",return_value=cfg), \
             patch.object(module,"get_key",return_value=None), \
             patch.object(module.providers,"ollama_stream",return_value=iter(["Who do you mean?"])) as llm:
            self.client.post("/api/chat/stream",json={"text":"Do you know about Alex?"},buffered=True)
        system=llm.call_args.args[1][0]["content"]
        self.assertIn("do not inherit the user's ChatGPT profile",system)
        self.assertIn("An unfamiliar person's name is not evidence of an NMS character",system)
        self.assertEqual(memory.facts(),[])

    def test_save_import_help_is_not_replaced_with_a_balance_report(self):
        self.assertFalse(grounding.is_report_request("What do you know about the save format?"))
        self.assertFalse(grounding.is_report_request("Como funciona importar meu save?"))

    def test_english_spending_advice_is_not_replaced_by_save_report(self):
        for question in ("Using my save, how should I spend my Units?",
                         "Using my save, what should I buy with my Units?",
                         "What upgrades should I invest in with my Nanites?"):
            with self.subTest(question=question):
                self.assertFalse(grounding.is_report_request(question))
        self.assertTrue(grounding.is_report_request(
            "Using my save, list my Units and Nanites, then suggest how to spend them."))

    def test_portuguese_spending_advice_is_not_replaced_by_save_report(self):
        for question in ("Com base no meu save, quais melhorias devo comprar com minhas Units?",
                         "Usando meu save, como devo gastar minhas unidades?",
                         "Quais melhorias devo usar para investir meus nanites?"):
            with self.subTest(question=question):
                self.assertFalse(grounding.is_report_request(question))
        self.assertTrue(grounding.is_report_request(
            "No meu save, liste minhas unidades e nanites, depois sugira como gastar."))

    def test_ui_language_is_separate_from_question_language(self):
        self.assertEqual(grounding.report_locale("Using my save, show statistics","pt"),"en")
        self.assertEqual(grounding.report_locale("Mostre meus dados","en"),"pt")


if __name__=="__main__":
    unittest.main()
