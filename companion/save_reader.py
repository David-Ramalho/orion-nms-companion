"""Bounded, read-only decoder for PC LZ4 save blocks; no game-file writes."""
import json
import struct
from pathlib import Path

MAX_BYTES=64*1024*1024
MAGIC=0xFEEDA1E5

def decode_pc(data,keymap_path):
    import lz4.block
    offset=0
    chunks=[]
    total=0
    while offset<len(data):
        if len(data)-offset<16:
            raise ValueError("Cabeçalho de save incompleto.")
        magic,compressed,expanded,_=struct.unpack_from("<IIII",data,offset)
        if magic!=MAGIC or not 0<compressed<=MAX_BYTES or not 0<expanded<=MAX_BYTES:
            raise ValueError("Formato de blocos do save não reconhecido.")
        offset+=16
        if offset+compressed>len(data) or total+expanded>MAX_BYTES:
            raise ValueError("Bloco incompleto ou save descompactado maior que 64 MB.")
        try:
            raw=lz4.block.decompress(data[offset:offset+compressed],uncompressed_size=expanded)
        except Exception as exc:
            raise ValueError("Não foi possível descompactar este save.") from exc
        if len(raw)!=expanded:
            raise ValueError("Tamanho do bloco não confere.")
        chunks.append(raw);total+=expanded;offset+=compressed
    raw=b"".join(chunks)
    text=raw.decode("utf-8-sig",errors="replace").rstrip("\x00")
    root=json.loads(text)
    binary_ids=text.count("\ufffd")
    path=Path(keymap_path)
    if not path.is_file():
        raise ValueError("Mapa de chaves do NMS ausente. Execute setup-reader.py ou importe JSON legível.")
    mapping=json.loads(path.read_text(encoding="utf-8"))
    mapping=mapping.get("mapping",mapping)
    if not isinstance(mapping,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in mapping.items()):
        raise ValueError("Mapa de chaves inválido.")
    def walk(value):
        if isinstance(value,list):
            return [walk(item) for item in value]
        if isinstance(value,dict):
            out={}
            for key,item in value.items():
                target=mapping.get(key,key)
                if target in out:
                    raise ValueError("Mapa de chaves ambíguo; atualize o leitor.")
                out[target]=walk(item)
            return out
        return value
    result=walk(root)
    if binary_ids:
        result["_orion_decode_warning"]="IDs binários ilegíveis foram omitidos do inventário."
    return result
