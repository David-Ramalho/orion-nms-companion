import io
import json
import sqlite3
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from companion import memory,game,providers
from companion.app import app
from companion.desktop import Desktop

def save(units=100,voxel=1):
    return {"PlayerStateData":{"Units":units,"Nanites":40,"UniverseAddress":{"GalacticAddress":{"VoxelX":voxel}},"Inventory":{"Slots":[{"Id":"^FUEL1","Amount":30}]},"PersistentPlayerBases":[{"Name":"Big Forest","GalacticAddress":"0x123"}]}}

class ExplorationTests(unittest.TestCase):
    def setUp(self):
        temp_root=Path(__file__).parent/".runtime"
        temp_root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=temp_root)
        self.old=memory.DB_PATH
        memory.DB_PATH=Path(self.temp.name)/"memory.sqlite3"
        self.client=app.test_client()
        app.testing=True
        self.other=memory.add_profile("Royal")
    def tearDown(self):
        memory.DB_PATH=self.old
        self.temp.cleanup()
    def test_profiles_isolate_every_memory_layer(self):
        memory.add_fact("segredo A")
        memory.add_fact("segredo A",self.other)
        memory.add_entry("default",{"kind":"lore","title":"Império","content":"Lore A"})
        memory.add_message("user","Conversação A")
        memory.add_entry(self.other,{"kind":"goal","title":"Meta B","content":"Explorar"})
        self.assertEqual(memory.history(profile=self.other),[])
        self.assertNotIn("Lore A",memory.context(self.other))
        self.assertNotIn("Meta B",memory.context("default"))
        self.assertEqual(memory.facts(self.other),["segredo A"])
    def test_legacy_migration_preserves_existing_notes(self):
        memory.DB_PATH.unlink(missing_ok=True)
        with sqlite3.connect(memory.DB_PATH) as db:
            db.executescript("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created_at TEXT); CREATE TABLE facts(id INTEGER PRIMARY KEY,content TEXT UNIQUE,created_at TEXT); INSERT INTO facts VALUES(1,'Old ship','old');")
        db.close()
        self.assertEqual(memory.facts(),["Old ship"])
        memory.add_fact("Old ship",self.other)
        self.assertEqual(memory.facts(self.other),["Old ship"])
    def test_read_does_not_modify_source_and_deduplicates(self):
        path=Path(self.temp.name)/"save.json"
        raw=json.dumps(save()).encode()
        path.write_bytes(raw)
        result=game.sync("default",str(path))
        self.assertTrue(result["changed"])
        self.assertFalse(game.sync("default",str(path))["changed"])
        self.assertEqual(path.read_bytes(),raw)
        snap=memory.latest_snapshot("default")
        self.assertEqual(snap["payload"]["inventory"][0]["item"],"FUEL1")
    def test_diff_events_are_coarse_and_not_duplicated(self):
        game.ingest("default",json.dumps(save()).encode(),"save.json")
        result=game.ingest("default",json.dumps(save(200,2)).encode(),"save.json")
        self.assertEqual(len(result["events"]),2)
        self.assertFalse(game.ingest("default",json.dumps(save(200,2)).encode(),"save.json")["changed"])
        self.assertEqual(len(memory.entries("default")),2)
    def test_unknown_partial_and_obfuscated_saves_leave_snapshot_intact(self):
        game.ingest("default",json.dumps(save()).encode(),"save.json")
        before=memory.latest_snapshot("default")
        for raw in (b'{"broken":',b'{"abc":{}}',b"compressed"):
            with self.assertRaises((ValueError,json.JSONDecodeError)):
                game.ingest("default",raw,"save.hg")
        self.assertEqual(memory.latest_snapshot("default")["digest"],before["digest"])
    def test_snapshot_time_is_file_time(self):
        path=Path(self.temp.name)/"save.json";path.write_text(json.dumps(save()))
        result=game.sync("default",str(path))
        self.assertIn("T",result["snapshot"]["observed_at"])
        self.assertNotIn("live",result["snapshot"]["source"])
    def test_helper_only_receives_private_copy_and_read_command(self):
        cli=Path(self.temp.name)/"libNOM.cli.exe";cli.write_bytes(b"fixture")
        class Result:
            returncode=0
            stdout=json.dumps(save()).encode()
        with patch("companion.game.subprocess.run",return_value=Result()) as run:
            game.decode_snapshot(b"compressed","save.hg",str(cli))
        args=run.call_args.args[0]
        self.assertEqual(args[1],"Read")
        self.assertNotEqual(Path(args[3]).parent,cli.parent)
        self.assertIn("-JsonHumanReadable",args)
    def test_journal_api_search_complete_and_export(self):
        p="?profile="+self.other
        response=self.client.post("/api/journal"+p,json={"kind":"goal","title":"Observatório","content":"Construir em Big Forest"})
        ident=response.json["id"]
        self.assertEqual(len(self.client.get("/api/journal?q=Forest&profile="+self.other).json),1)
        self.client.patch("/api/journal/"+str(ident)+p,json={"status":"done"})
        self.assertEqual(self.client.get("/api/briefing"+p).json["goals"],[])
        self.assertEqual(self.client.get("/api/journal").json,[])
        self.assertIn("attachment",self.client.get("/api/journal/export"+p).json["entries"][0])
    def test_cross_profile_delete_cannot_remove_entry(self):
        ident=memory.add_entry("default",{"title":"A","content":"A"})
        self.client.delete("/api/journal/"+str(ident)+"?profile="+self.other)
        self.assertEqual(len(memory.entries("default")),1)
    def test_capture_requires_review_before_memory(self):
        fixture={"id":"a"*32,"profile":"default","text":"Water","requires_review":True}
        with patch("companion.exploration.capture.capture",return_value=fixture):
            response=self.client.post("/api/capture")
        self.assertTrue(response.json["requires_review"])
        self.assertEqual(memory.entries("default"),[])
    def test_attachment_path_and_profile_are_checked(self):
        response=self.client.post("/api/journal",json={"title":"X","content":"Y","attachment":"../../file"})
        self.assertEqual(response.status_code,400)
        self.assertEqual(memory.entries("default"),[])
    def test_cross_origin_mutation_and_dns_rebinding_are_blocked(self):
        self.assertEqual(self.client.post("/api/profiles",json={"name":"bad"},headers={"Origin":"https://evil.example"}).status_code,403)
        self.assertEqual(self.client.get("/api/profiles",headers={"Host":"evil.example"}).status_code,403)
    def test_chat_uses_only_selected_character_context(self):
        memory.add_entry("default",{"title":"HiddenA","content":"Never in B"})
        memory.add_entry(self.other,{"title":"VisibleB","content":"Explore"})
        cfg={"provider_mode":"ollama","system_prompt":"Be brief","ollama_model":"fixture"}
        with patch("companion.app.load_config",return_value=cfg),patch("companion.app.providers.ollama_stream",return_value=iter(["OK"])) as stream:
            response=self.client.post("/api/chat/stream?profile="+self.other,json={"text":"Oi"},buffered=True)
        self.assertEqual(response.status_code,200)
        context=stream.call_args.args[1][0]["content"]
        self.assertIn("VisibleB",context);self.assertNotIn("HiddenA",context)
    def test_invalid_profile_does_not_lock_future_chat(self):
        self.assertEqual(self.client.post("/api/chat/stream?profile=missing",json={"text":"Hi"}).status_code,400)
        cfg={"provider_mode":"ollama","system_prompt":"Be brief"}
        with patch("companion.app.load_config",return_value=cfg),patch("companion.app.providers.ollama_stream",return_value=iter(["OK"])):
            response=self.client.post("/api/chat/stream",json={"text":"Hi"},buffered=True)
        self.assertIn(b'"done"',response.data)
    def test_old_place_is_recalled_by_name(self):
        memory.add_entry("default",{"kind":"place","title":"Gonna Outpost","content":"Observatório costeiro"})
        for index in range(25):
            memory.add_entry("default",{"title":f"Nota {index}","content":"Viagem recente"})
        self.assertIn("Gonna Outpost",memory.context("default","Onde fica Gonna?"))

    def test_large_save_summary_keeps_totals_and_valid_json(self):
        payload={"Units":123456,"Nanites":789,"Specials":42,
                 "bases":[{"Name":"Observatory "+str(i)+"x"*160,"Position":[1,2,3]} for i in range(200)],
                 "inventory":[{"item":"FUEL1","amount":5,"container":"Chest1Inventory"} for _ in range(624)]}
        summary=memory._snapshot_summary(payload,{"fuel1"})
        encoded=json.dumps(summary,ensure_ascii=False)
        self.assertLessEqual(len(encoded),10000)
        parsed=json.loads(encoded)
        self.assertEqual(parsed["currencies"],{"Units":123456,"Nanites":789,"Quicksilver":42})
        self.assertEqual(parsed["bases_count"],200)
        self.assertEqual(parsed["inventory_readable_entries"],624)
        self.assertEqual(parsed["inventory_container_counts"]["Chest1Inventory"],624)

    def test_specific_item_retrieval_can_find_end_of_inventory(self):
        payload={"bases":[],"inventory":[{"item":"FUEL1","amount":1,"container":"Inventory"} for _ in range(600)]
                 +[{"item":"RARE_ITEM","amount":7,"container":"FreighterInventory"}]}
        summary=memory._snapshot_summary(payload,{"rare_item"})
        self.assertEqual(summary["inventory_matches"][0]["item"],"RARE_ITEM")
        self.assertEqual(summary["inventory_matches"][0]["amount"],7)

    def test_generic_question_does_not_match_common_words_in_containers(self):
        memory.store_snapshot("default","fixture","save.json",memory.now(),
            {"bases":[],"inventory":[{"item":"FUEL1","amount":3,"container":"ShipOwnership The Wraith"}]})
        context=memory.context("default","Tell me all the info you have about my save")
        data=json.loads(context.splitlines()[-1].split("] ",1)[1])
        self.assertEqual(data["inventory_matches"],[])
        self.assertEqual(data["inventory_readable_entries"],1)

    def test_empty_journal_and_missing_mission_book_are_explicit(self):
        context=memory.context("default","What should we do next?")
        self.assertIn("recorded open goals: 0",context)
        self.assertIn("mission book is not imported",context)
        self.assertIn("No save snapshot",context)

    def test_normal_chat_context_keeps_facts_without_container_number_noise(self):
        memory.store_snapshot("default","compact","fixture.json",memory.now(),
            {"Units":123456,"Nanites":789,"Specials":42,"bases":[{"Name":"Fixture base"}],
             "inventory":[{"item":"FUEL1","amount":57,"container":"Chest1Inventory"}]})
        context=memory.context("default","What do you know about my save?")
        self.assertIn("Units: 123456",context)
        self.assertIn("Nanites: 789",context)
        self.assertIn("Quicksilver: 42",context)
        self.assertNotIn("inventory_container_counts",context)
        data=json.loads(context.splitlines()[-1].split("] ",1)[1])
        self.assertEqual(data["inventory_examples"],[])
        self.assertEqual(data["inventory_matches"],[])

    def test_requested_container_breakdown_still_receives_counts(self):
        memory.store_snapshot("default","containers","fixture.json",memory.now(),
            {"bases":[],"inventory":[{"item":"FUEL1","amount":3,"container":"Chest1Inventory"}]})
        context=memory.context("default","Show a breakdown of my inventory containers")
        data=json.loads(context.splitlines()[-1].split("] ",1)[1])
        self.assertEqual(data["inventory_container_counts"],{"Chest1Inventory":1})

    def test_captured_snapshot_does_not_mix_with_later_watcher_update(self):
        memory.store_snapshot("default","first","fixture.json",memory.now(),
            {"Units":123456,"bases":[],"inventory":[]})
        captured=memory.latest_snapshot("default")
        memory.store_snapshot("default","second","fixture.json",memory.now(),
            {"Units":654321,"bases":[],"inventory":[]})
        context=memory.context("default","What is my save?",snapshot=captured)
        self.assertIn("Units: 123456",context)
        self.assertNotIn("654321",context)
        self.assertIn("No save snapshot",memory.context("default","Hi",snapshot=None))

    def test_google_quota_explains_no_retry(self):
        error=urllib.error.HTTPError("https://example",429,"quota",{},io.BytesIO(b"quota"))
        with patch("companion.providers.urllib.request.urlopen",side_effect=error) as request:
            with self.assertRaisesRegex(providers.ProviderError,"429"):
                list(providers.gemini_stream({"gemini_model":"fixture"},[],"fixture-key"))
        self.assertEqual(request.call_count,1)
    def test_google_503_is_explained_without_repeating_request(self):
        error=urllib.error.HTTPError("https://example",503,"unavailable",{},io.BytesIO(b"busy"))
        with patch("companion.providers.urllib.request.urlopen",side_effect=error) as request:
            with self.assertRaisesRegex(providers.ProviderError,"temporariamente indisponível"):
                list(providers.gemini_stream({"gemini_model":"fixture"},[],"fixture-key"))
        self.assertEqual(request.call_count,1)

    def test_desktop_events_have_cursor_and_profile(self):
        desktop=Desktop();desktop.profile=self.other
        desktop.emit("notice",text="Recording")
        desktop.emit("stop")
        self.assertEqual(len(desktop.since(0)),2)
        self.assertEqual(len(desktop.since(1)),1)
        self.assertEqual(desktop.since(1)[0]["profile"],self.other)

if __name__=="__main__":
    unittest.main()
