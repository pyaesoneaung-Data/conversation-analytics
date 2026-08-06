# Keyword Search Process

## Purpose

Keyword search was used as a baseline method to analyze
customer-chatbot conversations in the loan and insurance domain.

The goal was to convert message text into structured information about:

- Product mentions
- Product types
- Customer concerns
- Reasons for contacting the chatbot
- Product conditions and requirements
- Payment and application questions
- Campaign-related questions
- Campaign joining interest
- System issues
- Complaints

## Input Data

The process used the cleaned dataset created during preprocessing.

The field `message_english` was kept for reviewing the original
English-translated message.

Keyword rules were applied to `cleaned_message`, which contains a
normalized version of the message text.

Roles were standardized into:

- Customer
- Chatbot
- Agent
- System
- Unknown

Customer-demand summaries mainly used customer messages.

The full message-level output still included all cleaned messages.

## Method

The keyword-search method was rule-based and did not use machine
learning.

The text-processing steps included:

- Converting text to lowercase
- Removing unnecessary spaces
- Removing placeholders
- Limiting unnecessary punctuation
- Matching keywords and phrases
- Using regular expressions

The project defined keyword dictionaries for:

- Products
- Customer concerns
- Campaigns
- Product conditions
- Payments
- Applications
- Complaints
- System issues

One message could match more than one category.

The process recorded matched keywords and created:

- A primary product
- A primary concern
- Secondary concerns
- A customer intent
- Campaign-related classifications

Campaign messages were detected using both `cleaned_message` and
`detected_ad_name` when available.

## Main Output Fields

The main structured fields included:

- `industry_category`
- `product_category`
- `product_subcategory`
- `primary_concern`
- `secondary_concerns`
- `customer_intent`
- `is_campaign_related`
- `campaign_question_type`
- `campaign_related_product`
- `campaign_joining_intent`

## Message-Level Analysis

Message-level analysis created one classified row for each message.

This level is useful for:

- Reviewing individual messages
- Checking matched keywords
- Counting message topics
- Filtering detailed Power BI visuals

## Conversation-Level Analysis

Conversation-level analysis grouped messages by `userID`.

It summarized:

- Products mentioned
- Customer concerns
- Customer intents
- Campaign status
- Complaint flags
- Payment concerns
- Application concerns
- System issues

This helped reduce overcounting when one customer sent many messages.

A limitation is that `userID` was used as the conversation identifier
because the dataset did not include a separate conversation-session ID.

## Power BI Output Files

The results were exported to:

`data/processed/powerbi/`

### `message_level_analytics.csv`

Contains one classified row per message.

It is used for detailed review, filtering, and message-level charts.

### `conversation_level_analytics.csv`

Contains one summarized row per `userID`.

It is used for customer-level and conversation-level analysis.

### `concern_summary.csv`

Summarizes message counts and customer coverage by primary concern.

### `product_summary.csv`

Summarizes products, industries, and their main concerns.

### `campaign_summary.csv`

Summarizes campaign questions, related products, and joining intent.

### `monthly_trend_summary.csv`

Summarizes monthly trends by industry, concern, and intent.

### `keyword_match_review.csv`

Contains messages selected for quality review, including:

- Low-confidence classifications
- Multi-category messages
- Sampled customer messages

## Why Keyword Search Was Used

Keyword search was selected because it is:

- Simple to implement
- Fast to run
- Easy to explain
- Transparent
- Easy to update
- Useful as a baseline
- Suitable for creating Power BI columns

It also allows comparison with the team's intent-classification and
embedding-based approaches.

## Advantages

The main advantages are:

- No model training is required
- Matched keywords can be reviewed
- Rules can be changed easily
- Results are explainable
- Processing is relatively fast
- Outputs are easy to use in Power BI

## Limitations

The method also has several limitations:

- It may miss spelling variations
- It may miss unclear wording
- It may miss words outside the keyword dictionaries
- Broad keywords may create false matches
- The same word may have different meanings
- Some messages may remain `Unknown`
- Translation quality may affect matching
- Campaign names may be technical
- `userID` may not represent a true conversation session

Keyword search does not understand context as well as a trained intent
model or embedding-based method.

## Quality Checks

The results were checked by:

- Reviewing matched keywords
- Creating `keyword_match_review.csv`
- Reviewing low-confidence messages
- Reviewing messages with multiple categories
- Checking duplicate message IDs
- Checking classification coverage
- Checking `Unknown` percentages
- Validating date formats before Power BI export

## Final Outcome

The keyword-search process transformed unstructured customer messages
into structured fields that could be summarized and visualized in
Power BI.

The results should be treated as a baseline.

They can be improved by:

- Refining the keyword dictionaries
- Adding more phrases and spelling variations
- Reviewing false matches
- Comparing results with intent classification
- Comparing results with embedding-based methods