# AI-Powered Restaurant Recommendation System (Zomato Use Case)

## Project Overview

Build an AI-powered restaurant recommendation service inspired by Zomato. The system should intelligently suggest restaurants based on user preferences by combining structured restaurant data with a Large Language Model (LLM).

This document is the source of truth for project context: goals, workflow, inputs/outputs, and expected behavior.

## Objective

Design and implement an application that:

1. Takes user preferences (location, budget, cuisine, ratings, and optional extras)
2. Uses a real-world dataset of restaurants
3. Leverages an LLM to generate personalized, human-like recommendations
4. Displays clear and useful results to the user

## Dataset

- **Source:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) on Hugging Face
- **Relevant fields (examples):**
  - Restaurant name
  - Location
  - Cuisine
  - Cost / price range
  - Rating
  - Other attributes useful for filtering or explanation (e.g., votes, service notes)

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face
- Extract and normalize relevant fields (name, location, cuisine, cost, rating, etc.)
- Prepare data so it can be filtered efficiently against user preferences

### 2. User Input

Collect user preferences such as:

| Preference | Example | Notes |
|---|---|---|
| Location | Bangalore | City / area filter |
| Budget | low, medium, high | Map to cost ranges in the dataset |
| Cuisine | Italian, Chinese | Primary cuisine preference |
| Minimum rating | e.g. 4.0 | Soft or hard filter |
| Additional preferences | family-friendly, quick service | Free-text or structured extras for the LLM |

### 3. Integration Layer

- Filter and prepare relevant restaurant data based on user input
- Pass structured candidate results into an LLM prompt
- Design a prompt that helps the LLM reason about fit and rank options

### 4. Recommendation Engine

Use the LLM to:

- Rank restaurants against the user's preferences
- Provide explanations (why each recommendation fits)
- Optionally summarize the overall set of choices

### 5. Output Display

Present top recommendations in a user-friendly format, including at least:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation

## High-Level Architecture

```text
User Preferences
       │
       ▼
┌──────────────────┐
│  Data Ingestion  │  ← Hugging Face Zomato dataset
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Filter / Rank    │  ← Structured filtering by location, budget, cuisine, rating
│ Candidates       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ LLM Prompting    │  ← Personalized ranking + explanations
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Result Display   │  ← Name, cuisine, rating, cost, explanation
└──────────────────┘
```

## Success Criteria

- User can specify preferences and receive ranked restaurant recommendations
- Recommendations are grounded in real dataset records (not invented restaurants)
- Each recommendation includes a clear AI-generated explanation
- Output is readable and useful for decision-making

## Out of Scope (Initial Version)

Unless explicitly added later:

- Real-time booking / reservations
- Live delivery or order placement
- User accounts, history, or collaborative filtering
- Production-scale search infrastructure beyond dataset filtering + LLM ranking

## Interfaces

- **CLI** (`app/main.py` / `zomato-recommend`) — primary v1 entrypoint
- **Streamlit UI** (`app/streamlit_app.py`, optional) — same `RecommendationService`; preference form + recommendation cards

## Project Context Notes

- This is a learning / prototype project (`zomato-m11`) focused on combining structured data filtering with LLM reasoning.
- Prefer grounding LLM output in filtered dataset candidates to reduce hallucination.
- Prompt design is a core part of the deliverable: ranking logic and explanations should be intentional, not generic.
