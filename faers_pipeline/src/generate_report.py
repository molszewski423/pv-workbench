import json, glob, os, base64, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO

output_dir = os.path.expanduser("~/pv_workbench/output")
files = glob.glob(f"{output_dir}/cefiderocol_signals_*.json")
signals = json.load(open(sorted(files)[-1]))
sig = [s for s in signals if s['signal'] and s['reaction_pt'] != 'no adverse event']

# Generate chart
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.patch.set_facecolor('white')
top14 = sorted(sig, key=lambda x: x['prr'], reverse=True)[:14]
colors = ['#c0392b' if s['prr']>=10 else '#e67e22' if s['prr']>=5 else '#f39c12' for s in top14]
bars = axes[0].barh([s['reaction_pt'] for s in top14],[s['prr'] for s in top14],color=colors)
axes[0].axvline(x=2,color='black',linestyle='--',alpha=0.5,label='PRR=2 threshold')
axes[0].set_xlabel('PRR')
axes[0].set_title('Top Signals by PRR',fontweight='bold')
axes[0].legend()
axes[0].invert_yaxis()
for bar,s in zip(bars,top14):
    axes[0].text(bar.get_width()+0.2,bar.get_y()+bar.get_height()/2,f'{s["prr"]:.1f}',va='center',fontsize=8)
axes[1].scatter([s['drug_cases'] for s in sig],[s['prr'] for s in sig],
    s=[s['chi2']*3 for s in sig],alpha=0.6,c=[s['prr'] for s in sig],cmap='YlOrRd')
axes[1].axhline(y=2,color='black',linestyle='--',alpha=0.5)
axes[1].set_xlabel('N (cases)')
axes[1].set_ylabel('PRR')
axes[1].set_title('PRR vs Case Count\n(bubble size = chi2)',fontweight='bold')
for s in sig:
    if s['drug_cases']>10:
        axes[1].annotate(s['reaction_pt'],(s['drug_cases'],s['prr']),fontsize=7,xytext=(5,5),textcoords='offset points')
plt.tight_layout()
buf = BytesIO()
plt.savefig(buf,format='png',dpi=150,bbox_inches='tight')
buf.seek(0)
chart = base64.b64encode(buf.read()).decode()
plt.close()

# Build table rows
rows = ""
for s in sorted(sig, key=lambda x: x['prr'], reverse=True):
    c = '#c0392b' if s['prr']>=10 else '#e67e22' if s['prr']>=5 else '#f39c12'
    rows += f"<tr><td>{s['reaction_pt'].title()}</td><td>{s['drug_cases']}</td><td style='color:{c};font-weight:bold'>{s['prr']:.2f}</td><td>{s['chi2']:.2f}</td><td style='color:green'>YES</td></tr>\n"

html = open('/dev/null').read() if False else ""
html = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Cefiderocol FAERS Signal Detection</title>
<style>
body{font-family:Arial,sans-serif;max-width:1100px;margin:0 auto;padding:40px 20px;color:#2c3e50}
h1{color:#1a252f;border-bottom:3px solid #2980b9;padding-bottom:10px}
h2{color:#2980b9;margin-top:40px}
.meta{background:#eaf4fb;border-left:4px solid #2980b9;padding:15px 20px;margin:20px 0;border-radius:4px}
table{width:100%;border-collapse:collapse;margin:20px 0;font-size:14px}
th{background:#1a252f;color:white;padding:10px 12px;text-align:left}
td{padding:8px 12px;border-bottom:1px solid #ddd;text-align:center}
td:first-child{text-align:left}
tr:nth-child(even){background:#f8f9fa}
tr:hover{background:#eaf4fb}
.lim{background:#fef9e7;border-left:4px solid #f39c12;padding:10px 16px;margin:8px 0;border-radius:4px}
.footer{margin-top:60px;padding-top:20px;border-top:1px solid #ddd;color:#7f8c8d;font-size:13px}
.badge{display:inline-block;background:#2980b9;color:white;padding:2px 8px;border-radius:3px;font-size:12px;margin:2px}
img{max-width:100%;border:1px solid #ddd;border-radius:4px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
</style></head><body>
<h1>Cefiderocol FAERS Signal Detection Analysis</h1>
<div class="meta">
<p><strong>Author:</strong> Michael Olszewski, PharmD, BCPS, BCCCP</p>
<p><strong>Data Source:</strong> OpenFDA FAERS API &nbsp;|&nbsp; <strong>Date:</strong> 2026-05-05</p>
<p><strong>Methodology:</strong> PRR — Evans Criteria (PRR &ge; 2, N &ge; 3, &chi;&sup2; &ge; 4)</p>
<p><strong>Stack:</strong>
<span class="badge">Python 3.12</span>
<span class="badge">Docker</span>
<span class="badge">Debian Linux</span>
<span class="badge">OpenFDA API</span>
<span class="badge">ICH E2C-aligned</span></p>
</div>
<h2>1. Background</h2>
<p>Cefiderocol is a siderophore cephalosporin active against carbapenem-resistant Gram-negative organisms including <em>Pseudomonas aeruginosa</em>, <em>Acinetobacter baumannii</em>, and carbapenem-resistant Enterobacteriaceae. Given its last-resort status in critically ill patients, robust post-marketing pharmacovigilance is essential.</p>
<p>This analysis implements a reproducible signal detection pipeline using the OpenFDA FAERS API with PRR disproportionality analysis against a beta-lactam reference population (meropenem, n=5,000).</p>
<h2>2. Signal Detection Results</h2>
<table>
<tr><th>MedDRA PT</th><th>N (Cases)</th><th>PRR</th><th>Chi&sup2;</th><th>Signal</th></tr>
""" + rows + """</table>
<h2>3. Visualization</h2>
<img src="data:image/png;base64,""" + chart + """" alt="PRR Signal Charts">
<h2>4. Clinical Interpretation</h2>
<table>
<tr><th>MedDRA PT</th><th>PRR</th><th>Clinical Assessment</th></tr>
<tr><td>Pneumonia Pseudomonal</td><td>16.10</td><td>Expected — primary indication; confirms on-label use in resistant pseudomonal pneumonia</td></tr>
<tr><td>Treatment Failure</td><td>9.88</td><td>Clinically significant — aligns with RCT data showing non-inferiority concerns vs carbapenems</td></tr>
<tr><td>Death</td><td>9.34</td><td>Confounding by indication — reflects critically ill last-resort population; not a de novo safety signal</td></tr>
<tr><td>Therapy Non-Responder</td><td>17.71</td><td>Warrants monitoring — may reflect emerging resistance; correlates with MIC creep literature</td></tr>
<tr><td>Drug Resistance / Pathogen Resistance</td><td>2.64 / 2.57</td><td>Hypothesis-generating — surveillance signal for emerging resistance patterns</td></tr>
<tr><td>Ototoxicity</td><td>7.25</td><td>Notable — requires further evaluation; potential class effect or co-administration signal</td></tr>
</table>
<h2>5. Methodological Limitations</h2>
<div class="lim">Confounding by indication: cefiderocol patients are inherently sicker than the meropenem reference population</div>
<div class="lim">OpenFDA exposes a subset of total FAERS reports; regulatory-grade analysis requires complete quarterly ASCII files</div>
<div class="lim">Meropenem comparator chosen for clinical relevance; PRR values would differ with broader background population</div>
<div class="lim">Standard FAERS underreporting bias applies — actual event rates are higher than reported</div>
<h2>6. Technical &amp; Regulatory Context</h2>
<p>Pipeline architecture: OpenFDA REST API &rarr; Python 3.12 pagination &rarr; PRR/&chi;&sup2; computation &rarr; JSON output &rarr; HTML report. Containerized via Docker on Debian Linux for reproducibility.</p>
<p>This methodology maps directly to quantitative signal detection workflows in Veeva Vault Safety and Oracle Argus, consistent with ICH E2E signal management guidance and PSUR/PBRER preparation workflows.</p>
<div class="footer">
<p>Generated: 2026-05-05 | Michael Olszewski, PharmD, BCPS, BCCCP | PV Data Science Portfolio</p>
<p>Data: OpenFDA FAERS API | Reference: Evans et al. (2001) PRR methodology | ICH E2C(R2), ICH E2E</p>
</div>
</body></html>"""

out = f"{output_dir}/cefiderocol_report.html"
with open(out, 'w') as f:
    f.write(html)
print(f"Report saved: {out}")
