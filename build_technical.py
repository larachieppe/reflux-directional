"""
Assemble the technical foundations chapter from sections/*.html.

Each section was drafted against the code and the measured results, then put
through an adversarial review pass by a reviewer instructed to refute it, then
rewritten to answer the surviving objections. The review found real errors --
including two in this report's own prior text -- so the sections are kept as
authored rather than paraphrased.

Exposes technical_html() for build_full_report.py and writes TECHNICAL.html
standalone.
"""
import datetime, os, re, subprocess

SEC_DIR = "sections"

# (file prefix, number, short label for the contents list)
ORDER = [
    ("physical_basis_and_governing_equations", "3.1",
     "the field model, and the two conditions that license it"),
    ("the_complete_electrode_model_and_its_d", "3.2",
     "the boundary value problem actually solved, and what its verification proves"),
    ("reciprocity_lead_fields_and_the_sensitiv", "3.3",
     "where a zone looks, with what sign, and how deep"),
    ("why_direction_is_observable_and_why_on", "3.4",
     "the identifiability argument for reading a direction off a surface array"),
    ("common_mode_rejection_and_the_refuted_", "3.5",
     "what mean subtraction nulls, and the hypothesis it was built to defend"),
    ("estimation_theory_arrival_times_apertu", "3.6",
     "the estimator as a statistical procedure, and where it is heuristic"),
    ("noise_instrumentation_and_what_the_snr_b", "3.7",
     "what the assumed SNR budget demands of real hardware"),
    ("threats_to_validity", "3.8",
     "what would have to be true for these numbers to be wrong"),
]


def _rev():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "n/a"
    except Exception:
        return "n/a"


def _load(prefix):
    if not os.path.isdir(SEC_DIR):
        return None
    for f in sorted(os.listdir(SEC_DIR)):
        if f.startswith(prefix) and f.endswith(".html"):
            return open(os.path.join(SEC_DIR, f)).read()
    return None


def _number(html, num):
    """Prefix the section's own <h3> with its number, and demote stray <h2>."""
    html = re.sub(r"<h2([^>]*)>", r"<h3\1>", html)
    html = re.sub(r"</h2>", "</h3>", html)
    return re.sub(r"<h3([^>]*)>\s*", rf"<h3\1>{num}&nbsp; ", html, count=1)


def technical_html():
    parts, missing, toc = [], [], []
    for prefix, num, blurb in ORDER:
        h = _load(prefix)
        if not h:
            missing.append(num)
            continue
        title = re.search(r"<h3[^>]*>(.*?)</h3>", h, re.S)
        title = re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else num
        toc.append(f"<li><b>{num}</b> &nbsp;{title} &mdash; "
                   f"<span class='sub'>{blurb}</span></li>")
        parts.append(f"<div class='techsec'>{_number(h, num)}</div>")

    head = f"""
<p>The studies answer <i>whether</i> the design works. This chapter answers
<i>why</i>, at the level of detail a specialist reviewer will want, and states
where the reasoning stops being derivation and starts being assumption.</p>
<p>Each section below was written against the source and the measured results,
then given to a reviewer instructed to refute it, then rewritten to answer the
objections that survived. That pass found real errors, including two in this
report's own earlier text: the claim that reciprocity was an assumption-free
validation of the forward operator, and the claim that contact impedance
&ldquo;largely drops out&rdquo; of a tetrapolar measurement. Both are corrected
here and in &sect;7.</p>
<ol class="toc">{''.join(toc)}</ol>
"""
    if missing:
        head += (f"<div class='warn'><b>Sections {', '.join(missing)} are not "
                 f"present.</b> They are omitted rather than stubbed, so nothing "
                 f"below is a placeholder.</div>")
    return head + "".join(parts)


CSS = """
.techsec{margin:30px 0;padding-top:6px;border-top:1px solid #dfe6e9}
.techsec h3{color:#1155cc;font-size:14pt;margin:14px 0 8px}
.techsec h4{font-size:11.5pt;margin:16px 0 5px;color:#33484f}
.techsec p{margin:8px 0}
.techsec code{background:#eef3f6;padding:1px 4px;border-radius:3px;font-size:.92em}
ol.toc{margin:12px 0 18px 22px} ol.toc li{margin:4px 0}
"""


def main():
    body = technical_html()
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Technical foundations &mdash; directional reflux sensing</title>
<link rel="icon" href="favicon.ico"><style>
body{{font-family:Arial,Helvetica,sans-serif;font-size:11pt;color:#000;
 max-width:860px;margin:32px auto;line-height:1.55;padding:0 22px}}
h1{{font-size:22pt;margin-bottom:4px}} .sub{{color:#555;font-size:10pt}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:9.5pt}}
th,td{{border:1px solid #000;padding:5px 7px;text-align:left}} th{{background:#efefef}}
table.mm-t th,table.mm-t td{{border:1px solid #d7e0e4;padding:3px 9px}}
.mm-warn{{background:#fff6e5;border:1px solid #f0d090;padding:10px 14px;
 border-radius:5px;margin:12px 0;font-size:.95em}}
.warn{{border-left:4px solid #c0392b;padding:10px 14px;background:#fdf2f1;margin:14px 0}}
ul,ol{{margin:8px 0 8px 24px}} li{{margin:5px 0}}
{CSS}</style></head><body>
<h1>Technical foundations</h1>
<p class="sub">Directional bioimpedance detection of vesicoureteral reflux &middot;
generated {datetime.date.today().isoformat()} &middot; commit <code>{_rev()}</code></p>
{body}
</body></html>"""
    open("TECHNICAL.html", "w").write(html)
    have = sum(1 for p, _, _ in ORDER if _load(p))
    print(f"TECHNICAL.html written  ({have}/{len(ORDER)} sections, "
          f"{len(html)//1024} KB)")


if __name__ == "__main__":
    main()
