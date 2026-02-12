from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from contextlib import asynccontextmanager
import os
import secrets
import base64
from datetime import datetime
import time
import json as json_module
import asyncio
import urllib.request
import urllib.error

from app.docker_manager import DockerManager
from app.registry import ImageRegistry
from app.benchmark import init_db as init_benchmark_db, get_all_tests, generate_csv
from app.models import (
    RegisterImageRequest,
    RegisterImageResponse,
    StartContainerRequest,
    StartContainerResponse,
    StopContainerResponse,
    ContainerStatusResponse,
    ListContainersResponse,
    ListImagesResponse,
    HealthResponse,
    ContainerInfo
)

# Global instances
docker_manager: DockerManager = None
image_registry: ImageRegistry = None
start_time = time.time()

# Basic Auth credentials from environment (use `or` to handle empty strings)
BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME") or "qatestsuit"
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD") or "d09r5uBDo7o3cq3C"


def verify_basic_auth(request: Request):
    """Verify HTTP Basic Auth credentials"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Basic "):
        return None

    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, password = decoded.split(":", 1)

        if secrets.compare_digest(username, BASIC_AUTH_USERNAME) and \
           secrets.compare_digest(password, BASIC_AUTH_PASSWORD):
            return username
    except Exception:
        pass

    return None


async def require_auth(request: Request):
    """Dependency that enforces Basic Auth on all routes"""
    user = verify_basic_auth(request)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": 'Basic realm="QA Test Suite"'},
        )
    return user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    global docker_manager, image_registry

    # Startup
    print("Starting QA Docker Test Manager...")
    docker_manager = DockerManager(
        docker_host=os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock"),
        public_host=os.getenv("PUBLIC_HOST", "localhost")
    )
    docker_manager.set_max_containers(int(os.getenv("MAX_CONTAINERS", "10")))

    image_registry = ImageRegistry(
        db_file=os.getenv("DB_FILE", "data/registry.json")
    )

    # Seed preconfigured images from saas-images.json
    config_file = os.getenv("SAAS_IMAGES_CONFIG", "config/saas-images.json")
    seeded = image_registry.seed_from_config(config_file)
    if seeded > 0:
        print(f"Seeded {seeded} preconfigured images from {config_file}")

    # Initialize benchmark test cases DB
    init_benchmark_db()
    print("Benchmark test cases loaded into SQLite")

    print(f"Loaded {len(image_registry.list_images())} registered images")
    print(f"Basic Auth: {BASIC_AUTH_USERNAME} / {BASIC_AUTH_PASSWORD}")
    print("Server ready!")

    yield

    # Shutdown
    print("\nShutting down...")
    if docker_manager:
        result = await docker_manager.stop_all_containers()
        print(f"Stopped {result['stopped']} containers")
    print("Shutdown complete")


app = FastAPI(
    title="QA Docker Test Manager API",
    description="Docker container management API for QA testing with human-readable image IDs",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Basic Auth middleware - protects ALL routes including static files
@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    """Enforce HTTP Basic Auth on every request"""
    # Allow CORS preflight through
    if request.method == "OPTIONS":
        return await call_next(request)

    # Allow emulation endpoint without auth (used by centrifuge-js fetch from browser)
    if request.url.path == "/emulation":
        return await call_next(request)

    # Allow centrifugo client page and its API dependencies without auth
    if request.url.path in ("/static/centrifugo-client.html", "/api/containers"):
        return await call_next(request)

    user = verify_basic_auth(request)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": 'Basic realm="QA Test Suite"'},
        )

    return await call_next(request)


# Health check (still behind auth)
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        uptime=time.time() - start_time
    )


# API Info
@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "QA Docker Test Manager API",
        "version": "1.0.0",
        "description": "Docker container management for QA testing",
        "auth": "HTTP Basic Auth",
        "endpoints": {
            "POST /api/images/register": "Register a Docker image with human-readable ID",
            "GET /api/images": "List all registered images",
            "GET /api/images/{image_id}": "Get image details",
            "DELETE /api/images/{image_id}": "Delete a registered image",
            "POST /api/images/{image_id}/pull": "Pull image and all its dependencies",
            "POST /api/containers/start": "Start a container from registered image",
            "POST /api/containers/{instance_id}/stop": "Stop a running container",
            "GET /api/containers/{instance_id}": "Get container status",
            "GET /api/containers": "List all running containers",
            "POST /api/containers/stop-all": "Stop all containers",
            "POST /api/containers/cleanup": "Cleanup stale containers"
        }
    }


# ===== IMAGE REGISTRATION ENDPOINTS =====

@app.post("/api/images/register", response_model=RegisterImageResponse)
async def register_image(request: RegisterImageRequest):
    """
    Register a Docker image and get a human-readable ID

    This ID can be used to start, stop, and manage containers
    """
    try:
        image_id = image_registry.register_image(
            name=request.name,
            image_name=request.image_name,
            exposed_port=request.exposed_port,
            description=request.description,
            env=request.env,
            health_check_path=request.health_check_path,
            dependencies=request.dependencies
        )

        image = image_registry.get_image(image_id)

        return RegisterImageResponse(
            success=True,
            image_id=image_id,
            message=f"Image registered successfully with ID: {image_id}",
            data=image.model_dump()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/images", response_model=ListImagesResponse)
async def list_images():
    """List all registered images"""
    try:
        images = image_registry.list_images()
        return ListImagesResponse(
            success=True,
            data={
                "count": len(images),
                "images": [img.model_dump() for img in images]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/images/{image_id}")
async def get_image(image_id: str):
    """Get details of a registered image"""
    image = image_registry.get_image(image_id)

    if not image:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found")

    return {
        "success": True,
        "data": image.model_dump()
    }


@app.delete("/api/images/{image_id}")
async def delete_image(image_id: str):
    """Delete a registered image"""
    if not image_registry.delete_image(image_id):
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found")

    return {
        "success": True,
        "message": f"Image '{image_id}' deleted successfully"
    }


# ===== CONTAINER MANAGEMENT ENDPOINTS =====

@app.post("/api/containers/start", response_model=StartContainerResponse)
async def start_container(request: StartContainerRequest):
    """
    Start a new container from a registered image

    Returns instance_id, URL, and port information
    """
    try:
        # Get registered image
        image = image_registry.get_image(request.image_id)

        if not image:
            raise HTTPException(
                status_code=404,
                detail=f"Image '{request.image_id}' not found. Register it first using /api/images/register"
            )

        # Build dependency configs for docker manager
        dep_configs = None
        if image.dependencies:
            dep_configs = [
                {
                    "id": dep.id,
                    "image_name": dep.image_name,
                    "exposed_port": dep.exposed_port,
                    "env": dep.env,
                    "command": dep.command,
                    "entrypoint": dep.entrypoint,
                    "wait_time": dep.wait_time,
                }
                for dep in image.dependencies
            ]

        # Start container
        container_info = await docker_manager.start_container(
            image_id=image.image_id,
            image_name=image.image_name,
            exposed_port=image.exposed_port,
            env=image.env,
            dependencies=dep_configs,
            host_port=image.host_port,
            command=image.command,
            entrypoint=image.entrypoint
        )

        # Include credentials if available
        if image.credentials:
            container_info["credentials"] = image.credentials

        return StartContainerResponse(
            success=True,
            data=ContainerInfo(**container_info)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/containers/{instance_id}/stop", response_model=StopContainerResponse)
async def stop_container(instance_id: str):
    """Stop and remove a container"""
    try:
        result = await docker_manager.stop_container(instance_id)
        return StopContainerResponse(
            success=True,
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/containers/{instance_id}", response_model=ContainerStatusResponse)
async def get_container_status(instance_id: str):
    """Get status and details of a running container"""
    try:
        status = await docker_manager.get_container_status(instance_id)
        return ContainerStatusResponse(
            success=True,
            data=ContainerInfo(**status)
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/containers", response_model=ListContainersResponse)
async def list_containers():
    """List all running containers"""
    try:
        containers = await docker_manager.list_containers()
        return ListContainersResponse(
            success=True,
            data={
                "count": len(containers),
                "containers": containers
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/containers/stop-all")
async def stop_all_containers():
    """Stop all running containers"""
    try:
        result = await docker_manager.stop_all_containers()
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/containers/cleanup")
async def cleanup_containers(max_age_seconds: int = 3600):
    """Cleanup stale containers older than max_age_seconds"""
    try:
        result = await docker_manager.cleanup_stale_containers(max_age_seconds)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== IMAGE DEPENDENCY ENDPOINTS =====

@app.post("/api/images/{image_id}/pull")
async def pull_image_dependencies(image_id: str):
    """
    Pull the Docker image and all its dependencies.

    This pre-downloads all required images so that container startup is fast.
    """
    try:
        image = image_registry.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=404,
                detail=f"Image '{image_id}' not found"
            )

        pulled = []

        # Pull the main image
        await docker_manager.pull_image(image.image_name)
        pulled.append({"image": image.image_name, "status": "ready"})

        # Pull dependency images
        for dep in image.dependencies:
            await docker_manager.pull_image(dep.image_name)
            pulled.append({"image": dep.image_name, "status": "ready"})

        return {
            "success": True,
            "image_id": image_id,
            "message": f"Pulled {len(pulled)} image(s) successfully",
            "data": {"images": pulled}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== PROXY ENDPOINT =====

@app.post("/api/proxy/{identifier}/{path:path}")
async def proxy_request(identifier: str, path: str, request: Request):
    """Proxy HTTP requests to a running container (avoids CORS issues for browser clients).
    Accepts either instance_id or image_id as identifier."""
    try:
        # Try as instance_id first, then fall back to image_id lookup
        container_status = None
        try:
            container_status = await docker_manager.get_container_status(identifier)
        except Exception:
            # Fall back: find container by image_id
            containers = await docker_manager.list_containers()
            for c in containers:
                if c.get("image_id") == identifier:
                    container_status = c
                    break

        if not container_status:
            raise HTTPException(status_code=404, detail=f"No running container found for '{identifier}'")

        target_url = f"{container_status['url']}/{path}"
        body = await request.body()

        def do_request():
            req = urllib.request.Request(
                target_url, data=body, method="POST",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json_module.loads(resp.read())

        result = await asyncio.to_thread(do_request)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/emulation")
async def emulation_proxy(request: Request):
    """Proxy emulation requests to the centrifugo container.
    Used by centrifuge-js for SSE/HTTP-Streaming bidirectional communication."""
    try:
        # Look up centrifugo host port from image registry
        image = image_registry.get_image("centrifugo") if image_registry else None
        if not image or not image.host_port:
            raise HTTPException(status_code=404, detail="Centrifugo image not found in registry")

        target_url = f"http://localhost:{image.host_port}/emulation"
        body = await request.body()
        content_type = request.headers.get("content-type", "application/octet-stream")

        def do_request():
            req = urllib.request.Request(
                target_url, data=body, method="POST",
                headers={"Content-Type": content_type}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.read(), resp.headers.get("Content-Type", "application/octet-stream"), resp.status
            except urllib.error.HTTPError as e:
                return e.read(), e.headers.get("Content-Type", "application/octet-stream"), e.code

        resp_body, resp_content_type, resp_status = await asyncio.to_thread(do_request)
        return Response(content=resp_body, media_type=resp_content_type, status_code=resp_status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ===== BENCHMARK TEST SUITE ENDPOINTS =====

@app.get("/api/benchmark/tests")
async def list_benchmark_tests():
    """List all benchmark test cases"""
    tests = get_all_tests()
    return {
        "success": True,
        "data": {
            "count": len(tests),
            "tests": tests
        }
    }


@app.get("/api/benchmark/csv")
async def export_benchmark_csv():
    """Export all benchmark test cases as a CSV file"""
    csv_content = generate_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=benchmark_test_cases.csv"}
    )


# ===== DASHBOARD UI =====

@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the dashboard UI"""
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "static", "index.html"))


# Mount static files (must be after all API routes)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static")), name="static")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8085"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
