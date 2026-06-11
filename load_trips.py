from pathlib import Path

import pandas as pd

DRIVE_FILE_ID = "16NyoAdc-KGnpYZfBr-CLXO8wZweOYAY0"
DRIVE_VIEW_URL = f"https://drive.google.com/file/d/{DRIVE_FILE_ID}/view"
DRIVE_CSV_URL = f"https://drive.google.com/uc?export=download&id={DRIVE_FILE_ID}"


def _project_roots() -> list[Path]:
    here = Path.cwd().resolve()
    return [here, here.parent, here.parent.parent]


def _local_csv_paths() -> list[Path]:
    paths: list[Path] = []
    for root in _project_roots():
        paths.append(root / "trips_segments.csv")
    return paths


def read_trips_csv() -> tuple[pd.DataFrame, Path | str]:
    for path in _local_csv_paths():
        if path.is_file():
            return pd.read_csv(path, keep_default_na=False), path
    return pd.read_csv(DRIVE_CSV_URL, keep_default_na=False), DRIVE_VIEW_URL


def prepare_trips_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("country", "city"):
        out[col] = out[col].replace("None", pd.NA)
    out["year"] = out["year"].astype(int)
    return out
