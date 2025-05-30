# Cloud Dronitor API

A REST API service for uploading and retrieving drone monitoring data with location and air quality index (AQI) measurements.

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following content:
```
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
DATABASE_URL=sqlite+aiosqlite:///./dronitor.db
```

4. Run the server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

### Authentication

All endpoints require an API key to be passed in the `X-API-Key` header.

### Endpoints

#### 1. Upload Data

```
POST /upload
```

Upload a text file containing drone readings in the format "longitude,latitude,aqi" (one reading per line).

**Example request:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@readings.txt"
```

#### 2. Get Readings

```
GET /readings
```

Retrieve drone readings filtered by date.

Query Parameters:
- `year` (optional): Filter by year
- `month` (optional): Filter by month (requires year)
- `day` (optional): Filter by day (requires year and month)

**Example requests:**
```bash
# Get all readings
curl "http://localhost:8000/readings" \
  -H "X-API-Key: your-api-key-here"

# Get readings for a specific year
curl "http://localhost:8000/readings?year=2023" \
  -H "X-API-Key: your-api-key-here"

# Get readings for a specific month
curl "http://localhost:8000/readings?year=2023&month=12" \
  -H "X-API-Key: your-api-key-here"

# Get readings for a specific day
curl "http://localhost:8000/readings?year=2023&month=12&day=25" \
  -H "X-API-Key: your-api-key-here"
```

## Data Format

The input file should contain readings in the following format:
```
longitude,latitude,aqi
```

Example:
```
-73.935242,40.730610,42
-73.935242,40.730610,45
-73.935242,40.730610,38
``` 