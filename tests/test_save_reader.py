import json,struct,tempfile,unittest
from pathlib import Path
import lz4.block
from companion.save_reader import decode_pc,MAGIC
from companion.game import normalize

class SaveReaderTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).parent/".runtime";root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root)
        self.map=Path(self.temp.name)/"map.json"
        self.map.write_text(json.dumps({"mapping":{"PS":"PlayerStateData","UI":"Units","INV":"Inventory","SL":"Slots","ID":"Id","AM":"Amount"}}))
    def tearDown(self):
        self.temp.cleanup()
    def block(self,raw):
        compressed=lz4.block.compress(raw,store_size=False)
        return struct.pack("<IIII",MAGIC,len(compressed),len(raw),0)+compressed
    def test_multiblock_save_is_normalized(self):
        raw=json.dumps({"PS":{"UI":50,"INV":{"SL":[{"ID":"^FUEL1","AM":3}]}}}).encode()+b"\0"
        data=self.block(raw[:20])+self.block(raw[20:])
        result=normalize(decode_pc(data,self.map))
        self.assertEqual(result["Units"],50)
        self.assertEqual(result["inventory"],[{"item":"FUEL1","amount":3,"container":"Inventory"}])
    def test_binary_identifiers_are_omitted_with_warning(self):
        raw=b'{"PS":{"UI":50,"INV":{"SL":[{"ID":"^\x80bad","AM":3},{"ID":"^FUEL1","AM":2}]}}}\0'
        result=normalize(decode_pc(self.block(raw),self.map))
        self.assertEqual(len(result["inventory"]),1)
        self.assertIn("warning",result)
    def test_truncated_block_rejected(self):
        data=self.block(b'{"PS":{"UI":50}}')
        with self.assertRaises(ValueError):decode_pc(data[:-2],self.map)
    def test_decompression_size_bounded_before_allocation(self):
        data=struct.pack("<IIII",MAGIC,2,128*1024*1024,0)+b"AA"
        with self.assertRaises(ValueError):decode_pc(data,self.map)
    def test_unmapped_schema_rejected(self):
        data=self.block(b'{"unknown":{"balance":50}}')
        with self.assertRaises(ValueError):normalize(decode_pc(data,self.map))
    def test_mapping_collision_rejected(self):
        self.map.write_text(json.dumps({"mapping":{"A":"Units","B":"Units"}}))
        with self.assertRaisesRegex(ValueError,"ambíguo"):decode_pc(self.block(b'{"A":1,"B":2}'),self.map)

if __name__=="__main__":unittest.main()
