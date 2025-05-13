# Booking Engine API

A white-label, appointment-booking backend built with FastAPI, MongoDB (PyMongo), CQRS & Event-Sourcing, JWT authentication, SMTP-based password recovery, and full CI/CD via GitHub Actions.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Getting Started](#getting-started)

   - [Prerequisites](#prerequisites)
   - [Clone & Install](#clone--install)
   - [Environment Variables](#environment-variables)
   - [Run Locally](#run-locally)
   - [Run with Docker](#run-with-docker)

5. [Usage](#usage)

   - [Authentication](#authentication)
   - [Booking Endpoints](#booking-endpoints)

6. [Testing](#testing)

   - [with Docker](#with-docker)

7. [CI/CD](#cicd)
8. [Folder Structure](#folder-structure)
9. [Extending & Customizing](#extending--customizing)
10. [License](#license)

---

## Features

- **CQRS & Event-Sourcing** – append-only event store for all domain changes
- **FastAPI** – high-performance, asynchronous REST API with automatic docs
- **MongoDB (PyMongo)** – both event store and read-model persistence
- **JWT Authentication** – OAuth2 password flow with JWTs
- **Password Recovery** – SMTP-driven “forgot password” email flow
- **Twelve-Factor Config** – environment variables via Pydantic & `.env`
- **Automated Tests** – pytest suite with fixtures & CI integration
- **CI/CD** – GitHub Actions for linting & testing on every push/PR

---

## Tech Stack

- **Language:** Python 3.10+
- **Web Framework:** FastAPI
- **Database:** MongoDB (via PyMongo)
- **Auth:** OAuth2 + JWT (python-jose)
- **Rate Limiting:** SlowAPI (based on Flask-Limiter)
- **Email:** `smtplib` (SMTP)
- **Testing:** pytest
- **CI/CD:** GitHub Actions
- **Linting:** flake8

---

## Architecture

```
Client
   │
   ├─ /auth/token      ← JWT issue
   ├─ /auth/recover    ← Password recovery
   ├─ /bookings        ← Command (write) endpoint
   └─ /bookings        ← Query (read) endpoint
           │
           ├─ Auth Dependencies (JWT validation)
           ├─ Command Handler → Event Store (MongoDB “events”)
           └─ Query Handler   → Replay events or read_model
```

- **Commands** write events to an append-only `events` collection.
- **Queries** rebuild state by replaying or reading projections.
- **Read Models** (optional) stored in `read_models` for faster queries.
- **Env Config** lives in `.env`, loaded via Pydantic.
- **CI/CD** runs lint & tests on GitHub Actions.

---

## Getting Started

### Prerequisites

- Python 3.10+
- MongoDB instance (local or Atlas)
- SMTP server credentials (e.g., Mailtrap, SendGrid)
- Git & GitHub account

### Clone & Install

```bash
git clone https://github.com/rcpassos/booking-engine-api.git
cd booking-engine-api
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in project root:

```dotenv
MONGODB_URI=mongodb://localhost:27017/
JWT_SECRET_KEY=your_jwt_secret
JWT_EXPIRE_MINUTES=60
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=your_user
SMTP_PASS=your_pass
SMTP_FROM_EMAIL=no-reply@your-domain.com
```

### Run Locally

```bash
uvicorn app.main:app --reload
```

- API docs: `http://localhost:8000/docs`
- Redoc UI: `http://localhost:8000/redoc`

---

### Run with Docker

```bash
docker compose up --build -d
```

## Usage

### Authentication

- **Issue Token**

  ```
  POST /auth/token
  Content-Type: application/x-www-form-urlencoded

  username=demo
  password=secret
  ```

- **Recover Password**

  ```
  POST /auth/recover-password
  Content-Type: application/json

  { "email": "user@example.com" }
  ```

### Booking Endpoints

- **Create Booking** (requires `Authorization: Bearer <token>`)

  ```http
  POST /bookings?slot=2025-05-12T14:30:00
  ```

- **List Bookings** (requires `Authorization: Bearer <token>`)

  ```http
  GET /bookings
  ```

### Rate Limits

The API implements rate limiting to prevent abuse:

- Registration: 5 attempts per hour per IP
- Login: 10 attempts per minute per IP
- Password Recovery: 3 requests per hour per IP
- Password Reset: 5 requests per hour per IP
- User Profile: 60 requests per minute per IP
- Profile Updates: 30 requests per hour per IP
- Password Changes: 5 requests per hour per IP

---

## Testing

Run the full test suite:

```bash
pytest --maxfail=1 --disable-warnings -q
```

### with Docker

```bash
docker compose exec api pytest --maxfail=1 --disable-warnings -q
```

---

## CI/CD

A GitHub Actions workflow (`.github/workflows/ci.yml`) automatically:

1. Checks out code
2. Sets up Python 3.10
3. Installs dependencies
4. Runs `flake8` linting
5. Executes `pytest` tests

All on every push or pull request to `main`.

---

## Folder Structure

```
booking-engine-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── auth/
│   │   ├── jwt.py
│   │   └── dependencies.py
│   ├── commands/
│   │   ├── events.py
│   │   └── handlers.py
│   ├── queries/
│   │   ├── models.py
│   │   └── handlers.py
│   └── email.py
├── tests/
│   └── test_app.py
├── .env
├── .gitignore
├── requirements.txt
├── README.md
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Extending & Customizing

- **Add Read-Model Projections**: populate `read_models` for faster queries.
- **Role-Based Access**: enrich JWT payload and enforce scopes.
- **Snapshots**: optimize event replay for large streams.
- **Dockerization**: add `Dockerfile` and `docker-compose.yml`.
- **Monitoring**: integrate Sentry, Prometheus, or New Relic.

---

## License

MIT License © Rafael Passos
