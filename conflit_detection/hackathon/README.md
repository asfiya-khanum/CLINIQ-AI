# Patient Record Reconciliation Agent

An agent that compares old and new patient records and detects conflicts.

## Problem
Old record says Diabetes, new record says No Diabetes. Which one is correct? This agent catches such mismatches.

## How it Works
- If diagnosis is same -> SAFE
- If diagnosis is different -> CONFLICT

## How to Run
python -m pytest test_reconciliation.py -v

## Example
purana = {"diagnosis": "Diabetes"}
naya = {"diagnosis": "No Diabetes"}
Result = CONFLICT
