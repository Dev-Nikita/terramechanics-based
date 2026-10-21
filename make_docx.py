#!/usr/bin/env python3
"""
Build a clean Word version of the manuscript.

Pandoc drops \\ref, \\citep and siunitx macros when converting LaTeX to DOCX,
which is what produced the blank symbols and raw [eq:...] labels in the earlier
Word file. This script resolves all of them to literal text *before* pandoc runs,
so the DOCX carries real numbers, real citations and real units.

Usage:  python3 make_docx.py manuscript.tex manuscript.docx
"""
import re, subprocess, sys, os

def brace(s, i):
    """Return (content, index_after) for a balanced {...} starting at s[i] == '{'."""
    d, j = 0, i
    while j < len(s):
        if s[j] == "{":
            d += 1
        elif s[j] == "}":
            d -= 1
            if d == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced brace")



SRC = sys.argv[1] if len(sys.argv) > 1 else "manuscript.tex"
OUT = sys.argv[2] if len(sys.argv) > 2 else "manuscript.docx"
TMP = "_docx_source.tex"

tex = open(SRC, encoding="utf-8").read()

# Splice the BibTeX output into the source so that pandoc sees a real
# bibliography and the citation labels can be resolved.
_bib = re.search(r"\\bibliography\{([^}]*)\}", tex) if False else None
import re as _re
m_bib = _re.search(r"\\bibliography\{[^}]*\}", tex)
if m_bib:
    bbl_path = os.path.splitext(SRC)[0] + ".bbl"
    if os.path.exists(bbl_path):
        bbl = open(bbl_path, encoding="utf-8").read()
        bbl = _re.sub(r"\\providecommand.*", "", bbl)
        bbl = _re.sub(r"\\expandafter.*", "", bbl)
        bbl = _re.sub(r"\\ifx\\xfnm.*", "", bbl)
        bbl = bbl.replace("\\newblock", " ")
        bbl = _re.sub(r"\\bibinfo\{[a-z]*\}", "", bbl)
        bbl = bbl.replace("\\DOIprefix", "doi:").replace("\\URLprefix", "URL: ")
        # expand the link macros the .bbl defines, otherwise pandoc drops the
        # DOI text and the entry degenerates to a bare "doi:."
        bbl = _re.sub(r"\\doi\{([^}]*)\}", r"\1", bbl)
        bbl = _re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", bbl)
        bbl = _re.sub(r"\\path\{([^}]*)\}", r"\1", bbl)
        bbl = _re.sub(r"\\url\{([^}]*)\}", r"\1", bbl)
        bbl = _re.sub(r"doi:\s*\.", "", bbl)
        tex = tex[:m_bib.start()] + "\\section*{References}\n" + bbl + tex[m_bib.end():]
    else:
        raise SystemExit("run bibtex first: no %s" % bbl_path)

# ----------------------------------------------------------------------
# 0. Flatten the elsarticle frontmatter into plain LaTeX pandoc understands
# ----------------------------------------------------------------------
def _strip_comments(src):
    """Drop LaTeX comment text. Without this, a commented-out example such as
    %%   \\author[lpnu]{...}
    is parsed as a real author and the name is emitted twice."""
    out = []
    for line in src.split("\n"):
        k, esc = None, False
        for i, ch in enumerate(line):
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
            elif ch == "%":
                k = i
                break
        out.append(line if k is None else line[:k])
    return "\n".join(out)


def flatten_frontmatter(tex):
    if "\\begin{frontmatter}" not in tex:
        return tex
    tex = _strip_comments(tex)
    fm = tex[tex.index("\\begin{frontmatter}"):tex.index("\\end{frontmatter}")]
    rest = tex[tex.index("\\end{frontmatter}") + len("\\end{frontmatter}"):]

    def grab(env):
        a = "\\begin{%s}" % env
        if a not in fm:
            return ""
        i = fm.index(a) + len(a)
        return fm[i:fm.index("\\end{%s}" % env)].strip()

    title = re.search(r"\\title\{", fm)
    ttl = brace(fm, fm.index("{", title.end() - 1))[0] if title else ""
    authors = [brace(fm, m.end() - 1)[0]
               for m in re.finditer(r"\\author(?:\[[^\]]*\])?\s*\{", fm)]
    authors = [re.sub(r"\\(corref|fnref)\{[^}]*\}", "", a).strip() for a in authors]
    aff = ""
    ma = re.search(r"\\affiliation(?:\[[^\]]*\])?\s*\{", fm)
    if ma:
        raw = brace(fm, ma.end() - 1)[0]
        parts = re.findall(r"(?:organization|addressline|city|postcode|country)=\{([^}]*)\}", raw)
        aff = ", ".join(p.strip() for p in parts if p.strip())

    out = ["\\documentclass{article}", "\\usepackage{graphicx}",
           "\\usepackage{booktabs}", "\\usepackage{multirow}",
           "\\usepackage{amsmath}", "\\usepackage{siunitx}",
           "\\title{%s}" % ttl,
           "\\author{%s}" % " \\and ".join(authors),
           "\\date{%s}" % aff,
           "\\begin{document}", "\\maketitle"]
    hl = grab("highlights")
    if hl:
        out += ["\\section*{Highlights}", "\\begin{itemize}", hl, "\\end{itemize}"]
    ab = grab("abstract")
    if ab:
        out += ["\\section*{Abstract}", ab]
    kw = grab("keyword")
    if kw:
        out += ["\\section*{Keywords}", kw.replace("\\sep", ";")]
    return "\n".join(out) + "\n" + rest


tex = flatten_frontmatter(tex)

# ----------------------------------------------------------------------
# 1. Number equations, figures and tables in order of appearance
# ----------------------------------------------------------------------
eq_no, fig_no, tab_no = {}, {}, {}

n = 0
for m in re.finditer(r"\\begin\{equation\}(.*?)\\end\{equation\}", tex, re.S):
    body = m.group(1)
    lab = re.search(r"\\label\{(.*?)\}", body)
    if lab:
        n += 1
        eq_no[lab.group(1)] = n

n = 0
for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", tex, re.S):
    lab = re.search(r"\\label\{(.*?)\}", m.group(0))
    if lab:
        n += 1
        fig_no[lab.group(1)] = n

n = 0
for m in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", tex, re.S):
    lab = re.search(r"\\label\{(.*?)\}", m.group(0))
    if lab:
        n += 1
        tab_no[lab.group(1)] = n

# section numbers
sec_no, cur = {}, [0, 0]
for line in tex.splitlines():
    ms = re.match(r"\\section\{", line)
    msub = re.match(r"\\subsection\{", line)
    if ms:
        cur = [cur[0] + 1, 0]
    elif msub:
        cur[1] += 1
    lab = re.search(r"\\label\{(sec:[^}]*)\}", line)
    if lab:
        sec_no[lab.group(1)] = f"{cur[0]}" if cur[1] == 0 else f"{cur[0]}.{cur[1]}"

ALL = {}
ALL.update({k: str(v) for k, v in eq_no.items()})
ALL.update({k: str(v) for k, v in fig_no.items()})
ALL.update({k: str(v) for k, v in tab_no.items()})
ALL.update(sec_no)

# ----------------------------------------------------------------------
# 2. Bibliography keys -> author-year strings
# ----------------------------------------------------------------------
cite = {}
for m in re.finditer(r"\\bibitem\[\{?(.*?)\}?\]\{(.*?)\}", tex, re.S):
    label = re.sub(r"\\s+", " ", m.group(1)).strip("{} ")
    key = m.group(2)
    mm = re.match(r"(.*?)\((\d{4}[a-z]?)\)", label)
    if mm:
        cite[key] = (mm.group(1).strip(), mm.group(2))
    else:
        cite[key] = (label, "")

def _cite(keys, paren):
    parts = []
    for k in [x.strip() for x in keys.split(",")]:
        a, y = cite.get(k, (k, ""))
        parts.append(f"{a}, {y}" if paren else f"{a} ({y})")
    return "(" + "; ".join(parts) + ")" if paren else " and ".join(parts)

# ----------------------------------------------------------------------
# 3. siunitx expansion
# ----------------------------------------------------------------------
UNITS = [
    ("\\kilo\\newton\\per\\metre^{n+2}", "kN/m^(n+2)"),
    ("\\kilo\\newton\\per\\metre^{n+1}", "kN/m^(n+1)"),
    ("\\metre\\cubed\\per\\second", "m3/s"),
    ("\\kilogram\\per\\metre\\cubed", "kg/m3"),
    ("\\metre\\per\\second", "m/s"),
    ("\\metre\\squared", "m2"),
    ("\\kilo\\newton", "kN"), ("\\kilo\\pascal", "kPa"),
    ("\\kilo\\watt", "kW"), ("\\kilo\\gram", "kg"),
    ("\\milli\\metre", "mm"), ("\\centi\\metre", "cm"),
    ("\\percent", "%"), ("\\degree", "\u00b0"),
    ("\\newton", "N"), ("\\pascal", "Pa"), ("\\watt", "W"),
    ("\\metre", "m"), ("\\second", "s"),
]


def unit(u):
    u = u.strip()
    for pat, rep in UNITS:
        u = u.replace(pat, rep)
    return u.replace("\\", "").strip()


def expand_macro(s, name, fn, nargs):
    out, i = [], 0
    pat = "\\" + name
    while True:
        k = s.find(pat, i)
        if k < 0 or (k + len(pat) < len(s) and s[k + len(pat)].isalpha()):
            if k < 0:
                out.append(s[i:]); break
            out.append(s[i:k + len(pat)]); i = k + len(pat); continue
        out.append(s[i:k])
        j = k + len(pat)
        args = []
        try:
            for _ in range(nargs):
                while j < len(s) and s[j] == " ":
                    j += 1
                a, j = brace(s, j)
                args.append(a)
        except ValueError:
            out.append(pat); i = k + len(pat); continue
        out.append(fn(*args))
        i = j
    return "".join(out)

# ----------------------------------------------------------------------
# 4. Rewrite
# ----------------------------------------------------------------------
t = tex

# equation numbers inside the maths
def numberise(m):
    body = m.group(1)
    lab = re.search(r"\\label\{(.*?)\}", body)
    if not lab:
        return m.group(0)
    num = eq_no[lab.group(1)]
    body = re.sub(r"\\label\{.*?\}", "", body).rstrip()
    body = body.rstrip(",.;")
    return "\\begin{equation}" + body + r"\qquad(" + str(num) + ")\n\\end{equation}"

t = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", numberise, t, flags=re.S)

# cross references
t = expand_macro(t, "ref", lambda k: ALL.get(k, "?"), 1)

# citations
t = expand_macro(t, "citep", lambda k: _cite(k, True), 1)
t = expand_macro(t, "citet", lambda k: _cite(k, False), 1)

# units
def _val(v):
    v = v.strip().replace("\\pm", "\u00b1").replace("\\times", "\u00d7")
    return re.sub(r"\u00b1\s+", "\u00b1", v)

t = expand_macro(t, "SI", lambda v, u: (f"{_val(v)}\\%" if unit(u) == "%"
                                        else f"{_val(v)} {unit(u)}").strip(), 2)
t = expand_macro(t, "si", lambda u: "\\%" if unit(u) == "%" else unit(u), 1)
t = expand_macro(t, "num", lambda v: v.strip(), 1)

# structures pandoc handles badly
t = expand_macro(t, "multirow", lambda a, b, c: c, 3)
t = expand_macro(t, "underbrace", lambda a: a, 1)
t = re.sub(r"_\{[FP]_\{(?:roll|skirt|aero|prop|fan)\}\}", "", t)
t = re.sub(r"_\{\\text\{Eq\.[^}]*\}\}", "", t)

# nomenclature tabbing -> two-column table
def tabbing_to_table(m):
    rows = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or "\\kill" in line or line.startswith("%"):
            continue
        line = line.rstrip("\\\\").rstrip()
        if "\\>" in line:
            a, b = line.split("\\>", 1)
            rows.append((a.strip(), b.strip().rstrip("\\\\").strip()))
    body = "\n".join(f"{a} & {b} \\\\" for a, b in rows)
    return ("\\begin{tabular}{ll}\n\\toprule\nSymbol & Quantity \\\\\n"
            "\\midrule\n" + body + "\n\\bottomrule\n\\end{tabular}")

t = re.sub(r"\\begin\{tabbing\}(.*?)\\end\{tabbing\}", tabbing_to_table, t, flags=re.S)

# packages / commands pandoc does not need
for pkg in ["lineno", "hyperref", "siunitx", "natbib", "multirow", "caption", "geometry"]:
    t = re.sub(r"\\usepackage(\[[^\]]*\])?\{" + pkg + r"\}", "", t)
t = t.replace(r"\linenumbers", "")
t = re.sub(r"\\thanks\{.*?\}", "", t, flags=re.S)
t = re.sub(r"\\sisetup\{.*?\}", "", t)
t = t.replace("\\renewcommand{\\figurename}{Fig.}", "")

# prefix captions with an explicit number (pandoc does not number)
def cap_fig(m):
    lab = re.search(r"\\label\{(fig:[^}]*)\}", m.group(0))
    num = fig_no.get(lab.group(1), "?") if lab else "?"
    return m.group(0).replace("\\caption{", "\\caption{Fig. %s. " % num, 1)

def cap_tab(m):
    lab = re.search(r"\\label\{(tab:[^}]*)\}", m.group(0))
    num = tab_no.get(lab.group(1), "?") if lab else "?"
    return m.group(0).replace("\\caption{", "\\caption{Table %s. " % num, 1)

t = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", cap_fig, t, flags=re.S)
t = re.sub(r"\\begin\{table\}.*?\\end\{table\}", cap_tab, t, flags=re.S)

open(TMP, "w", encoding="utf-8").write(t)
subprocess.run(["pandoc", TMP, "-o", OUT, "--resource-path=."], check=True)
os.remove(TMP)

print(f"{OUT} written: {len(eq_no)} equations, {len(fig_no)} figures, "
      f"{len(tab_no)} tables, {len(cite)} references resolved")
