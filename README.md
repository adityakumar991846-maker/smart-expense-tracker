# Smart Expense Tracker

A full-stack expense management web application built with Django REST Framework, MySQL, JavaScript, and local Tesseract OCR. It supports manual expense tracking and extracting payment details from user-uploaded Google Pay and UPI payment screenshots.

> **Privacy and Security:** This application does not directly access Google Pay or bank accounts. It processes screenshots uploaded by the user. It does not require banking credentials or direct access to private payment APIs. OCR is performed locally using Tesseract rather than a third-party OCR cloud service.

## 1. Features

### Receipt OCR
- Extracts payment amount, merchant or receiver, date, time, payment status, payment method, UPI transaction ID, Google transaction ID, bank name, and UPI ID (VPA), where available.
- Uses local Tesseract OCR with image preprocessing and rule-based parsing.
- Provides an editable confirmation screen before saving an expense.
- Handles missing amounts safely by warning the user instead of silently saving an incorrect amount.
- Suggests expense categories based on merchant information.

### Duplicate Detection
- Checks transaction identifiers and other transaction details for potential duplicates.
- Helps prevent accidental double-counting.
- Supports reviewing duplicate warnings before saving.

### Expense Management
- Add expenses manually or through receipt scanning.
- Search, filter, sort, view, and delete expenses.
- Filter by category, payment method, and date range.
- Keep user expense records isolated through authenticated backend operations.

### Dashboard and Analytics
- View total spending, monthly spending, today's spending, transaction count, and highest expense.
- Visualize monthly spending trends and category distribution.
- Track monthly budget progress and receive threshold warnings.

### Reports and Export
- Generate daily, weekly, monthly, and custom-period reports.
- Review average expense, highest expense, transaction count, and total amount.
- Export authenticated users' expense data to CSV.

### Authentication and Security
- Token-based REST API authentication.
- Django password hashing.
- Input validation on the frontend and backend.
- Configurable CORS and security settings.

## 2. Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, Django, Django REST Framework |
| Database | MySQL 8.4 |
| Frontend | HTML5, CSS3, Vanilla JavaScript, Bootstrap 5.3 |
| Charts | Chart.js |
| OCR | Tesseract OCR, pytesseract, Pillow |
| Database connectivity | PyMySQL |
| API support | Django REST Framework, django-cors-headers |

## 3. Project Structure

```text
smart-expense-tracker/
├── backend/
│   ├── config/
│   ├── accounts/
│   ├── categories/
│   ├── expenses/
│   ├── dashboard/
│   ├── ocr/
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── expenses.html
│   ├── add-expense.html
│   ├── scan-payment.html
│   ├── reports.html
│   ├── profile.html
│   ├── css/
│   └── js/
├── package.json
├── package-lock.json
└── README.md
```

## 4. Requirements

Install the following before setting up the project:

- Python 3.10 or a compatible version supported by the project dependencies.
- MySQL Server.
- Node.js and npm.
- Tesseract OCR.

### Install Tesseract OCR

**Windows**

Install Tesseract using the [UB Mannheim Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki).

The usual executable path is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Add its installation directory to your Windows PATH, or configure `TESSERACT_CMD` if supported by your project settings.

**Ubuntu/Debian**

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
```

**macOS**

```bash
brew install tesseract
```

## 5. Installation and Setup

Run commands from the project root unless otherwise specified.

### A. Clone the repository

```bash
git clone https://github.com/adityakumar991846-maker/smart-expense-tracker.git
cd smart-expense-tracker
```

If your downloaded repository contains an additional nested `smart-expense-tracker` directory, enter the directory that contains `backend/manage.py` and `package.json`.

### B. Set up the Python environment

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Windows Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

Install backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

### C. Configure environment variables

Create `backend/.env` by copying `backend/.env.example`. On Windows PowerShell:

```powershell
Copy-Item backend/.env.example backend/.env
```

Edit `backend/.env` and configure the values required by your `backend/config/settings.py`:

```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=smart_expense_tracker
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Replace the example password with your own local MySQL password. Configure any other required settings from `.env.example`.

**Security:** Never commit `.env` files, database passwords, Django secret keys, or API credentials to GitHub. Keep local secrets excluded by `.gitignore`.

### D. Create the MySQL database

Connect to MySQL and run:

```sql
CREATE DATABASE smart_expense_tracker
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

If the database already exists, do not recreate or reset it.

### E. Apply migrations

From the project root:

```bash
python backend/manage.py migrate
```

Check the Django configuration:

```bash
python backend/manage.py check
```

### F. Start the backend

```bash
python backend/manage.py runserver 127.0.0.1:8008
```

Keep this terminal open.

### G. Install and start the frontend

Open a second terminal at the project root:

```bash
npm install
npm run dev
```

Open the URL printed by Vite. In the current development setup, the expected URL is:

http://127.0.0.1:3000/

If Vite selects another port, use the URL shown in the terminal.

Register an account, sign in, and begin adding expenses or scanning payment screenshots.

## 6. API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Register a user |
| POST | `/api/auth/login/` | Authenticate a user |
| POST | `/api/auth/logout/` | Log out |
| GET / PUT | `/api/auth/profile/` | View or update profile |
| POST | `/api/auth/change-password/` | Change password |
| GET / POST | `/api/categories/` | List or create categories |
| GET / POST | `/api/expenses/` | List or create expenses |
| GET / PUT / DELETE | `/api/expenses/<id>/` | Retrieve, update, or delete an expense |
| POST | `/api/expenses/check-duplicate/` | Check for potential duplicates |
| POST | `/api/ocr/analyze/` | Analyze an uploaded payment screenshot |
| POST | `/api/ocr/confirm/` | Validate and save a confirmed OCR transaction |
| GET | `/api/dashboard/summary/` | Retrieve dashboard summary |
| GET | `/api/dashboard/category-summary/` | Retrieve category totals |
| GET | `/api/dashboard/monthly-summary/` | Retrieve monthly totals |
| GET | `/api/reports/` | Generate expense reports |

Authentication and request formats depend on the endpoint configuration. Consult the backend code for exact request and response schemas.

## 7. Automated Testing

Run the OCR tests:

```bash
python backend/manage.py test ocr --verbosity 1
```

Run the broader test suite:

```bash
python backend/manage.py test accounts expenses dashboard ocr
```

The OCR regression tests include cases for payment amount extraction, missing amounts, and avoiding confusion between payment amounts and account suffixes.

Run the frontend build:

```bash
npm run build
```

Record the actual test counts and results from your current environment before publishing a release. Do not assume that earlier test counts still describe the current code.

## 8. OCR Workflow

1. The user uploads a payment confirmation screenshot.
2. Tesseract OCR extracts text locally.
3. The backend parser identifies available payment details.
4. The confirmation screen displays extracted fields for review and editing.
5. Missing or invalid amounts must be resolved before submission.
6. The user confirms the details.
7. The backend validates the transaction and checks for potential duplicates before saving.

OCR results can vary with screenshot quality and layout. Always verify the extracted information before confirming an expense.

## 9. Limitations

- OCR accuracy depends on image quality and receipt layout.
- Some fields may be unavailable or unreadable on particular receipts.
- The application does not directly retrieve transactions from a Google Pay or bank account.
- The application requires a configured backend, database, and local OCR engine.

## 10. Future Improvements

- Improve automatic category suggestions.
- Add more receipt layouts and OCR regression fixtures.
- Expand analytics and budget insights.
- Improve deployment documentation and production security configuration.

## 11. License

Check the repository's `LICENSE` file for the applicable license terms.

## Author

**Aditya Maddheshiya**

GitHub: [adityakumar991846-maker](https://github.com/adityakumar991846-maker)
