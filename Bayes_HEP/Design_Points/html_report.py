"""
HTML report generator — Rivet-style layout.

All plots are copied into output/html/plots/ so every HTML file can reference
them with simple paths like  plots/emulators/RMSPE_Comparison.png.
No base64, no complex relative paths, no broken links.

Output layout:
    output/html/
        index.html                       <- top level
        plots/                           <- full copy of output/plots/
        {system}_emulator.html
        {system}_calibration.html
        {system}_results.html            <- all inspire keys + histograms on one page
"""

import os
import glob
import shutil
from datetime import datetime

_TS = datetime.now().strftime("%A, %d. %B %Y %I:%M%p")

# ─────────────────────────────────────────────
# Rivet-style CSS
# ─────────────────────────────────────────────

_CSS = """
html { font-family: arial black, sans-serif; color: #333333; }
body { margin: 2em; }
img  { border: 0; max-width: 100%; }
a    { text-decoration: none; font-weight: bold; color: #1a5276; }
a:hover { text-decoration: underline; }
h1   { margin-bottom: 0.3em; }
h2   { margin-top: 1.2em; margin-bottom: 0.3em; border-bottom: 2px solid #aaa; padding-bottom: 0.2em; }
h3   { margin-top: 1em; margin-bottom: 0.3em; color: #444; }
footer { clear:both; margin-top:2em; padding-top:1em; border-top:1px solid #ccc; color:#999; font-size:0.85em; }
.back { margin-bottom: 1.5em; }
.back a { color: gray; font-variant: small-caps; }
.nav  { margin-bottom: 1.5em; font-size: 0.95em; }
.nav a { margin-right: 1.2em; }
.plot { float:left; font-weight:bold; page-break-inside:avoid; margin:0.5em; text-align:center; }
.plotname { font-size: smaller; display:block; margin-bottom:0.2em; }
.clear { clear: both; }
.anasumm { margin: 0.5em 0 1.5em; line-height: 1.5; font-size: 110%; font-family: georgia, palatino, serif; max-width: 860px; }
table { border-collapse: collapse; margin: 1em 0; font-size: 0.9em; }
th { background: #2c3e50; color: white; padding: 5px 12px; text-align: left; border: 1px solid #999; }
td { padding: 4px 12px; border: 1px solid #ccc; font-family: monospace; }
tr:nth-child(even) td { background: #f5f5f5; }
"""

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

_MATHJAX = """
<script type="text/javascript">
  window.MathJax = { tex: { inlineMath: [['$','$']] },
                     options: { menuOptions: { settings: { inTabOrder: false } } } };
</script>
<script type="text/javascript" id="MathJax-script" async
    src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-chtml-full.min.js">
</script>
"""

def _page(title, body):
    return (f'<!DOCTYPE html>\n<html>\n<head>\n'
            f'<meta charset="UTF-8">\n'
            f'<title>{title}</title>\n'
            f'<style>{_CSS}</style>\n'
            f'{_MATHJAX}'
            f'</head>\n<body>\n'
            f'{body}\n'
            f'<footer><p>Generated at {_TS}</p></footer>\n'
            f'</body>\n</html>')


def _write(path, html):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(html)


def _plot(img_path, label="", width=420):
    """One float:left plot card (img_path relative to the HTML file's directory)."""
    if not img_path:
        return ""
    return (f'<div class="plot">'
            f'<span class="plotname">{label}</span>'
            f'<a href="{img_path}"><img src="{img_path}" width="{width}"></a>'
            f'</div>')


def _section(title, content):
    return f'<h3>{title}</h3>\n{content}\n<div class="clear"></div>\n'


# ─────────────────────────────────────────────
# MAP parser
# ─────────────────────────────────────────────

def _parse_map(txt):
    meta, params, in_p = {}, [], False
    if not os.path.exists(txt):
        return meta, params
    with open(txt) as f:
        for line in f:
            line = line.rstrip()
            if not in_p and ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                if k in ("Source", "N samples used", "Log-prob at MAP",
                         "Log-evidence", "Log-evidence err"):
                    meta[k] = v.strip()
            if "MAP Parameters" in line:
                in_p = True
            elif in_p and ":" in line and not line.startswith("Check"):
                k, v = line.split(":", 1)
                params.append((k.strip(), v.strip()))
    return meta, params


def _map_table(meta, params):
    if not params:
        return "<p><em>No MAP info found.</em></p>"
    rows = "".join(f"<tr><td>{p}</td><td>{v}</td></tr>" for p, v in params)
    mrows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in meta.items())
    return (f'<table><tr><th>Parameter</th><th>MAP Value</th></tr>{rows}</table>'
            f'<table><tr><th>Field</th><th>Value</th></tr>{mrows}</table>')


# ─────────────────────────────────────────────
# Copy plots into html/plots/
# ─────────────────────────────────────────────

def _copy_plots(plots_dir, html_dir):
    dest = os.path.join(html_dir, "plots")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(plots_dir, dest)

    # Rename any extensionless files to .png (result plots saved without extension
    # by older containers that pre-date the .png fix in plots.py)
    for root, dirs, files in os.walk(dest):
        for fname in files:
            if "." not in fname:
                src = os.path.join(root, fname)
                dst = src + ".png"
                os.rename(src, dst)

    print(f"[HTML] Copied plots → {dest}")
    return dest


# ─────────────────────────────────────────────
# Emulator page
# ─────────────────────────────────────────────

def _write_emulator(html_dir, system):
    """All emulator plots on one page. Images at plots/emulators/..."""
    p = "plots/emulators"
    sections = []

    # RMSPE comparison
    f = f"{p}/RMSPE_Comparison.png"
    if os.path.exists(os.path.join(html_dir, f)):
        sections.append(_section("RMSPE Comparison", _plot(f, "RMSPE Comparison", 600)))

    # Per-inspire summary — scan all PNGs, don't filter by system name
    files = sorted(glob.glob(os.path.join(html_dir, p, "RMSPE_per_inspire_*.png")))
    if files:
        divs = "".join(_plot(f"plots/emulators/{os.path.basename(x)}", os.path.basename(x)) for x in files)
        sections.append(_section("RMSPE per Publication", divs))

    # RMSPE detail — all PNGs in rmspe_detail/
    files = sorted(glob.glob(os.path.join(html_dir, p, "rmspe_detail", "*.png")))
    if files:
        divs = "".join(_plot(f"plots/emulators/rmspe_detail/{os.path.basename(x)}", os.path.basename(x)) for x in files)
        sections.append(_section("RMSPE Detail per Inspire Key", divs))

    # RMSPE vs emulator variance — all PNGs in rmspe_emuvar/*/*
    files = sorted(glob.glob(os.path.join(html_dir, p, "rmspe_emuvar", "*", "*.png")))
    if files:
        divs = "".join(
            _plot(f"plots/emulators/rmspe_emuvar/{os.path.basename(os.path.dirname(x))}/{os.path.basename(x)}",
                  os.path.basename(x))
            for x in files
        )
        sections.append(_section("RMSPE vs Emulator Uncertainty", divs))

    # Uncertainty at MAP — all PNGs matching pattern
    files = sorted(glob.glob(os.path.join(html_dir, p, "uncertainty_comparison_MAP_*.png")))
    if files:
        divs = "".join(_plot(f"plots/emulators/{os.path.basename(x)}", os.path.basename(x)) for x in files)
        sections.append(_section("Uncertainty at MAP", divs))

    body = (f'<h1>Emulator Validation — {system}</h1>\n'
            f'<div class="nav"><a href="index.html">&larrhk; Index</a></div>\n'
            + ("\n".join(sections) if sections else "<p><em>No emulator plots found.</em></p>"))

    out = os.path.join(html_dir, f"{system}_emulator.html")
    _write(out, _page(f"Emulator — {system}", body))
    return out


# ─────────────────────────────────────────────
# Calibration page
# ─────────────────────────────────────────────

def _write_calibration(html_dir, output_dir, system):
    sections = []

    # filenames use the underscore-free slug (e.g. "pp_200" → "pp200", "all" → "all")
    sys_slug = system.replace("_", "")

    def _filter(files):
        return [f for f in files if sys_slug in os.path.basename(f)]

    # Corner plot — filter by system
    files = _filter(sorted(glob.glob(os.path.join(html_dir, "plots/calibration", "*.png"))))
    if files:
        divs = "".join(_plot(f"plots/calibration/{os.path.basename(x)}", os.path.basename(x), 600) for x in files)
        sections.append(_section("Posterior Corner Plot", divs))

    # Prior vs posterior — filter by system
    files = _filter(sorted(glob.glob(os.path.join(html_dir, "plots/prior_posterior", "*.png"))))
    if files:
        divs = "".join(_plot(f"plots/prior_posterior/{os.path.basename(x)}", os.path.basename(x)) for x in files)
        sections.append(_section("Prior vs Posterior", divs))

    # Correlation — filter by system
    files = _filter(sorted(glob.glob(os.path.join(html_dir, "plots/correlation", "*.png"))))
    if files:
        divs = "".join(_plot(f"plots/correlation/{os.path.basename(x)}", os.path.basename(x)) for x in files)
        sections.append(_section("Posterior Correlation", divs))

    # Convergence — filter by system
    files = _filter(sorted(glob.glob(os.path.join(html_dir, "plots/convergence", "*.png"))))
    if files:
        divs = "".join(_plot(f"plots/convergence/{os.path.basename(x)}", os.path.basename(x)) for x in files)
        sections.append(_section("Emcee Convergence", divs))

    # Traces — filter by system
    files = _filter(sorted(glob.glob(os.path.join(html_dir, "plots/trace", "*.png"))))
    if files:
        divs = "".join(_plot(f"plots/trace/{os.path.basename(x)}", os.path.basename(x)) for x in files)
        sections.append(_section("Walker Traces", divs))

    # MAP tables — filter by system (handle both pp_200 and pp200 variants)
    all_map_files = sorted(glob.glob(os.path.join(output_dir, "calibration", "map_info", "*.txt")))
    map_files = _filter(all_map_files)
    if map_files:
        blocks = []
        for mf in map_files:
            name = os.path.basename(mf).replace("_map.txt", "").replace(f"{sys_slug}_", "", 1)
            blocks.append(f"<h4>MAP — {name}</h4>" + _map_table(*_parse_map(mf)))
        sections.append("<h3>MAP Parameters</h3>\n" + "\n".join(blocks))

    body = (f'<h1>Calibration — {system}</h1>\n'
            f'<div class="nav"><a href="index.html">&larrhk; Index</a></div>\n'
            + ("\n".join(sections) if sections else "<p><em>No calibration plots found.</em></p>"))

    out = os.path.join(html_dir, f"{system}_calibration.html")
    _write(out, _page(f"Calibration — {system}", body))
    return out


# ─────────────────────────────────────────────
# Results page (all inspire keys + histograms on one page, Rivet style)
# ─────────────────────────────────────────────

def _write_results(html_dir, system):
    # Find the actual results directory — may be results_pp200 even when system=pp_200
    plots_root = os.path.join(html_dir, "plots")
    candidates = sorted(glob.glob(os.path.join(plots_root, "results_*")))
    results_plots = None
    system_slug = system.replace("_", "")
    for c in candidates:
        dirname = os.path.basename(c).replace("results_", "")
        if dirname == system or dirname == system_slug or dirname.replace("_","") == system_slug:
            results_plots = c
            break
    if results_plots is None or not os.path.isdir(results_plots):
        return None
    results_rel = os.path.relpath(results_plots, html_dir)  # e.g. plots/results_pp200

    inspire_keys = sorted(d for d in os.listdir(results_plots)
                          if os.path.isdir(os.path.join(results_plots, d)))
    if not inspire_keys:
        return None

    sections = []
    for inspire in inspire_keys:
        # collect .png files; also catch files saved without extension (old plots.py)
        pngs = sorted(glob.glob(os.path.join(results_plots, inspire, "*.png")))
        if not pngs:
            pngs = sorted(
                f for f in glob.glob(os.path.join(results_plots, inspire, "*"))
                if os.path.isfile(f) and "." not in os.path.basename(f)
            )
        if not pngs:
            continue
        divs = "".join(
            _plot(f"{results_rel}/{inspire}/{os.path.basename(p)}",
                  os.path.basename(p).removesuffix(".png"))
            for p in pngs
        )
        sections.append(f'<h2 id="{inspire}">{inspire}</h2>\n{divs}\n<div class="clear"></div>')

    if not sections:
        return None

    # jump links at top
    jumps = " &nbsp;|&nbsp; ".join(
        f'<a href="#{k}">{k}</a>' for k in inspire_keys
    )

    body = (f'<h1>Results — {system}</h1>\n'
            f'<div class="nav"><a href="index.html">&larrhk; Index</a></div>\n'
            f'<p>{jumps}</p>\n'
            + "\n".join(sections))

    out = os.path.join(html_dir, f"{system}_results.html")
    _write(out, _page(f"Results — {system}", body))
    return out


# ─────────────────────────────────────────────
# Summary block (like Rivet .info)
# ─────────────────────────────────────────────

def _prior_label(prior):
    """Human-readable description of a bilby prior."""
    t = type(prior).__name__
    try:
        if t in ("Uniform", "LogUniform", "PowerLaw"):
            return f"{t} [{prior.minimum:.4g}, {prior.maximum:.4g}]"
        elif t in ("Normal", "Gaussian"):
            return f"{t} μ={prior.mu:.4g}, σ={prior.sigma:.4g}"
        elif t == "TruncatedGaussian":
            return (f"{t} μ={prior.mu:.4g}, σ={prior.sigma:.4g}"
                    f" [{prior.minimum:.4g}, {prior.maximum:.4g}]")
        elif t == "DeltaFunction":
            return f"Fixed = {prior.peak:.4g}"
        else:
            return t
    except Exception:
        return t


def _obs_label(obs):
    """Clean observable label for display — strip redundant separators."""
    if isinstance(obs, list):
        obs = " ".join(obs)
    return obs.strip(" /,")


def _build_obs_rows(all_data):
    """
    Build {inspire: {systems, histograms, observable}} from all_data.
    Keyed by inspire, with histogram list and one representative observable per inspire.
    """
    rows = {}
    for system, histograms in all_data.items():
        for h in histograms:
            inspire   = h.get('Inspire', '')
            histogram = h.get('Histogram', '')
            obs       = _obs_label(h.get('Observable', ''))
            if not inspire:
                continue
            if inspire not in rows:
                rows[inspire] = {'systems': set(), 'histograms': [], 'observable': obs}
            rows[inspire]['systems'].add(system)
            if histogram not in rows[inspire]['histograms']:
                rows[inspire]['histograms'].append(histogram)
    return rows


# ─────────────────────────────────────────────
# Top-level index
# ─────────────────────────────────────────────

def _write_index(html_dir, plots_dir, output_dir, systems, emulator_types,
                 sampler_names, model="", priors=None, all_data=None,
                 train_size=None, validation_size=None):

    # ── Navigation (top) ──────────────────────────────────────────────
    nav_rows = []
    for system in systems:
        links = []
        if os.path.exists(os.path.join(html_dir, f"{system}_emulator.html")):
            links.append(f'<a href="{system}_emulator.html">Emulator</a>')
        if os.path.exists(os.path.join(html_dir, f"{system}_calibration.html")):
            links.append(f'<a href="{system}_calibration.html">Calibration</a>')
        if os.path.exists(os.path.join(html_dir, f"{system}_results.html")):
            links.append(f'<a href="{system}_results.html">Results</a>')
        link_str = " &nbsp;|&nbsp; ".join(links) or "(no pages generated yet)"
        nav_rows.append(f'<tr><td><b>{system}</b></td><td>{link_str}</td></tr>')

    nav_table = ('<table>'
                 '<tr><th>System</th><th>Pages</th></tr>'
                 + "".join(nav_rows)
                 + '</table>')

    # ── Run summary table ──────────────────────────────────────────────
    meta_rows = [
        f'<tr><td>Model</td><td>{model or "(not set)"}</td></tr>',
        f'<tr><td>Collision systems</td><td>{", ".join(systems)}</td></tr>',
        f'<tr><td>Emulators</td><td>{", ".join(emulator_types)}</td></tr>',
        f'<tr><td>Samplers</td><td>{", ".join(sampler_names)}</td></tr>',
    ]
    if train_size is not None:
        meta_rows.append(f'<tr><td>Training points</td><td>{train_size}</td></tr>')
    if validation_size is not None:
        meta_rows.append(f'<tr><td>Validation points</td><td>{validation_size}</td></tr>')
    meta_rows.append(f'<tr><td>Generated</td><td>{_TS}</td></tr>')

    meta_table = ('<table>'
                  '<tr><th>Field</th><th>Value</th></tr>'
                  + "".join(meta_rows)
                  + '</table>')

    # ── Prior space table ──────────────────────────────────────────────
    prior_table = ""
    if priors:
        rows = "".join(
            f'<tr><td>{name}</td><td>{_prior_label(p)}</td></tr>'
            for name, p in priors.items()
        )
        prior_table = ('<h3>Prior Space</h3>'
                       '<table><tr><th>Parameter</th><th>Distribution</th></tr>'
                       + rows + '</table>')

    # ── Observables table ─────────────────────────────────────────────
    obs_table = ""
    if all_data:
        obs_rows = _build_obs_rows(all_data)
        if obs_rows:
            trows = []
            for inspire, info in sorted(obs_rows.items()):
                hist_names = ", ".join(sorted(info['histograms']))
                sys_str    = ", ".join(sorted(info['systems']))
                n          = len(info['histograms'])
                # show histogram names; full observable as tooltip
                trows.append(
                    f'<tr>'
                    f'<td>{inspire}</td>'
                    f'<td title="{info["observable"]}">{hist_names}</td>'
                    f'<td style="text-align:center">{n}</td>'
                    f'<td>{sys_str}</td>'
                    f'</tr>'
                )
            obs_table = ('<h3>Observables</h3>'
                         '<table>'
                         '<tr><th>Inspire Key</th>'
                         '<th>Histograms <span style="font-weight:normal;font-size:smaller">'
                         '(hover for observable label)</span></th>'
                         '<th>#</th><th>Systems</th></tr>'
                         + "".join(trows) + '</table>')

    # ── Notes / Discussion ────────────────────────────────────────────
    notes_path = os.path.join(output_dir, "notes.txt")
    if os.path.exists(notes_path):
        with open(notes_path) as f:
            notes_text = f.read().strip()
    else:
        notes_text = None

    notes_block = ""
    if notes_text:
        notes_block = f'<h3>Discussion</h3><p class="anasumm">{notes_text}</p>'
    else:
        notes_block = ('<h3>Discussion</h3>'
                       '<p style="color:#aaa;font-style:italic">'
                       'Add a <tt>notes.txt</tt> file to the output directory '
                       'to display run notes here.</p>')

    # ── Design points plot ────────────────────────────────────────────
    dp = "plots/Design_Points.png"
    dp_html = ""
    if os.path.exists(os.path.join(html_dir, dp)):
        dp_html = (f'<h3>Design Points</h3>'
                   f'{_plot(dp, "", 500)}'
                   f'<div class="clear"></div>')

    # ── Assemble ──────────────────────────────────────────────────────
    body = (
        f'<h1>Bayes_HEP Report</h1>\n'
        f'<h2>Analyses</h2>\n{nav_table}\n'
        f'<h2>Run Summary</h2>\n{meta_table}\n'
        f'{prior_table}\n'
        f'{obs_table}\n'
        f'{notes_block}\n'
        f'{dp_html}'
    )

    out = os.path.join(html_dir, "index.html")
    _write(out, _page("Bayes_HEP Report", body))
    return out


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def generate_report(output_dir, Coll_System, Emulators, samplers,
                    all_data=None, priors=None, model="",
                    train_size=None, validation_size=None):
    """
    Generate HTML report. Copies the entire plots/ directory into html/plots/
    so all image paths are simple and self-contained.
    """
    html_dir       = os.path.join(output_dir, "html")
    plots_dir      = os.path.join(output_dir, "plots")
    emulator_types = list(Emulators.keys())
    sampler_names  = list(samplers.keys()) if isinstance(samplers, dict) else list(samplers)
    systems        = list(Coll_System)

    print("[HTML] Copying plots into html directory ...")
    _copy_plots(plots_dir, html_dir)

    for system in systems:
        _write_emulator(html_dir, system)
        _write_calibration(html_dir, output_dir, system)
        _write_results(html_dir, system)

    index = _write_index(html_dir, plots_dir, output_dir, systems, emulator_types,
                         sampler_names, model=model, priors=priors, all_data=all_data,
                         train_size=train_size, validation_size=validation_size)
    print(f"[HTML] Report ready — open: {index}")
    return index
