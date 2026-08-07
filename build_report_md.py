"""
Render report/*.md into FULL_REPORT.html.

THE POINT OF THIS FILE. The prose lives in report/*.md and is edited by hand, by
anyone, in any editor or straight in GitHub's web UI. The numbers live in
report_data.py and are regenerated from the metrics files whenever a study
re-runs. Neither can clobber the other: editing prose cannot change a result, and
re-running a study cannot undo an edit.

MARKDOWN YOU CAN USE
    ## Heading                     a numbered top-level section
    ### Heading                    a subsection
    **bold**  *italic*  `code`     the usual
    - item                         a list
    | a | b |                      a table (or use a {{table:...}} placeholder)

    > [!KEY]     a highlighted takeaway box
    > [!WARN]    a correction or a caveat that changes how a number reads
    > [!NOTE]    an aside

PLACEHOLDERS, resolved from live metrics at build time
    {{val:recip_err}}              one formatted number
    {{table:precision}}            a whole table
    {{fig:figs_new/n1_mesh.png|caption}}
    {{methods:precision}}          the Materials & Methods block for a study
    {{common_methods}}             the shared-model methods block
    {{technical}}                  the technical-foundations chapter

Run `python build_report_md.py` to rebuild. Unknown placeholders become visible
HTML comments rather than silent blanks, so a typo shows up instead of vanishing.
"""
import datetime, glob, os, re, subprocess

import markdown

import report_data as rd

OUT = "FULL_REPORT.html"
SRC = "report"

TITLE = "Directional bioimpedance sensing for pediatric vesicoureteral reflux"
SUBTITLE = ("Complete simulation report, covering all work since the two-strip "
            "design decision.<br>"
            "Live: https://larachieppe.github.io/reflux-directional/ &middot; "
            "Source: https://github.com/larachieppe/reflux-directional")

CALLOUT = {"KEY": "key", "WARN": "warn", "NOTE": "note"}


def _rev():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "n/a"
    except Exception:
        return "n/a"


# ---------------------------------------------------------------- callouts
def _callouts(text):
    """> [!KEY] ...  ->  a div the stylesheet knows about, markdown still parsed."""
    out, i, lines = [], 0, text.split("\n")
    while i < len(lines):
        m = re.match(r"^>\s*\[!(KEY|WARN|NOTE)\]\s*(.*)$", lines[i])
        if not m:
            out.append(lines[i]); i += 1; continue
        cls = CALLOUT[m.group(1)]
        body = [m.group(2).strip()] if m.group(2).strip() else []
        i += 1
        while i < len(lines) and lines[i].startswith(">"):
            body.append(re.sub(r"^>\s?", "", lines[i])); i += 1
        # Keep the body's own line structure so a blank "> " line stays a
        # paragraph break. Joining it all into one string collapsed multi-
        # paragraph callouts into a wall of text.
        out += ["", f'<div class="{cls}" markdown="1">', ""] + body + ["", "</div>", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- placeholders
_PH = re.compile(r"\{\{(\w+)(?::((?:[^{}]|\{(?!\{))*))?\}\}")


def _resolve(text):
    return _PH.sub(lambda m: rd.resolve(m.group(1), (m.group(2) or "").strip()), text)


# ---------------------------------------------------------------- build
def build():
    # Only NN-named files are report content. Anything else in the folder --
    # README.md, notes, drafts -- is documentation and must not be rendered into
    # the report, which is what happened the first time this ran.
    files = sorted(f for f in glob.glob(os.path.join(SRC, "*.md"))
                   if re.match(r"\d\d-", os.path.basename(f)))
    if not files:
        raise SystemExit(f"no NN-named markdown found in {SRC}/")

    md = markdown.Markdown(extensions=["tables", "attr_list", "md_in_html",
                                       "sane_lists", "smarty"],
                           extension_configs={"smarty": {"smart_dashes": False}})

    chunks = []
    for f in files:
        raw = open(f).read()
        md.reset()
        chunks.append(md.convert(_callouts(raw)))
    html = "\n".join(chunks)

    # placeholders AFTER markdown, so generated tables are not reflowed as text
    html = re.sub(r"<p>\s*(\{\{[^}]+\}\})\s*</p>", r"\1", html)   # unwrap block ones
    html = _resolve(html)

    # Defensive: if a block placeholder shared a paragraph with something else --
    # a missing blank line in the source -- markdown will have wrapped a <table>
    # or <div> inside a <p>, which is invalid and renders inconsistently. Lift it
    # back out rather than shipping broken markup.
    for _ in range(3):
        new = re.sub(r"<p>((?:(?!</p>).)*?)(<(?:table|div)\b.*?</(?:table|div)>)"
                     r"((?:(?!</p>).)*?)</p>",
                     lambda m: (f"<p>{m.group(1)}</p>" if m.group(1).strip() else "")
                               + m.group(2)
                               + (f"<p>{m.group(3)}</p>" if m.group(3).strip() else ""),
                     html, flags=re.S)
        if new == html:
            break
        html = new

    # anchors + contents, derived from the headings themselves
    def anchor(m):
        lvl, num, rest = m.group(1), m.group(2), m.group(3)
        return f'<h{lvl} id="s{num.replace(".", "_")}">{num}{rest}</h{lvl}>'

    # The number may be "1." or "8.1" or "3.1&nbsp;". Requiring a literal "." or
    # "&nbsp;" straight after the number made the engine backtrack on "8.1 Title",
    # capturing "8" and leaving ".1 Title", which rendered as "8 1" in the
    # contents. Allow an optional dot then any separator.
    HEAD = r'<h([23])>(\d+(?:\.\d+)?)(\.?(?:&nbsp;|\s)[^<]*)</h\1>'
    html = re.sub(HEAD, anchor, html)

    toc = []
    for m in re.finditer(r'<h([23]) id="([^"]+)">(\d+(?:\.\d+)?)(\.?(?:&nbsp;|\s)[^<]*)</h\1>',
                         html):
        lvl, hid, num, rest = m.groups()
        title = re.sub(r"&mdash;.*$", "", rest.lstrip(". ").replace("&nbsp;", "")).strip()
        toc.append(f'<li class="t{lvl}"><a href="#{hid}"><b>{num}</b> {title}</a></li>')
    html = html.replace("<!--TOC-->",
                        f'<div class="toc"><b>Contents</b><ul>{"".join(toc)}</ul></div>')

    html = re.sub(r"&sect;(\d+(?:\.\d+)?)",
                  lambda m: f'<a href="#s{m.group(1).replace(".", "_")}">'
                            f'&sect;{m.group(1)}</a>', html)

    missing = re.findall(r"<!-- unknown ([^>]+) -->", html)
    if missing:
        print("  WARNING unresolved:", set(missing))

    page = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Directional reflux sensing: complete simulation report</title>
<link rel="icon" href="favicon.ico">
<style>
 body{{font-family:Arial,Helvetica,sans-serif;font-size:11pt;color:#000;max-width:860px;
      margin:32px auto;line-height:1.55;padding:0 22px}}
 h1{{font-size:23pt;margin:28px 0 6px}}
 h2{{font-size:16pt;color:#1155cc;margin:32px 0 8px;border-bottom:1px solid #ccc;padding-bottom:4px}}
 h3{{font-size:12.5pt;margin:20px 0 6px}}
 table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:9.5pt}}
 th,td{{border:1px solid #000;padding:5px 7px;text-align:center;vertical-align:top}}
 th{{background:#efefef}} td:first-child,th:first-child{{text-align:left}}
 tr.hi td{{background:#e8f2e8}} tr.bad td{{background:#fdecea}}
 ul,ol{{margin:8px 0 8px 24px}} li{{margin:5px 0}}
 .cap{{font-size:9.5pt;color:#555;text-align:center;margin:0 0 18px;font-style:italic}}
 em.cap,p em{{}}
 .key{{border:2px solid #1155cc;background:#eef3fb;padding:12px 16px;margin:16px 0}}
 .warn{{border-left:4px solid #c0392b;padding:10px 14px;background:#fdf2f1;margin:14px 0}}
 .note{{border-left:4px solid #c98500;padding:10px 14px;background:#fbf7ef;margin:14px 0}}
 .key p:first-child,.warn p:first-child,.note p:first-child{{margin-top:0}}
 .key p:last-child,.warn p:last-child,.note p:last-child{{margin-bottom:0}}
 img{{max-width:100%;border:1px solid #ddd}} .sub{{color:#555;font-size:10pt}}
 .toc{{border:1px solid #ccd6da;background:#fbfcfd;padding:14px 20px;margin:22px 0;
   border-radius:5px;font-size:10pt;column-count:2;column-gap:28px}}
 .toc ul{{margin:8px 0 0 0;padding:0;list-style:none}}
 .toc li{{margin:2px 0;break-inside:avoid}}
 .toc li.t3{{padding-left:16px;font-size:9.5pt;color:#555}}
 .toc a{{color:#1155cc;text-decoration:none}} .toc a:hover{{text-decoration:underline}}
 h2[id],h3[id]{{scroll-margin-top:12px}}
 @media(max-width:700px){{.toc{{column-count:1}}}}
{rd.bm.CSS}
{rd.bt.CSS}
 .methods table.mm-t th,.methods table.mm-t td{{text-align:left}}
 .techsec table.mm-t th,.techsec table.mm-t td{{text-align:left;border:1px solid #d7e0e4}}
</style></head><body>

<h1>{TITLE}</h1>
<p class="sub">{SUBTITLE}<br>
Built {datetime.date.today().isoformat()} from <code>report/*.md</code> &middot;
commit <code>{_rev()}</code></p>

{html}
</body></html>"""

    open(OUT, "w").write(page)
    print(f"wrote {OUT} ({len(page)//1024} KB) from {len(files)} markdown files, "
          f"{len(toc)} headings linked")


if __name__ == "__main__":
    build()
