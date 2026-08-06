"""Preprocessing utilities for conversation analytics.

The raw dataset may contain confidential customer text. Functions in this file
keep the original English message only because it is needed for classification
review and Power BI quality checks.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "userID",
    "time",
    "role",
    "message",
    "detected_ad_name",
    "message_english",
]

MISSING_DATETIME_VALUES = {
    "": pd.NA,
    "None": pd.NA,
    "none": pd.NA,
    "nan": pd.NA,
    "NaN": pd.NA,
    "NaT": pd.NA,
    "nat": pd.NA,
}


def standardize_role(value: object) -> str:
    """Map source role values into a small reporting-friendly role set."""

    role = str(value).strip().lower()

    if role in {"user", "customer", "client"}:
        return "customer"
    if role in {"assistant", "bot", "chatbot", "admin", "administrator"}:
        return "chatbot"
    if role in {"agent", "staff", "human", "operator", "officer"}:
        return "agent"
    if role == "system":
        return "system"
    if role in {"", "nan", "none"}:
        return "unknown"

    return "unknown"


def clean_message_text(value: object) -> str:
    """Normalize text for keyword matching while preserving financial phrases."""

    text = "" if pd.isna(value) else str(value)
    text = text.lower().strip()

    text = re.sub(r"<(?:name|phone|link|org|email|address)>", " ", text)
    text = text.replace("[[", " ").replace("]]", " ")
    text = text.replace("{{", " ").replace("}}", " ")
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = re.sub(r"[^a-z0-9%.\s'-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def parse_datetime_series(series: pd.Series) -> tuple[pd.Series, pd.Series, dict[str, int]]:
    """Safely parse date/time values for Power BI exports.

    Empty-like values are converted to missing before parsing. Datetimes are
    parsed day-first, invalid values are coerced to missing, and timezone
    metadata is normalized away before CSV export.
    """

    normalized = (
        series.astype("string")
        .str.strip()
        .replace(MISSING_DATETIME_VALUES)
    )
    iso_like = normalized.str.match(r"^\d{4}-\d{1,2}-\d{1,2}", na=False)
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")

    parsed.loc[iso_like] = pd.to_datetime(
        normalized.loc[iso_like],
        errors="coerce",
        dayfirst=False,
        utc=True,
    )
    parsed.loc[~iso_like] = pd.to_datetime(
        normalized.loc[~iso_like],
        errors="coerce",
        dayfirst=True,
        utc=True,
    )
    parsed = parsed.dt.tz_convert(None)

    missing_before_parse = normalized.isna()
    invalid_after_parse = normalized.notna() & parsed.isna()
    stats = {
        "input_count": int(len(series)),
        "blank_or_missing_count": int(missing_before_parse.sum()),
        "invalid_count": int(invalid_after_parse.sum()),
        "valid_count": int(parsed.notna().sum()),
    }

    return parsed, invalid_after_parse, stats


def _stable_message_id(row: pd.Series) -> str:
    key = "|".join(
        [
            str(row.get("userID", "")),
            str(row.get("time", "")),
            str(row.get("standardized_role", "")),
            str(row.get("message_english", "")),
            str(row.get("_duplicate_sequence", 0)),
        ]
    )
    return "msg_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required raw data columns: {missing}")


def load_raw_data(raw_path: str | Path) -> pd.DataFrame:
    """Load the confidential raw CSV without modifying it."""

    raw_path = Path(raw_path)
    df = pd.read_csv(raw_path)
    validate_required_columns(df)
    return df


def preprocess_messages(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw messages and add date, role, and stable ID fields."""

    validate_required_columns(raw_df)

    df = raw_df.copy()
    df["_source_row_number"] = range(len(df))

    df["message_english"] = df["message_english"].fillna("").astype(str)
    df = df[df["message_english"].str.strip() != ""].copy()

    df["standardized_role"] = df["role"].apply(standardize_role)
    df["is_customer_message"] = (df["standardized_role"] == "customer").astype(int)
    df["cleaned_message"] = df["message_english"].apply(clean_message_text)
    df = df[df["cleaned_message"] != ""].copy()

    df["original_time_value"] = df["time"]
    parsed_time, invalid_time, time_stats = parse_datetime_series(df["time"])
    df["time"] = parsed_time
    df["datetime_valid"] = df["time"].notna().map({True: "Yes", False: "No"})
    df["_datetime_parse_invalid"] = invalid_time
    df.attrs["datetime_parse_stats"] = time_stats

    duplicate_subset = ["userID", "time", "role", "message_english"]
    df = df.drop_duplicates(subset=duplicate_subset, keep="first").copy()
    df["_duplicate_sequence"] = df.groupby(duplicate_subset, dropna=False).cumcount()
    df["message_id"] = df.apply(_stable_message_id, axis=1)

    df["message_date"] = df["time"].dt.date
    df["message_year"] = df["time"].dt.year.astype("Int64")
    df["message_month"] = df["time"].dt.month.astype("Int64")
    df["message_month_name"] = df["time"].dt.month_name().fillna("")
    df["message_day"] = df["time"].dt.day.astype("Int64")
    df["message_hour"] = df["time"].dt.hour.astype("Int64")
    df["month_start"] = df["time"].dt.to_period("M").dt.to_timestamp()
    df["year_month"] = df["time"].dt.strftime("%b %Y").fillna("")

    return df.sort_values(["time", "_source_row_number"], na_position="last").reset_index(drop=True)


def load_and_preprocess(raw_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return both raw and cleaned message dataframes."""

    raw_df = load_raw_data(raw_path)
    cleaned_df = preprocess_messages(raw_df)
    return raw_df, cleaned_df
