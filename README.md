# ✈️ Trip Expense Tracker

A personal travel expense tracker built with **Flask** and **SQLite**. Log expenses across multiple trips, filter by category or payment method, and export your data — all tied to your own account.

---

## Features

- **User authentication** — register, login, and logout with hashed passwords
- **Trip management** — create, edit, and delete trips with country and date range
- **Expense logging** — add expenses with category, currency, payment method, and date
- **Multi-currency support** — expenses are converted to NTD (base currency) using preset exchange rates
- **Filtering** — filter expenses by date, category, or payment method on the view page
- **CSV export** — download all your expenses as a `.csv` file
- **Country flags** — emoji flags generated from country codes

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite3 |
| Auth | Werkzeug password hashing, Flask session |
| Frontend | HTML, Jinja2, CSS |
| Export | Python `csv` + `io` modules |

---

## Project Structure

```
project/
│
├── app.py                  # Main Flask application
├── expenses.db             # SQLite database (auto-created on first run)
│
├── static/
│   ├── style.css
│   └── js/
│       ├── modal.js
│       └── display.js
│
└── templates/
    ├── index.html
    ├── login.html
    ├── register.html
    ├── newTrip.html
    ├── newExpense.html
    ├── viewExpense.html
    ├── editTrip.html
    └── editExpense.html
```


---

## Supported Countries & Currencies

| Country | Currency | Code |
|---|---|---|
| Taiwan | New Taiwanese Dollar | NTD |
| Japan | Japanese Yen | JPY |
| South Korea | Korean Won | KRW |
| Vietnam | Vietnamese Dong | VND |
| United States | US Dollar | USD |
| United Kingdom | British Pound | GBP |
| Canada | Canadian Dollar | CAD |
| Thailand | Thai Baht | THB |
| Singapore | Singapore Dollar | SGD |
| Malaysia | Malaysian Ringgit | MYR |
| Mexico | Mexican Peso | MXN |
| Austria / Ireland | Euro | EUR |

> All expenses are converted to **NTD** as the base currency for total calculations.

---

## Routes

| Method | Route | Description |
|---|---|---|
| GET/POST | `/register` | Create a new account |
| GET/POST | `/login` | Log in to your account |
| GET | `/logout` | Log out and clear session |
| GET | `/` | Home — shows visited countries and trips |
| GET/POST | `/newTrip` | Add a new trip |
| GET/POST | `/newExpense` | Add expenses to a trip |
| GET | `/viewExpense` | View and filter expenses by trip |
| GET/POST | `/editTrip/<trip_id>` | Edit a trip's name and dates |
| POST | `/deleteTrip/<trip_id>` | Delete a trip |
| GET/POST | `/editExpense/<trip_id>/<expense_id>` | Edit an expense |
| POST | `/deleteExpense/<expense_id>` | Delete an expense |
| GET | `/downloadBackup` | Download your expenses as a CSV |

---

## Security

- Passwords are hashed using **Werkzeug's** `generate_password_hash`
- All database queries are filtered by `user_id` from the server-side session — users can only access their own data
- URL parameter tampering returns empty results, not another user's data
