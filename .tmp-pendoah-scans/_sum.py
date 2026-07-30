import json,sys
from pathlib import Path
for name in ["crewscore-self","agenthub","elli","tellgence"]:
    p = Path(r"C:\Repos\shmindmaster\crewscore\.tmp-pendoah-scans")/f"{name}.json"
    print(f"\n===== {name} =====")
    if not p.exists():
        print("missing"); continue
    raw = p.read_text(encoding="utf-8").strip()
    if not raw.startswith(("[","{")):
        print("NOT_JSON:", raw[:180].replace("\n"," ")); continue
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("files") or data.get("results") or [data]
    print(f"files={len(data)}")
    for f in data[:30]:
        smells = f.get("smells") or []
        sn = ",".join((s.get("name") or s.get("smell_id") or "?") for s in smells[:3])
        path = (f.get("path") or "?")[:95]
        print(f"  {path}")
        print(f"    prof={f.get('profile')} overall={f.get('overall','-')} smells={len(smells)} [{sn}] tier={str(f.get('tier',''))[:45]}")
    if len(data)>30: print(f"  ... +{len(data)-30} more")
