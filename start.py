#!/usr/bin/env python3
"""
QA Docker Test Manager - Python Startup Script
This script starts the FastAPI server using uvicorn
"""

import os
import sys
import subprocess
from pathlib import Path


def check_docker():
    """Check if Docker is running"""
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_env_file():
    """Check if .env file exists, create from example if not"""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists():
        print("⚠️  Warning: .env file not found")
        if env_example.exists():
            print("Creating .env file from .env.example...")
            env_file.write_text(env_example.read_text())
            print("✓ Created .env file")
        else:
            print("Warning: .env.example not found either")


def main():
    """Main entry point"""
    print("QA Docker Test Manager")
    print("=" * 40)
    print()

    # Check Docker
    if not check_docker():
        print("❌ Error: Docker is not running")
        print("Please start Docker Desktop or Docker daemon")
        sys.exit(1)

    print("✓ Docker is running")

    # Check .env file
    check_env_file()

    # Get host and port from environment or use defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print()
    print("Starting FastAPI server...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print()
    print("API Documentation:")
    print(f"  - Swagger UI: http://localhost:{port}/docs")
    print(f"  - ReDoc: http://localhost:{port}/redoc")
    print(f"  - Health Check: http://localhost:{port}/health")
    print()
    print("Press Ctrl+C to stop the server")
    print()

    # Start the server
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True
        )
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        sys.exit(0)
    except ImportError:
        print("❌ Error: uvicorn not found")
        print("Run: uv sync")
        sys.exit(1)


if __name__ == "__main__":
    main()
