from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw"

SEASONS = [
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
]

BASE_URL = (
    "https://raw.githubusercontent.com/"
    "vaastav/Fantasy-Premier-League/master/data"
)

FILES = [
    "players_raw.csv",
    "teams.csv",
]


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading: {url}")

    request = Request(
        url,
        headers={"User-Agent": "football-intelligence-platform"},
    )

    with urlopen(request, timeout=60) as response:
        data = response.read()

    if not data:
        raise RuntimeError(f"Downloaded empty file: {url}")

    destination.write_bytes(data)

    print(f"Saved: {destination} ({len(data):,} bytes)")


def main() -> None:
    print("DATA: acquiring historical Premier League data")

    for season in SEASONS:
        print(f"\nSeason: {season}")

        for filename in FILES:
            url = f"{BASE_URL}/{season}/{filename}"
            destination = RAW_ROOT / season / filename

            download(url, destination)

    print("\nDATA: raw data acquisition complete")

    missing = []

    for season in SEASONS:
        for filename in FILES:
            path = RAW_ROOT / season / filename

            if not path.is_file() or path.stat().st_size == 0:
                missing.append(str(path))

    if missing:
        raise FileNotFoundError(
            "Raw data acquisition completed with missing files:\n"
            + "\n".join(missing)
        )

    print("DATA: all expected raw files are present")


if __name__ == "__main__":
    main()