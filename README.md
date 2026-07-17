# Lost & Found Portal

A full-stack Lost & Found web portal: report lost or found items, browse and
filter reports in real time, claim items, and analyze activity in Power BI.

**Stack:** Flask (Python) · MySQL · HTML/CSS/JS (vanilla, AJAX) · Power BI (analytics)

---

## 1. Features

- User accounts (register / login / logout) with hashed passwords
- Report a **lost** item or a **found** item, with photo upload
- Dynamic **browse & search** page — filters by type, category, location,
  status and keyword update results instantly via AJAX (no page reload)
- Item detail page with a **claim** workflow:
  - Anyone can submit a claim on an open item
  - The original reporter can accept or reject claims from their dashboard/item page
  - Accepting a claim automatically marks the item **resolved**
- Personal **dashboard**: your reports, claims received, claims you've sent
- REST-style JSON API (`/api/items`, `/api/stats`) that also powers Power BI
- CSV export endpoint for one-click Power BI import
- Responsive, accessible UI with a distinct "claim-tag" visual design
- Proper error pages (404 / 403 / 500)

---

## 2. Project structure

```
lostfound/
├── app.py                 # Flask application & all routes
├── config.py               # Config (reads from environment variables)
├── db.py                    # MySQL connection pool + query helper
├── models.py                # User model (Flask-Login)
├── requirements.txt
├── database/
│   ├── schema.sql           # Creates database, tables, and analytics view
│   └── seed.sql              # Optional sample data (demo login included)
├── templates/                # Jinja2 templates (all pages)
├── static/
│   ├── css/style.css         # Design system + all styling
│   ├── js/main.js             # AJAX browse/filter, previews, small UI logic
│   └── uploads/                # Uploaded item photos land here
└── README.md
```

---

## 3. Prerequisites

- Python 3.9+
- MySQL 8.x (or MariaDB 10.x) server running locally or remotely
- pip

---

## 4. Setup

### 4.1 Clone / unzip the project, then create a virtual environment

```bash
cd lostfound
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4.2 Create the database

Log into MySQL and run the schema file:

```bash
mysql -u root -p < database/schema.sql
```

This creates the `lost_found_db` database, three tables (`users`, `items`,
`claims`) and an analytics view (`vw_items_report`) used for reporting.

Optionally load sample data:

```bash
mysql -u root -p < database/seed.sql
```

This adds two demo users you can log in with immediately:

| Email | Password |
|---|---|
| aarav@example.com | Password123 |
| meera@example.com | Password123 |

### 4.3 Configure environment variables

The app reads DB credentials from environment variables (see `config.py`
for defaults). Set them to match your MySQL setup:

```bash
export SECRET_KEY="change-this-to-something-random"
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_mysql_password
export MYSQL_DB=lost_found_db
```

On Windows (PowerShell):
```powershell
$env:MYSQL_PASSWORD="your_mysql_password"
```

> Tip: create a `.env` file and load it with `python-dotenv` if you prefer —
> it's already included in `requirements.txt`. Just add
> `from dotenv import load_dotenv; load_dotenv()` at the top of `app.py`.

### 4.4 Run the app

```bash
python app.py
```

Visit **http://localhost:5000** in your browser.

---

## 5. How the dynamic parts work

- `templates/browse.html` renders an empty grid and a filter form.
- `static/js/main.js` listens for input on that form, builds a query string,
  and calls `GET /api/items` — the Flask route runs a parameterized SQL
  query and returns JSON. Results are rendered into item cards client-side,
  so filtering never triggers a full page reload.
- The homepage's live counters (`hero-stats`) animate on load using the
  same pattern with plain JS (`animateCounters()`), fed by server-rendered
  initial values from `/`.

---

## 6. Power BI integration

There are two supported ways to bring this data into Power BI:

### Option A — Direct MySQL connection (recommended, live data)

1. Open **Power BI Desktop** → **Get Data** → search for **MySQL database**.
2. Server: `<your MySQL host>` (e.g. `localhost:3306`)
   Database: `lost_found_db`
3. Use your MySQL username/password when prompted.
4. Power BI will show all tables — select `vw_items_report` (a pre-built,
   flattened view combining items + reporter name + claim counts) for the
   cleanest starting point, or pull `items`, `users`, `claims` directly and
   build your own relationships.
5. Click **Load**, then build visuals: lost vs. found over time, items by
   category, resolution rate (`status = 'resolved'` vs total), items by
   location, etc.
6. Set a **scheduled refresh** in the Power BI service so your dashboard
   stays current (requires the on-premises data gateway if MySQL isn't
   publicly reachable).

> Note: Power BI Desktop needs the **MySQL Connector/NET** (or the
> MySQL ODBC driver) installed locally for this connector to work —
> Power BI will prompt you to install it the first time if missing.

### Option B — CSV import (quick, no drivers needed)

1. With the Flask app running, visit:
   `http://localhost:5000/export/items.csv`
   (or click **"Export data (CSV)"** in the site footer)
2. Save the file, then in Power BI: **Get Data → Text/CSV**, and pick the
   downloaded file.
3. This is a one-time snapshot; re-download and re-import to refresh, or
   point Power BI's **Web** connector directly at that URL for a
   refreshable source (no login required on that endpoint by default —
   consider restricting it if you deploy publicly).

### What's in the analytics view

`vw_items_report` (and the `/api/stats` JSON endpoint) expose:
- item id, type (lost/found), title, category, location, status, created date
- who reported it
- how many claims it has received

Good starter visuals: a stacked column of lost vs. found per month, a donut
of items by status, a table of open items by location, and a KPI card for
resolution rate.

---

## 7. Security notes for production use

- Change `SECRET_KEY` to a long random value and never commit it.
- Set `debug=False` in `app.run()` before deploying.
- Serve behind a real web server (gunicorn/uWSGI + Nginx), not the Flask dev server.
- Restrict `/export/items.csv` (e.g. require login) if the database contains
  sensitive contact information you don't want publicly downloadable.
- Validate/resize uploaded images and consider a max upload count per user
  if opening this up publicly.

---

## 8. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `mysql.connector.errors.InterfaceError: 2003` | MySQL isn't running, or host/port in your env vars is wrong |
| `Access denied for user` | Wrong `MYSQL_USER` / `MYSQL_PASSWORD` |
| `Unknown database 'lost_found_db'` | Run `database/schema.sql` first |
| Images don't show after upload | Check `static/uploads/` exists and is writable |
| Login says "Invalid email or password" for seed users | Make sure you loaded `seed.sql` **after** `schema.sql`, and are using password `Password123` |

---

Built with Flask, MySQL, vanilla JS, and a claim-ticket-inspired design system.
