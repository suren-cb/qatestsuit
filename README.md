# QA Docker Test Manager API (FastAPI)

A Docker container management API designed for QA test automation. Register Docker images with human-readable IDs and spin up fresh, isolated container instances for testing with clean state guaranteed for each test run.

## Features

- 🐳 **Docker Container Management**: Start, stop, and monitor Docker containers via REST API
- 🔤 **Human-Readable IDs**: Register images with friendly names (e.g., `nginx-demo`, `wordpress-test`)
- 🔄 **Clean State per Test**: Each test gets a fresh container instance with clean state
- 📝 **Image Registry**: Persistent storage of registered Docker images
- 🔒 **Port Management**: Automatic host port allocation to avoid conflicts
- 🧹 **Auto Cleanup**: Automatic cleanup of stale containers
- 📊 **Health Monitoring**: Container status tracking and health checks
- 🔐 **API Key Authentication**: Optional API key protection
- 📚 **Auto-generated API Docs**: Interactive Swagger UI at `/docs`

## Prerequisites

- Python 3.8+
- Docker installed and running
- Docker socket accessible at `/var/run/docker.sock`

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

## Configuration

Edit `.env` file (will be created from `.env.example` on first run):

```env
HOST=0.0.0.0
PORT=8000
DOCKER_HOST=unix:///var/run/docker.sock
MAX_CONTAINERS=10
CONTAINER_TIMEOUT_SECONDS=3600
AUTO_CLEANUP_INTERVAL_SECONDS=300
API_KEY=your-secret-api-key-here
DB_FILE=data/registry.json
```

## Usage

### Start the Server

**Option 1: Using the startup script (recommended)**
```bash
# Bash script (Linux/Mac)
./start.sh

# Python script (Cross-platform)
python start.py

# Or using uv
uv run python start.py
```

**Option 2: Direct uvicorn command**
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

## API Endpoints

### 1. Register a Docker Image

First, register your Docker image with a human-readable ID:

```bash
POST /api/images/register
Content-Type: application/json
X-API-Key: your-secret-api-key-here

{
  "name": "nginx-demo",
  "image_name": "nginx:latest",
  "exposed_port": 80,
  "description": "NGINX web server for testing",
  "env": ["NGINX_HOST=localhost"],
  "health_check_path": "/"
}
```

**Response:**
```json
{
  "success": true,
  "image_id": "nginx-demo",
  "message": "Image registered successfully with ID: nginx-demo",
  "data": {
    "image_id": "nginx-demo",
    "name": "nginx-demo",
    "image_name": "nginx:latest",
    "exposed_port": 80,
    "description": "NGINX web server for testing",
    "env": ["NGINX_HOST=localhost"],
    "health_check_path": "/",
    "registered_at": "2026-02-04T10:30:00.000Z"
  }
}
```

### 2. List Registered Images

```bash
GET /api/images
```

**Response:**
```json
{
  "success": true,
  "data": {
    "count": 2,
    "images": [
      {
        "image_id": "nginx-demo",
        "name": "nginx-demo",
        "image_name": "nginx:latest",
        "exposed_port": 80,
        ...
      }
    ]
  }
}
```

### 3. Start a Container

Use the `image_id` from registration:

```bash
POST /api/containers/start
Content-Type: application/json
X-API-Key: your-secret-api-key-here

{
  "image_id": "nginx-demo"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "instance_id": "a1b2c3d4",
    "image_id": "nginx-demo",
    "container_id": "abc123...",
    "container_name": "qa-nginx-demo-a1b2c3d4",
    "image_name": "nginx:latest",
    "host_port": 32768,
    "exposed_port": 80,
    "url": "http://localhost:32768",
    "status": "running",
    "created_at": "2026-02-04T10:30:00.000Z"
  }
}
```

### 4. Get Container Status

```bash
GET /api/containers/{instance_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "instance_id": "a1b2c3d4",
    "image_id": "nginx-demo",
    "container_id": "abc123...",
    "container_name": "qa-nginx-demo-a1b2c3d4",
    "image_name": "nginx:latest",
    "host_port": 32768,
    "exposed_port": 80,
    "url": "http://localhost:32768",
    "status": "running",
    "running": true,
    "created_at": "2026-02-04T10:30:00.000Z",
    "uptime": "5m 30s"
  }
}
```

### 5. Stop a Container

```bash
POST /api/containers/{instance_id}/stop
X-API-Key: your-secret-api-key-here
```

**Response:**
```json
{
  "success": true,
  "message": "Container stopped and removed successfully"
}
```

### 6. List All Running Containers

```bash
GET /api/containers
```

### Other Endpoints

- `POST /api/containers/stop-all` - Stop all containers
- `POST /api/containers/cleanup` - Cleanup stale containers
- `DELETE /api/images/{image_id}` - Delete registered image
- `GET /health` - Health check

## Complete Workflow Example

```python
import requests
import time

API_BASE = "http://localhost:8000"
API_KEY = "your-secret-api-key-here"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Step 1: Register a Docker image (one-time setup)
print("Registering Docker image...")
register_response = requests.post(
    f"{API_BASE}/api/images/register",
    headers=headers,
    json={
        "name": "nginx-demo",
        "image_name": "nginx:latest",
        "exposed_port": 80,
        "description": "NGINX web server for testing"
    }
)
image_data = register_response.json()
image_id = image_data["image_id"]
print(f"✓ Image registered with ID: {image_id}")

# Step 2: Start a container using the image_id
print("\nStarting container...")
start_response = requests.post(
    f"{API_BASE}/api/containers/start",
    headers=headers,
    json={"image_id": image_id}
)
container_data = start_response.json()["data"]
instance_id = container_data["instance_id"]
url = container_data["url"]
print(f"✓ Container started at: {url}")
print(f"  Instance ID: {instance_id}")

# Step 3: Wait for container to be ready
print("\nWaiting for container to be ready...")
time.sleep(5)

# Step 4: Run your tests
print(f"\nRunning tests against {url}...")
test_response = requests.get(url)
assert test_response.status_code == 200
print("✓ Test passed!")

# Step 5: Get container status
status_response = requests.get(
    f"{API_BASE}/api/containers/{instance_id}"
)
status = status_response.json()["data"]
print(f"\nContainer Status:")
print(f"  Status: {status['status']}")
print(f"  Uptime: {status['uptime']}")

# Step 6: Cleanup - Stop container
print("\nStopping container...")
stop_response = requests.post(
    f"{API_BASE}/api/containers/{instance_id}/stop",
    headers=headers
)
print("✓ Container stopped and removed")
```

## Security Considerations

- Set a strong `API_KEY` in production
- Restrict access to the API server (use firewall rules)
- Monitor container resource usage to prevent abuse
- Set reasonable `MAX_CONTAINERS` limit
- Use Docker security best practices

## Troubleshooting

### Docker socket permission denied

```bash
# Add your user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended for production)
sudo npm start
```

### Port already in use

The API automatically finds available ports for containers. If the API port (3000) is in use, change `PORT` in `.env`.

### Container fails to start

- Check Docker is running: `docker ps`
- Check Docker logs: `docker logs <container-id>`
- Verify image exists: `docker images`
- Check available disk space: `df -h`

## Architecture

```
┌─────────────────┐
│   QA Test Agent │
└────────┬────────┘
         │ HTTP API
         │
┌────────▼────────────────────┐
│  Docker Manager API Server  │
│  (Express.js)               │
└────────┬────────────────────┘
         │ dockerode
         │
┌────────▼────────────────────┐
│    Docker Engine            │
│  ┌──────────┐ ┌──────────┐ │
│  │Container1│ │Container2│ │
│  └──────────┘ └──────────┘ │
└─────────────────────────────┘
```

## License

MIT

## Contributing

Pull requests are welcome! Please ensure all tests pass before submitting.
