"""Download a pinned GPL-3.0 key mapping; the game save is never accessed here."""
import base64
import hashlib
import json
from pathlib import Path
import urllib.request

BLOB="8199b7833bbdf81981159e88efe7d52ce03165ea"
URL="https://api.github.com/repos/zencq/libNOM.map/git/blobs/"+BLOB

def setup(target=None):
    request=urllib.request.Request(URL,headers={"Accept":"application/vnd.github+json","User-Agent":"Orion-NMS-Companion"})
    with urllib.request.urlopen(request,timeout=30) as response:
        document=json.load(response)
    raw=base64.b64decode(document["content"])
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if digest!=BLOB:
        raise ValueError("O mapa recebido não corresponde à versão esperada.")
    data=json.loads(raw)
    wanted={"BaseContext","ExpeditionContext","PlayerStateData","Units","Nanites","Specials","TotalPlayTime","UniverseAddress","GalacticAddress","RealityIndex","VoxelX","VoxelY","VoxelZ","SolarSystemIndex","PlanetIndex","Inventory","Inventory_Cargo","Inventory_TechOnly","FreighterInventory","Slots","Id","Amount","ShipOwnership","VehicleOwnership","Name","PersistentPlayerBases","Position","SaveName"}
    wanted.update(f"Chest{i}Inventory" for i in range(1,11))
    mapping={row["Key"]:row["Value"] for row in data["Mapping"] if row["Value"] in wanted}
    result={"source":"https://github.com/zencq/libNOM.map","blob":BLOB,"version":data["libMBIN_version"],"license":"GPL-3.0","mapping":mapping}
    path=target or Path(__file__).resolve().parent/".runtime"/"helpers"/"nms-keymap.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Mapa de chaves pronto:",path)
    return path

if __name__=="__main__":
    setup()
