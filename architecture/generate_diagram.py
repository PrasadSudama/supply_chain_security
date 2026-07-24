#!/usr/bin/env python3
"""Generate the Airflow-on-AKS architecture diagram.

Emits two files from a single geometry definition so they always match:
  - airflow-k8s-architecture.drawio  (draw.io / diagrams.net XML, exportable to Visio VSDX)
  - airflow-k8s-architecture.svg     (rendered preview)

All icons are embedded as inline vectors (data URIs in the .drawio), so no
icon can ever render as a broken image.
"""

import base64
from xml.sax.saxutils import escape, quoteattr

W, H = 1440, 1240

# ---------------------------------------------------------------- palette --
BLUE   = "#1565C0"   # user flows
CORE   = "#1E88E5"   # core component boxes
GREENL = "#2E7D32"   # pools accents
GREENB = "#43A047"   # pool borders
RED    = "#D32F2F"   # secrets flows
REDT   = "#C62828"
OBS    = "#D84315"   # observability
TEALD  = "#00838F"   # metadata / db flows
TEALG  = "#26A69A"   # git-sync
GRAYT  = "#7A8CA3"
SUBG   = "#6B7B8D"

FONT = "Rubik, 'Segoe UI', Helvetica, Arial, sans-serif"

TITLE_MAIN = "Airflow 3.2 on AKS · Cloud Solutions Working Architecture"
TITLE_SUB = "cloud solutions | rev 0.5 draft | Jul 2026 | helm chart: apache-airflow/airflow"

# id, label, x, y, w, h, fill, stroke, fontcolor
LAYERS = [
    ("L1", "USER LAYER",                        200,   55, 1120, 110, "#EAF4FE", "#4A90D9", "#1565C0"),
    ("L2", "AIRFLOW CORE LAYER",                200,  200, 1120, 155, "#E3F7FA", "#4DC5D6", "#00838F"),
    ("L3", "KUBERNETES NODE POOLS LAYER (AKS)", 200,  415, 1120, 235, "#EAF6EC", "#58B26A", "#2E7D32"),
    ("L4", "SECRETS & CONFIGURATION LAYER",     200,  690, 1120, 140, "#FDEDEB", "#E57368", "#C62828"),
    ("L5", "OBSERVABILITY LAYER",               200,  870, 1120, 140, "#FDF0E9", "#EF8A65", "#D84315"),
    ("L6", "METADATA & STORAGE LAYER",          200, 1050, 1120, 140, "#E1F6F7", "#4FC3CF", "#00838F"),
]

# id, title, sub-lines, colour, x, y, w, h
BOXES = [
    ("nginx",   "NGINX Ingress Controller", ["TLS 1.2+ · :443 · cert-manager"],                 CORE, 1005,   80, 210, 55),

    ("sched",   "Scheduler",        ["schedules & queues tasks", "2 replicas (HA)"],            CORE,  228,  240, 180, 62),
    ("dagproc", "DAG Processor",    ["parses DAG files", "2 replicas (HA)"],                    CORE,  426,  240, 180, 62),
    ("trig",    "Triggerer",        ["async deferred tasks"],                                   CORE,  624,  240, 180, 62),
    ("wtp",     "Worker Task Pods", ["ephemeral, one pod per task", "(KubernetesExecutor)"],    CORE,  822,  240, 180, 62),
    ("api",     "API Server",       ["web UI + REST + execution API", ":8080, 2 replicas (HA)"], CORE, 1020,  240, 180, 62),

    ("spc",     "SecretProviderClass",     ["azure keyvault provider"],                        RED,   528,  715, 210, 50),
    ("csi",     "Secrets Store CSI Driver", ["mounts secrets as volumes / env"],               RED,   878,  715, 235, 50),

    ("alloy",   "Grafana Alloy",    ["daemonset log collector"],                               OBS,   265,  910, 190, 50),
    ("loki",    "Loki",             ["log store · :3100 · 31d retention"],                     OBS,   530,  910, 190, 50),
    ("prom",    "Prometheus",       [":9090 · 30s scrape · 15d retention"],                    OBS,   790,  910, 205, 50),
    ("graf",    "Grafana",          ["dashboards & alerting"],                                 OBS,  1070,  910, 190, 50),

    ("pgb",     "PgBouncer",        ["connection pooling"],                                    TEALD, 290, 1085, 180, 50),
    ("github",  "GitHub",           ["DAG repository (main branch)"],                          TEALD, 1140, 1085, 170, 50),
]

# ------------------------------------------------------------------ pools --
POOL_Y, POOL_W, POOL_H = 450, 170, 165
# x, title, subtitle, desc_title, desc_sub, dashed_note, foot
# components are detailed once, in their own layer; pools only state placement
POOLS = [
    (215, "Airflow Pool",           "core services",
     "Airflow core services", "(see Airflow core layer)",
     "2 replicas each · HA spread",     "nodeSelector: pool=airflow"),
    (399, "Observability Pool",     "monitoring stack",
     "Observability services", "(see observability layer)",
     "Alloy daemonset on every pool",   "nodeSelector: pool=observability"),
    (583, "Jobs Pool",              "general task execution",
     "Worker task pods", "standard ETL tasks",
     "cluster autoscaler enabled",      "taint: workload=jobs"),
    (767, "High Memory Pool",       "memory-intensive tasks",
     "Worker task pods", "large ETL / dataframe workloads",
     "autoscales 0 to N, no idle cost", "taint: workload=high-mem"),
    (951, "Ultra High Memory Pool", "very large in-memory jobs",
     "Worker task pods", "very large in-memory workloads",
     "scale from zero on demand",       "taint: workload=ultra-high-mem"),
    (1135, "Compute Optimised Pool", "CPU-intensive tasks",
     "Worker task pods", "CPU-bound task workloads",
     "cluster autoscaler enabled",      "taint: workload=compute-opt"),
]

# ------------------------------------------------------------------ icons --
ICON_SRC = {
    "person": '<circle cx="24" cy="13" r="9" fill="#1565C0"/>'
              '<path d="M6 44c0-10 8-16 18-16s18 6 18 16z" fill="#1565C0"/>',
    "lb": '<rect x="11" y="11" width="26" height="26" rx="4" transform="rotate(45 24 24)" fill="#689F38"/>'
          '<circle cx="24" cy="24" r="6.5" fill="#fff"/>'
          '<path d="M24 9.5l3.5 5h-7z" fill="#fff"/><path d="M24 38.5l-3.5-5h7z" fill="#fff"/>',
    "entra": '<path d="M24 4L4 31h13z" fill="#225086"/><path d="M24 4l20 27H31z" fill="#28A8EA"/>'
             '<path d="M24 14l10 13-10 17-10-17z" fill="#0078D4"/>',
    "keyvault": '<circle cx="24" cy="24" r="20.5" fill="#fff" stroke="#0078D4" stroke-width="3"/>'
                '<circle cx="17" cy="24" r="5.5" fill="none" stroke="#F9A825" stroke-width="4"/>'
                '<path d="M22 24h16M32 24v6M38 24v5" stroke="#F9A825" stroke-width="4" '
                'stroke-linecap="round" fill="none"/>',
    "k8s": '<polygon points="24,3 41.5,11.5 45,30 33,44.5 15,44.5 3,30 6.5,11.5" fill="#326CE5"/>'
           '<circle cx="24" cy="24" r="8" fill="none" stroke="#fff" stroke-width="2.5"/>'
           '<path d="M24 12v6M24 30v6M12 24h6M30 24h6M15.5 15.5l4.2 4.2M28.3 28.3l4.2 4.2'
           'M32.5 15.5l-4.2 4.2M19.7 28.3l-4.2 4.2" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>',
    "postgres": '<path d="M8 10v28c0 3.5 7.2 6 16 6s16-2.5 16-6V10z" fill="#336791"/>'
                '<ellipse cx="24" cy="10" rx="16" ry="5.5" fill="#7EB6E4"/>'
                '<path d="M8 22c0 3 7.2 5.5 16 5.5S40 25 40 22M8 31c0 3 7.2 5.5 16 5.5S40 34 40 31" '
                'stroke="#7EB6E4" stroke-width="1.5" fill="none"/>',
    "azfiles": '<path d="M4 12h16l4 4h20v6H4z" fill="#D98E12"/>'
               '<rect x="26" y="4" width="16" height="22" rx="1.5" fill="#fff" stroke="#A5AEB5" stroke-width="1.3"/>'
               '<path d="M29 9h10M29 13h10M29 17h7" stroke="#90A4AE" stroke-width="1.6" fill="none"/>'
               '<path d="M4 20h44v18H4z" fill="#F6A821"/><path d="M4 20h44l-2 3H6z" fill="#FFC352"/>',
}

# key, cx, top, size, label lines, label colour
ICONS = [
    ("person",  330,   80, 38, ["Data Engineers", "/ Users"],            BLUE),
    ("lb",      620,   78, 42, ["Azure Internal Load Balancer", "(private IP, VNet only)"], BLUE),
    ("entra",  1272,   80, 38, ["Microsoft Entra ID", "SSO for UI, OIDC redirect"],         BLUE),
    ("keyvault", 316, 718, 44, ["Azure Key Vault"],                       REDT),
    ("k8s",    1288,  417, 30, [],                                        GREENL),
    ("postgres", 624, 1086, 46, ["Azure Database for PostgreSQL",
                                 "airflow metadata db · :5432 · sslmode=require · zone-redundant HA"], TEALD),
    ("azfiles",  930, 1088, 44, ["Azure Files",
                                 "task logs on shared PVC (azurefile CSI, SMB)"],                      TEALD),
]

# ------------------------------------------------------------------ edges --
# id, colour, dashed, double-headed, points (arrow at last point)
EDGES = [
    ("u1",   BLUE,  False, False, [(350, 100), (598, 100)]),
    ("u2",   BLUE,  False, False, [(642, 100), (1005, 100)]),
    ("u3",   BLUE,  False, True,  [(1215, 102), (1248, 102)]),
    ("u4",   BLUE,  False, False, [(1110, 135), (1110, 240)]),
    ("laun", GREENL, False, False, [(652, 355), (652, 415)]),
    ("kv1",  RED,   False, False, [(350, 740), (528, 740)]),
    ("kv2",  RED,   False, False, [(738, 740), (878, 740)]),
    ("sec",  RED,   True,  False, [(995, 715), (995, 670), (944, 670), (944, 355)]),
    ("logs", OBS,   False, False, [(1320, 310), (1345, 310), (1345, 840), (360, 840), (360, 910)]),
    ("mets", OBS,   False, False, [(1320, 295), (1365, 295), (1365, 850), (892, 850), (892, 910)]),
    ("o1",   OBS,   False, False, [(455, 935), (530, 935)]),
    ("o2",   OBS,   False, False, [(995, 935), (1070, 935)]),
    ("o3",   OBS,   False, False, [(1165, 960), (1165, 988), (625, 988), (625, 960)]),
    ("db",   TEALD, False, False, [(200, 318), (165, 318), (165, 1110), (290, 1110)]),
    ("pgc",  TEALD, False, False, [(470, 1110), (597, 1110)]),
    ("git",  TEALG, True,  False, [(1225, 1085), (1225, 1042), (1390, 1042), (1390, 252), (1320, 252)]),
]

# ------------------------------------------------------------------ notes --
# text (\n = line break), x, y(first baseline), size, colour, align
NOTES = [
    ("HTTPS :443",                                            785,   94, 8.5, BLUE,  "center"),
    ("namespace: airflow",                                   1300,  222, 8.5, TEALD, "right"),
    ("executor: KubernetesExecutor (no celery, no redis/broker)", 228, 340, 8.5, TEALD, "left"),
    ("scheduler launches task pods via k8s API\nnodeSelector + tolerations set in pod_override",
                                                              535,  378, 9,   GREENL, "center"),
    ("secrets mounted into Airflow pods (volumes / env)",     958,  378, 9,   RED,   "left"),
    ("secrets sync",                                          400,  731, 8.5, RED,   "center"),
    ("access via Microsoft Entra Workload ID (no static credentials)", 228, 816, 8.5, REDT, "left"),
    ("container logs (all pods)",                             420,  834, 8.5, OBS,   "left"),
    ("metrics (Prometheus scrape / StatsD)",                  920,  864, 8.5, OBS,   "left"),
    ("push logs",                                             492,  928, 8.5, OBS,   "center"),
    ("metric queries",                                       1032,  928, 8,   OBS,   "center"),
    ("log queries",                                           895, 1001, 8.5, OBS,   "center"),
    ("metadata DB connections (all Airflow components)",      210, 1026, 8.5, TEALD, "left"),
    ("task pods write logs to the Azure Files PVC, read back by the API server",
                                                             1195, 1026, 8.5, TEALD, "right"),
    ("pooled connections",                                    533, 1102, 8.5, TEALD, "center"),
    ("git-sync sidecars pull DAGs\ninto pods · 60s interval", 1225, 1152, 8,  GRAYT, "center"),
]


def icon_data_uri(key: str) -> str:
    svg_doc = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">{ICON_SRC[key]}</svg>'
    return "data:image/svg+xml," + base64.b64encode(svg_doc.encode()).decode()


# ------------------------------------------------------------- draw.io ----


def drawio() -> str:
    cells = []

    def vtx(cid, value, style, x, y, w, h):
        cells.append(
            f'        <mxCell id="{cid}" value={quoteattr(value)} style={quoteattr(style)} '
            f'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />\n'
            f'        </mxCell>')

    def note(cid, textval, x, y, w, size, col, align, bold_first=False):
        lines = textval.split("\n")
        if bold_first and len(lines) > 1:
            value = (f"<b>{escape(lines[0])}</b><br/>" +
                     "<br/>".join(escape(s) for s in lines[1:]))
        elif bold_first:
            value = f"<b>{escape(lines[0])}</b>"
        else:
            value = "<br/>".join(escape(s) for s in lines)
        vtx(cid, value,
            f"text;html=1;fontSize={size};align={align};verticalAlign=top;fontColor={col};",
            x, y, w, 14 * len(lines) + 6)

    vtx("title", f'<b>{escape(TITLE_MAIN)}</b>',
        "text;html=1;fontSize=15;align=center;verticalAlign=middle;fontColor=#017CEE;",
        200, 0, 1120, 26)
    vtx("subtitle", escape(TITLE_SUB),
        f"text;html=1;fontSize=8;align=center;verticalAlign=middle;fontColor={GRAYT};",
        200, 26, 1120, 16)

    for cid, label, x, y, w, h, fill, stroke, fc in LAYERS:
        vtx(cid, label,
            f"rounded=1;arcSize=6;html=1;whiteSpace=wrap;fillColor={fill};"
            f"strokeColor={stroke};verticalAlign=top;align=left;spacingLeft=12;"
            f"spacingTop=4;fontSize=10;fontStyle=1;fontColor={fc};", x, y, w, h)

    # pools
    for px, ptitle, psub, dtitle, dsub, dashed_note, foot in POOLS:
        pid = "pool" + str(px)
        vtx(pid,
            f'<b>{escape(ptitle)}</b><br/><font style="font-size:8px;" color="{GRAYT}">'
            f'<i>{escape(psub)}</i></font>',
            f"rounded=1;arcSize=10;html=1;whiteSpace=wrap;fillColor=#FFFFFF;"
            f"strokeColor={GREENB};strokeWidth=1.5;verticalAlign=top;spacingTop=2;"
            f"fontSize=10;fontColor={GREENL};", px, POOL_Y, POOL_W, POOL_H)
        vtx(f"{pid}_w", f'<b>{escape(dtitle)}</b><br/>'
            f'<font style="font-size:8px;" color="{SUBG}">{escape(dsub)}</font>',
            f"rounded=1;arcSize=14;html=1;whiteSpace=wrap;fillColor=#E3F3E4;"
            f"strokeColor={GREENB};fontSize=9;fontColor={GREENL};align=center;"
            f"verticalAlign=middle;", px + 12, POOL_Y + 42, POOL_W - 24, 40)
        vtx(f"{pid}_d", dashed_note,
            f"rounded=1;arcSize=20;html=1;whiteSpace=wrap;fillColor=#F3FAF3;"
            f"strokeColor=#7CB56A;dashed=1;fontSize=8;fontColor=#4C9A55;",
            px + 12, POOL_Y + 92, POOL_W - 24, 26)
        note(f"{pid}_f", foot, px, POOL_Y + 138, POOL_W, 8, GRAYT, "center")

    for bid, btitle, subs, col, x, y, w, h in BOXES:
        sub = "<br/>".join(escape(s) for s in subs)
        vtx(bid,
            f'<b><font color="{col}">{escape(btitle)}</font></b><br/>'
            f'<font style="font-size:8px;" color="{SUBG}">{sub}</font>',
            f"rounded=1;arcSize=12;html=1;whiteSpace=wrap;fillColor=#FFFFFF;"
            f"strokeColor={col};strokeWidth=1.7;align=center;verticalAlign=middle;"
            f"fontSize=10;fontColor=#2F3B47;", x, y, w, h)

    for key, cx, top, size, labels, lcol in ICONS:
        vtx(f"ic_{key}", "",
            f"shape=image;html=1;imageAspect=0;aspect=fixed;image={icon_data_uri(key)};",
            cx - size / 2, top, size, size)
        if labels:
            note(f"ic_{key}_l", "\n".join(labels), cx - 170, top + size + 4, 340,
                 8.5, lcol, "center", bold_first=True)

    for eid, col, dashed, double, pts in EDGES:
        (sx, sy), (tx, ty) = pts[0], pts[-1]
        mids = pts[1:-1]
        pts_xml = ""
        if mids:
            inner = "".join(f'<mxPoint x="{px}" y="{py}" />' for px, py in mids)
            pts_xml = f"<Array as=\"points\">{inner}</Array>"
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth=1.7;"
                 f"strokeColor={col};endArrow=block;endFill=1;endSize=5;")
        if dashed:
            style += "dashed=1;"
        if double:
            style += "startArrow=block;startFill=1;startSize=5;"
        cells.append(
            f'        <mxCell id="{eid}" style="{style}" edge="1" parent="1">\n'
            f'          <mxGeometry relative="1" as="geometry">\n'
            f'            <mxPoint x="{sx}" y="{sy}" as="sourcePoint" />\n'
            f'            <mxPoint x="{tx}" y="{ty}" as="targetPoint" />\n'
            f'            {pts_xml}\n'
            f'          </mxGeometry>\n'
            f'        </mxCell>')

    for i, (textval, x, y, size, col, align) in enumerate(NOTES):
        wbox = 340
        if align == "left":
            nx = x
        elif align == "right":
            nx = x - wbox
        else:
            nx = x - wbox / 2
        note(f"note{i}", textval, nx, y - 10, wbox, size, col, align)

    body = "\n".join(cells)
    return f'''<mxfile host="app.diagrams.net" agent="airflow-arch-generator" version="24.7.5" type="device">
  <diagram id="airflow-k8s-arch" name="Airflow 3.2 on AKS">
    <mxGraphModel dx="1420" dy="900" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" background="#ffffff" math="0" shadow="0">
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
    out.append("<defs>")
    for col in {c for _, c, _, _, _ in EDGES}:
        mid = "m" + col.lstrip("#")
        out.append(
            f'<marker id="{mid}" markerWidth="9" markerHeight="9" refX="6.5" refY="3.5" '
            f'orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
            f'<path d="M0,0 L7,3.5 L0,7 z" fill="{col}"/></marker>')
    out.append("</defs>")
    out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

    def text(x, y, s, size, col, anchor="start", bold=False, italic=False):
        style = ' font-weight="600"' if bold else ""
        if italic:
            style += ' font-style="italic"'
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" '
                   f'text-anchor="{anchor}"{style}>{escape(s)}</text>')

    text(760, 20, TITLE_MAIN, 15, "#017CEE", anchor="middle", bold=True)
    text(760, 38, TITLE_SUB, 8, GRAYT, anchor="middle")

    for _, label, x, y, w, h, fill, stroke, fc in LAYERS:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
                   f'fill="{fill}" stroke="{stroke}"/>')
        text(x + 12, y + 18, label, 10, fc, bold=True)

    # pools
    for px, ptitle, psub, dtitle, dsub, dashed_note, foot in POOLS:
        out.append(f'<rect x="{px}" y="{POOL_Y}" width="{POOL_W}" height="{POOL_H}" rx="10" '
                   f'fill="#ffffff" stroke="{GREENB}" stroke-width="1.5"/>')
        text(px + POOL_W / 2, POOL_Y + 18, ptitle, 10, GREENL, anchor="middle", bold=True)
        text(px + POOL_W / 2, POOL_Y + 31, psub, 8, GRAYT, anchor="middle", italic=True)
        bx = px + 12
        bw = POOL_W - 24
        out.append(f'<rect x="{bx}" y="{POOL_Y + 42}" width="{bw}" height="40" rx="7" '
                   f'fill="#E3F3E4" stroke="{GREENB}"/>')
        text(px + POOL_W / 2, POOL_Y + 58, dtitle, 9, GREENL, anchor="middle", bold=True)
        text(px + POOL_W / 2, POOL_Y + 71, dsub, 8, SUBG, anchor="middle")
        out.append(f'<rect x="{bx}" y="{POOL_Y + 92}" width="{bw}" height="26" rx="6" '
                   f'fill="#F3FAF3" stroke="#7CB56A" stroke-dasharray="4,3"/>')
        text(px + POOL_W / 2, POOL_Y + 108, dashed_note, 8, "#4C9A55", anchor="middle")
        text(px + POOL_W / 2, POOL_Y + 147, foot, 8, GRAYT, anchor="middle")

    for _, btitle, subs, col, x, y, w, h in BOXES:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
                   f'fill="#ffffff" stroke="{col}" stroke-width="1.7"/>')
        cx = x + w / 2
        n = len(subs)
        block = 13 + n * 11
        ty = y + (h - block) / 2 + 10
        text(cx, ty, btitle, 10.5, col, anchor="middle", bold=True)
        for i, s in enumerate(subs):
            text(cx, ty + 13 + i * 11, s, 8, SUBG, anchor="middle")

    for key, cx, top, size, labels, lcol in ICONS:
        s = size / 48
        out.append(f'<g transform="translate({cx - size / 2},{top}) scale({s})">'
                   f'{ICON_SRC[key]}</g>')
        for i, lab in enumerate(labels):
            text(cx, top + size + 13 + i * 11, lab, 9 if i == 0 else 8,
                 lcol if i == 0 else SUBG, anchor="middle", bold=(i == 0))

    for _, col, dashed, double, pts in EDGES:
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        mid = "m" + col.lstrip("#")
        dash = ' stroke-dasharray="6,4"' if dashed else ""
        start = f' marker-start="url(#{mid})"' if double else ""
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.7"{dash} '
                   f'marker-end="url(#{mid})"{start}/>')

    for textval, x, y, size, col, align in NOTES:
        anchor = {"left": "start", "center": "middle", "right": "end"}[align]
        for i, line in enumerate(textval.split("\n")):
            text(x, y + i * 11, line, size, col, anchor=anchor)

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    import pathlib
    here = pathlib.Path(__file__).parent
    (here / "airflow-k8s-architecture.drawio").write_text(drawio())
    (here / "airflow-k8s-architecture.svg").write_text(svg())
    print("wrote drawio + svg")
