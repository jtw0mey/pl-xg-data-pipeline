import json
import os
import requests

SEASONS = ["2026"]
RAW_DATA_DIR = "data/raw"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}

def main():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)

    for season in SEASONS:
        url = f"https://understat.com/getLeagueData/EPL/{season}"
        headers = {**HEADERS, "Referer": f"https://understat.com/league/EPL/{season}"}
        res = requests.get(url, headers=headers, timeout=20)
        res.raise_for_status()
        data = res.json()

        with open(os.path.join(RAW_DATA_DIR, f"epl_players_{season}.json"), "w") as f:
            json.dump(data["players"], f, indent=2)
        with open(os.path.join(RAW_DATA_DIR, f"epl_teams_{season}.json"), "w") as f:
            json.dump(data["teams"], f, indent=2)

        print(f"✅ Saved season {season}")

if __name__ == "__main__":
    main()
