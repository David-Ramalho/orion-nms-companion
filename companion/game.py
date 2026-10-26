"""Read-only NMS save adapter. External libNOM CLI is optional and not bundled."""
from __future__ import annotations
import hashlib
import json
import math
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from . import memory
from .config import DATA_DIR, load_config

MAX_SAVE_BYTES = 64 * 1024 * 1024
sync_lock = threading.Lock()
watch_status = {}

def normalize(root):
    if not isinstance(root, dict):
        raise ValueError("O save precisa ser um objeto JSON.")
    original_root = root
    warning=root.get("_orion_decode_warning")
    # Recent saves may contain separate BaseContext / ExpeditionContext. Do not merge them.
    if isinstance(root.get("BaseContext"), dict):
        root = root["BaseContext"]
    state = root.get("PlayerStateData")
    if not isinstance(state, dict):
        raise ValueError("Formato não reconhecido. Exporte JSON com chaves legíveis; saves ofuscados exigem libNOM CLI compatível.")
    payload = {"schema": "nms-readable-v1", "inventory": [], "bases": []}
    if warning:
        payload["warning"]=warning
    for key in ("Units", "Nanites", "Specials"):
        value = state.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            payload[key] = value
    common = original_root.get("CommonStateData", {})
    if not isinstance(common, dict):
        common = root.get("CommonStateData", {})
    play_time = common.get("TotalPlayTime") if isinstance(common, dict) else None
    if not isinstance(play_time, (int, float)) or isinstance(play_time, bool):
        play_time = state.get("TotalPlayTime")
    if isinstance(play_time, (int, float)) and not isinstance(play_time, bool) and play_time >= 0 and (not isinstance(play_time, float) or math.isfinite(play_time)):
        payload["TotalPlayTime"] = play_time
    address = state.get("UniverseAddress")
    if isinstance(address, dict):
        payload["address"] = address
    for key in ("Inventory", "Inventory_Cargo", "Inventory_TechOnly", "FreighterInventory"):
        inv = state.get(key)
        if isinstance(inv, dict):
            read_slots(payload["inventory"], key, inv)
    for number in range(1,11):
        key=f"Chest{number}Inventory"
        if isinstance(state.get(key),dict):
            read_slots(payload["inventory"],key,state[key])
    for group in ("ShipOwnership", "VehicleOwnership"):
        for i, item in enumerate(state.get(group, []) if isinstance(state.get(group),list) else []):
            if isinstance(item, dict) and isinstance(item.get("Inventory"), dict):
                read_slots(payload["inventory"], f"{group}[{i}] {str(item.get('Name',''))[:80]}", item["Inventory"])
    for item in state.get("PersistentPlayerBases", []) if isinstance(state.get("PersistentPlayerBases"),list) else []:
        if isinstance(item,dict):
            payload["bases"].append({key:item[key] for key in ("Name","GalacticAddress","Position") if key in item})
    payload["bases"] = payload["bases"][:200]
    payload["inventory"] = payload["inventory"][:3000]
    return payload

def read_slots(out, container, inventory):
    slots = inventory.get("Slots", [])
    if not isinstance(slots,list):
        return
    for item in slots:
        if not isinstance(item,dict):
            continue
        ident = item.get("Id")
        amount = item.get("Amount")
        if isinstance(ident,str) and "\ufffd" not in ident and all(ord(c)>=32 for c in ident) and isinstance(amount,(int,float)) and not isinstance(amount,bool):
            out.append({"item":ident.lstrip("^"),"amount":amount,"container":container})

def stable_bytes(path):
    before = path.stat()
    if before.st_size > MAX_SAVE_BYTES:
        raise ValueError("Save maior que 64 MB.")
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size,before.st_mtime_ns) != (after.st_size,after.st_mtime_ns):
        raise ValueError("O jogo está gravando o save. Tente novamente em alguns segundos.")
    return data, after

def decode_snapshot(data, filename, cli=""):
    if data.lstrip(b"\xef\xbb\xbf\x00 \r\n\t").startswith(b"{"):
        return json.loads(data.decode("utf-8-sig").rstrip("\x00"))
    if data[:4]==bytes.fromhex("e5a1edfe"):
        from .save_reader import decode_pc
        keymap=load_config().get("keymap_path","") or str(Path(__file__).resolve().parents[1]/".runtime"/"helpers"/"nms-keymap.json")
        return decode_pc(data,keymap)
    if not cli or not Path(cli).is_file():
        raise ValueError("Para ler .hg, configure libNOM.cli.exe compatível ou importe uma exportação JSON legível.")
    # Execute read on a private snapshot, never on the original NMS file.
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="orion-save-",dir=DATA_DIR) as temp:
        copy = Path(temp) / Path(filename).name
        copy.write_bytes(data)
        try:
            result = subprocess.run([str(Path(cli).resolve()),"Read","-Input",str(copy),"-JsonHumanReadable","true"],capture_output=True,timeout=30,stdin=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        except subprocess.TimeoutExpired as exc:
            raise ValueError("O leitor externo não respondeu em 30 segundos. Use o leitor PC integrado ou JSON exportado.") from exc
        if result.returncode:
            raise ValueError("libNOM não conseguiu ler esta versão do save. Verifique a compatibilidade do leitor.")
        if len(result.stdout)>MAX_SAVE_BYTES:
            raise ValueError("Exportação do leitor excede 64 MB.")
        return json.loads(result.stdout.decode("utf-8-sig").strip().rstrip("\x00"))

def ingest(profile, data, filename, observed_at=None, cli=""):
    payload = normalize(decode_snapshot(data,filename,cli))
    digest = hashlib.sha256(data).hexdigest()
    previous = memory.latest_snapshot(profile)
    changed = memory.store_snapshot(profile,digest,Path(filename).name,observed_at or memory.now(),payload)
    events = []
    if changed and previous:
        before = previous["payload"]
        if before.get("address") != payload.get("address"):
            events.append("Localização mudou entre os dois últimos saves.")
        for key in ("Units","Nanites"):
            if key in payload and key in before and payload[key] != before[key]:
                events.append(f"{key}: {before[key]} → {payload[key]}.")
    if changed:
        for text in events:
            memory.add_entry(profile,{"kind":"observation","title":"Atualização do save","content":text,"source":"save-diff"})
    return {"changed":changed,"snapshot":memory.latest_snapshot(profile),"events":events}

def sync(profile, binding=None):
    with sync_lock:
        cfg = load_config()
        binding = binding or cfg.get("save_bindings",{}).get(profile)
        if not binding:
            raise ValueError("Selecione um arquivo de save para este personagem.")
        path = Path(binding).expanduser().resolve()
        data, stat = stable_bytes(path)
        stamp = datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat()
        result = ingest(profile,data,path.name,stamp,cfg.get("libnom_cli",""))
        if result["events"]:
            from .desktop import service
            service.emit("observation",profile,text="Atualização observada no último save: "+" ".join(result["events"]))
        watch_status[profile] = {"ok":True,"checked_at":memory.now(),"file":path.name}
        return result

def candidates():
    root = Path(os.environ.get("APPDATA","")) / "HelloGames" / "NMS"
    if not root.is_dir():
        return []
    return [{"path":str(p),"name":f"{p.parent.name} / {p.name}","modified":p.stat().st_mtime}
            for p in root.glob("*/save*.hg") if p.is_file()]

def watch(stop_event):
    signatures = {}
    while not stop_event.wait(4):
        for profile,path in list(load_config().get("save_bindings",{}).items()):
            try:
                stat = Path(path).stat()
                signature = (path,stat.st_mtime_ns,stat.st_size)
                if signatures.get(profile) == signature:
                    continue
                # debounce: two samples with no change
                if stop_event.wait(.6):
                    return
                if (Path(path).stat().st_mtime_ns,Path(path).stat().st_size) != signature[1:]:
                    continue
                sync(profile,path)
                signatures[profile] = signature
            except Exception as exc:
                watch_status[profile] = {"ok":False,"error":str(exc),"checked_at":memory.now()}
                # retry after file changes instead of hammering an incompatible parser
                try:
                    signatures[profile] = (path,Path(path).stat().st_mtime_ns,Path(path).stat().st_size)
                except OSError:
                    pass
