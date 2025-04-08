import csv
from datetime import datetime
from pathlib import Path


def get_postal_vote_dispatch_dates(council_id):
    with open(
        Path(__file__).parent / "data" / "20250501_postal_votes.csv"
    ) as csvfile:
        reader = csv.DictReader(csvfile)
        dispatch_dates = {row.pop("Reg"): row for row in list(reader)}

        if council_id not in dispatch_dates:
            return None

        try:
            row = dispatch_dates[council_id]
            return [
                datetime.strptime(row["Date 1"], "%d/%m/%Y").date(),
                datetime.strptime(row["Date 2"], "%d/%m/%Y").date(),
                datetime.strptime(row["Date 3"], "%d/%m/%Y").date(),
            ]
        except ValueError:
            return None
