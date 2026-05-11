# Sanos y Salvos - API Gateway

Gateway centralizado del sistema Sanos y Salvos. Expone autenticacion JWT, rutas proxy hacia microservicios y circuit breakers para resiliencia.

## Stack

- FastAPI
- JWT con python-jose
- SQLAlchemy + PostgreSQL para usuarios
- HTTPX para proxy interno
- Docker

## Variables de entorno

Copia `.env.example` como `.env` y ajusta los valores segun el ambiente.

## Ejecucion local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker build -t sanos-salvos-gateway .
docker run --env-file .env -p 8000:8000 sanos-salvos-gateway
```

## Endpoints principales

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- Proxy hacia `/api/pets`, `/api/geo`, `/api/matches` y `/api/notifications`
