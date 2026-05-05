# Flagr

A production-grade Feature Flag & Experimentation API built with Django and Django REST Framework.

Supports feature toggling, gradual rollouts, A/B testing, and metrics tracking — designed with the same mindset as LaunchDarkly or Unleash.

---

## Features

- **Feature flags** — enable/disable features globally or per rollout percentage
- **Deterministic rollouts** — hash-based bucketing means the same user always gets the same result
- **A/B experimentation** — assign users to variants with weighted splits
- **Metrics tracking** — log impressions and conversions, read aggregated results per variant
- **Hardened for production** — indexes, validation, caching, consistent error responses

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Django 4.2 + Django REST Framework |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Caching | LocMemCache (dev) / Redis (prod) |
| Language | Python 3.10+ |

---

## Project Structure

```
flagr/
├── manage.py
├── requirements.txt
├── flagr/
│   ├── settings.py          # config: apps, DB, cache, DRF, exception handler
│   ├── urls.py              # root router
│   └── wsgi.py
└── feature_flags/
    ├── models.py            # FeatureFlag, Experiment, Variant, Assignment, MetricEvent
    ├── evaluator.py         # flag evaluation engine with caching
    ├── assigner.py          # A/B assignment engine with weighted bucketing
    ├── serializers.py       # request/response validation
    ├── views.py             # HTTP layer
    ├── urls.py              # all routes
    ├── exceptions.py        # global error handler
    └── admin.py             # Django admin registration
```

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/yourname/flagr.git
cd flagr
pip install -r requirements.txt
```

### 2. Run migrations

```bash
python manage.py migrate
```

### 3. Create an admin user (optional)

```bash
python manage.py createsuperuser
```

### 4. Start the server

```bash
python manage.py runserver
```

API is live at `http://127.0.0.1:8000/api/`

---

## API Reference

### Health

```
GET /api/health/
```

```json
{
    "status": "ok",
    "service": "flagr",
    "version": "0.1.0"
}
```

---

### Feature Flags

#### Create a flag

```
POST /api/flags/
```

```json
{
    "name": "dark-mode",
    "description": "Dark mode UI rollout",
    "is_active": true,
    "rollout_percentage": 50
}
```

#### List all flags

```
GET /api/flags/
```

#### Get one flag

```
GET /api/flags/<name>/
```

#### Update a flag (toggle, change rollout)

```
PATCH /api/flags/<name>/
```

```json
{
    "is_active": false
}
```

#### Evaluate a flag for a user

```
POST /api/flags/evaluate/
```

```json
{
    "flag_name": "dark-mode",
    "user_id": "user_001"
}
```

**Response:**

```json
{
    "enabled": true,
    "reason": "rollout",
    "flag_name": "dark-mode",
    "user_id": "user_001",
    "bucket": 23,
    "rollout_percentage": 50
}
```

Possible `reason` values:

| Reason | Meaning |
|---|---|
| `flag_not_found` | Flag doesn't exist |
| `flag_disabled` | Flag is globally off |
| `full_rollout` | Rollout is 100% — everyone is in |
| `zero_rollout` | Rollout is 0% — nobody is in |
| `rollout` | User's hash bucket is within rollout % |
| `not_in_rollout` | User's hash bucket is outside rollout % |

---

### Experiments

#### Create an experiment

```
POST /api/experiments/
```

```json
{
    "name": "Checkout V2 Experiment",
    "description": "Testing new checkout flow",
    "feature_flag": 1,
    "status": "running"
}
```

#### Add variants to an experiment

```
POST /api/experiments/<id>/variants/
```

```json
{
    "name": "control",
    "weight": 50
}
```

```json
{
    "name": "treatment",
    "weight": 50
}
```

Weights are relative — `control=80, treatment=20` gives an 80/20 split.

#### Assign a user to a variant

```
POST /api/experiments/assign/
```

```json
{
    "experiment_id": 1,
    "user_id": "user_001"
}
```

**Response:**

```json
{
    "success": true,
    "already_assigned": false,
    "user_id": "user_001",
    "experiment_id": 1,
    "experiment_name": "Checkout V2 Experiment",
    "variant_id": 1,
    "variant_name": "control",
    "bucket": 23
}
```

Calling this endpoint again for the same user returns `already_assigned: true` with the same variant — assignment is permanent and deterministic.

#### List / get / update experiments

```
GET  /api/experiments/
GET  /api/experiments/<id>/
PATCH /api/experiments/<id>/
```

---

### Metrics

#### Log an event

```
POST /api/experiments/events/
```

```json
{
    "experiment_id": 1,
    "user_id": "user_001",
    "event_type": "impression"
}
```

```json
{
    "experiment_id": 1,
    "user_id": "user_001",
    "event_type": "conversion"
}
```

Duplicate events are silently ignored — safe to call multiple times.

#### Get aggregated metrics

```
GET /api/experiments/<id>/metrics/
```

**Response:**

```json
{
    "experiment_id": 1,
    "experiment_name": "Checkout V2 Experiment",
    "status": "running",
    "variants": [
        {
            "variant_id": 1,
            "variant_name": "control",
            "impressions": 120,
            "conversions": 36,
            "conversion_rate_pct": 30.0
        },
        {
            "variant_id": 2,
            "variant_name": "treatment",
            "impressions": 118,
            "conversions": 47,
            "conversion_rate_pct": 39.83
        }
    ]
}
```

---

## How Deterministic Assignment Works

Both flag evaluation and A/B assignment use SHA-256 hashing — never randomness.

```
bucket = SHA256(user_id + flag_name)[:8] → int → mod 100
```

- Same user + same flag → always the same bucket (0–99)
- Each flag/experiment is independent — a user in bucket 12 for one flag may be in bucket 87 for another
- Changing rollout percentage never reassigns users already in the rollout

---

## Error Responses

All errors return the same envelope:

```json
{
    "error": true,
    "code": "bad_request",
    "message": "Must be between 0 and 100.",
    "detail": {
        "rollout_percentage": ["Must be between 0 and 100."]
    }
}
```

| Code | HTTP Status |
|---|---|
| `bad_request` | 400 |
| `unauthorized` | 401 |
| `forbidden` | 403 |
| `not_found` | 404 |
| `method_not_allowed` | 405 |
| `too_many_requests` | 429 |
| `server_error` | 500 |

---

## Production Checklist

- [ ] Replace `SECRET_KEY` in `settings.py` with a real secret (use environment variable)
- [ ] Set `DEBUG = False`
- [ ] Set `ALLOWED_HOSTS` to your actual domain
- [ ] Switch database to PostgreSQL
- [ ] Switch cache backend to Redis
- [ ] Serve with `gunicorn` behind `nginx`
- [ ] Add API key authentication (Phase 7 extension)
- [ ] Set up log aggregation (Datadog, Sentry, etc.)
- [ ] Add rate limiting on the evaluate endpoint

### Switching to PostgreSQL

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "flagr",
        "USER": "flagr_user",
        "PASSWORD": "yourpassword",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

### Switching to Redis cache

```bash
pip install django-redis
```

```python
# settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
```

### Running with Gunicorn

```bash
pip install gunicorn
gunicorn flagr.wsgi:application --workers 4 --bind 0.0.0.0:8000
```

---

## Running Tests

```bash
pip install pytest pytest-django
pytest
```

---

## License

MIT