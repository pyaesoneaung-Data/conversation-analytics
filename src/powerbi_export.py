"""Generate Power BI-ready CSV exports for conversation analytics.

Run from the project root:

    python -m src.powerbi_export

The exported CSVs include customer message text for classification review. Treat
files under data/processed/powerbi/ and outputs/reports/ as confidential.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .keyword_search import (
    CONCERN_PRIORITY,
    INTENT_PRIORITY,
    PRODUCT_PRIORITY,
    choose_primary,
    classify_messages,
    pipe_join,
)
from .preprocess import REQUIRED_COLUMNS, load_and_preprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "chatlog_translated_sampled.csv"
POWERBI_DIR = PROJECT_ROOT / "data" / "processed" / "powerbi"
REPORT_DIR = PROJECT_ROOT / "outputs" / "reports"
MAX_INVALID_CONVERSATION_START_RATE = 0.20

DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


MESSAGE_COLUMNS = [
    "message_id",
    "userID",
    "time",
    "message_date",
    "message_year",
    "message_month",
    "message_month_name",
    "message_day",
    "message_hour",
    "role",
    "standardized_role",
    "is_customer_message",
    "message_english",
    "cleaned_message",
    "detected_ad_name",
    "industry_category",
    "product_category",
    "product_subcategory",
    "matched_product_keywords",
    "primary_concern",
    "secondary_concerns",
    "matched_concern_keywords",
    "customer_intent",
    "intent_confidence_rule",
    "is_campaign_related",
    "campaign_name",
    "campaign_question_type",
    "campaign_related_product",
    "campaign_joining_intent",
    "matched_campaign_keywords",
    "month_start",
    "year_month",
    "datetime_valid",
]

CONVERSATION_COLUMNS = [
    "userID",
    "conversation_start_time",
    "conversation_end_time",
    "total_messages",
    "customer_message_count",
    "chatbot_message_count",
    "agent_message_count",
    "conversation_duration_minutes",
    "full_customer_conversation",
    "industries_mentioned",
    "products_mentioned",
    "primary_product",
    "concerns_mentioned",
    "primary_concern",
    "customer_intents",
    "primary_intent",
    "campaign_related",
    "campaign_names",
    "campaign_question_types",
    "campaign_joining_intent",
    "has_complaint",
    "has_payment_concern",
    "has_application_concern",
    "has_insurance_claim_concern",
    "has_product_condition_concern",
    "has_system_issue",
    "requested_human_agent",
    "number_of_unique_products",
    "number_of_unique_concerns",
    "conversation_start_date",
    "conversation_start_datetime_valid",
    "conversation_end_datetime_valid",
]

MONTHLY_TREND_COLUMNS = [
    "message_year",
    "message_month",
    "message_month_name",
    "month_start",
    "year_month",
    "industry_category",
    "primary_concern",
    "customer_intent",
    "customer_message_count",
    "unique_customer_count",
]

POWERBI_REQUIRED_SCHEMAS = {
    "message_level_analytics.csv": MESSAGE_COLUMNS,
    "conversation_level_analytics.csv": CONVERSATION_COLUMNS,
    "monthly_trend_summary.csv": MONTHLY_TREND_COLUMNS,
}

COLUMN_DEFAULTS = {
    "campaign_related_product": "Unknown",
    "requested_human_agent": "No",
    "conversation_start_datetime_valid": "No",
    "conversation_end_datetime_valid": "No",
    "datetime_valid": "No",
    "is_customer_message": "No",
    "campaign_related": "No",
    "has_complaint": "No",
    "has_payment_concern": "No",
    "has_application_concern": "No",
    "has_insurance_claim_concern": "No",
    "has_product_condition_concern": "No",
    "has_system_issue": "No",
    "industry_category": "Unknown",
    "product_category": "Unknown",
    "product_subcategory": "Unknown",
    "primary_concern": "Unknown",
    "customer_intent": "Unknown",
    "intent_confidence_rule": "Low",
    "campaign_question_type": "Not Campaign Related",
    "campaign_joining_intent": "Not Applicable",
}


def _yes_no(series: pd.Series) -> pd.Series:
    return series.map({1: "Yes", 0: "No", True: "Yes", False: "No"}).fillna("No")


def _format_datetime_text(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")


def _format_date_text(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d").fillna("")


def _format_nullable_integer_text(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").astype("Int64")
    return numeric.astype("string").fillna("")


def _format_for_powerbi(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    datetime_columns = [
        "time",
        "conversation_start_time",
        "conversation_end_time",
    ]
    date_columns = [
        "message_date",
        "month_start",
        "conversation_start_date",
    ]
    integer_columns = [
        "message_year",
        "message_month",
        "message_day",
        "message_hour",
    ]

    for column in datetime_columns:
        if column in formatted.columns:
            formatted[column] = _format_datetime_text(formatted[column])

    for column in date_columns:
        if column in formatted.columns:
            formatted[column] = _format_date_text(formatted[column])

    for column in integer_columns:
        if column in formatted.columns:
            formatted[column] = _format_nullable_integer_text(formatted[column])

    for column in ["message_id", "userID"]:
        if column in formatted.columns:
            formatted[column] = formatted[column].astype("string").fillna("")

    for column in formatted.columns:
        if pd.api.types.is_bool_dtype(formatted[column]):
            formatted[column] = formatted[column].map({True: "Yes", False: "No"})
        formatted[column] = formatted[column].fillna("")
    return formatted


def enforce_powerbi_schema(df: pd.DataFrame, required_columns: list[str], file_name: str) -> pd.DataFrame:
    """Restore required columns and order them for existing Power BI queries."""

    output = df.copy()
    missing_before = [column for column in required_columns if column not in output.columns]
    restored_columns = []

    for column in missing_before:
        output[column] = COLUMN_DEFAULTS.get(column, "")
        restored_columns.append(column)

    missing_after = [column for column in required_columns if column not in output.columns]
    if missing_after:
        raise ValueError(f"{file_name} is missing required Power BI columns: {missing_after}")

    extra_columns = [column for column in output.columns if column not in required_columns]
    ordered = output[required_columns + extra_columns]

    print(f"{file_name} missing columns before correction: {missing_before}")
    print(f"{file_name} restored columns: {restored_columns}")
    print(f"{file_name} final column count: {len(ordered.columns)}")
    print(f"{file_name} final ordered column list: {ordered.columns.tolist()}")

    return ordered


def build_message_level(classified_df: pd.DataFrame) -> pd.DataFrame:
    message_level = classified_df.copy()
    message_level["is_customer_message"] = _yes_no(message_level["is_customer_message"])
    return _format_for_powerbi(message_level[MESSAGE_COLUMNS])


def _conversation_duration_minutes(group: pd.DataFrame) -> float:
    valid_times = group["time"].dropna()
    if valid_times.empty:
        return 0.0
    return round((valid_times.max() - valid_times.min()).total_seconds() / 60, 2)


def _flag_contains(values: pd.Series, targets: set[str]) -> str:
    return "Yes" if any(value in targets for value in values.dropna().astype(str)) else "No"


def build_conversation_level(classified_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for user_id, group in classified_df.groupby("userID", dropna=False):
        customer_group = group[group["standardized_role"] == "customer"]
        customer_source = customer_group if not customer_group.empty else group
        conversation_start_time = group["time"].min()
        conversation_end_time = group["time"].max()

        rows.append(
            {
                "userID": user_id,
                "conversation_start_time": conversation_start_time,
                "conversation_end_time": conversation_end_time,
                "conversation_start_date": conversation_start_time.date() if pd.notna(conversation_start_time) else pd.NaT,
                "conversation_start_datetime_valid": "Yes" if pd.notna(conversation_start_time) else "No",
                "conversation_end_datetime_valid": "Yes" if pd.notna(conversation_end_time) else "No",
                "total_messages": len(group),
                "customer_message_count": int((group["standardized_role"] == "customer").sum()),
                "chatbot_message_count": int((group["standardized_role"] == "chatbot").sum()),
                "agent_message_count": int((group["standardized_role"] == "agent").sum()),
                "conversation_duration_minutes": _conversation_duration_minutes(group),
                "full_customer_conversation": " | ".join(customer_group["message_english"].fillna("").astype(str)),
                "industries_mentioned": pipe_join(customer_source["industry_category"]),
                "products_mentioned": pipe_join(customer_source["_products_mentioned"]),
                "primary_product": choose_primary(customer_source["product_subcategory"], [item.title() for item in PRODUCT_PRIORITY]),
                "concerns_mentioned": pipe_join(customer_source["_concerns_mentioned"]),
                "primary_concern": choose_primary(customer_source["primary_concern"], CONCERN_PRIORITY),
                "customer_intents": pipe_join(customer_source["customer_intent"]),
                "primary_intent": choose_primary(customer_source["customer_intent"], INTENT_PRIORITY),
                "campaign_related": "Yes" if (customer_source["is_campaign_related"] == "Yes").any() else "No",
                "campaign_names": pipe_join(customer_source["campaign_name"]),
                "campaign_question_types": pipe_join(customer_source["campaign_question_type"]),
                "campaign_joining_intent": choose_primary(customer_source["campaign_joining_intent"], ["Yes", "Unclear", "No", "Not Applicable"]),
                "has_complaint": _flag_contains(customer_source["primary_concern"], {"Complaint"}),
                "has_payment_concern": _flag_contains(
                    customer_source["primary_concern"],
                    {"Monthly Installment", "Payment Method", "Late Payment", "Outstanding Balance", "Early Repayment", "Debt or Collection", "Insurance Premium"},
                ),
                "has_application_concern": _flag_contains(
                    customer_source["primary_concern"],
                    {"Application Process", "Application Status", "Approval or Rejection", "Required Documents"},
                ),
                "has_insurance_claim_concern": _flag_contains(customer_source["primary_concern"], {"Insurance Claim", "Claim Status"}),
                "has_product_condition_concern": _flag_contains(customer_source["primary_concern"], {"Product Conditions", "Eligibility"}),
                "has_system_issue": _flag_contains(customer_source["primary_concern"], {"Account or System Issue"}),
                "requested_human_agent": _flag_contains(customer_source["primary_concern"], {"Contact Agent"}),
                "number_of_unique_products": len({value for value in customer_source["product_subcategory"].astype(str) if value and value != "Unknown"}),
                "number_of_unique_concerns": len({value for value in customer_source["primary_concern"].astype(str) if value and value != "Unknown"}),
            }
        )

    conversation_level = pd.DataFrame(rows).sort_values("userID").reset_index(drop=True)
    return _format_for_powerbi(conversation_level)


def _customer_messages(classified_df: pd.DataFrame) -> pd.DataFrame:
    return classified_df[classified_df["standardized_role"] == "customer"].copy()


def build_concern_summary(classified_df: pd.DataFrame) -> pd.DataFrame:
    customer_df = _customer_messages(classified_df)
    total_messages = max(len(customer_df), 1)
    total_customers = max(customer_df["userID"].nunique(), 1)
    rows = []
    for concern, group in customer_df.groupby("primary_concern", dropna=False):
        rows.append(
            {
                "primary_concern": concern,
                "message_count": len(group),
                "customer_count": group["userID"].nunique(),
                "percentage_of_customer_messages": round(len(group) / total_messages * 100, 2),
                "percentage_of_customers": round(group["userID"].nunique() / total_customers * 100, 2),
                "top_industry": choose_primary(group["industry_category"]),
                "top_product": choose_primary(group["product_subcategory"], [item.title() for item in PRODUCT_PRIORITY]),
                "campaign_related_message_count": int((group["is_campaign_related"] == "Yes").sum()),
            }
        )
    return _format_for_powerbi(pd.DataFrame(rows).sort_values("message_count", ascending=False))


def build_product_summary(classified_df: pd.DataFrame) -> pd.DataFrame:
    customer_df = _customer_messages(classified_df)
    total_messages = max(len(customer_df), 1)
    rows = []
    grouped = customer_df.groupby(["industry_category", "product_category", "product_subcategory"], dropna=False)
    for keys, group in grouped:
        rows.append(
            {
                "industry_category": keys[0],
                "product_category": keys[1],
                "product_subcategory": keys[2],
                "message_count": len(group),
                "customer_count": group["userID"].nunique(),
                "percentage_of_customer_messages": round(len(group) / total_messages * 100, 2),
                "top_concern": choose_primary(group["primary_concern"], CONCERN_PRIORITY),
                "campaign_related_message_count": int((group["is_campaign_related"] == "Yes").sum()),
            }
        )
    return _format_for_powerbi(pd.DataFrame(rows).sort_values("message_count", ascending=False))


def build_campaign_summary(classified_df: pd.DataFrame) -> pd.DataFrame:
    customer_df = _customer_messages(classified_df)
    campaign_df = customer_df[customer_df["is_campaign_related"] == "Yes"].copy()
    if campaign_df.empty:
        return pd.DataFrame(
            columns=[
                "campaign_name",
                "campaign_related_product",
                "campaign_question_type",
                "message_count",
                "customer_count",
                "joining_intent_yes_count",
                "joining_intent_unclear_count",
                "top_customer_concern",
                "top_customer_intent",
            ]
        )

    rows = []
    grouped = campaign_df.groupby(["campaign_name", "campaign_related_product", "campaign_question_type"], dropna=False)
    for keys, group in grouped:
        rows.append(
            {
                "campaign_name": keys[0],
                "campaign_related_product": keys[1],
                "campaign_question_type": keys[2],
                "message_count": len(group),
                "customer_count": group["userID"].nunique(),
                "joining_intent_yes_count": int((group["campaign_joining_intent"] == "Yes").sum()),
                "joining_intent_unclear_count": int((group["campaign_joining_intent"] == "Unclear").sum()),
                "top_customer_concern": choose_primary(group["primary_concern"], CONCERN_PRIORITY),
                "top_customer_intent": choose_primary(group["customer_intent"], INTENT_PRIORITY),
            }
        )
    return _format_for_powerbi(pd.DataFrame(rows).sort_values("message_count", ascending=False))


def build_monthly_trend_summary(classified_df: pd.DataFrame) -> pd.DataFrame:
    customer_df = _customer_messages(classified_df)
    grouped = customer_df.groupby(
        [
            "message_year",
            "message_month",
            "message_month_name",
            "month_start",
            "year_month",
            "industry_category",
            "primary_concern",
            "customer_intent",
        ],
        dropna=False,
    )
    rows = []
    for keys, group in grouped:
        rows.append(
            {
                "message_year": keys[0],
                "message_month": keys[1],
                "message_month_name": keys[2],
                "month_start": keys[3],
                "year_month": keys[4],
                "industry_category": keys[5],
                "primary_concern": keys[6],
                "customer_intent": keys[7],
                "customer_message_count": len(group),
                "unique_customer_count": group["userID"].nunique(),
            }
        )
    monthly_trend = pd.DataFrame(rows)
    monthly_trend = monthly_trend.sort_values(
        ["message_year", "message_month", "customer_message_count"],
        ascending=[True, True, False],
    )
    return _format_for_powerbi(monthly_trend)


def build_datetime_error_review(classified_df: pd.DataFrame, conversation_level: pd.DataFrame) -> pd.DataFrame:
    rows = []
    invalid_messages = classified_df[classified_df["datetime_valid"] == "No"]
    for _, row in invalid_messages.iterrows():
        rows.append(
            {
                "source_table": "message_level_analytics",
                "message_id": row.get("message_id", ""),
                "userID": row.get("userID", ""),
                "original_time_value": row.get("original_time_value", ""),
                "datetime_field": "time",
                "parse_status": "Invalid or missing",
                "message_english": row.get("message_english", ""),
            }
        )

    invalid_conversation_starts = conversation_level[
        conversation_level["conversation_start_datetime_valid"] == "No"
    ]
    for _, row in invalid_conversation_starts.iterrows():
        rows.append(
            {
                "source_table": "conversation_level_analytics",
                "message_id": "",
                "userID": row.get("userID", ""),
                "original_time_value": row.get("conversation_start_time", ""),
                "datetime_field": "conversation_start_time",
                "parse_status": "Invalid or missing",
                "message_english": "",
            }
        )

    review = pd.DataFrame(
        rows,
        columns=[
            "source_table",
            "message_id",
            "userID",
            "original_time_value",
            "datetime_field",
            "parse_status",
            "message_english",
        ],
    )
    return _format_for_powerbi(review.drop_duplicates())


def build_keyword_match_review(classified_df: pd.DataFrame) -> pd.DataFrame:
    customer_df = _customer_messages(classified_df)
    low_confidence = customer_df[customer_df["intent_confidence_rule"] == "Low"]
    multiple_categories = customer_df[
        (customer_df["concern_count"] > 1)
        | customer_df["_products_mentioned"].str.contains(r"\|", regex=True, na=False)
        | customer_df["matched_campaign_keywords"].str.contains(r"\|", regex=True, na=False)
    ]
    selected_ids = set(low_confidence["message_id"]) | set(multiple_categories["message_id"])
    remaining = customer_df[~customer_df["message_id"].isin(selected_ids)]
    sample_size = min(100, len(remaining))
    sample = remaining.sample(n=sample_size, random_state=42) if sample_size else remaining

    review = pd.concat([low_confidence, multiple_categories, sample], ignore_index=True)
    review = review.drop_duplicates(subset=["message_id"])
    columns = [
        "message_id",
        "userID",
        "message_english",
        "product_category",
        "primary_concern",
        "customer_intent",
        "matched_product_keywords",
        "matched_concern_keywords",
        "matched_campaign_keywords",
    ]
    return _format_for_powerbi(review[columns].sort_values("message_id"))


def build_validation_report(
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    classified_df: pd.DataFrame,
    outputs: dict[str, pd.DataFrame],
    output_paths: dict[str, Path],
) -> str:
    customer_df = _customer_messages(classified_df)
    required_output_columns = set(MESSAGE_COLUMNS)
    message_missing = sorted(required_output_columns - set(outputs["message_level_analytics.csv"].columns))
    warnings = []
    if message_missing:
        warnings.append(f"Missing message-level columns: {message_missing}")
    if classified_df["message_id"].duplicated().any():
        warnings.append("Duplicate message_id values detected.")
    if classified_df["time"].isna().any():
        warnings.append("Invalid or missing dates detected after datetime conversion.")
    if not set(REQUIRED_COLUMNS).issubset(raw_df.columns):
        warnings.append("Raw input is missing required source columns.")
    if not warnings:
        warnings.append("No blocking validation warnings detected.")

    def pct(value: int, denominator: int) -> float:
        return round(value / max(denominator, 1) * 100, 2)

    unknown_concern_pct = pct(int((customer_df["primary_concern"] == "Unknown").sum()), len(customer_df))
    unknown_intent_pct = pct(int((customer_df["customer_intent"] == "Unknown").sum()), len(customer_df))
    no_product_pct = pct(int((customer_df["product_subcategory"] == "Unknown").sum()), len(customer_df))
    no_concern_pct = pct(int((customer_df["primary_concern"] == "Unknown").sum()), len(customer_df))
    campaign_pct = pct(int((customer_df["is_campaign_related"] == "Yes").sum()), len(customer_df))

    lines = [
        "Power BI Export Validation Report",
        "=================================",
        "Note: exported message text may contain confidential customer information.",
        "",
        f"Input row count: {len(raw_df)}",
        f"Cleaned row count: {len(cleaned_df)}",
        f"Customer message count: {len(customer_df)}",
        f"Unique customer count: {customer_df['userID'].nunique()}",
        "",
        "Output row counts:",
    ]
    for name, df in outputs.items():
        lines.append(f"- {name}: {len(df)}")

    lines.extend(
        [
            "",
            "Classification coverage:",
            f"- Unknown concern percentage: {unknown_concern_pct}%",
            f"- Unknown intent percentage: {unknown_intent_pct}%",
            f"- No product match percentage: {no_product_pct}%",
            f"- No concern match percentage: {no_concern_pct}%",
            f"- Campaign-related customer message percentage: {campaign_pct}%",
            "",
            "Required-column validation:",
            f"- Missing required message-level columns: {message_missing}",
            f"- Duplicate message IDs: {int(classified_df['message_id'].duplicated().sum())}",
            f"- Invalid dates: {int(classified_df['time'].isna().sum())}",
            "",
            "Primary value tie-breaking rules:",
            "- Primary product uses product priority first, then highest matched customer-message count, then alphabetical order.",
            "- Primary concern and intent use highest matched customer-message count, then the documented priority list, then alphabetical order.",
            "",
            "Output file paths:",
        ]
    )
    for name, path in output_paths.items():
        lines.append(f"- {name}: {path}")
    lines.extend(["", "Warnings:"] + [f"- {warning}" for warning in warnings])
    return "\n".join(lines) + "\n"


def _count_nonblank_format_violations(series: pd.Series, pattern: re.Pattern[str]) -> int:
    values = series.fillna("").astype(str)
    nonblank = values[values != ""]
    return int((~nonblank.str.match(pattern)).sum())


def validate_required_export_fields(outputs: dict[str, pd.DataFrame]) -> list[str]:
    warnings = []

    for name, columns in POWERBI_REQUIRED_SCHEMAS.items():
        missing = [column for column in columns if column not in outputs[name].columns]
        if missing:
            warnings.append(f"{name} is missing required columns: {missing}")

    message_df = outputs["message_level_analytics.csv"]
    conversation_df = outputs["conversation_level_analytics.csv"]

    if message_df["message_id"].duplicated().any():
        warnings.append("message_level_analytics.csv contains duplicate message_id values.")
    if message_df["userID"].astype(str).str.strip().eq("").any():
        warnings.append("message_level_analytics.csv contains blank userID values.")
    if conversation_df["userID"].astype(str).str.strip().eq("").any():
        warnings.append("conversation_level_analytics.csv contains blank userID values.")
    if conversation_df["userID"].duplicated().any():
        warnings.append("conversation_level_analytics.csv contains duplicate userID values.")

    invalid_start_rate = (
        (conversation_df["conversation_start_datetime_valid"] == "No").mean()
        if len(conversation_df)
        else 0
    )
    if invalid_start_rate > MAX_INVALID_CONVERSATION_START_RATE:
        warnings.append(
            "More than "
            f"{MAX_INVALID_CONVERSATION_START_RATE:.0%} of conversation start times are invalid."
        )

    return warnings


def validate_exported_date_text(output_paths: dict[str, Path]) -> dict[str, int | list[str]]:
    """Reopen exported CSVs as strings and check ISO-style date text."""

    message_df = pd.read_csv(
        output_paths["message_level_analytics.csv"],
        dtype=str,
        keep_default_na=False,
    )
    conversation_df = pd.read_csv(
        output_paths["conversation_level_analytics.csv"],
        dtype=str,
        keep_default_na=False,
    )
    monthly_df = pd.read_csv(
        output_paths["monthly_trend_summary.csv"],
        dtype=str,
        keep_default_na=False,
    )

    checks: dict[str, int | list[str]] = {
        "message_time_format_violations": _count_nonblank_format_violations(message_df["time"], DATETIME_PATTERN),
        "message_date_format_violations": _count_nonblank_format_violations(message_df["message_date"], DATE_PATTERN),
        "message_month_start_format_violations": _count_nonblank_format_violations(message_df["month_start"], DATE_PATTERN),
        "conversation_start_time_format_violations": _count_nonblank_format_violations(conversation_df["conversation_start_time"], DATETIME_PATTERN),
        "conversation_end_time_format_violations": _count_nonblank_format_violations(conversation_df["conversation_end_time"], DATETIME_PATTERN),
        "conversation_start_date_format_violations": _count_nonblank_format_violations(conversation_df["conversation_start_date"], DATE_PATTERN),
        "monthly_month_start_format_violations": _count_nonblank_format_violations(monthly_df["month_start"], DATE_PATTERN),
    }

    invalid_examples = []
    example_specs = [
        ("message_level_analytics.csv", message_df, "time", DATETIME_PATTERN),
        ("message_level_analytics.csv", message_df, "message_date", DATE_PATTERN),
        ("message_level_analytics.csv", message_df, "month_start", DATE_PATTERN),
        ("conversation_level_analytics.csv", conversation_df, "conversation_start_time", DATETIME_PATTERN),
        ("conversation_level_analytics.csv", conversation_df, "conversation_end_time", DATETIME_PATTERN),
        ("conversation_level_analytics.csv", conversation_df, "conversation_start_date", DATE_PATTERN),
        ("monthly_trend_summary.csv", monthly_df, "month_start", DATE_PATTERN),
    ]
    for source_table, df, column, pattern in example_specs:
        values = df[column].fillna("").astype(str)
        invalid = values[(values != "") & (~values.str.match(pattern))].head(3)
        for value in invalid:
            invalid_examples.append(f"{source_table}.{column}: {value}")
    checks["invalid_date_examples"] = invalid_examples[:20]

    return checks


def validate_exported_required_columns(output_paths: dict[str, Path]) -> None:
    """Reopen Power BI CSVs and assert required columns exist exactly as written."""

    for file_name in ["message_level_analytics.csv", "conversation_level_analytics.csv"]:
        df = pd.read_csv(
            output_paths[file_name],
            dtype=str,
            keep_default_na=False,
            nrows=0,
        )
        required_columns = POWERBI_REQUIRED_SCHEMAS[file_name]
        missing = [column for column in required_columns if column not in df.columns]
        if missing:
            raise ValueError(
                f"{file_name} is missing required columns after export: {missing}"
            )
        print(f"{file_name} post-export required-column assertion passed.")


def build_datetime_validation_report(
    outputs: dict[str, pd.DataFrame],
    output_paths: dict[str, Path],
    date_text_checks: dict[str, int | list[str]],
    warnings: list[str],
) -> str:
    message_df = outputs["message_level_analytics.csv"]
    conversation_df = outputs["conversation_level_analytics.csv"]

    valid_time_count = int((message_df["datetime_valid"] == "Yes").sum())
    invalid_time_count = int((message_df["datetime_valid"] == "No").sum())
    blank_message_date_count = int((message_df["message_date"].astype(str) == "").sum())
    valid_start_count = int((conversation_df["conversation_start_datetime_valid"] == "Yes").sum())
    invalid_start_count = int((conversation_df["conversation_start_datetime_valid"] == "No").sum())
    valid_end_count = int((conversation_df["conversation_end_datetime_valid"] == "Yes").sum())
    missing_end_count = int((conversation_df["conversation_end_time"].astype(str) == "").sum())

    invalid_examples = date_text_checks.get("invalid_date_examples", [])
    if not invalid_examples:
        invalid_examples = ["No nonblank exported date-format violations found."]

    lines = [
        "Power BI Datetime Validation Report",
        "===================================",
        "Files checked:",
        "- message_level_analytics.csv",
        "- conversation_level_analytics.csv",
        "- monthly_trend_summary.csv",
        "",
        "Message-level datetime checks:",
        f"- Total rows: {len(message_df)}",
        f"- Valid time rows: {valid_time_count}",
        f"- Invalid or missing time rows: {invalid_time_count}",
        f"- Blank message_date rows: {blank_message_date_count}",
        f"- Duplicate message_id count: {int(message_df['message_id'].duplicated().sum())}",
        f"- Minimum parsed time: {message_df.loc[message_df['time'] != '', 'time'].min() if valid_time_count else ''}",
        f"- Maximum parsed time: {message_df.loc[message_df['time'] != '', 'time'].max() if valid_time_count else ''}",
        "",
        "Conversation-level datetime checks:",
        f"- Total rows: {len(conversation_df)}",
        f"- Valid conversation_start_time rows: {valid_start_count}",
        f"- Invalid or missing conversation_start_time rows: {invalid_start_count}",
        f"- Valid conversation_end_time rows: {valid_end_count}",
        f"- Missing conversation_end_time rows: {missing_end_count}",
        f"- Duplicate userID count: {int(conversation_df['userID'].duplicated().sum())}",
        f"- Minimum conversation_start_time: {conversation_df.loc[conversation_df['conversation_start_time'] != '', 'conversation_start_time'].min() if valid_start_count else ''}",
        f"- Maximum conversation_start_time: {conversation_df.loc[conversation_df['conversation_start_time'] != '', 'conversation_start_time'].max() if valid_start_count else ''}",
        "",
        "Exported date formats:",
        "- time: YYYY-MM-DD HH:MM:SS",
        "- message_date: YYYY-MM-DD",
        "- month_start: YYYY-MM-DD",
        "- conversation_start_time: YYYY-MM-DD HH:MM:SS",
        "- conversation_end_time: YYYY-MM-DD HH:MM:SS",
        "- conversation_start_date: YYYY-MM-DD",
        "",
        "Date-format validation after reopening CSVs:",
    ]
    for key, value in date_text_checks.items():
        if key != "invalid_date_examples":
            lines.append(f"- {key}: {value}")

    lines.extend(["", "Invalid date examples, maximum 20:"])
    lines.extend([f"- {example}" for example in invalid_examples[:20]])

    lines.extend(["", "Final output paths:"])
    for name, path in output_paths.items():
        lines.append(f"- {name}: {path}")

    lines.extend(["", "Warnings:"])
    if warnings:
        lines.extend([f"- {warning}" for warning in warnings])
    else:
        lines.append("- No blocking datetime validation warnings detected.")

    return "\n".join(lines) + "\n"


def export_powerbi_files(raw_path: Path = RAW_PATH) -> dict[str, Path]:
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    raw_df, cleaned_df = load_and_preprocess(raw_path)
    classified_df = classify_messages(cleaned_df)
    conversation_level = build_conversation_level(classified_df)

    outputs = {
        "message_level_analytics.csv": build_message_level(classified_df),
        "conversation_level_analytics.csv": conversation_level,
        "concern_summary.csv": build_concern_summary(classified_df),
        "product_summary.csv": build_product_summary(classified_df),
        "campaign_summary.csv": build_campaign_summary(classified_df),
        "monthly_trend_summary.csv": build_monthly_trend_summary(classified_df),
        "keyword_match_review.csv": build_keyword_match_review(classified_df),
        "datetime_error_review.csv": build_datetime_error_review(classified_df, conversation_level),
    }

    for file_name, required_columns in POWERBI_REQUIRED_SCHEMAS.items():
        outputs[file_name] = enforce_powerbi_schema(
            outputs[file_name],
            required_columns,
            file_name,
        )

    blocking_warnings = validate_required_export_fields(outputs)
    if blocking_warnings:
        raise ValueError("Power BI export validation failed: " + " ".join(blocking_warnings))

    output_paths = {}
    for name, df in outputs.items():
        path = POWERBI_DIR / name
        df.to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
            na_rep="",
            lineterminator="\r\n",
        )
        output_paths[name] = path

    date_text_checks = validate_exported_date_text(output_paths)
    validate_exported_required_columns(output_paths)
    date_format_warnings = [
        f"{key}: {value}"
        for key, value in date_text_checks.items()
        if key != "invalid_date_examples" and int(value) > 0
    ]
    if date_format_warnings:
        raise ValueError("Exported datetime text validation failed: " + " ".join(date_format_warnings))

    validation_path = REPORT_DIR / "powerbi_export_validation.txt"
    validation_text = build_validation_report(raw_df, cleaned_df, classified_df, outputs, output_paths)
    validation_path.write_text(validation_text, encoding="utf-8")
    output_paths["powerbi_export_validation.txt"] = validation_path

    datetime_validation_path = REPORT_DIR / "powerbi_datetime_validation.txt"
    datetime_validation_text = build_datetime_validation_report(
        outputs,
        output_paths,
        date_text_checks,
        blocking_warnings + date_format_warnings,
    )
    datetime_validation_path.write_text(datetime_validation_text, encoding="utf-8")
    output_paths["powerbi_datetime_validation.txt"] = datetime_validation_path

    print(validation_text)
    print(datetime_validation_text)
    print("Power BI CSV export completed successfully.")
    return output_paths


if __name__ == "__main__":
    try:
        export_powerbi_files()
    except Exception as exc:
        print(f"Power BI CSV export failed: {exc}")
        raise
