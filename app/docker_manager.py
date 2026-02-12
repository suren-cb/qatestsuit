import docker
import asyncio
import socket
from typing import Dict, Optional, List
from datetime import datetime
import shortuuid


class DockerManager:
    """Manages Docker container lifecycle"""

    def __init__(self, docker_host: str = "unix:///var/run/docker.sock", public_host: str = "localhost"):
        try:
            self.client = docker.DockerClient(base_url=docker_host)
            self.containers: Dict[str, Dict] = {}
            self.max_containers = 10
            self.public_host = public_host
        except Exception as e:
            raise Exception(f"Failed to connect to Docker: {e}")

    def _find_available_port(self) -> int:
        """Find an available port on the host"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def _generate_instance_id(self) -> str:
        """Generate a unique short instance ID"""
        return shortuuid.uuid()[:8]

    def _calculate_uptime(self, created_at: str) -> str:
        """Calculate human-readable uptime"""
        try:
            created = datetime.fromisoformat(created_at)
            delta = datetime.utcnow() - created
            seconds = int(delta.total_seconds())

            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                minutes = seconds // 60
                secs = seconds % 60
                return f"{minutes}m {secs}s"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        except:
            return "unknown"

    async def pull_image(self, image_name: str) -> bool:
        """Pull Docker image if not exists"""
        try:
            # Check if image exists locally
            try:
                self.client.images.get(image_name)
                print(f"Image {image_name} already exists locally")
                return True
            except docker.errors.ImageNotFound:
                pass

            # Pull image
            print(f"Pulling image: {image_name}")
            self.client.images.pull(image_name)
            print(f"Image pulled successfully: {image_name}")
            return True
        except Exception as e:
            raise Exception(f"Failed to pull image {image_name}: {e}")

    def _create_network(self, network_name: str):
        """Create a Docker network, removing existing one if necessary"""
        try:
            existing = self.client.networks.get(network_name)
            existing.remove()
        except docker.errors.NotFound:
            pass
        return self.client.networks.create(network_name, driver="bridge")

    def _remove_network(self, network_name: str):
        """Remove a Docker network if it exists"""
        try:
            network = self.client.networks.get(network_name)
            network.remove()
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"Warning: Failed to remove network {network_name}: {e}")

    async def _start_dependency(self, dep_config, network_name: str) -> Dict:
        """Start a dependency container on the given network"""
        await self.pull_image(dep_config["image_name"])

        dep_id = dep_config["id"]
        container_name = f"qa-dep-{dep_id}"

        # Remove existing dependency container with same name
        try:
            existing = self.client.containers.get(container_name)
            existing.stop(timeout=5)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

        host_port = self._find_available_port()

        dep_container_config = {
            "image": dep_config["image_name"],
            "name": container_name,
            "ports": {f"{dep_config['exposed_port']}/tcp": host_port},
            "detach": True,
            "environment": dep_config.get("env", []),
            "auto_remove": False,
            "network": network_name,
        }

        if dep_config.get("command"):
            dep_container_config["command"] = dep_config["command"]

        if dep_config.get("entrypoint"):
            dep_container_config["entrypoint"] = dep_config["entrypoint"]

        container = self.client.containers.run(**dep_container_config)

        # Set network alias so the main container can reach it by dependency id
        network = self.client.networks.get(network_name)
        network.disconnect(container)
        network.connect(container, aliases=[dep_id])

        wait_seconds = dep_config.get("wait_time", 30000) / 1000
        print(f"Waiting {wait_seconds}s for dependency '{dep_id}' to be ready...")
        await asyncio.sleep(wait_seconds)

        return {
            "dep_id": dep_id,
            "container": container,
            "container_name": container_name,
            "host_port": host_port,
        }

    async def start_container(
        self,
        image_id: str,
        image_name: str,
        exposed_port: int,
        env: Optional[List[str]] = None,
        dependencies: Optional[List[Dict]] = None,
        host_port: Optional[int] = None,
        command: Optional[List[str]] = None,
        entrypoint: Optional[List[str]] = None
    ) -> Dict:
        """
        Start a new Docker container

        Args:
            image_id: Human-readable image ID
            image_name: Docker image name
            exposed_port: Port exposed by the container
            env: Environment variables
            dependencies: List of dependency container configs
            host_port: Fixed host port to bind to (if None, a random port is used)
            command: Command/args to pass to the container entrypoint
            entrypoint: Override the container entrypoint

        Returns:
            Dictionary with container information
        """
        try:
            # Check container limit
            if len(self.containers) >= self.max_containers:
                raise Exception(f"Maximum container limit ({self.max_containers}) reached")

            # Pull image
            await self.pull_image(image_name)

            # Generate instance ID and container name
            instance_id = self._generate_instance_id()
            container_name = f"qa-{image_id}-{instance_id}"

            # Use fixed host port if provided, otherwise find an available one
            if host_port is None:
                host_port = self._find_available_port()

            network_name = None
            dep_containers = []

            # Start dependency containers if any
            if dependencies:
                network_name = f"qa-net-{image_id}-{instance_id}"
                self._create_network(network_name)
                print(f"Created network: {network_name}")

                for dep_config in dependencies:
                    dep_info = await self._start_dependency(dep_config, network_name)
                    dep_containers.append(dep_info)
                    print(f"Dependency '{dep_info['dep_id']}' started on port {dep_info['host_port']}")

            # Replace {PUBLIC_HOST} placeholder in env vars
            resolved_env = [
                e.replace("{PUBLIC_HOST}", self.public_host) for e in (env or [])
            ]

            # Create container configuration
            container_config = {
                "image": image_name,
                "name": container_name,
                "ports": {f"{exposed_port}/tcp": host_port},
                "detach": True,
                "environment": resolved_env,
                "auto_remove": False
            }

            if command:
                container_config["command"] = command

            if entrypoint:
                container_config["entrypoint"] = entrypoint

            if network_name:
                container_config["network"] = network_name

            # Start container
            container = self.client.containers.run(**container_config)

            # Store metadata
            created_at = datetime.utcnow().isoformat()
            metadata = {
                "instance_id": instance_id,
                "image_id": image_id,
                "container_id": container.id,
                "container_name": container_name,
                "image_name": image_name,
                "exposed_port": exposed_port,
                "host_port": host_port,
                "url": f"http://{self.public_host}:{host_port}",
                "status": "running",
                "created_at": created_at,
                "container": container,
                "network_name": network_name,
                "dep_containers": dep_containers,
            }

            self.containers[instance_id] = metadata

            return {
                "instance_id": instance_id,
                "image_id": image_id,
                "container_id": container.id,
                "container_name": container_name,
                "image_name": image_name,
                "host_port": host_port,
                "exposed_port": exposed_port,
                "url": f"http://{self.public_host}:{host_port}",
                "status": "running",
                "created_at": created_at
            }

        except Exception as e:
            raise Exception(f"Failed to start container: {e}")

    async def stop_container(self, instance_id: str) -> Dict:
        """
        Stop and remove a container and its dependencies

        Args:
            instance_id: Instance ID of the container

        Returns:
            Dictionary with operation result
        """
        try:
            if instance_id not in self.containers:
                raise Exception(f"Container with instance_id {instance_id} not found")

            metadata = self.containers[instance_id]
            container = metadata["container"]

            # Stop and remove main container
            try:
                container.stop(timeout=10)
                container.remove(force=True)
            except docker.errors.NotFound:
                pass

            # Stop and remove dependency containers
            for dep_info in metadata.get("dep_containers", []):
                try:
                    dep_container = dep_info["container"]
                    dep_container.stop(timeout=10)
                    dep_container.remove(force=True)
                    print(f"Stopped dependency: {dep_info['dep_id']}")
                except docker.errors.NotFound:
                    pass
                except Exception as e:
                    print(f"Warning: Failed to stop dependency {dep_info['dep_id']}: {e}")

            # Remove network
            if metadata.get("network_name"):
                self._remove_network(metadata["network_name"])

            # Remove from tracking
            del self.containers[instance_id]

            return {
                "instance_id": instance_id,
                "status": "stopped",
                "message": "Container stopped and removed successfully"
            }

        except Exception as e:
            # Clean up metadata even if container doesn't exist
            if instance_id in self.containers:
                del self.containers[instance_id]
            raise Exception(f"Failed to stop container: {e}")

    async def get_container_status(self, instance_id: str) -> Dict:
        """
        Get container status and information

        Args:
            instance_id: Instance ID of the container

        Returns:
            Dictionary with container information
        """
        try:
            if instance_id not in self.containers:
                raise Exception(f"Container with instance_id {instance_id} not found")

            metadata = self.containers[instance_id]
            container = metadata["container"]

            # Refresh container info
            try:
                container.reload()
                status = container.status
                running = container.status == "running"
            except docker.errors.NotFound:
                status = "removed"
                running = False

            return {
                "instance_id": instance_id,
                "image_id": metadata["image_id"],
                "container_id": container.id,
                "container_name": metadata["container_name"],
                "image_name": metadata["image_name"],
                "host_port": metadata["host_port"],
                "exposed_port": metadata["exposed_port"],
                "url": metadata["url"],
                "status": status,
                "running": running,
                "created_at": metadata["created_at"],
                "uptime": self._calculate_uptime(metadata["created_at"])
            }

        except Exception as e:
            raise Exception(f"Failed to get container status: {e}")

    async def list_containers(self) -> List[Dict]:
        """List all active containers"""
        containers = []

        for instance_id in list(self.containers.keys()):
            try:
                status = await self.get_container_status(instance_id)
                containers.append(status)
            except Exception:
                # Remove stale entries
                if instance_id in self.containers:
                    del self.containers[instance_id]

        return containers

    async def stop_all_containers(self) -> Dict:
        """Stop all managed containers"""
        results = []
        errors = []

        for instance_id in list(self.containers.keys()):
            try:
                result = await self.stop_container(instance_id)
                results.append(result)
            except Exception as e:
                errors.append({"instance_id": instance_id, "error": str(e)})

        return {
            "stopped": len(results),
            "stopped_instances": results,
            "errors": errors if errors else None
        }

    async def cleanup_stale_containers(self, max_age_seconds: int = 3600) -> Dict:
        """Clean up containers older than max_age_seconds"""
        cleaned = []
        errors = []

        for instance_id, metadata in list(self.containers.items()):
            try:
                created = datetime.fromisoformat(metadata["created_at"])
                age = (datetime.utcnow() - created).total_seconds()

                if age > max_age_seconds:
                    await self.stop_container(instance_id)
                    cleaned.append(instance_id)
            except Exception as e:
                errors.append({"instance_id": instance_id, "error": str(e)})

        return {
            "cleaned": len(cleaned),
            "cleaned_instances": cleaned,
            "errors": errors if errors else None
        }

    def set_max_containers(self, max_containers: int):
        """Set maximum number of concurrent containers"""
        self.max_containers = max_containers
