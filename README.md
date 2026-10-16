# ⚽ Premier League xG Data Pipeline & Analytics Engine (2025/26)

[![CI/CD Pipeline](https://github.com/jtw0mey/pl-xg-data-pipeline/actions/workflows/pl_xg_pipeline_2025.yml/badge.svg)](https://github.com/jtw0mey/pl-xg-data-pipeline/actions)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![DuckDB](https://img.shields.io/badge/Database-DuckDB-FFF000?logo=duckdb)
![Pandas](https://img.shields.io/badge/Library-Pandas-150458?logo=pandas)
![GitHub Actions](https://img.shields.io/badge/Automation-GitHub_Actions-2088FF?logo=githubactions)

An end-to-end data engineering pipeline that extracts, transforms, and analyzes Expected Goals (xG) and Expected Assists (xA) metrics for Premier League players during the 2025/26 season. Built with **Python**, **Pandas**, **DuckDB**, and automated via **GitHub Actions**.

---

## 🏗️ Pipeline Architecture

```mermaid
flowchart LR
    A[Understat API] -->|Raw JSON| B[Extract Step\nextract_xg.py]
    B -->|data/raw/*.json| C[Transform Step\ntransform_xg.py]
    C -->|Feature Engineering & Cleaning| D[data/processed/*_clean.csv]
    D -->|In-Memory SQL Analytics| E[DuckDB Engine\nquery_xg.py]
    E -->|Automated CI/CD| F[GitHub Actions Runner]