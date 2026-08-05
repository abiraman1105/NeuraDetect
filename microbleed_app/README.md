# NeuroScan AI — Setup Guide

## Prerequisites
- Python 3.9+
- MySQL 8.x (running locally)
- pip

---

## Step-by-Step Setup

### Step 1 — Place your model
Copy your `model.pt` file into the `model/` folder:
```
microbleed_app/
  model/
    model.pt     ← your file goes here
```

### Step 2 — Install Python dependencies
Open a terminal in the `microbleed_app/` folder and run:
```bash
pip install -r requirements.txt
```

> On Windows if mysqlclient fails:
> ```bash
> pip install mysqlclient --only-binary=mysqlclient
> ```
> Or install it via: https://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient

---

### Step 3 — Set up MySQL database
Open MySQL (via MySQL Workbench, phpMyAdmin, or terminal):
```bash
mysql -u root -p
```
Then run the schema:
```sql
source schema.sql;
```
Or copy-paste the contents of `schema.sql` into your MySQL client.

---

### Step 4 — Configure the database connection
Open `app.py` and edit lines 44–48:
```python
app.config["MYSQL_HOST"]     = "localhost"
app.config["MYSQL_USER"]     = "root"
app.config["MYSQL_PASSWORD"] = ""        # ← your MySQL root password
app.config["MYSQL_DB"]       = "microbleed_db"
```

Also edit `init_admin.py` line 11 with the same password:
```python
"passwd": "",   # ← same MySQL password
```

---

### Step 5 — Create the admin account
Run the admin setup script:
```bash
python init_admin.py
```
Follow the prompts. Default values:
- Username: `admin`
- Password: `Admin@123`
- Full name: `System Administrator`

---

### Step 6 — Run the app
```bash
python app.py
```
Visit: **http://127.0.0.1:5000**

Log in with the credentials you set in Step 5.

---

## Connecting Your Own Model
The inference logic is at the top of `app.py` (lines 10–40).

The `predict(image_path)` function returns:
```python
label  # str   — e.g. "Microbleed - Moderate"
probs  # list  — [0.01, 0.02, 0.91, 0.06]
idx    # int   — class index (0–3)
```

Class mapping (matches your model's output):
```
Index 0 → No Microbleed
Index 1 → Microbleed - Mild
Index 2 → Microbleed - Moderate
Index 3 → Microbleed - Severe
```

If your model uses different class names, edit `CLASS_NAMES` at line 17.

---

## Project Structure
```
microbleed_app/
├── app.py               Main Flask application
├── init_admin.py        Admin account creator
├── schema.sql           MySQL schema
├── requirements.txt     Python dependencies
├── model/
│   └── model.pt         ← Place your model here
├── static/
│   ├── css/main.css     All styles
│   └── uploads/         MRI images stored here
└── templates/
    ├── base.html        Layout with sidebar
    ├── login.html       Admin login page
    ├── dashboard.html   Overview + chart
    ├── upload.html      Upload + analyse
    ├── result.html      Scan result detail
    └── history.html     Paginated scan list
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: MySQLdb` | `pip install mysqlclient` |
| `Access denied for user root` | Check MySQL password in `app.py` |
| `Table doesn't exist` | Re-run `schema.sql` in MySQL |
| Model not loading | Ensure `model/model.pt` exists; app runs in demo mode otherwise |
| Port already in use | Change `port=5000` at bottom of `app.py` |
