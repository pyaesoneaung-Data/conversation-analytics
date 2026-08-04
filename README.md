# Conversation Analytics for Loan and Insurance Calls

## Project Overview

This university project explores conversation analytics for the loan and insurance industry. The project is currently scaffolded for future work on data cleanup, keyword search, and exploratory analysis of conversation transcripts.

No analysis code has been added yet. The current repository contains only the starter project structure, placeholder modules, and empty notebooks for future development.

## Folder Structure

```text
conversation-analytics/
├── data/
│   ├── raw/              # Store original, unmodified source data here.
│   └── processed/        # Store cleaned or transformed data here.
├── docs/                 # Project notes, references, and documentation.
├── notebooks/            # Jupyter notebooks for exploration and reporting.
├── outputs/              # Generated charts, tables, reports, or exports.
├── src/                  # Reusable Python source code.
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Installation

This project is intended to use Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## How to Run Notebooks

Start Jupyter from the project root:

```bash
jupyter notebook
```

Then open one of the starter notebooks in the `notebooks/` folder:

- `01_data_cleanup.ipynb`
- `02_keyword_search.ipynb`

The notebooks are intentionally empty except for starter comments and headings.
