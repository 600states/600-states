import csv, json, hashlib, itertools, sys
FIELD="evidence_row_sha256"
path=sys.argv[1]
rows=list(csv.DictReader(open(path,encoding="utf-8")))
cols=[c for c in rows[0].keys() if c!=FIELD]

def coerce(v, typed):
    if v=="" : return None
    if not typed: return v
    if v in ("True","False"): return v=="True"
    try:
        if v.lstrip("-").isdigit(): return int(v)
    except Exception: pass
    try:
        f=float(v)
        if "." in v or "e" in v.lower(): return f
    except Exception: pass
    return v

# kandidatdelmangder av kolumner
subsets={
 "alla": cols,
 "utan_grid": [c for c in cols if c not in ("tile_index","grid_row","grid_column")],
 "utan_grid_obs": [c for c in cols if c not in ("tile_index","grid_row","grid_column","observation_id")],
 "utan_status": [c for c in cols if c not in ("selection_status","emotion_locked_out","color_protocol_access")],
}
found=[]
for sname,sub in subsets.items():
  for typed in (False,True):
    for empty_none in (True,False):
      for srt in (True,False):
        for sep in ((",",":"),(", ",": ")):
          for ascii_ in (True,False):
            hit=0
            for r in rows[:40]:
                d={}
                for k in sub:
                    v=r[k]
                    d[k]= (coerce(v,typed) if empty_none else (coerce(v,typed) if v!="" else ""))
                s=json.dumps(d,sort_keys=srt,separators=sep,ensure_ascii=ascii_)
                if hashlib.sha256(s.encode()).hexdigest()==r[FIELD].lower(): hit+=1
            if hit: found.append((sname,typed,empty_none,srt,sep,ascii_,hit))
print("JSON-varianter med traff (av 40 testrader):", found if found else "INGA")

# alternativ: sammanfogad strang med avgransare
seps=["|","\x1f","","\t",";"]
found2=[]
for sname,sub in subsets.items():
  for s_ in seps:
    for srt in (True,False):
      keys=sorted(sub) if srt else sub
      hit=0
      for r in rows[:40]:
          s=s_.join(str(r[k]) for k in keys)
          if hashlib.sha256(s.encode()).hexdigest()==r[FIELD].lower(): hit+=1
      if hit: found2.append((sname,repr(s_),srt,hit))
print("Strangvarianter med traff:", found2 if found2 else "INGA")
