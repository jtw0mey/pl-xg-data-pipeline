⚽ Premier League xG Data Pipeline & Analytics Engine (2025/26)
An end-to-end data engineering pipeline that extracts, transforms, and analyzes Expected Goals (xG) and Expected Assists (xA) metrics for Premier League players during the 2025/26 season. Built with Python, Pandas, DuckDB, and automated via GitHub Actions.

🏗️ Pipeline Architecture
Code snippet
flowchart LR
    A[Understat API] -->|Raw JSON| B[Extract Step\nextract_xg.py]
    B -->|data/raw/*.json| C[Transform Step\ntransform_xg.py]
    C -->|Feature Engineering & Cleaning| D[data/processed/*_clean.csv]
    D -->|In-Memory SQL Analytics| E[DuckDB Engine\nquery_xg.py]
    E -->|Automated CI/CD| F[GitHub Actions Runner]
✨ Key Features & Capabilities
Automated Data Ingestion: Extracts raw player performance JSONs directly from the Understat REST API using understatapi.

Data Transformation & Feature Engineering:

Parses raw nested JSON responses into clean tabular DataFrames using pandas.

Computes advanced analytical features such as xG Overperformance (goals - xG) and normalized xG Per 90 rates ((xG / minutes) * 90).

Handles missing records, standardizes numerical data types, and applies clean metric rounding.

In-Memory Analytical Engine: Leverages DuckDB for fast SQL queries directly over CSV storage, generating leaderboards and tactical insights without needing a heavy database server.

On-Demand CI/CD Integration: Fully integrated with GitHub Actions workflows to run the entire extraction, transformation, query, and repository sync process on demand.

📊 Analytical Insights (DuckDB Output)
Using DuckDB SQL queries over the processed dataset, the engine extracts key player performance metrics:

Top Expected Goal (xG) Accumulators
Identifies players generating the highest quality scoring chances over the season:

Plaintext
┌──────────────────────┬──────────────────────┬─────────┬───────┬───────┬────────────────────┐
│ player_name          │ team_title           │ games   │ goals │ xG    │ xg_overperformance │
├──────────────────────┼──────────────────────┼─────────┼───────┼───────┼────────────────────┤
│ Erling Haaland       │ Manchester City      │ 31      │ 27    │ 24.12 │ +2.88              │
│ Mohamed Salah        │ Liverpool            │ 32      │ 18    │ 18.05 │ -0.05              │
└──────────────────────┴──────────────────────┴─────────┴───────┴───────┴────────────────────┘
🛠️ Repository Structure
Plaintext
pl-xg-data-pipeline/
├── .github/
│   └── workflows/
│       └── pl_xg_pipeline_2025.yml    # CI/CD GitHub Actions automation definition
├── data/
│   ├── raw/                           # Raw extracted JSON payloads
│   └── processed/                     # Cleaned CSV outputs ready for analysis
├── src/
│   ├── extract_xg.py                  # API extraction script
│   ├── transform_xg.py                # Pandas ETL transformation & metric calculation
│   └── query_xg.py                    # DuckDB SQL analytics execution
├── requirements.txt                   # Python dependencies
└── README.md                          # Project documentation
💻 Local Setup & Execution
Prerequisites
Python 3.10+

Git

Installation
Clone the repository:

Bash
git clone https://github.com/jtw0mey/pl-xg-data-pipeline.git
cd pl-xg-data-pipeline
Set up virtual environment:

Bash
python3 -m venv venv
source venv/bin/activate
Install dependencies:

Bash
pip install -r requirements.txt
Run the ETL Pipeline manually:

Bash
python src/extract_xg.py
python src/transform_xg.py
python src/query_xg.py