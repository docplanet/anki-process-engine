"""Deterministic card checks. Everything here is a string operation — no judgment."""
import json,urllib.request,re,glob,sys,html

SRC="classes/ISF/Exam 2/Histology/Week 3/out/sources"
def inv(a,**p):
    r=json.loads(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765",
        json.dumps({"action":a,"version":6,"params":p}).encode(),{"Content-Type":"application/json"}),timeout=60).read())
    if r.get("error"): raise RuntimeError(f"{a}: {r['error']}")
    return r["result"]

def norm(s):
    s=re.sub(r'\[[^\]]*\]',' ',s)                    # drop [dynein]-style corrections
    s=s.replace("’","'").replace("‘","'").replace("­","")
    return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()

blob=" ".join(open(p,encoding="utf-8",errors="replace").read() for p in glob.glob(SRC+"/*.txt"))
NB=norm(blob)
CLOZE=re.compile(r'\{\{c(\d+)::(.*?)\}\}',re.S)
media=set(inv("getMediaFilesNames",pattern="isf-*"))

query=sys.argv[1] if len(sys.argv)>1 else 'deck:"ISF::Test 2::Histology::Week 3"'
notes=inv("notesInfo",notes=inv("findNotes",query=query))
bad=0
for n in sorted(notes,key=lambda x:x["fields"]["Source"]["value"]):
    T,E=n["fields"]["Text"]["value"],n["fields"]["Extra"]["value"]
    f=[]
    plain=html.unescape(re.sub(r'<[^>]+>',' ',E))     # strip tags BEFORE finding quotes
    for q in re.findall(r'"([^"]{15,})"',plain):
        nq=norm(q)
        if nq and nq not in NB: f.append(f"QUOTE not in sources: “{q[:60]}…”")
    if re.search(r'cues joined|consecutive cues',E,re.I): f.append("Extra admits JOINED CUES")
    cl=CLOZE.findall(T)
    if len({c for c,_ in cl})>3: f.append("more than 3 clozes")
    is_list = bool(re.search(r'<br>\s*\d+\.', T))      # list items share a cloze and take no hints
    if not is_list:
        for _,body in cl:
            if "<i" in body and "::" not in body: f.append("answer cloze with no hint")
    for img in re.findall(r'<img src="([^"]+)"',T+E):
        if img not in media: f.append(f"image missing from media: {img}")
    if f:
        bad+=1
        print(f"[{n['noteId']}] {n['fields']['Source']['value']}")
        for x in dict.fromkeys(f): print(f"    - {x}")
print(f"\n{len(notes)-bad}/{len(notes)} clean | {bad} with a mechanical flag")
