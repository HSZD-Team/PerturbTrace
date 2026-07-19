# `/bda-viz` skill

Renders a self-contained HTML report for a finished BDAbench `run_root`.

## Generate a report

```bash
python skills/bda-viz/scripts/render_report.py /path/to/run_root
# writes: /path/to/run_root/report.html
```

Open locally:

```bash
open /path/to/run_root/report.html
```

## In Codex

Install/link like other skills, then after a `/bda` run:

```text
$bda-viz run_root=<absolute run_root from the previous bda result>
```

## With Chef

Successful `chef run bda` automatically invokes this renderer when `auto_after_bda: true`.
You can also:

```bash
chef viz /path/to/run_root
```
