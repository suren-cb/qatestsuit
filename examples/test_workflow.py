"""
Example QA Test Workflow using Docker Manager API

This script demonstrates the complete workflow:
1. Register a Docker image with human-readable ID
2. Start a container from the registered image
3. Run tests against the container
4. Get container status
5. Stop and cleanup the container
"""

import requests
import time
import sys

API_BASE = "http://localhost:8000"
API_KEY = "your-secret-api-key-here"


class DockerTestManager:
    """Client for Docker Test Manager API"""

    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }

    def register_image(self, name: str, image_name: str, exposed_port: int, **kwargs):
        """Register a Docker image"""
        response = requests.post(
            f"{self.api_base}/api/images/register",
            headers=self.headers,
            json={
                "name": name,
                "image_name": image_name,
                "exposed_port": exposed_port,
                **kwargs
            }
        )
        response.raise_for_status()
        return response.json()

    def list_images(self):
        """List all registered images"""
        response = requests.get(f"{self.api_base}/api/images")
        response.raise_for_status()
        return response.json()

    def start_container(self, image_id: str):
        """Start a container from registered image"""
        response = requests.post(
            f"{self.api_base}/api/containers/start",
            headers=self.headers,
            json={"image_id": image_id}
        )
        response.raise_for_status()
        return response.json()

    def get_container_status(self, instance_id: str):
        """Get container status"""
        response = requests.get(
            f"{self.api_base}/api/containers/{instance_id}"
        )
        response.raise_for_status()
        return response.json()

    def stop_container(self, instance_id: str):
        """Stop a container"""
        response = requests.post(
            f"{self.api_base}/api/containers/{instance_id}/stop",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def list_containers(self):
        """List all running containers"""
        response = requests.get(f"{self.api_base}/api/containers")
        response.raise_for_status()
        return response.json()


def run_tests(url: str) -> bool:
    """Run tests against the container URL"""
    print(f"\n{'='*60}")
    print("Running Tests")
    print(f"{'='*60}")

    tests_passed = True

    # Test 1: Check if server responds
    print("\n▶ Test 1: Server responds with HTTP 200")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("  ✓ PASSED")
        else:
            print(f"  ✗ FAILED: Expected 200, got {response.status_code}")
            tests_passed = False
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_passed = False

    # Test 2: Check response time
    print("\n▶ Test 2: Response time < 1000ms")
    try:
        start = time.time()
        requests.get(url, timeout=10)
        duration = (time.time() - start) * 1000
        if duration < 1000:
            print(f"  ✓ PASSED ({duration:.2f}ms)")
        else:
            print(f"  ✗ FAILED: Response time {duration:.2f}ms exceeds 1000ms")
            tests_passed = False
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_passed = False

    # Test 3: Check content
    print("\n▶ Test 3: Response contains expected content")
    try:
        response = requests.get(url, timeout=10)
        if "nginx" in response.text.lower() or "welcome" in response.text.lower():
            print("  ✓ PASSED")
        else:
            print("  ✗ FAILED: Expected content not found")
            tests_passed = False
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        tests_passed = False

    print(f"\n{'='*60}")
    if tests_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    print(f"{'='*60}\n")

    return tests_passed


def main():
    """Main test workflow"""
    client = DockerTestManager(API_BASE, API_KEY)
    instance_id = None

    try:
        print("QA Docker Test Workflow")
        print("="*60)

        # Step 1: Check if image is already registered
        print("\nStep 1: Checking for registered images...")
        images = client.list_images()
        image_id = "nginx-demo"

        existing_image = next(
            (img for img in images["data"]["images"] if img["image_id"] == image_id),
            None
        )

        if existing_image:
            print(f"✓ Image '{image_id}' already registered")
        else:
            print(f"Registering new image '{image_id}'...")
            result = client.register_image(
                name="nginx-demo",
                image_name="nginx:latest",
                exposed_port=80,
                description="NGINX web server for testing",
                env=[],
                health_check_path="/"
            )
            print(f"✓ Image registered with ID: {result['image_id']}")

        # Step 2: Start container
        print(f"\nStep 2: Starting container from image '{image_id}'...")
        start_result = client.start_container(image_id)
        container_data = start_result["data"]
        instance_id = container_data["instance_id"]
        url = container_data["url"]

        print(f"✓ Container started successfully")
        print(f"  Instance ID: {instance_id}")
        print(f"  Container Name: {container_data['container_name']}")
        print(f"  URL: {url}")
        print(f"  Host Port: {container_data['host_port']}")

        # Step 3: Wait for container to be ready
        print("\nStep 3: Waiting for container to be ready...")
        time.sleep(5)
        print("✓ Container should be ready")

        # Step 4: Get container status
        print("\nStep 4: Getting container status...")
        status_result = client.get_container_status(instance_id)
        status = status_result["data"]
        print(f"✓ Container Status:")
        print(f"  Status: {status['status']}")
        print(f"  Running: {status['running']}")
        print(f"  Uptime: {status['uptime']}")

        # Step 5: Run tests
        print("\nStep 5: Running tests...")
        tests_passed = run_tests(url)

        # Step 6: List all containers
        print("Step 6: Listing all active containers...")
        containers = client.list_containers()
        print(f"✓ Active containers: {containers['data']['count']}")

        # Step 7: Stop container
        print(f"\nStep 7: Stopping container {instance_id}...")
        stop_result = client.stop_container(instance_id)
        print(f"✓ {stop_result['message']}")
        instance_id = None  # Mark as cleaned up

        # Final result
        print("\n" + "="*60)
        if tests_passed:
            print("✓ Workflow completed successfully!")
            print("="*60)
            sys.exit(0)
        else:
            print("✗ Workflow completed with test failures")
            print("="*60)
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to API server")
        print(f"  Make sure the server is running at {API_BASE}")
        print("  Run: uvicorn app.main:app --reload")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")

        # Cleanup on error
        if instance_id:
            try:
                print(f"\nCleaning up container {instance_id}...")
                client.stop_container(instance_id)
                print("✓ Container cleaned up")
            except Exception as cleanup_error:
                print(f"✗ Failed to cleanup: {cleanup_error}")

        sys.exit(1)


if __name__ == "__main__":
    main()
