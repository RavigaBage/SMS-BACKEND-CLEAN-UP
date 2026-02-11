# School Management System Backend

---
# Django Project Setup Guide

This repository contains a Django application that uses environment-based configuration.
Follow the steps below to set up and run the project locally or in production

---

## Prerequisites

Ensure you have the following installed:

* Python **3.9+** (or the version required by your project)
* pip
* virtualenv (recommended)
* PostgreSQL / MySQL / SQLite (depending on project configuration)
* Git

---

## Project Structure (Relevant Files)

```
.
├── apps
├── config
├── requirements/
│   └── base.txt
├── .env.development
├── .env.production
├── manage.py
└── README.md
```

---

## 1. Clone the Repository

```bash
git clone <repository-url>
cd <project-directory>
```

---

## 2. Create and Activate a Virtual Environment

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

All required libraries are defined in `requirements/base.txt`.

```bash
pip install -r requirements/base.txt
```

---

## 4. Environment Configuration

The project requires **environment-specific variables**.

### Required Files
Create the following file and folder

* `.env` → for environment variables

* `/static` 

### Example `.env`

```env
# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
ENVIRONMENT=production

# Database
DB_NAME=school_db
DB_USER=school_user
DB_PASSWORD=secure_password_here
DB_HOST=db
DB_PORT=3306
DB_ROOT_PASSWORD=root_password_here

# Security
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
CSRF_TRUSTED_ORIGINS=http://localhost:8000

# Email (Optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Superuser Credentials (IMPORTANT!)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@yourschool.com
DJANGO_SUPERUSER_PASSWORD=YourSecurePassword123!
DJANGO_SUPERUSER_ROLE=admin

```




## 👤 Creating Default Superuser

### Method 1: Using Custom Management Command (Recommended)

The project includes a custom management command that automatically creates a superuser if one doesn't exist.

```bash
python manage.py create_superuser
```

**What this does:**
- Checks if a superuser with the specified username exists
- Creates one if it doesn't exist
- Uses environment variables for credentials
- Assigns the ADMIN role automatically
- Safe to run multiple times (won't create duplicates)

### Method 2: Using Django's Built-in Command

If environment variables are set, you can also use:

```bash
python manage.py createsuperuser --noinput
```

### Method 3: Interactive Creation (Development Only)

For local development, you can create a superuser interactively:

```bash
python manage.py createsuperuser
```

Then follow the prompts to enter username, email, password, and role.

---


> ⚠️ **Never commit `.env` files to version control.**
> Ensure they are listed in `.gitignore`.

---

and run

`python manage.py migrate`

but if migrations is neccessary then;

Run the following commands to prepare the database:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 6. Create a Superuser (Admin Access)

To access the Django admin panel:

```bash
python manage.py createsuperuser
```

Follow the prompts to set:

* Username
* Email
* Password

---

You can also seed the database with minimal data by running

`python ./scripts/create_test_data.py`

The script will create 
- Admin
- Subjects
- Academic year

## 7. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at:

```
http://127.0.0.1:8000/
```

Admin panel:

```
http://127.0.0.1:8000/admin/
```

Swagger API Docs:

```
http://127.0.0.1:8000/api/docs
```
---

## Notes

* Always activate the virtual environment before running commands
* Keep environment variables secure
* Update `requirements/base.txt` when adding new dependencies

---
