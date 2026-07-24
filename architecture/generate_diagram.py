#!/usr/bin/env python3
"""Generate the Airflow-on-Kubernetes architecture diagram.

Emits two files from a single geometry definition so they always match:
  - airflow-k8s-architecture.drawio  (draw.io / diagrams.net XML, exportable to Visio VSDX)
  - airflow-k8s-architecture.svg     (rendered preview)

Visual language follows the Apache Airflow brand palette
(https://airflow.apache.org): flat rounded boxes, white fills,
brand-coloured 2px borders, light layer bands, Rubik/Helvetica type.
"""

from xml.sax.saxutils import escape, quoteattr

# ---------------------------------------------------------------- palette --
BLUE    = "#017CEE"   # Airflow blue  - Scheduler
TEAL    = "#00C7D4"   # Airflow teal  - DAG Processor
GREEN   = "#00AD46"   # Airflow green - Webserver
SKY     = "#0CB6FF"   # Airflow sky   - API Server
CORAL   = "#FF7557"   # Airflow coral - Triggerer
RED     = "#E43921"   # Airflow red   - Workers
GRAY    = "#51504F"   # Airflow text gray
SUBGRAY = "#6B7B8D"
LFILL   = "#F8FBFE"   # layer band fill
LSTROKE = "#C9D8E8"
LFONT   = "#7A8CA3"
POOLSTR = "#8CA3B8"
PURPLE  = "#8250DF"   # secrets/config flows
ORANGE  = "#F46800"   # telemetry flows
AZURE   = "#0078D4"
K8S     = "#326CE5"
PGBLUE  = "#336791"
PROM    = "#E6522C"
LOKI    = "#F9A825"
ALLOY   = "#FB8C00"

TINT = {
    BLUE: "#E6F2FE", TEAL: "#E5FAFB", GREEN: "#E6F7ED", SKY: "#E7F7FF",
    CORAL: "#FFF0EC", RED: "#FDEAE7", AZURE: "#E5F1FB", K8S: "#EAEFFC",
    PGBLUE: "#EAF0F6", PROM: "#FDEBE6", LOKI: "#FEF4E0", ALLOY: "#FFF1E0",
    ORANGE: "#FEEFE0",
}

FONT = "Rubik, 'Segoe UI', Helvetica, Arial, sans-serif"
W, H = 1500, 1300

# ---------------------------------------------------------------- content --
TITLE = "Apache Airflow · Kubernetes Deployment Architecture"
SUBTITLE = ("AKS node pools · Azure Key Vault secrets · "
            "Prometheus / Grafana / Loki / Alloy observability")

LAYERS = [
    ("L1", "1 · USER LAYER",                                   120,   60, 1200, 100),
    ("L2", "2 · AIRFLOW CORE LAYER",                           120,  200, 1200, 170),
    ("L3", "3 · KUBERNETES NODE POOLS LAYER · AKS cluster", 120, 410, 1200, 230),
    ("L4", "4 · SECRETS & CONFIGURATION LAYER",                350,  680,  740, 150),
    ("L5", "5 · OBSERVABILITY LAYER",                          120,  870, 1200, 150),
    ("L6", "6 · METADATA & STORAGE LAYER",                     120, 1060, 1200, 140),
]

# id, title, sub-lines, colour, x, y, w, h
BOXES = [
    ("user",    "Users",                    ["Data engineers · CI/CD"],                 GRAY,   200,   85, 170, 60),
    ("ingress", "Ingress / Load Balancer",  ["TLS termination · routes UI & API"],      BLUE,   575,   85, 290, 60),

    ("sched",   "Scheduler",                ["Schedules DAG runs", "& queues tasks"],        BLUE,   165,  260, 190, 80),
    ("dagproc", "DAG Processor",            ["Parses DAG files"],                            TEAL,   395,  260, 190, 80),
    ("api",     "API Server",               ["Airflow UI · REST", "& Execution API"],        SKY,    625,  260, 190, 80),
    ("trig",    "Triggerer",                ["Async deferred", "operators"],                 CORAL,  855,  260, 190, 80),
    ("work",    "Workers",                  ["Execute tasks", "(Kubernetes pods)"],          RED,   1085,  260, 190, 80),

    ("akv",     "Azure Key Vault",          ["connections · variables · certs"],   AZURE,  380,  730, 200, 70),
    ("spc",     "SecretProviderClass",      ["Secrets Store CSI driver"],                    AZURE,  620,  730, 200, 70),
    ("cfg",     "ConfigMaps & Helm values", ["airflow.cfg · environment vars"],         K8S,    860,  730, 200, 70),

    ("alloy",   "Grafana Alloy",            ["Log collector · DaemonSet"],              ALLOY,  140,  920, 220, 70),
    ("loki",    "Grafana Loki",             ["Log aggregation & storage"],                   LOKI,   430,  920, 220, 70),
    ("graf",    "Grafana",                  ["Dashboards & alerting"],                       ORANGE, 720,  920, 220, 70),
    ("prom",    "Prometheus",               ["Metrics · StatsD / OTel"],                PROM,  1010,  920, 220, 70),

    ("blob",    "Azure Blob Storage",       ["DAG bundles · remote task logs"],         AZURE,  180, 1105, 320, 70),
    ("pg",      "PostgreSQL Metadata DB",   ["DAG runs · task instances · connections · XComs"],
                                                                                             PGBLUE, 900, 1105, 350, 70),
]

# id, title, subtitle, x, chips  (all pools: y=455, w=220, h=160)
# each chip is (lines, colour) — 1-line chips are 22px, 2-line chips 34px
POOL_Y, POOL_W, POOL_H = 455, 220, 160
POOLS = [
    ("poolAf",    "Airflow Pool",              "core components",         150,
     [(["Scheduler"], BLUE), (["DAG Processor"], TEAL),
      (["Triggerer"], CORAL), (["API Server"], SKY)]),
    ("poolJobs",  "Jobs Pool",                 "general task execution",  385,
     [(["Worker Pods", "standard tasks"], RED)]),
    ("poolHi",    "High Memory Pool",          "memory-optimised nodes",  620,
     [(["Worker Pods", "memory-heavy tasks"], RED)]),
    ("poolUltra", "Ultra High Memory Pool",    "very large memory nodes", 855,
     [(["Worker Pods", "ultra-high-memory tasks"], RED)]),
    ("poolCpu",   "Compute Optimised Pool",    "CPU-optimised nodes",    1090,
     [(["Worker Pods", "CPU-intensive tasks"], RED)]),
]

# id, colour, points [(x,y)...] first=start last=end (arrow at end)
EDGES = [
    ("e1",  BLUE,   [(370, 115), (575, 115)]),
    ("e2",  BLUE,   [(720, 145), (720, 260)]),
    ("e4",  GRAY,   [(720, 370), (720, 410)]),
    ("e5",  PURPLE, [(580, 765), (620, 765)]),
    ("e6",  PURPLE, [(720, 730), (720, 640)]),
    ("e7",  PURPLE, [(960, 730), (960, 640)]),
    ("e8",  ORANGE, [(310, 640), (310, 920)]),
    ("e9",  ORANGE, [(1120, 640), (1120, 920)]),
    ("e10", ORANGE, [(360, 955), (430, 955)]),
    ("e11", ORANGE, [(720, 955), (650, 955)]),
    ("e12", ORANGE, [(940, 955), (1010, 955)]),
    ("e13", GREEN,  [(1320, 300), (1380, 300), (1380, 1140), (1250, 1140)]),
]

# free-floating annotation labels: text, x, y(top), width, colour, align
NOTES = [
    ("Pods scheduled onto node pools",              735,  381, 250, GRAY,   "left"),
    ("Secrets & config mounted\ninto Airflow pods", 732,  650, 215, PURPLE, "left"),
    ("sync",                                        578,  747,  44, PURPLE, "center"),
    ("pod logs & stdout",                           322,  844, 190, ORANGE, "left"),
    ("StatsD / OTel metrics",                       950,  844, 162, ORANGE, "right"),
    ("logs",                                        373,  938,  44, ORANGE, "center"),
    ("query",                                       658,  938,  54, ORANGE, "center"),
    ("query",                                       948,  938,  54, ORANGE, "center"),
]

DB_LABEL = "Metadata DB connections (all Airflow components)"  # vertical, beside right rail

LEGEND = [  # x, colour, label
    (140,  BLUE,   "User / HTTP traffic"),
    (350,  GRAY,   "Pod scheduling"),
    (545,  PURPLE, "Secrets & configuration"),
    (775,  ORANGE, "Metrics & logs"),
    (975,  GREEN,  "Database connections"),
]
LEGEND_Y = 1248

# ------------------------------------------------------------- draw.io ----


def drawio() -> str:
    cells = []

    def vtx(cid, value, style, x, y, w, h):
        cells.append(
            f'        <mxCell id="{cid}" value={quoteattr(value)} style={quoteattr(style)} '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />\n'
            f'        </mxCell>')

    # title block
    vtx("title", f'<b><font color="{BLUE}">Apache Airflow</font></b>'
                 f'<font color="{GRAY}"> · Kubernetes Deployment Architecture</font>',
        "text;html=1;fontSize=20;fontStyle=1;align=left;verticalAlign=middle;", 120, 0, 900, 30)
    vtx("subtitle", SUBTITLE,
        f"text;html=1;fontSize=11;align=left;verticalAlign=middle;fontColor={LFONT};",
        120, 28, 900, 18)

    for cid, label, x, y, w, h in LAYERS:
        vtx(cid, label,
            f"rounded=1;arcSize=4;html=1;whiteSpace=wrap;fillColor={LFILL};"
            f"strokeColor={LSTROKE};verticalAlign=top;align=left;spacingLeft=12;"
            f"spacingTop=4;fontSize=11;fontStyle=1;fontColor={LFONT};", x, y, w, h)

    for pid, ptitle, psub, px, chips in POOLS:
        vtx(pid,
            f'<b>{escape(ptitle)}</b><br/><font style="font-size:9px;" color="{LFONT}">'
            f'<i>{escape(psub)}</i></font>',
            f"rounded=1;arcSize=8;html=1;whiteSpace=wrap;fillColor=#FFFFFF;"
            f"strokeColor={POOLSTR};strokeWidth=1.5;verticalAlign=top;spacingTop=4;"
            f"fontSize=12;fontColor=#37474F;", px, POOL_Y, POOL_W, POOL_H)
        cy = POOL_Y + 44
        for i, (clines, ccol) in enumerate(chips):
            ch = 22 if len(clines) == 1 else 34
            vtx(f"{pid}_c{i}", "<br/>".join(escape(s) for s in clines),
                f"rounded=1;arcSize=40;html=1;whiteSpace=wrap;fillColor={TINT[ccol]};"
                f"strokeColor={ccol};strokeWidth=1.2;fontSize=10;fontColor=#2F3B47;",
                px + 20, cy, POOL_W - 40, ch)
            cy += ch + 5

    for bid, btitle, subs, col, x, y, w, h in BOXES:
        sub = "<br/>".join(escape(s) for s in subs)
        vtx(bid,
            f'<b><font color="{col}">{escape(btitle)}</font></b><br/>'
            f'<font style="font-size:9px;" color="{SUBGRAY}">{sub}</font>',
            f"rounded=1;arcSize=12;html=1;whiteSpace=wrap;fillColor=#FFFFFF;"
            f"strokeColor={col};strokeWidth=2;align=center;verticalAlign=middle;"
            f"fontSize=12;fontColor=#2F3B47;", x, y, w, h)

    # edges (fixed waypoints; endpoints are exact page coords so nothing re-routes)
    for eid, col, pts in EDGES:
        (sx, sy), (tx, ty) = pts[0], pts[-1]
        mids = pts[1:-1]
        pts_xml = ""
        if mids:
            inner = "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in mids)
            pts_xml = f"<Array as=\"points\">{inner}</Array>"
        cells.append(
            f'        <mxCell id="{eid}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;'
            f'html=1;strokeWidth=2;strokeColor={col};endArrow=block;endFill=1;'
            f'endSize=6;" edge="1" parent="1">\n'
            f'          <mxGeometry relative="1" as="geometry">\n'
            f'            <mxPoint x="{sx}" y="{sy}" as="sourcePoint" />\n'
            f'            <mxPoint x="{tx}" y="{ty}" as="targetPoint" />\n'
            f'            {pts_xml}\n'
            f'          </mxGeometry>\n'
            f'        </mxCell>')

    for i, (text, x, y, w, col, align) in enumerate(NOTES):
        vtx(f"note{i}", text.replace("\n", "<br/>"),
            f"text;html=1;fontSize=10;align={align};verticalAlign=top;fontColor={col};",
            x, y - 4, w, 30)

    vtx("dbLabel", DB_LABEL,
        f"text;html=1;fontSize=10;horizontal=0;align=center;verticalAlign=middle;"
        f"fontColor={GREEN};", 1388, 560, 26, 330)

    for i, (lx, col, label) in enumerate(LEGEND):
        vtx(f"legSw{i}", "",
            f"rounded=1;arcSize=50;fillColor={col};strokeColor=none;", lx, LEGEND_Y + 6, 36, 5)
        vtx(f"legTx{i}", label,
            f"text;html=1;fontSize=11;align=left;verticalAlign=middle;fontColor={GRAY};",
            lx + 44, LEGEND_Y - 3, 170, 22)

    body = "\n".join(cells)
    return f'''<mxfile host="app.diagrams.net" agent="airflow-arch-generator" version="24.7.5" type="device">
  <diagram id="airflow-k8s-arch" name="Airflow on Kubernetes">
    <mxGraphModel dx="1420" dy="900" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H + 20}" background="#ffffff" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''


# ---------------------------------------------------------------- SVG -----


def svg() -> str:
    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT}">')
    # arrow markers, one per colour used by edges
    out.append("<defs>")
    for col in {c for _, c, _ in EDGES}:
        mid = "m" + col.lstrip("#")
        out.append(
            f'<marker id="{mid}" markerWidth="9" markerHeight="9" refX="7.5" refY="4" '
            f'orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="{col}"/></marker>')
    out.append("</defs>")
    out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

    def text(x, y, s, size, col, anchor="start", bold=False, italic=False, rotate=None):
        style = f' font-weight="600"' if bold else ""
        if italic:
            style += ' font-style="italic"'
        tr = f' transform="translate({x},{y}) rotate(-90)"' if rotate else f' x="{x}" y="{y}"'
        out.append(f'<text{tr} font-size="{size}" fill="{col}" '
                   f'text-anchor="{anchor}"{style}>{escape(s)}</text>')

    # title
    out.append(f'<text x="120" y="22" font-size="20" font-weight="700">'
               f'<tspan fill="{BLUE}">Apache Airflow</tspan>'
               f'<tspan fill="{GRAY}"> · Kubernetes Deployment Architecture</tspan></text>')
    text(120, 42, SUBTITLE, 11, LFONT)

    for _, label, x, y, w, h in LAYERS:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                   f'fill="{LFILL}" stroke="{LSTROKE}"/>')
        text(x + 12, y + 18, label, 11, LFONT, bold=True)

    for _, ptitle, psub, px, chips in POOLS:
        out.append(f'<rect x="{px}" y="{POOL_Y}" width="{POOL_W}" height="{POOL_H}" rx="10" '
                   f'fill="#ffffff" stroke="{POOLSTR}" stroke-width="1.5"/>')
        text(px + POOL_W / 2, POOL_Y + 20, ptitle, 12.5, "#37474F", anchor="middle", bold=True)
        text(px + POOL_W / 2, POOL_Y + 35, psub, 9.5, LFONT, anchor="middle", italic=True)
        cy = POOL_Y + 44
        for clines, ccol in chips:
            ch = 22 if len(clines) == 1 else 34
            out.append(f'<rect x="{px + 20}" y="{cy}" width="{POOL_W - 40}" height="{ch}" '
                       f'rx="11" fill="{TINT[ccol]}" stroke="{ccol}" stroke-width="1.2"/>')
            if len(clines) == 1:
                text(px + POOL_W / 2, cy + 15, clines[0], 10, "#2F3B47", anchor="middle")
            else:
                for j, line in enumerate(clines):
                    text(px + POOL_W / 2, cy + 14 + j * 12, line, 10, "#2F3B47",
                         anchor="middle")
            cy += ch + 5

    for _, btitle, subs, col, x, y, w, h in BOXES:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
                   f'fill="#ffffff" stroke="{col}" stroke-width="2"/>')
        cx = x + w / 2
        n = len(subs)
        ty = y + h / 2 - (n * 12) / 2 + 1
        text(cx, ty, btitle, 12.5, col, anchor="middle", bold=True)
        for i, s in enumerate(subs):
            text(cx, ty + 15 + i * 12, s, 9.5, SUBGRAY, anchor="middle")

    for _, col, pts in EDGES:
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        mid = "m" + col.lstrip("#")
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" '
                   f'marker-end="url(#{mid})"/>')

    for t, x, y, w, col, align in NOTES:
        anchor = {"left": "start", "center": "middle", "right": "end"}[align]
        ax = {"left": x, "center": x + w / 2, "right": x + w}[align]
        for i, line in enumerate(t.split("\n")):
            text(ax, y + 8 + i * 12, line, 10, col, anchor=anchor)

    text(1406, 725 + len(DB_LABEL) * 2.55, DB_LABEL, 10, GREEN, anchor="start", rotate=True)

    for lx, col, label in LEGEND:
        out.append(f'<rect x="{lx}" y="{LEGEND_Y + 4}" width="36" height="5" rx="2.5" fill="{col}"/>')
        text(lx + 44, LEGEND_Y + 11, label, 11, GRAY)

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    import pathlib
    here = pathlib.Path(__file__).parent
    (here / "airflow-k8s-architecture.drawio").write_text(drawio())
    (here / "airflow-k8s-architecture.svg").write_text(svg())
    print("wrote drawio + svg")
