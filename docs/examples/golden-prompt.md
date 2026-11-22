# Golden prompt example (Phase 3)

Illustrative grounded prompt for Groq ranking. Compact candidate JSON only —
no `raw` fields. Model must return JSON matching the schema in the system
message.

## System

```text
You are a restaurant recommendation assistant.
Rank restaurants ONLY from the provided candidate list. Never invent venues,
ids, names, cuisines, ratings, or costs that are not in the candidates.
…
Respond with JSON only — no markdown fences, no prose before or after.
```

(Full text lives in `recommender.prompts.SYSTEM_PROMPT`.)

## User (example)

```json
{
  "task": "Rank up to 2 restaurants from candidates that best match the preferences. Return JSON only.",
  "preferences": {
    "location": "Bangalore",
    "budget": "medium",
    "cuisine": "Chinese",
    "min_rating": 4.0,
    "top_k": 2,
    "additional_preferences": "family-friendly"
  },
  "candidates": [
    {
      "restaurant_id": "id-a",
      "name": "Alpha",
      "location": "Koramangala, Bangalore",
      "cuisines": ["Chinese", "Asian"],
      "cost": 500.0,
      "cost_band": "medium",
      "rating": 4.5,
      "votes": 200
    },
    {
      "restaurant_id": "id-b",
      "name": "Beta",
      "location": "Indiranagar, Bangalore",
      "cuisines": ["Italian", "Continental"],
      "cost": 450.0,
      "cost_band": "medium",
      "rating": 4.1,
      "votes": 80
    }
  ]
}
```

## Expected model JSON (shape)

```json
{
  "summary": "Strong Chinese options within medium budget.",
  "recommendations": [
    {
      "restaurant_id": "id-a",
      "name": "Alpha",
      "rank": 1,
      "cuisine": "Chinese, Asian",
      "rating": 4.5,
      "estimated_cost": 500,
      "explanation": "Matches Chinese + medium budget with the highest rating in the shortlist."
    },
    {
      "restaurant_id": "id-b",
      "name": "Beta",
      "rank": 2,
      "cuisine": "Italian, Continental",
      "rating": 4.1,
      "estimated_cost": 450,
      "explanation": "In-budget backup with solid rating if you want variety."
    }
  ]
}
```

Any `restaurant_id` not in `candidates` is dropped by `ResponseParser`.
