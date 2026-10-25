from __future__ import annotations
import json
import threading
from flask import Blueprint, jsonify, request, send_file, Response
from . import memory, game, capture
from .config import load_config, save_config
from .desktop import service

api = Blueprint("exploration",__name__)
_capture_lock = threading.Lock()

def profile():
    return memory.require_profile(request.args.get("profile","default"))

@api.get("/api/profiles")
def profiles():
    return jsonify(memory.profiles())

@api.post("/api/profiles")
def add_profile():
    return jsonify(id=memory.add_profile(request.get_json()["name"]))

@api.post("/api/active-profile")
def active_profile():
    service.profile = profile()
    save_config({"active_profile":service.profile})
    return jsonify(ok=True)

@api.get("/api/journal")
def journal():
    return jsonify(memory.entries(profile(),request.args.get("q","")))

@api.post("/api/journal")
def add_entry():
    p = profile()
    body = request.get_json()
    if body.get("kind")=="observation":
        body["source"] = "user-reviewed"
    elif body.get("kind")=="summary":
        body["source"] = "assistant-generated"
    else:
        body["source"] = "user"
    attachment = body.get("attachment","")
    if attachment and not capture.image_path(p,attachment).is_file():
        raise ValueError("Imagem não pertence a este personagem.")
    return jsonify(id=memory.add_entry(p,body))

@api.patch("/api/journal/<int:ident>")
def update_entry(ident):
    memory.update_entry(profile(),ident,request.get_json()["status"])
    return jsonify(ok=True)

@api.delete("/api/journal/<int:ident>")
def delete_entry(ident):
    with memory.session() as db:
        db.execute("DELETE FROM journal WHERE profile=? AND id=?",(profile(),ident))
    return jsonify(ok=True)

@api.get("/api/briefing")
def briefing():
    p = profile()
    rows = memory.entries(p,limit=100)
    return jsonify(goals=[x for x in rows if x["kind"]=="goal" and x["status"]=="open"],
                   recent=rows[:8],snapshot=memory.latest_snapshot(p))

@api.get("/api/journal/export")
def export():
    p = profile()
    return Response(json.dumps({"profile":p,"exported_at":memory.now(),"entries":memory.entries(p,limit=10000)},ensure_ascii=False,indent=2),
                    mimetype="application/json",headers={"Content-Disposition":'attachment; filename="orion-journal.json"'})

@api.get("/api/game")
def game_status():
    p = profile()
    return jsonify(snapshot=memory.latest_snapshot(p),watch=game.watch_status.get(p),candidates=game.candidates(),
                   binding=load_config().get("save_bindings",{}).get(p,""))

@api.post("/api/game/bind")
def bind():
    p = profile()
    path = str(request.get_json().get("path","")).strip()
    cfg = load_config()
    bindings = cfg.get("save_bindings",{})
    if path:
        # Validate read before persisting a watcher.
        result = game.sync(p,path)
        bindings[p] = path
    else:
        result = {"changed":False}
        bindings.pop(p,None)
    save_config({"save_bindings":bindings})
    return jsonify(result)

@api.post("/api/game/sync")
def sync():
    return jsonify(game.sync(profile()))

@api.post("/api/game/import")
def import_save():
    file = request.files.get("save")
    if not file:
        raise ValueError("Selecione um save ou exportação JSON.")
    data = file.read(game.MAX_SAVE_BYTES+1)
    if len(data)>game.MAX_SAVE_BYTES:
        raise ValueError("Arquivo maior que 64 MB.")
    return jsonify(game.ingest(profile(),data,file.filename or "save.json",cli=load_config().get("libnom_cli","")))

@api.post("/api/capture")
def scan():
    p = profile()
    file = request.files.get("image")
    raw = file.read(12*1024*1024+1) if file else None
    if not _capture_lock.acquire(blocking=False):
        return jsonify(error="Uma captura já está em processamento. Aguarde."),409
    try:
        return jsonify(capture.capture(p,raw))
    finally:
        _capture_lock.release()

@api.get("/api/captures/<ident>")
def get_capture(ident):
    return send_file(capture.image_path(profile(),ident),mimetype="image/png")

@api.get("/api/desktop/events")
def desktop_events():
    p = profile()
    return jsonify(events=[e for e in service.since(int(request.args.get("after","0"))) if e["profile"]==p],cursor=service.seq)

@api.post("/api/desktop/action")
def action():
    service.profile = profile()
    kind = request.get_json().get("action")
    if kind=="record":
        service.toggle_record()
    elif kind=="stop":
        service.emit("stop")
    elif kind=="capture":
        service.scan()
    return jsonify(ok=True)

@api.post("/api/subtitle")
def subtitle():
    if profile()==service.profile:
        service.subtitle = str(request.get_json().get("text",""))[:1200]
    return jsonify(ok=True)

@api.get("/api/diagnostics")
def diagnostics():
    p = profile()
    with memory.session() as db:
        timings = [dict(r) for r in db.execute("SELECT kind,COUNT(*) AS samples,ROUND(AVG(seconds),3) AS average_seconds FROM metrics WHERE profile=? GROUP BY kind",(p,))]
    from .runtime import resources
    from .config import DATA_DIR
    return jsonify(timings=timings, process=resources(), hotkeys=service.hotkeys,
                   hotkey_errors=getattr(service,"hotkey_errors",{}), desktop_running=service.started,
                   logs_dir=str(DATA_DIR / "logs"),
                   note="Logs locais não incluem mensagens ou chaves. O dump encontrado do NMS estava vazio; a causa do travamento não foi confirmada. FPS precisa ser medido durante o jogo.")
