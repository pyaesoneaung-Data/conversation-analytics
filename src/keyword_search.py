"""Rule-based keyword classification for Power BI conversation analytics."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

import pandas as pd


def pipe_join(values: Iterable[object]) -> str:
    """Return unique non-empty values as Power BI-friendly pipe-separated text."""

    cleaned = []
    for value in values:
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return " | ".join(cleaned)


PRODUCT_RULES = {
    "personal loan": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["personal loan", "cash loan", "salary loan", "consumer loan"],
    },
    "car loan": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["car loan", "auto loan", "vehicle loan", "car financing", "finance a car"],
    },
    "motorcycle loan": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["motorcycle loan", "motorbike loan", "bike loan", "big bike loan", "loan for motorcycle"],
    },
    "home loan": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["home loan", "house loan", "mortgage", "housing loan"],
    },
    "land loan": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["land loan", "loan for land", "land financing", "title deed loan", "land collateral"],
    },
    "business loan": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["business loan", "sme loan", "merchant loan", "shop loan"],
    },
    "agricultural loan": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["agricultural loan", "farmer loan", "farm loan", "agriculture loan"],
    },
    "refinancing": {
        "industry": "Loan",
        "category": "Loan Product",
        "patterns": ["refinance", "refinancing", "transfer debt", "close old debt"],
    },
    "credit card": {
        "industry": "Loan",
        "category": "Credit Product",
        "patterns": ["credit card", "card limit", "cash card"],
    },
    "life insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["life insurance"],
    },
    "health insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["health insurance", "medical insurance"],
    },
    "car insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["car insurance", "auto insurance", "vehicle insurance", "class 1 car insurance"],
    },
    "motorcycle insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["motorcycle insurance", "motorbike insurance", "bike insurance"],
    },
    "travel insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["travel insurance"],
    },
    "accident insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["accident insurance", "personal accident insurance", "pa insurance"],
    },
    "home insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["home insurance", "house insurance", "fire insurance", "property insurance"],
    },
    "loan protection insurance": {
        "industry": "Insurance",
        "category": "Insurance Product",
        "patterns": ["loan protection insurance", "credit protection insurance", "payment protection insurance"],
    },
}

PRODUCT_PRIORITY = [
    "car loan",
    "motorcycle loan",
    "home loan",
    "land loan",
    "personal loan",
    "business loan",
    "agricultural loan",
    "refinancing",
    "credit card",
    "car insurance",
    "motorcycle insurance",
    "loan protection insurance",
    "health insurance",
    "life insurance",
    "accident insurance",
    "travel insurance",
    "home insurance",
]

CONCERN_RULES = {
    "Product Information": ["product information", "details about", "want to know", "tell me about", "information about"],
    "Product Conditions": ["condition", "conditions", "requirement", "requirements", "criteria", "terms"],
    "Eligibility": ["am i eligible", "eligible for", "eligibility", "qualify for", "qualification", "income requirement", "salary requirement"],
    "Application Process": ["apply for", "application process", "submit application", "loan application", "insurance application", "register for"],
    "Application Status": ["application status", "approval status", "check application", "follow up application", "application result"],
    "Required Documents": ["required document", "required documents", "documents required", "what documents", "prepare documents", "bank statement", "salary slip", "id card copy"],
    "Approval or Rejection": ["approved", "not approved", "rejected", "approval result", "pending approval"],
    "Interest Rate": ["interest rate", "monthly interest", "annual interest", "rate per month", "rate per year"],
    "Fees and Charges": ["service fee", "processing fee", "application fee", "late fee", "penalty fee", "extra charge", "fees and charges"],
    "Loan Amount": ["loan amount", "approved amount", "maximum loan", "how much can i borrow", "borrow amount"],
    "Credit Limit": ["credit limit", "increase credit limit", "card limit", "limit increase"],
    "Down Payment": ["down payment", "deposit amount", "first payment"],
    "Monthly Installment": ["monthly installment", "installment amount", "installment payment", "repayment schedule", "pay installment"],
    "Payment Method": ["payment method", "payment channel", "where to pay", "how to pay", "pay via", "bank transfer", "qr payment", "mobile banking"],
    "Late Payment": ["late payment", "overdue payment", "past due", "missed payment", "behind on payment"],
    "Outstanding Balance": ["outstanding balance", "remaining balance", "amount outstanding", "unpaid balance"],
    "Early Repayment": ["early repayment", "close loan early", "pay off early", "settle loan"],
    "Debt or Collection": ["debt collection", "collection notice", "collector", "legal notice", "debt restructuring"],
    "Insurance Premium": ["insurance premium", "premium payment", "pay premium", "premium amount", "premium price"],
    "Insurance Coverage": ["insurance coverage", "what is covered", "cover damage", "sum insured", "deductible", "third party coverage"],
    "Insurance Claim": ["make a claim", "file a claim", "submit claim", "claim documents", "accident claim", "repair claim"],
    "Claim Status": ["claim status", "check claim", "claim result", "claim approved", "claim pending"],
    "Policy Renewal": ["policy renewal", "renew policy", "renew insurance", "insurance renewal", "extend policy"],
    "Policy Cancellation": ["cancel policy", "cancel insurance", "policy cancellation", "terminate policy"],
    "Account or System Issue": ["system error", "login problem", "cannot login", "app error", "website error", "otp problem", "cannot register"],
    "Contact Agent": ["contact staff", "talk to staff", "speak with officer", "call center", "human agent", "please call me"],
    "Complaint": ["complaint", "complain", "bad service", "not satisfied", "problem with staff", "wrong information"],
    "Campaign or Promotion": ["campaign", "promotion", "promo", "offer", "discount", "cashback", "reward", "privilege"],
    "Joining Campaign": ["join campaign", "register for campaign", "participate in campaign", "redeem code", "sign up for promotion"],
    "Campaign Eligibility": ["campaign eligibility", "eligible for campaign", "qualify for promotion", "campaign condition"],
    "Campaign Reward": ["campaign reward", "cashback", "bonus", "reward points", "redeem reward"],
}

CONCERN_PRIORITY = list(CONCERN_RULES) + ["Other", "Unknown"]

CAMPAIGN_KEYWORDS = [
    "campaign",
    "promotion",
    "promo",
    "offer",
    "discount",
    "cashback",
    "reward",
    "bonus",
    "privilege",
    "register",
    "join",
    "eligible",
    "qualification",
    "redeem",
    "code",
]

CAMPAIGN_TYPE_RULES = {
    "Campaign Eligibility": ["eligible for campaign", "eligible for promotion", "campaign eligibility", "qualify for promotion"],
    "How to Join": ["join campaign", "register for campaign", "participate in campaign", "sign up for promotion"],
    "Registration Problem": ["cannot register", "registration problem", "register failed", "registration error"],
    "Campaign Conditions": ["campaign condition", "promotion condition", "terms of campaign", "campaign requirement"],
    "Reward or Cashback": ["cashback", "reward", "bonus", "privilege"],
    "Redemption": ["redeem", "redemption", "redeem code", "coupon code"],
    "Campaign Period": ["campaign period", "promotion period", "deadline", "end date", "valid until"],
    "Campaign Status": ["campaign status", "registration status", "reward status"],
    "Complaint": ["complaint", "complain", "not received reward", "cashback not received"],
    "Campaign Information": ["campaign", "promotion", "promo", "offer", "discount"],
}

INTENT_PRIORITY = [
    "Make Complaint",
    "Report System Problem",
    "Request Human Agent",
    "Join Campaign",
    "Ask Campaign Information",
    "Submit or Check Insurance Claim",
    "Ask Insurance Coverage",
    "Report Payment Problem",
    "Ask Payment Information",
    "Check Application Status",
    "Apply for Product",
    "Ask Required Documents",
    "Ask Eligibility",
    "Ask Product Conditions",
    "Ask Product Information",
    "Greeting",
    "Other",
    "Unknown",
]


def find_phrase_matches(text: object, phrases: Iterable[str]) -> list[str]:
    matches = []
    clean_text = "" if pd.isna(text) else str(text).lower()
    for phrase in phrases:
        pattern = rf"(?<!\w){re.escape(phrase.lower())}(?!\w)"
        if re.search(pattern, clean_text):
            matches.append(phrase)
    return matches


def classify_products(text: object) -> dict[str, str]:
    matches = []
    keyword_matches = []
    for product, rule in PRODUCT_RULES.items():
        found = find_phrase_matches(text, rule["patterns"])
        if found:
            matches.append(product)
            keyword_matches.extend([f"{product}:{keyword}" for keyword in found])

    broad_loan = bool(find_phrase_matches(text, ["loan", "financing", "credit"]))
    broad_insurance = bool(find_phrase_matches(text, ["insurance", "policy", "coverage"]))
    if broad_loan and not any(PRODUCT_RULES.get(item, {}).get("industry") == "Loan" for item in matches):
        matches.append("unknown loan product")
        keyword_matches.append("unknown loan product:loan or credit")
    if broad_insurance and not any(PRODUCT_RULES.get(item, {}).get("industry") == "Insurance" for item in matches):
        matches.append("unknown insurance product")
        keyword_matches.append("unknown insurance product:insurance or policy")

    industries = set()
    categories = []
    for product in matches:
        rule = PRODUCT_RULES.get(product)
        if rule:
            industries.add(rule["industry"])
            categories.append(rule["category"])
        elif product == "unknown loan product":
            industries.add("Loan")
            categories.append("Loan Product")
        elif product == "unknown insurance product":
            industries.add("Insurance")
            categories.append("Insurance Product")

    if industries == {"Loan", "Insurance"}:
        industry_category = "Loan and Insurance"
    elif industries == {"Loan"}:
        industry_category = "Loan"
    elif industries == {"Insurance"}:
        industry_category = "Insurance"
    elif matches:
        industry_category = "Other"
    else:
        industry_category = "Unknown"

    priority = PRODUCT_PRIORITY + ["unknown loan product", "unknown insurance product"]
    primary_product = next((product for product in priority if product in matches), "Unknown")
    product_category = pipe_join(categories) if categories else "Unknown"
    product_subcategory = primary_product.title() if primary_product != "Unknown" else "Unknown"

    return {
        "industry_category": industry_category,
        "product_category": product_category,
        "product_subcategory": product_subcategory,
        "matched_product_keywords": pipe_join(keyword_matches),
        "_products_mentioned": pipe_join(product.title() for product in matches),
    }


def classify_concerns(text: object) -> dict[str, object]:
    matched_concerns = []
    keyword_matches = []
    for concern, phrases in CONCERN_RULES.items():
        found = find_phrase_matches(text, phrases)
        if found:
            matched_concerns.append(concern)
            keyword_matches.extend([f"{concern}:{keyword}" for keyword in found])

    primary = next((concern for concern in CONCERN_PRIORITY if concern in matched_concerns), "Unknown")
    secondary = [concern for concern in matched_concerns if concern != primary]

    return {
        "primary_concern": primary,
        "secondary_concerns": pipe_join(secondary),
        "matched_concern_keywords": pipe_join(keyword_matches),
        "concern_count": len(matched_concerns),
        "_concerns_mentioned": pipe_join(matched_concerns),
    }


def classify_campaign(row: pd.Series) -> dict[str, str]:
    text = row.get("cleaned_message", "")
    ad_name = "" if pd.isna(row.get("detected_ad_name", "")) else str(row.get("detected_ad_name", "")).strip()
    matched_keywords = find_phrase_matches(text, CAMPAIGN_KEYWORDS)
    is_related = bool(ad_name or matched_keywords)

    question_type = "Not Campaign Related"
    if is_related:
        question_type = "Other"
        for label, phrases in CAMPAIGN_TYPE_RULES.items():
            if find_phrase_matches(text, phrases):
                question_type = label
                break

    join_yes = bool(find_phrase_matches(text, ["join campaign", "register for campaign", "participate in campaign", "sign up for promotion", "redeem code"]))
    if not is_related:
        joining_intent = "Not Applicable"
    elif join_yes:
        joining_intent = "Yes"
    elif question_type in {"How to Join", "Registration Problem"}:
        joining_intent = "Unclear"
    else:
        joining_intent = "Unclear"

    industry = row.get("industry_category", "Unknown")
    if industry == "Loan and Insurance":
        campaign_product = "Both"
    elif industry in {"Loan", "Insurance", "Other"}:
        campaign_product = industry
    else:
        campaign_product = "Unknown"

    return {
        "is_campaign_related": "Yes" if is_related else "No",
        "campaign_name": ad_name if ad_name else ("Keyword Mentioned" if is_related else ""),
        "campaign_question_type": question_type,
        "campaign_related_product": campaign_product,
        "campaign_joining_intent": joining_intent,
        "matched_campaign_keywords": pipe_join(matched_keywords),
    }


def classify_intent(row: pd.Series) -> dict[str, str]:
    concern = row.get("primary_concern", "Unknown")
    text = row.get("cleaned_message", "")

    if find_phrase_matches(text, ["hello", "hi", "good morning", "good afternoon"]):
        intent = "Greeting"
    elif concern == "Complaint":
        intent = "Make Complaint"
    elif concern == "Account or System Issue":
        intent = "Report System Problem"
    elif concern == "Contact Agent":
        intent = "Request Human Agent"
    elif concern == "Joining Campaign":
        intent = "Join Campaign"
    elif concern in {"Campaign or Promotion", "Campaign Eligibility", "Campaign Reward"}:
        intent = "Ask Campaign Information"
    elif concern in {"Insurance Claim", "Claim Status"}:
        intent = "Submit or Check Insurance Claim"
    elif concern == "Insurance Coverage":
        intent = "Ask Insurance Coverage"
    elif concern in {"Late Payment", "Outstanding Balance", "Debt or Collection"}:
        intent = "Report Payment Problem"
    elif concern in {"Monthly Installment", "Payment Method", "Insurance Premium", "Early Repayment"}:
        intent = "Ask Payment Information"
    elif concern == "Application Status":
        intent = "Check Application Status"
    elif concern == "Application Process":
        intent = "Apply for Product"
    elif concern == "Required Documents":
        intent = "Ask Required Documents"
    elif concern == "Eligibility":
        intent = "Ask Eligibility"
    elif concern == "Product Conditions":
        intent = "Ask Product Conditions"
    elif concern == "Product Information":
        intent = "Ask Product Information"
    else:
        intent = "Unknown"

    if intent in {"Unknown", "Other"}:
        confidence = "Low"
    elif row.get("concern_count", 0) > 0 and (
        row.get("matched_product_keywords", "") or row.get("matched_campaign_keywords", "")
    ):
        confidence = "High"
    else:
        confidence = "Medium"

    return {"customer_intent": intent, "intent_confidence_rule": confidence}


def classify_messages(df: pd.DataFrame) -> pd.DataFrame:
    """Apply product, concern, campaign, and high-level intent rules."""

    classified = df.copy()

    product_df = classified["cleaned_message"].apply(classify_products).apply(pd.Series)
    classified = pd.concat([classified, product_df], axis=1)

    concern_df = classified["cleaned_message"].apply(classify_concerns).apply(pd.Series)
    classified = pd.concat([classified, concern_df], axis=1)

    campaign_df = classified.apply(classify_campaign, axis=1).apply(pd.Series)
    classified = pd.concat([classified, campaign_df], axis=1)

    intent_df = classified.apply(classify_intent, axis=1).apply(pd.Series)
    classified = pd.concat([classified, intent_df], axis=1)

    return classified


def choose_primary(values: pd.Series, priority: list[str] | None = None) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip() and str(value).strip() != "Unknown"]
    if not cleaned:
        return "Unknown"
    counts = Counter(cleaned)
    max_count = max(counts.values())
    candidates = [value for value, count in counts.items() if count == max_count]
    if priority:
        for item in priority:
            if item in candidates:
                return item
    return sorted(candidates)[0]
