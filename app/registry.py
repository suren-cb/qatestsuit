import json
import os
from typing import Any, Dict, Optional, List
from datetime import datetime
from app.models import ImageRegistryEntry, DependencyConfig
import re


class ImageRegistry:
    """Manages registration and storage of Docker images"""

    def __init__(self, db_file: str = "data/registry.json"):
        self.db_file = db_file
        self.images: Dict[str, ImageRegistryEntry] = {}
        self._ensure_db_dir()
        self._load_registry()

    def _ensure_db_dir(self):
        """Ensure the database directory exists"""
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

    def _load_registry(self):
        """Load registry from file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    data = json.load(f)
                    for image_id, image_data in data.items():
                        self.images[image_id] = ImageRegistryEntry(**image_data)
            except Exception as e:
                print(f"Warning: Failed to load registry: {e}")
                self.images = {}

    def _save_registry(self):
        """Save registry to file"""
        try:
            data = {
                image_id: image.model_dump()
                for image_id, image in self.images.items()
            }
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving registry: {e}")
            raise

    def _generate_image_id(self, name: str) -> str:
        """
        Generate a human-readable image ID from the name
        Converts name to lowercase, replaces spaces/special chars with hyphens
        """
        # Convert to lowercase and replace non-alphanumeric chars with hyphens
        image_id = re.sub(r'[^a-z0-9]+', '-', name.lower())
        # Remove leading/trailing hyphens
        image_id = image_id.strip('-')

        # If ID already exists, append a number
        if image_id in self.images:
            counter = 2
            while f"{image_id}-{counter}" in self.images:
                counter += 1
            image_id = f"{image_id}-{counter}"

        return image_id

    def register_image(
        self,
        name: str,
        image_name: str,
        exposed_port: int,
        description: Optional[str] = None,
        env: Optional[List[str]] = None,
        health_check_path: Optional[str] = None,
        dependencies: Optional[List[Dict]] = None
    ) -> str:
        """
        Register a Docker image and return its human-readable ID

        Args:
            name: Human-readable name for the image
            image_name: Docker image name (e.g., 'nginx:latest')
            exposed_port: Port exposed by the container
            description: Optional description
            env: Optional environment variables
            health_check_path: Optional health check path
            dependencies: Optional list of dependency configs

        Returns:
            image_id: Human-readable ID for the image
        """
        image_id = self._generate_image_id(name)

        dep_models = []
        if dependencies:
            for dep in dependencies:
                dep_models.append(DependencyConfig(**dep))

        entry = ImageRegistryEntry(
            image_id=image_id,
            name=name,
            image_name=image_name,
            exposed_port=exposed_port,
            description=description,
            env=env or [],
            health_check_path=health_check_path,
            registered_at=datetime.utcnow().isoformat(),
            dependencies=dep_models,
        )

        self.images[image_id] = entry
        self._save_registry()

        return image_id

    def get_image(self, image_id: str) -> Optional[ImageRegistryEntry]:
        """Get image by ID"""
        return self.images.get(image_id)

    def list_images(self) -> List[ImageRegistryEntry]:
        """List all registered images"""
        return list(self.images.values())

    def delete_image(self, image_id: str) -> bool:
        """Delete an image from registry"""
        if image_id in self.images:
            del self.images[image_id]
            self._save_registry()
            return True
        return False

    def image_exists(self, image_id: str) -> bool:
        """Check if an image exists"""
        return image_id in self.images

    def update_image(
        self,
        image_id: str,
        name: Optional[str] = None,
        image_name: Optional[str] = None,
        exposed_port: Optional[int] = None,
        description: Optional[str] = None,
        env: Optional[List[str]] = None,
        health_check_path: Optional[str] = None
    ) -> bool:
        """Update an existing image registration"""
        if image_id not in self.images:
            return False

        entry = self.images[image_id]

        if name is not None:
            entry.name = name
        if image_name is not None:
            entry.image_name = image_name
        if exposed_port is not None:
            entry.exposed_port = exposed_port
        if description is not None:
            entry.description = description
        if env is not None:
            entry.env = env
        if health_check_path is not None:
            entry.health_check_path = health_check_path

        self._save_registry()
        return True

    def clear_registry(self):
        """Clear all registered images"""
        self.images = {}
        self._save_registry()

    def seed_from_config(self, config_file: str) -> int:
        """
        Seed registry with preconfigured images from a JSON config file.
        Only adds images whose IDs are not already registered.

        Returns:
            Number of images seeded
        """
        if not os.path.exists(config_file):
            print(f"Config file not found: {config_file}")
            return 0

        try:
            with open(config_file, 'r') as f:
                data = json.load(f)

            seeded = 0
            for img in data.get("images", []):
                image_id = img["id"]
                if image_id in self.images:
                    continue

                # Parse dependencies if present
                dependencies = []
                for dep in img.get("dependencies", []):
                    dependencies.append(DependencyConfig(
                        id=dep["id"],
                        image_name=dep["imageName"],
                        exposed_port=dep["exposedPort"],
                        env=dep.get("env", []),
                        wait_time=dep.get("waitTime", 30000),
                        health_check=dep.get("healthCheck"),
                    ))

                entry = ImageRegistryEntry(
                    image_id=image_id,
                    name=img["name"],
                    image_name=img["imageName"],
                    exposed_port=img["exposedPort"],
                    host_port=img.get("hostPort"),
                    command=img.get("command"),
                    entrypoint=img.get("entrypoint"),
                    credentials=img.get("credentials"),
                    description=img.get("description"),
                    env=img.get("env", []),
                    health_check_path=img.get("healthCheck"),
                    registered_at=datetime.utcnow().isoformat(),
                    dependencies=dependencies,
                    wait_time=img.get("waitTime", 30000),
                )

                self.images[image_id] = entry
                seeded += 1

            if seeded > 0:
                self._save_registry()

            return seeded
        except Exception as e:
            print(f"Error seeding from config: {e}")
            return 0
