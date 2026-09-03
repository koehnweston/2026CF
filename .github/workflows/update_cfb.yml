name: Auto Update CFB Lines and Matchups

on:
  workflow_dispatch:
  schedule:
    # Auto-runs Tuesday and Friday mornings
    - cron: '0 10 * * 2,5'

jobs:
  update-data:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: pip install requests

      - name: Run ESPN CFB Live Data Fetcher
        run: python update_cfb.py

      - name: Commit and Push Changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add league_data.json
          git diff --quiet && git diff --staged --quiet || (git commit -m "Auto-update ESPN matchups & betting lines" && git push)
