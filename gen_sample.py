# Builds the demo 1 sample CSV and the expected results, by hand-specified plan.
# Expected values are written here from the plan, never computed by the tool.
import csv, io, json

COLS = ["Name","Email","Phone","Street address","City","Province","Postal code","Customer since"]
names = ["Maya Patel","Omar Haddad","Grace Liu","Robert Chen","Jon Tremblay","Anna Kowalski","Farah Siddiqui",
 "Priya Raman","Arjun Raman","David Smith","Karen Smith","Siobhan O'Brien","Lucas DeSouza","Marie-Claire O'Neill",
 "Kevin McDonald","Samuel Adeyemi","Hannah Weber","Élodie Gagné","Tom Nguyen","Lena Fischer","Noah Martin",
 "Ines Carvalho","Wei Zhang","Rachel Bauer","Ethan Brooks","Amara Okeke","Liam Fraser","Sofia Rossi",
 "Mateo Alvarez","Chloe Dubois","Yusuf Khan","Nadia Petrova","Ben Hofstetter","Aisha Bello","Owen Clarke",
 "Mei Tanaka","Isaac Mensah","Zoe Laurent","Ravi Kapoor","Julia Novak","Caleb Hughes","Leila Nasser",
 "Victor Lindqvist","Hana Sato","Marcus Reid","Tessa Kaur","Diego Morales","Fiona Walsh","Adam Kowal",
 "Sara Lindberg","Kofi Asante","Emily Harper","Daniel Moreau"]
assert len(names)==53 and len(set(names))==53
streets = ["King St W","Queen St S","Erb St W","Weber St N","University Ave E","Columbia St W","Victoria St S",
 "Frederick St","Belmont Ave W","Lancaster St E","Fischer-Hallman Rd","Ottawa St S","Highland Rd W","Bridgeport Rd E"]
cities = ["Kitchener","Waterloo","Cambridge","Kitchener","Waterloo","Elmira","Kitchener","New Hamburg"]
# unique valid postal codes (letters avoid D F I O Q U; first letter N)
L2 = "ABCEGHJKLMNPRSTVWXYZ"
postals=[]
for i in range(53):
    postals.append(f"N2{L2[i%20]} {i//20+1}{L2[(i*7)%20]}{i%10}")
assert len(set(postals))==53
base=[]
for i,n in enumerate(names):
    first,last = n.split(" ",1)
    slug = (first+"."+last).lower().replace("'","").replace("é","e").replace(" ","")
    dom = ["example.com","example.org","example.net"][i%3]
    area = "519" if i<45 else "226"
    phone = f"{area}-555-{100+i:04d}"[:12]
    phone = f"{area}-555-01{i:02d}"
    date = f"20{22+i%4}-{(i%12)+1:02d}-{(i*2)%27+1:02d}"
    base.append({"Name":n,"Email":f"{slug}@{dom}","Phone":phone,"Street address":f"{10+i*7} {streets[i%len(streets)]}",
                 "City":cities[i%len(cities)],"Province":"ON","Postal code":postals[i],"Customer since":date})
B={r["Name"]:r for r in base}
# Traps: Raman household shares address + postal; the two Smiths share a street only
B["Arjun Raman"]["Street address"]=B["Priya Raman"]["Street address"]
B["Arjun Raman"]["Postal code"]=B["Priya Raman"]["Postal code"]
B["Arjun Raman"]["City"]=B["Priya Raman"]["City"]
B["Karen Smith"]["Street address"]=B["David Smith"]["Street address"].split(" ",1)[0]+"0 "+B["David Smith"]["Street address"].split(" ",1)[1]
B["Lucas DeSouza"]["Postal code"]="N2Z 1W4"   # valid: Z and W allowed after first letter
B["Siobhan O'Brien"]["Phone"]="519-555-0111 ext. 5"  # already correct with extension
B["Marcus Reid"]["Customer since"]="2024-05-05"

clean={n:dict(r) for n,r in B.items()}   # expected clean values per base row
raw={n:dict(r) for n,r in B.items()}
changes=[]   # (name, col, category)
flags=[]     # (name, col, code)
def mut(n,col,rawv,cat,cleanv=None):
    raw[n][col]=rawv
    if cleanv is not None: clean[n][col]=cleanv
    changes.append((n,col,cat))
def flag(n,col,rawv,code):
    raw[n][col]=rawv; clean[n][col]=rawv; flags.append((n,col,code))

# 12 spacing/capitalization cells on base rows (+2 on the Grace Liu copy = 14)
mut("Marie-Claire O'Neill","Name","MARIE-CLAIRE O'NEILL","text")
mut("Kevin McDonald","Name","kevin mcdonald","text")
mut("Samuel Adeyemi","Name","Samuel  Adeyemi","text")
mut("Hannah Weber","Name","  Hannah Weber ","text")
mut("Élodie Gagné","Name","ÉLODIE GAGNÉ","text")
clean["Noah Martin"]["City"]="Waterloo"; mut("Noah Martin","City","waterloo","text")
clean["Ines Carvalho"]["City"]="Kitchener"; mut("Ines Carvalho","City","KITCHENER","text")
clean["Wei Zhang"]["City"]="Cambridge"; mut("Wei Zhang","City","Cambridge ","text")
mut("Tom Nguyen","Email","Tom.Nguyen@Example.com","text")
mut("Lena Fischer","Email"," lena.fischer@example.org","text")
clean["Rachel Bauer"]["Street address"]="12 Queen St S"; mut("Rachel Bauer","Street address","12  Queen St S","text")
mut("Ethan Brooks","Province","ON ","text")

# 8 phone fixes on base rows (+1 on the Grace Liu copy = 9)
def ph(n,rawfmt):
    d=clean[n]["Phone"].replace("-","")
    mut(n,"Phone",rawfmt.format(a=d[:3],b=d[3:6],c=d[6:]),"phone")
ph("Amara Okeke","{a}{b}{c}")
ph("Liam Fraser","({a}) {b}-{c}")
ph("Sofia Rossi","{a}.{b}.{c}")
ph("Mateo Alvarez","+1 {a} {b} {c}")
ph("Chloe Dubois","1-{a}-{b}-{c}")
ph("Yusuf Khan","{a} {b} {c}")
ph("Kofi Asante","({a}){b}{c}")          # a 226 number
ph("Nadia Petrova","{a}-{b}-{c} x12"); clean["Nadia Petrova"]["Phone"]+=" ext. 12"
flag("Ben Hofstetter","Phone","555-0131","phone_invalid")
flag("Aisha Bello","Phone","519-555-01322","phone_invalid")

# postal: 6 fixes, 4 invalid
def pc(n,f):
    mut(n,"Postal code",f(clean[n]["Postal code"]),"postal")
pc("Owen Clarke",lambda p:p.replace(" ","").lower())
pc("Mei Tanaka",lambda p:p.lower())
pc("Isaac Mensah",lambda p:p.replace(" ","-"))
pc("Zoe Laurent",lambda p:p.replace(" ","").lower())
pc("Ravi Kapoor",lambda p:" "+p)
pc("Julia Novak",lambda p:p.replace(" ","  "))
flag("Caleb Hughes","Postal code","N2L 3G","postal_invalid")
flag("Leila Nasser","Postal code","D2L 3G1","postal_invalid")
flag("Victor Lindqvist","Postal code","N2O 4B7","postal_invalid")
flag("Hana Sato","Postal code","12345","postal_invalid")

# dates: 8 fixes, 3 ambiguous, 1 impossible
def dt(n,rawv,iso):
    clean[n]["Customer since"]=iso; mut(n,"Customer since",rawv,"date")
dt("Tessa Kaur","2024/03/15","2024-03-15")
dt("Diego Morales","15/03/2024","2024-03-15")
dt("Fiona Walsh","03/15/2024","2024-03-15")
dt("Adam Kowal","March 4, 2025","2025-03-04")
dt("Sara Lindberg","4 Mar 2025","2025-03-04")
dt("Emily Harper","2025.06.30","2025-06-30")
dt("Marcus Reid","05/05/2025","2025-05-05")
dt("Daniel Moreau","2023-7-4","2023-07-04")
AMB={"Mei Tanaka":("03/04/2025","2025-04-03","2025-03-04"),
     "Isaac Mensah":("07/11/2024","2024-11-07","2024-07-11"),
     "Zoe Laurent":("02/01/2026","2026-01-02","2026-02-01")}
for n,(r,dfirst,mfirst) in AMB.items(): flag(n,"Customer since",r,"date_ambiguous")
flag("Ravi Kapoor","Customer since","2025-02-30","date_impossible")

# missing required (name, email, phone)
flag("Victor Lindqvist","Name","","missing")   # also has invalid postal: two flags, one row
flag("Julia Novak","Email","","missing")
flag("Owen Clarke","Email","","missing")
flag("Sofia Rossi","Phone","","missing"); changes[:] = [c for c in changes if c[0:2]!=("Sofia Rossi","Phone")]
flag("Leila Nasser","Phone","","missing")
# ...Sofia's phone fix was replaced by a blank, so move that phone format to another row
ph("Fiona Walsh","({a}){b}-{c}")
# blank but not required: must not be flagged
raw["Hannah Weber"]["City"]=""; clean["Hannah Weber"]["City"]=""
raw["Kofi Asante"]["City"]=""; clean["Kofi Asante"]["City"]=""

# ---- assemble rows: 53 base + 7 duplicate rows, in a fixed interleaved order
rows=[]  # list of (label, raw, clean)
extra={}
g=raw["Grace Liu"]
extra["X1"]=(dict(raw["Maya Patel"]),dict(clean["Maya Patel"]))
extra["X2"]=(dict(raw["Omar Haddad"]),dict(clean["Omar Haddad"]))
x3r=dict(g); x3r["Name"]="grace liu"; x3r["Email"]=g["Email"].upper(); d=g["Phone"].replace("-",""); x3r["Phone"]=f"({d[:3]}) {d[3:6]}-{d[6:]}"
extra["X3"]=(x3r,dict(clean["Grace Liu"]))
n1=dict(clean["Robert Chen"]); n1.update({"Name":"Bob Chen","Phone":"519-555-0170","Customer since":"2025-09-12"})
extra["N1"]=(dict(n1),dict(n1))
n2=dict(clean["Jon Tremblay"]); n2.update({"Name":"John Tremblay","Email":"j.tremblay.work@example.com","Customer since":"2024-10-02"})
extra["N2"]=(dict(n2),dict(n2))
n3=dict(clean["Anna Kowalski"]); n3.update({"Name":"Anna Kowalsky","Email":"annak@example.net","Phone":"519-555-0172","Customer since":"2026-01-20"})
extra["N3"]=(dict(n3),dict(n3))
n4=dict(clean["Farah Siddiqui"]); n4.update({"Email":"farah.s@example.org","Phone":"226-555-0173","Street address":clean["Farah Siddiqui"]["Street address"].replace(" St S"," Street South"),"Customer since":"2025-11-30"})
extra["N4"]=(dict(n4),dict(n4))
changes.append(("X3","Name","text")); changes.append(("X3","Email","text")); changes.append(("X3","Phone","phone"))

order=list(names)
import random as _r
_r.Random(11).shuffle(order)
inserts={"Karen Smith":"X1","Zoe Laurent":"X2","Emily Harper":"X3","Hana Sato":"N1","Leila Nasser":"N2","Daniel Moreau":"N3","Fiona Walsh":"N4"}
for n in order:
    rows.append((n,raw[n],clean[n]))
    if n in inserts:
        k=inserts[n]; rows.append((k,)+extra[k])
assert len(rows)==60
rowno={lab:i+2 for i,(lab,_,_) in enumerate(rows)}
buf=io.StringIO(); w=csv.writer(buf,lineterminator="\n"); w.writerow(COLS)
for _,r,_ in rows: w.writerow([r[c] for c in COLS])
open("sample.csv","w",encoding="utf-8").write(buf.getvalue())

cat_counts={}
for _,_,c in changes: cat_counts[c]=cat_counts.get(c,0)+1
flag_counts={}
for _,_,c in flags: flag_counts[c]=flag_counts.get(c,0)+1
pairs=[("exact",rowno["Maya Patel"],rowno["X1"]),("exact",rowno["Omar Haddad"],rowno["X2"]),("exact",rowno["Grace Liu"],rowno["X3"]),
       ("near",rowno["Robert Chen"],rowno["N1"]),("near",rowno["Jon Tremblay"],rowno["N2"]),
       ("near",rowno["Anna Kowalski"],rowno["N3"]),("near",rowno["Farah Siddiqui"],rowno["N4"])]
exp={"columns":COLS,
 "clean":[[r2[c] for c in COLS] for _,_,r2 in rows],
 "changes":sorted([[rowno[n],col,cat] for n,col,cat in changes]),
 "flags":sorted([[rowno[n],col,code] for n,col,code in flags]),
 "pairs":sorted([[t,min(a,b),max(a,b)] for t,a,b in pairs],key=lambda x:(x[1],x[2])),
 "chen":{"rows":sorted([rowno["Robert Chen"],rowno["N1"]]),"names":{str(rowno["Robert Chen"]):"Robert Chen",str(rowno["N1"]):"Bob Chen"}},
 "ambiguous":{str(rowno[n]):{"day":v[1],"month":v[2]} for n,v in AMB.items()},
 "counts":{"changes":cat_counts,"flags":flag_counts,"changes_total":len(changes),"flags_total":len(flags)},
 "traps":{"raman":[rowno["Priya Raman"],rowno["Arjun Raman"]],"smith":[rowno["David Smith"],rowno["Karen Smith"]],
          "obrien":rowno["Siobhan O'Brien"],"desouza":rowno["Lucas DeSouza"]}}
json.dump(exp,open("expected.json","w"),indent=1,ensure_ascii=False)
print(json.dumps(exp["counts"]),exp["pairs"])
