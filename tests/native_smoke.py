import json,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from companion.capture import ocr
from companion.desktop import Desktop
root=Path(".test-data");root.mkdir(exist_ok=True)
image=Image.new("RGB",(1000,220),"white")
draw=ImageDraw.Draw(image)
font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",38)
draw.text((35,40),"ORION EXPLORATION 12345",font=font,fill="black")
path=root/"ocr-fixture.png";image.save(path)
desktop=Desktop();desktop.start(lambda raw,suffix:"")
time.sleep(.5)
result={"ocr":ocr(path),"hotkeys_registered":desktop.hotkeys}
desktop.close()
print(json.dumps(result,ensure_ascii=True))
