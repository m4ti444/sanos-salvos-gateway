"""
Sanos y Salvos — API Gateway
Main entry point. Centralizes authentication, routing, and resilience.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text

from app.config import settings
from app.auth.jwt_handler import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.auth.middleware import get_current_user
from app.routing.proxy import router as proxy_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

# Database engine for auth
engine = create_engine(settings.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 API Gateway starting...")
    logger.info(f"  → Pets Service:          {settings.PETS_SERVICE_URL}")
    logger.info(f"  → Geolocation Service:   {settings.GEO_SERVICE_URL}")
    logger.info(f"  → Match Service:         {settings.MATCH_SERVICE_URL}")
    logger.info(f"  → Notifications Service: {settings.NOTIFICATIONS_SERVICE_URL}")
    yield
    logger.info("🛑 API Gateway shutting down...")


app = FastAPI(
    title="Sanos y Salvos — API Gateway",
    description="Gateway centralizado con autenticación JWT, routing y Circuit Breaker",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Pydantic Schemas for Auth
# ============================================================

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str | None = None
    phone: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


# ============================================================
# Health Check
# ============================================================

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
    }


# ============================================================
# Auth Endpoints (handled directly by gateway)
# ============================================================

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Auth"])
async def register(data: RegisterRequest):
    """Register a new user."""
    with engine.connect() as conn:
        # Check if user exists
        result = conn.execute(
            text("SELECT id FROM auth_service.users WHERE email = :email OR username = :username"),
            {"email": data.email, "username": data.username},
        )
        if result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email o nombre de usuario ya está registrado",
            )

        # Create user
        hashed = hash_password(data.password)
        result = conn.execute(
            text("""
                INSERT INTO auth_service.users (email, username, hashed_password, full_name, phone)
                VALUES (:email, :username, :hashed_password, :full_name, :phone)
                RETURNING id, email, username, full_name, phone
            """),
            {
                "email": data.email,
                "username": data.username,
                "hashed_password": hashed,
                "full_name": data.full_name,
                "phone": data.phone,
            },
        )
        user = result.fetchone()
        conn.commit()

    user_data = {
        "sub": str(user[0]),
        "email": user[1],
        "username": user[2],
    }

    return TokenResponse(
        access_token=create_access_token(user_data),
        refresh_token=create_refresh_token(user_data),
        user={
            "id": user[0],
            "email": user[1],
            "username": user[2],
            "full_name": user[3],
            "phone": user[4],
        },
    )


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(data: LoginRequest):
    """Authenticate user and return JWT tokens."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, email, username, hashed_password, full_name, phone FROM auth_service.users WHERE email = :email"),
            {"email": data.email},
        )
        user = result.fetchone()

    if not user or not verify_password(data.password, user[3]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    user_data = {
        "sub": str(user[0]),
        "email": user[1],
        "username": user[2],
    }

    return TokenResponse(
        access_token=create_access_token(user_data),
        refresh_token=create_refresh_token(user_data),
        user={
            "id": user[0],
            "email": user[1],
            "username": user[2],
            "full_name": user[4],
            "phone": user[5],
        },
    )


@app.post("/api/auth/refresh", tags=["Auth"])
async def refresh_token(data: RefreshRequest):
    """Get a new access token using a refresh token."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
        )

    user_data = {
        "sub": payload["sub"],
        "email": payload["email"],
        "username": payload["username"],
    }

    return {
        "access_token": create_access_token(user_data),
        "token_type": "bearer",
    }


@app.get("/api/auth/me", tags=["Auth"])
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, email, username, full_name, phone FROM auth_service.users WHERE id = :id"),
            {"id": int(user["sub"])},
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "id": row[0],
        "email": row[1],
        "username": row[2],
        "full_name": row[3],
        "phone": row[4],
    }


# ============================================================
# Include proxy routes for microservices
# ============================================================
app.include_router(proxy_router)
