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
    A[Understat API] -->|Raw JSON| B["Extract Step (extract_xg.py)"]
    B -->|data/raw/*.json| C["Transform Step (transform_xg.py)"]
    C -->|Feature Engineering & Cleaning| D["data/processed/*_clean.csv"]
    D -->|In-Memory SQL Analytics| E["DuckDB Engine (query_xg.py)"]
    E -->|Automated CI/CD| F[GitHub Actions Runner]
✨ Key Features & CapabilitiesAutomated Data Ingestion: Extracts raw player performance JSON directly from Understat using understatapi.Data Transformation & Feature Engineering:Parses raw nested JSON responses into clean tabular DataFrames using pandas.Computes analytical features such as xG Overperformance (goals - xG) and normalized xG Per 90 ((xG / minutes) * 90).Handles missing records, standardizes numerical data types, and applies consistent metric rounding.In-Memory Analytical Engine: Uses DuckDB to run fast SQL queries directly over CSV files, generating leaderboards and tactical insights without a database server.On-Demand CI/CD: A GitHub Actions workflow runs the full extract → transform → query → commit process on demand.📊 Analytical Insights (DuckDB Output)Using DuckDB SQL queries over the processed dataset, the engine produces player performance leaderboards.Top Expected Goals (xG) AccumulatorsPlayers generating the highest-quality scoring chances over the season:PlayerTeamGamesGoalsxGxG OverperformanceErling HaalandManchester City312724.12+2.88Mohamed SalahLiverpool321818.05-0.05🛠️ Repository StructurePlaintextpl-xg-data-pipeline/
├── .github/
│   └── workflows/
│       └── pl_xg_pipeline_2025.yml    # GitHub Actions workflow
├── data/
│   ├── raw/                           # Raw extracted JSON payloads
│   └── processed/                     # Cleaned CSV outputs ready for analysis
├── src/
│   ├── extract_xg.py                  # API extraction script
│   ├── transform_xg.py                # Pandas transformation & metric calculation
│   └── query_xg.py                    # DuckDB SQL analytics
├── requirements.txt                   # Python dependencies
└── README.md                          # Project documentation
💻 Local Setup & ExecutionPrerequisitesPython 3.10+GitInstallationClone the repository:Bashgit clone [https://github.com/jtw0mey/pl-xg-data-pipeline.git](https://github.com/jtw0mey/pl-xg-data-pipeline.git)
cd pl-xg-data-pipeline
Set up a virtual environment:Bashpython3 -m venv venv
source venv/bin/activate
Install dependencies:Bashpip install -r requirements.txt
Run the pipeline manually:Bashpython src/extract_xg.py
python src/transform_xg.py
python src/query_xg.py
---