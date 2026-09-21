# Spend Tracker Design

A simple expense tracker with APIs to add expense, view all expenses by category and date filters and a summary endpoint to provide a short summary on expenses by category, spend amount and month over month change

## 1. Scope:
### Must:

- 3 endpoints 
    - `POST /expenses` - add expense
    - `GET /expenses` - fetch all expenses
    - `GET /summary` - Generate summary on category and spend amount
- Minimal UI
    - Can add, view expenses and display summaries
    - Display month over month change

### Bonus:

- API Key - Single User
- Deployed to Render or Railway
- Flag spends in a category that exceeds 20% of previous month

### Out of Scope

- JWT / Multi User

### Assumptions

- Single user
- INR Only 

## 2. Data Model

```
Table Name: Expenses

Columns:

- id            UUID PRIMARY KEY
- amount        INTEGER NOT NULL, > 0 
- category      STRING NOT NULL
- note          STRING 
- spent_on      ISO TEXT NOT NULL
- created_at    ISO TEXT NOT NULL

indexes : date, category
```

## 3. API Contract

### `POST /expenses`

#### Request:

```json
{
    "amount": 100,
    "category": "medicine",
    "note": "fever medicines",
    "spent_on": "21-09-2026"
}
```

#### Response:

```
201 - {"id": "12345678-1234-5678-1234-567812345678", message: "Expense added successfully"}
```

### `GET /expenses`

`request`:
```
GET /expenses?category=food&category=medicine&date_from=2026-09-01&date_to=2026-09-10&limit=50&offset=0
```

#### Response:

`200`:
```json

{"expenses": [
    {
        "amount_paise": 10000,
        "category": "food",
        "note": null,
        "date": "21-09-2026"
    }
]}

```

### `GET /summary`

