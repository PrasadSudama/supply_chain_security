# Apache Airflow · Kubernetes Deployment Architecture

Architecture diagram of Apache Airflow deployed on Kubernetes (AKS), drawn in the
official Apache Airflow visual style — flat rounded boxes, white fills, Airflow
brand palette (`#017CEE` blue, `#00C7D4` teal, `#00AD46` green, `#FF7557` coral,
`#E43921` red), light layer bands, and clean orthogonal connectors.

![Airflow on Kubernetes](airflow-k8s-architecture.png)

## Files

| File | Purpose |
|------|---------|
| `airflow-k8s-architecture.drawio` | Editable source — open at [app.diagrams.net](https://app.diagrams.net) or in the draw.io desktop app |
| `airflow-k8s-architecture.svg` | Vector render (identical geometry) |
| `airflow-k8s-architecture.png` | Raster preview |
| `generate_diagram.py` | Generator — emits the `.drawio` and `.svg` from one geometry definition |

**Visio:** open the `.drawio` file in draw.io and use *File → Export as → VSDX*
to get a native Visio file.

## Layers (top → bottom)

1. **User Layer** — users reach the Airflow UI and REST API through an
   Ingress / Load Balancer (TLS termination).
2. **Airflow Core Layer** — Scheduler, DAG Processor, API Server (serves the
   Airflow UI as well as the REST & Execution APIs in Airflow 3), Triggerer,
   Workers.
3. **Kubernetes Node Pools Layer** — pods are placed by resource profile:
   - **Airflow Pool** — the core components: Scheduler, DAG Processor,
     Triggerer, API Server
   - **Jobs Pool** — worker pods for standard tasks
   - **High Memory Pool** — worker pods for memory-heavy tasks
   - **Ultra High Memory Pool** — worker pods for very large in-memory workloads
   - **Compute Optimised Pool** — worker pods for CPU-intensive tasks
4. **Secrets & Configuration Layer** — Azure Key Vault synced through a
   `SecretProviderClass` (Secrets Store CSI driver); secrets and ConfigMaps /
   Helm values are mounted into the Airflow pods as volumes and env vars.
5. **Observability Layer** — Grafana Alloy (DaemonSet) ships pod logs to Loki;
   Prometheus scrapes StatsD / OTel metrics; Grafana queries both.
6. **Metadata & Storage Layer** — PostgreSQL metadata database (all Airflow
   components connect to it) and Azure Blob Storage for DAG bundles and remote
   task logs.

## Regenerating

```bash
python3 generate_diagram.py   # rewrites the .drawio and .svg
```

Edit geometry or labels in `generate_diagram.py`; both output files stay in
sync because they are emitted from the same coordinate data.
