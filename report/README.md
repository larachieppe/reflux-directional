# Editing the report

The report is split so that prose and data cannot overwrite each other.

- **Prose** lives in the `.md` files in this folder. Edit them freely, by hand.
- **Numbers, tables and figures** live in `report_data.py` and are regenerated
  from the `metrics_*.json` files every time a study re-runs.

Editing prose can never change a result. Re-running a study can never undo your
edit. No number in the prose is ever typed by hand: it is referred to by name, so
if the study behind it changes, the sentence changes with it.

## To edit

Change any `.md` file in this folder, then rebuild:

```bash
python build_report_md.py
```

That writes `FULL_REPORT.html`. Commit and push, and the live page updates.

You can edit these files straight in GitHub's web UI (open the file, click the
pencil, commit) if you would rather not touch a terminal. Files are rendered in
filename order, so `09-...` comes after `08-...`.

## Formatting you can use

```markdown
## 4. Section heading            top-level section, numbered
### 4.1 Subsection               subsection, numbered to match

**bold**   *italic*   `code`
- a list item

| column | column |                a normal markdown table
|--------|--------|
| a      | b      |
```

Headings are numbered by hand in the text, and the contents list, the anchors
and every `§4`-style cross-reference are generated from those numbers. If you
renumber a section, renumber the `§` references that point at it.

### Callout boxes

```markdown
> [!KEY]
> The takeaway a reader should leave with.

> [!WARN]
> A correction, or a caveat that changes how a number should be read.

> [!NOTE]
> An aside.
```

Leave a `>` on its own line to start a new paragraph inside a box.

### Placeholders

These pull live values in at build time. Put block ones on their own line with a
blank line above and below.

| placeholder | what it inserts |
|---|---|
| `{{val:recip_err}}` | a single formatted number |
| `{{table:precision}}` | a complete table, header included |
| `{{fig:figs_new/n1_mesh.png\|caption text}}` | a figure, embedded in the page |
| `{{methods:precision}}` | the Materials & Methods block for one study |
| `{{common_methods}}` | the shared-model methods block |
| `{{technical}}` | the whole technical-foundations chapter |

A typo in a placeholder name renders as a visible HTML comment rather than
disappearing silently, so check the build output for `WARNING unresolved`.

To see every name available:

```bash
python -c "import report_data as r; print(sorted(r.VALS)); print(sorted(r.TABLES))"
```

## Adding a number to the prose

Do not type it. Add it to `VALS` in `report_data.py`, reading it from the metrics
file, then refer to it as `{{val:your_name}}`. That is what keeps the report and
the studies from drifting apart, which has already happened twice: the defect
count was stated as fifteen in one place and fourteen in another while the table
listed sixteen. It is now counted from the table itself.
