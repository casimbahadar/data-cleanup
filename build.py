import json
t=open("template.html",encoding="utf-8").read()
s=open("sample.csv",encoding="utf-8").read()
out=t.replace("__SAMPLE__", json.dumps(s, ensure_ascii=False))
import re, hashlib, base64
script=re.search(r"<script>([\s\S]*?)</script>", out).group(1)
h=base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode()
csp=("default-src 'none'; script-src 'sha256-"+h+"'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
     "font-src https://fonts.gstatic.com; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'")
out=out.replace("__CSP__", '<meta http-equiv="Content-Security-Policy" content="'+csp+'">')
import os; os.makedirs("out",exist_ok=True)
open("out/index.html","w",encoding="utf-8").write(out)
print(len(out))
