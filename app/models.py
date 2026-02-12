from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class RegisterImageRequest(BaseModel):
    """Request model for registering a Docker image"""
    name: str = Field(..., description="Human-readable name for the image (e.g., 'wordpress', 'nginx-demo')")
    image_name: str = Field(..., description="Docker image name (e.g., 'nginx:latest', 'wordpress:6.0')")
    exposed_port: int = Field(..., description="Port exposed by the container", gt=0, le=65535)
    description: Optional[str] = Field(None, description="Description of the image/application")
    env: Optional[List[str]] = Field(default=[], description="Environment variables for the container")
    health_check_path: Optional[str] = Field(None, description="HTTP path for health checking")
    dependencies: Optional[List[Dict]] = Field(default=[], description="Dependency container configurations")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "nginx-demo",
                "image_name": "nginx:latest",
                "exposed_port": 80,
                "description": "NGINX web server for testing",
                "env": ["NGINX_HOST=localhost"],
                "health_check_path": "/"
            }
        }


class RegisterImageResponse(BaseModel):
    """Response model for image registration"""
    success: bool
    image_id: str = Field(..., description="Human-readable ID for the registered image")
    message: str
    data: Optional[Dict] = None


class StartContainerRequest(BaseModel):
    """Request model for starting a container"""
    image_id: str = Field(..., description="Image ID returned from registration")

    class Config:
        json_schema_extra = {
            "example": {
                "image_id": "nginx-demo"
            }
        }


class ContainerInfo(BaseModel):
    """Container information model"""
    instance_id: str
    image_id: str
    container_id: str
    container_name: str
    image_name: str
    host_port: int
    exposed_port: int
    url: str
    status: str
    created_at: str
    uptime: Optional[str] = None
    credentials: Optional[Dict] = Field(None, description="Default login credentials for the application")


class StartContainerResponse(BaseModel):
    """Response model for starting a container"""
    success: bool
    data: Optional[ContainerInfo] = None
    error: Optional[str] = None


class StopContainerResponse(BaseModel):
    """Response model for stopping a container"""
    success: bool
    message: str
    error: Optional[str] = None


class ContainerStatusResponse(BaseModel):
    """Response model for container status"""
    success: bool
    data: Optional[ContainerInfo] = None
    error: Optional[str] = None


class ListContainersResponse(BaseModel):
    """Response model for listing containers"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None


class ListImagesResponse(BaseModel):
    """Response model for listing registered images"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    uptime: float


class DependencyConfig(BaseModel):
    """Configuration for a dependency container (e.g., MySQL for PrestaShop)"""
    id: str = Field(..., description="Unique identifier for the dependency (used as network alias)")
    image_name: str = Field(..., description="Docker image name for the dependency")
    exposed_port: int = Field(..., description="Port exposed by the dependency container")
    env: List[str] = Field(default=[], description="Environment variables")
    command: Optional[List[str]] = Field(None, description="Command/args to pass to the dependency entrypoint")
    entrypoint: Optional[List[str]] = Field(None, description="Override the dependency entrypoint")
    wait_time: int = Field(default=30000, description="Time to wait for dependency to be ready (ms)")
    health_check: Optional[str] = Field(None, description="Health check path")


class ImageRegistryEntry(BaseModel):
    """Internal model for storing registered images"""
    image_id: str
    name: str
    image_name: str
    exposed_port: int
    host_port: Optional[int] = Field(None, description="Fixed host port to map to (if None, a random port is used)")
    command: Optional[List[str]] = Field(None, description="Command/args to pass to the container entrypoint")
    entrypoint: Optional[List[str]] = Field(None, description="Override the container entrypoint")
    credentials: Optional[Dict] = Field(None, description="Default login credentials (username/password) for reference")
    description: Optional[str]
    env: List[str]
    health_check_path: Optional[str]
    registered_at: str
    dependencies: List[DependencyConfig] = Field(default=[], description="Dependency containers required by this image")
    wait_time: int = Field(default=30000, description="Time to wait for container to be ready (ms)")

    class Config:
        json_schema_extra = {
            "example": {
                "image_id": "nginx-demo",
                "name": "nginx-demo",
                "image_name": "nginx:latest",
                "exposed_port": 80,
                "description": "NGINX web server",
                "env": [],
                "health_check_path": "/",
                "registered_at": "2026-02-04T10:30:00.000Z",
                "dependencies": [],
                "wait_time": 5000
            }
        }
