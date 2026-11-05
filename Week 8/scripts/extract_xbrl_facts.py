"""Parse the MSFT 10-Q XBRL instance (Data Engineering repo) into flat fact rows.

    python scripts/extract_xbrl_facts.py upstream/data_engineering_kpmg/data/raw/sec/0001193125-26-191507/msft-20260331_htm.xml data/msft_xbrl_facts.jsonl

One row per fact: concept, value (as filed), unit, decimals, period start/end, dimensions (axis -> member).
This is the same source document the RAG Gold Set v0 and the Data team's RDS load use, so all three agree
on what a "fact" is. Standard library + lxml only."""
import sys, json
from lxml import etree
path, out = sys.argv[1:3]
tree = etree.parse(path); root = tree.getroot()
NS = {"x": "http://www.xbrl.org/2003/instance", "xbrldi": "http://xbrl.org/2006/xbrldi"}
ctx = {}
for c in root.findall("x:context", NS):
    p = c.find("x:period", NS)
    inst = p.find("x:instant", NS)
    if inst is not None: per = {"instant": inst.text.strip()}
    else: per = {"start": p.find("x:startDate", NS).text.strip(), "end": p.find("x:endDate", NS).text.strip()}
    dims = {m.get("dimension"): (m.text or "").strip() for m in c.iter("{%s}explicitMember" % NS["xbrldi"])}
    typed = {m.get("dimension"): "".join(m.itertext()).strip() for m in c.iter("{%s}typedMember" % NS["xbrldi"])}
    dims.update(typed)
    ctx[c.get("id")] = {**per, "dims": dims}
units = {}
for u in root.findall("x:unit", NS):
    m = u.find(".//x:measure", NS)
    num = u.find(".//x:unitNumerator/x:measure", NS); den = u.find(".//x:unitDenominator/x:measure", NS)
    units[u.get("id")] = f"{num.text}/{den.text}" if num is not None else m.text
rows = []
for el in root:
    if not isinstance(el.tag, str) or el.get("contextRef") is None: continue
    q = etree.QName(el)
    prefix = {v: k for k, v in el.nsmap.items() if k}.get(q.namespace, q.namespace)
    c = ctx[el.get("contextRef")]
    rows.append({"concept": f"{prefix}:{q.localname}", "value": (el.text or "").strip()[:400],
                 "unit": units.get(el.get("unitRef")), "decimals": el.get("decimals"),
                 "start": c.get("start"), "end": c.get("end") or c.get("instant"), "instant": "instant" in c,
                 "dims": c["dims"], "id": el.get("id")})
CIK, ACC = "0000789019", "0001193125-26-191507"
with open(out, "w") as f:
    for r in rows:
        r.update({"cik": CIK, "accession": ACC, "ticker": "MSFT"})
        f.write(json.dumps(r) + "\n")
print(len(rows), "facts", len(ctx), "contexts")
