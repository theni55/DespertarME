"""Crea un usuario admin de prueba en la BD (Fase 3 seed).

Uso: python scripts/seed_admin.py
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


async def main() -> int:
    async with SessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == "admin@despertarme.com"))
        if existing.scalar_one_or_none():
            print("Admin ya existe: admin@despertarme.com / admin123")
            return 0

        user = User(
            id=str(uuid.uuid4()),
            email="admin@despertarme.com",
            hashed_password=hash_password("admin123"),
            phone_normalized="+34600000000",
            timezone="Europe/Madrid",
            role="admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print("Admin creado:")
        print("  email:    admin@despertarme.com")
        print("  password: admin123")
        print("  URL:      http://localhost:8000/admin/login")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
