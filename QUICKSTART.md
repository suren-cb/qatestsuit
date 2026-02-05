# Quick Start Guide

## Prerequisites

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Ensure Docker is running**:
   ```bash
   docker info
   ```

## Installation & Setup

```bash
# Navigate to project directory
cd qatestsuit

# Sync dependencies with uv
uv sync
```

## Start the Server

### Option 1: Using the Bash script (Linux/Mac)
```bash
./start.sh
```

### Option 2: Using the Python script (Cross-platform)
```bash
python start.py
# or
uv run python start.py
```

### Option 3: Direct uvicorn command
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Access the API

Once the server is running:

- **Swagger UI (Interactive Docs)**: http://localhost:8000/docs
- **ReDoc (Alternative Docs)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **API Info**: http://localhost:8000/api/info

## Quick Test

### 1. Register a Docker Image

```bash
curl -X POST http://localhost:8000/api/images/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nginx-demo",
    "image_name": "nginx:latest",
    "exposed_port": 80,
    "description": "NGINX web server for testing"
  }'
```

**Response:**
```json
{
  "success": true,
  "image_id": "nginx-demo",
  "message": "Image registered successfully with ID: nginx-demo"
}
```

### 2. Start a Container

```bash
curl -X POST http://localhost:8000/api/containers/start \
  -H "Content-Type: application/json" \
  -d '{"image_id": "nginx-demo"}'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "instance_id": "a1b2c3d4",
    "image_id": "nginx-demo",
    "url": "http://localhost:32768",
    "status": "running"
  }
}
```

### 3. Test the Container

```bash
# Use the URL from the response
curl http://localhost:32768
```

### 4. Stop the Container

```bash
curl -X POST http://localhost:8000/api/containers/a1b2c3d4/stop
```

## Run the Example Test

```bash
uv run python examples/test_workflow.py
```

## Configuration

Edit `.env` to customize settings:

```env
HOST=0.0.0.0
PORT=8000
MAX_CONTAINERS=10
API_KEY=your-secret-api-key-here
```

## Troubleshooting

### Docker not running
```bash
# Check Docker status
docker info

# Start Docker (Mac)
open -a Docker

# Start Docker (Linux)
sudo systemctl start docker
```

### Port already in use
Edit `.env` and change `PORT=8000` to another port.

### Permission denied on start.sh
```bash
chmod +x start.sh
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8000/docs
- Check out `examples/test_workflow.py` for test automation examples
- Review test suites in `*.json` files for QA benchmarks
