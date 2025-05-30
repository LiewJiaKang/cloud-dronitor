from fastapi import FastAPI, Depends, HTTPException, Security, status, File, UploadFile, Query, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Float, String, DateTime, select, Text
from datetime import datetime
from typing import List, Optional
import csv
from io import StringIO
import os
from dotenv import load_dotenv
import secrets
import aiofiles
from pathlib import Path
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Define data directory - use Render mount path if available
DATA_DIR = Path(os.getenv("RENDER_MOUNT_PATH", "data"))
DATA_DIR.mkdir(exist_ok=True)  # Ensure directory exists

# Create FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"Server started. Use this API key for authentication: {list(API_KEYS)[0]}")
    yield

app = FastAPI(title="Cloud Dronitor API", lifespan=lifespan)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key")

# Get API keys from environment
def get_api_keys():
    api_keys_str = os.getenv("API_KEYS", "your-api-key-here")
    return {key.strip() for key in api_keys_str.split(",")}

# Production API keys loaded from .env
API_KEYS = get_api_keys()

# Database Models
class DroneReading(Base):
    __tablename__ = "drone_readings"
    
    id = Column(String, primary_key=True)
    longitude = Column(Float)
    latitude = Column(Float)
    aqi = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(Text, nullable=True)  # Store raw data in database

# Database dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# API Key verification
async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return api_key

# Create tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/upload")
async def upload_data(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    content = await file.read()
    text_content = content.decode()
    csv_reader = csv.reader(StringIO(text_content))
    
    readings = []
    for idx, row in enumerate(csv_reader):
        if len(row) != 3:
            continue
            
        try:
            longitude, latitude, aqi = float(row[0]), float(row[1]), float(row[2])
            current_time = datetime.utcnow()
            reading = DroneReading(
                id=f"{current_time.timestamp()}_{longitude}_{latitude}_{idx}",
                longitude=longitude,
                latitude=latitude,
                aqi=aqi,
                timestamp=current_time,
                raw_data=",".join(row)  # Store raw data in database
            )
            readings.append(reading)
        except ValueError:
            continue
    
    # Save to database
    db.add_all(readings)
    await db.commit()
    
    return {"message": f"Successfully uploaded {len(readings)} readings"}

@app.get("/readings", response_model=List[dict])
async def get_readings(
    request: Request,
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(None, description="Filter by month"),
    day: Optional[int] = Query(None, description="Filter by day"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    print(f"Request method: {request.method}")
    print(f"Request URL: {request.url}")
    
    # Start with a base query
    query = select(DroneReading).order_by(DroneReading.timestamp.desc())
    
    # Apply date filters only if year is provided
    if year is not None:
        if month is not None:
            if day is not None:
                # Filter by specific date
                start_date = datetime(year, month, day)
                end_date = datetime(year, month, day, 23, 59, 59)
            else:
                # Filter by month
                if month == 12:
                    next_year = year + 1
                    next_month = 1
                else:
                    next_year = year
                    next_month = month + 1
                start_date = datetime(year, month, 1)
                end_date = datetime(next_year, next_month, 1)
        else:
            # Filter by year
            start_date = datetime(year, 1, 1)
            end_date = datetime(year + 1, 1, 1)
            
        query = query.where(DroneReading.timestamp >= start_date, 
                          DroneReading.timestamp < end_date)
    
    # Execute query and get results
    result = await db.execute(query)
    readings = result.scalars().all()
    
    print(f"Found {len(readings)} readings")
    
    if not readings:
        return []
    
    return [
        {
            "longitude": reading.longitude,
            "latitude": reading.latitude,
            "aqi": reading.aqi,
            "timestamp": reading.timestamp.isoformat(),
            "raw_data": reading.raw_data
        }
        for reading in readings
    ]

@app.get("/files/{date}")
async def get_file_data(
    date: str,
    api_key: str = Depends(verify_api_key)
):
    """Get data directly from a date's file"""
    try:
        file_path = DATA_DIR / f"{date}.csv"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="No data for this date")
            
        async with aiofiles.open(file_path, mode='r') as f:
            content = await f.read()
            
        readings = []
        for line in content.splitlines():
            lon, lat, aqi, timestamp = line.strip().split(',')
            readings.append({
                "longitude": float(lon),
                "latitude": float(lat),
                "aqi": float(aqi),
                "timestamp": timestamp
            })
            
        return readings
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format") 