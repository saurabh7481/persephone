#!/usr/bin/env python3
"""Download OpenFlights data and emit top-500 airports.csv + routes.csv."""
from __future__ import annotations

import csv
import io
import urllib.request
from collections import Counter
from pathlib import Path

AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
TOP_N = 500
OUT_DIR = Path("plugins/persephone-plugin-airline-delay/src/persephone_airline_delay/data")

def fetch(url: str) -> list[list[str]]:
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(text)))

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching airports.dat …")
    airport_rows = fetch(AIRPORTS_URL)
    # columns: id,name,city,country,iata,icao,lat,lon,alt,tz,dst,tz_name,type,source
    airports: dict[str, dict] = {}
    for row in airport_rows:
        if len(row) < 8:
            continue
        iata = row[4].strip().strip('"')
        if len(iata) != 3 or iata == r"\N":
            continue
        try:
            lat, lon = float(row[6]), float(row[7])
        except ValueError:
            continue
        airports[iata] = {
            "name": row[1].strip().strip('"'),
            "city": row[2].strip().strip('"'),
            "country": row[3].strip().strip('"'),
            "lat": lat,
            "lon": lon,
        }

    print(f"  {len(airports)} airports with valid IATA codes")

    print("Fetching routes.dat …")
    route_rows = fetch(ROUTES_URL)
    # columns: airline,airline_id,src,src_id,dst,dst_id,codeshare,stops,equipment
    route_count: Counter[str] = Counter()
    for row in route_rows:
        if len(row) < 5:
            continue
        src, dst = row[2].strip(), row[4].strip()
        if src in airports:
            route_count[src] += 1
        if dst in airports:
            route_count[dst] += 1

    top_iata = {iata for iata, _ in route_count.most_common(TOP_N)}
    print(f"  Top-{TOP_N} airports selected")

    # edge weight = number of routes between each ordered pair
    pair_count: Counter[tuple[str, str]] = Counter()
    for row in route_rows:
        if len(row) < 5:
            continue
        src, dst = row[2].strip(), row[4].strip()
        if src in top_iata and dst in top_iata and src != dst:
            key = tuple(sorted((src, dst)))
            pair_count[key] += 1  # type: ignore[arg-type]

    # assign sequential ids to top airports sorted by route_count desc, then iata
    ordered = sorted(top_iata, key=lambda x: (-route_count[x], x))
    iata_to_id = {iata: i for i, iata in enumerate(ordered)}

    # normalise edge weights to [0, 1]
    max_w = max(pair_count.values()) if pair_count else 1

    airports_path = OUT_DIR / "airports.csv"
    with airports_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "iata", "name", "city", "country", "lat", "lon", "route_count"])
        for iata in ordered:
            a = airports[iata]
            w.writerow([iata_to_id[iata], iata, a["name"], a["city"], a["country"],
                        a["lat"], a["lon"], route_count[iata]])

    routes_path = OUT_DIR / "routes.csv"
    with routes_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["src_id", "dst_id", "weight"])
        for (a, b), count in sorted(pair_count.items()):
            w.writerow([iata_to_id[a], iata_to_id[b], round(count / max_w, 4)])

    print(f"  {len(ordered)} airports → {airports_path}")
    print(f"  {len(pair_count)} edges → {routes_path}")

if __name__ == "__main__":
    main()
