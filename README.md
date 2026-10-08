# Smart Expense Tracker

A modern, full-stack Expense Tracker web application with manual expense tracking and automated receipt extraction from user-uploaded **Google Pay and UPI payment confirmation screenshots** using local Tesseract OCR.

> **Privacy & Security Notice:**
> **This application does not directly access Google Pay or bank accounts. It reads payment information strictly from screenshots uploaded by the user.** No banking credentials, phone notifications, private APIs, SMS messages, or financial credentials are ever accessed. All OCR processing occurs locally on the server without communicating with external third-party AI or OCR clouds.

---

## 1. Features

- **Automated Google Pay & UPI Screenshot OCR:**
  - Extracts transaction Amount, Merchant/Receiver, Date, Time, Payment Status, Payment Method, UPI Transaction ID (12-digit), Google Transaction ID, Bank Name, and UPI ID (VPA).
  - Intelligent merchant-to-category suggestion (e.g. Swiggy/Zomato → Food, Uber/Ola → Travel, Amazon/Flipkart → Shopping, Airtel/Electricity → Bills).
  - Review screen before saving: **every single field is fully editable** before confirming.
- **Accidental Duplicate Detection:**
  - Prevents double-counting by detecting matching UPI Transaction IDs, Google Transaction IDs, or composite match `(User, Amount, Merchant, Date)`.
  - Gives users the option to cancel or "Save Anyway".
- **Complete Expense Management:**
  - Manual expense creation with date, time, category, payment method, and notes.
  - Search by merchant or notes with debounce.
  - Category, payment method, date range, and multi-parameter sorting (newest, oldest, highest/lowest amount).
  - View detailed transaction metadata modal and delete records.
  - Strict user-level data isolation (IDOR protection).
- **Interactive Dashboard & Analytics:**
  - Financial summary cards: Total Spent, This Month, Today, Transactions Count, Highest Expense.
  - Monthly spending trend bar chart powered by Chart.js.
  - Category distribution doughnut chart powered by Chart.js.
  - Monthly budget limit progress bar with automatic 80% threshold warning alert.
- **Reports & Data Export:**
  - Breakdown by Daily, Weekly, Monthly, or Custom Date Range.
  - Summary metrics: Average Expense, Highest Expense, Total Count, and Total Amount.
  - Instant **CSV Export** containing only the authenticated user's records.
- **Robust Security & User Authentication:**
  - Token-based REST authentication.
  - Password hashing via Django PBKDF2.
  - Input validation on both client and backend.
  - CSRF and CORS configuration.

---

## 2. Technology Stack

- **Backend:** Python, Django 5.0, Django REST Framework, django-cors-headers, PyMySQL.
- **Database:** MySQL (with fallback support for local development).
- **OCR Engine:** Tesseract OCR (v5.3+), `pytesseract`, Pillow (PIL).
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js.

---

## 3. Project Directory Structure

```
.
├── backend/
│   ├── config/             # Django project settings, WSGI/ASGI, root URLs
│   ├── accounts/           # User authentication, registration, profiles
│   ├── categories/         # System default and user-custom categories
│   ├── expenses/           # Expense models, filtering, search, pagination
│   ├── dashboard/          # Metric summaries, monthly trends, and CSV reports
│   ├── ocr/                # Tesseract OCR engine, regex parser, screenshot endpoints
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html          # Authentication router & landing
│   ├── login.html          # Sign In page
│   ├── register.html       # Sign Up page
│   ├── dashboard.html      # Analytics dashboard with Chart.js
│   ├── expenses.html       # Searchable & filterable expense table with view modal
│   ├── add-expense.html    # Manual expense entry form
│   ├── scan-payment.html   # Screenshot dropzone & OCR confirmation interface
│   ├── reports.html        # Analytics reports & CSV export
│   ├── profile.html        # Budget setting and password management
│   ├── css/                # style.css, auth.css, dashboard.css, responsive.css
│   └── js/                 # api.js, auth.js, ocr.js, dashboard.js, reports.js
└── README.md
```

---

## 4. Installation & Setup

### A. Prerequisites
1. **Python 3.10+**
2. **MySQL Server** (or local development database)
3. **Tesseract OCR**

#### Installing Tesseract OCR:
- **Ubuntu/Debian:**
  ```bash
  sudo apt-get update
  sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
  ```
- **macOS:**
  ```bash
  brew install tesseract
  ```
- **Windows:**
  - Download and run the installer from: [UB-Mannheim Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki).
  - Default installation path: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
  - Add `C:\Program Files\Tesseract-OCR` to your Windows System `PATH` or set `TESSERACT_CMD` in your `.env` file:
    ```env
    TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
    ```

---

### B. Backend Setup
1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Configure Environment Variables:
   Copy `.env.example` to `.env` in the `backend/` directory:
   ```bash
   cp backend/.env.example backend/.env
   ```

   Configure MySQL connection in `backend/.env`:
   ```env
   SECRET_KEY=your-secure-django-secret-key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

   DB_ENGINE=django.db.backends.mysql
   DB_NAME=smart_expense_tracker
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_HOST=127.0.0.1
   DB_PORT=3306

   TESSERACT_CMD=tesseract
   ```

4. Create MySQL database:
   ```sql
   CREATE DATABASE smart_expense_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

5. Run Migrations:
   ```bash
   python backend/manage.py makemigrations
   python backend/manage.py migrate
   ```

6. Start Django Server:
   ```bash
   python backend/manage.py runserver 127.0.0.1:8008
   ```

---

### C. Frontend Setup
The frontend is built with clean vanilla JavaScript and HTML5.
When running with the dev server proxy or a static web server:
- Open `http://localhost:3000/frontend/login.html` (or `http://localhost:3000/`).
- Sign up for a new account.
- Sign in to explore the dashboard.

---

## 5. API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register/` | Register new user account |
| `POST` | `/api/auth/login/` | Log in with email & password, returns Token |
| `POST` | `/api/auth/logout/` | Invalidate current user session |
| `GET` / `PUT` | `/api/auth/profile/` | Retrieve or update user budget & profile |
| `POST` | `/api/auth/change-password/` | Change account password |
| `GET` | `/api/categories/` | List default & custom categories |
| `POST` | `/api/categories/` | Create a new custom category |
| `GET` | `/api/expenses/` | Filter, search, sort, and paginate expenses |
| `POST` | `/api/expenses/` | Create a manual expense |
| `GET` / `PUT` / `DELETE` | `/api/expenses/<id>/` | Retrieve, update, or delete specific expense |
| `POST` | `/api/expenses/check-duplicate/` | Check duplicate transaction identifiers |
| `POST` | `/api/ocr/analyze/` | Upload screenshot & extract transaction JSON |
| `POST` | `/api/ocr/confirm/` | Confirm, validate, and save OCR transaction |
| `GET` | `/api/dashboard/summary/` | Overview metrics, budget status, recent expenses |
| `GET` | `/api/dashboard/category-summary/` | Category spending aggregations |
| `GET` | `/api/dashboard/monthly-summary/` | 6-month spending trends |
| `GET` | `/api/reports/` | Period report or CSV export (`?export=csv`) |

---

## 6. Automated Testing

To run the complete automated test suite (19 tests covering authentication, user isolation, IDOR prevention, expense CRUD, OCR parsing, duplicate checks, budget warnings, and CSV export):

```bash
python backend/manage.py test accounts expenses dashboard ocr
```

Output:
```
Ran 19 tests in 10.573s
OK
System check identified no issues (0 silenced).
```
