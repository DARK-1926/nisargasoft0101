#!/usr/bin/env python3
"""
Fix availability column length in offers table.
Run this on EC2 to increase the column size from VARCHAR(128) to TEXT.
"""
import asyncio
import os
from sqlalchemy import text
from backend.app.db import engine

async def fix_availability_column():
    """Alter the availability column to TEXT type."""
    async with engine.begin() as conn:
        print("Altering offers.availability column from VARCHAR(128) to TEXT...")
        await conn.execute(text("ALTER TABLE offers ALTER COLUMN availability TYPE TEXT"))
        print("✓ Column altered successfully!")

if __name__ == "__main__":
    asyncio.run(fix_availability_column())
