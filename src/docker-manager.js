const Docker = require('dockerode');
const { v4: uuidv4 } = require('uuid');

class DockerManager {
  constructor() {
    this.docker = new Docker({ socketPath: process.env.DOCKER_HOST || '/var/run/docker.sock' });
    this.containers = new Map(); // containerId -> containerInfo
    this.maxContainers = parseInt(process.env.MAX_CONTAINERS) || 10;
  }

  /**
   * Start a new Docker container from an image
   * @param {string} imageName - Docker image name (e.g., 'nginx:latest')
   * @param {number} exposedPort - Port to expose inside the container
   * @param {Object} options - Additional container options
   * @returns {Promise<Object>} Container information
   */
  async startContainer(imageName, exposedPort, options = {}) {
    try {
      // Check container limit
      if (this.containers.size >= this.maxContainers) {
        throw new Error(`Maximum container limit (${this.maxContainers}) reached`);
      }

      // Pull image if not exists
      await this.pullImage(imageName);

      // Generate unique container ID
      const instanceId = uuidv4();
      const containerName = `qa-test-${instanceId}`;

      // Find available host port
      const hostPort = await this.findAvailablePort();

      // Create container configuration
      const containerConfig = {
        Image: imageName,
        name: containerName,
        ExposedPorts: {
          [`${exposedPort}/tcp`]: {}
        },
        HostConfig: {
          PortBindings: {
            [`${exposedPort}/tcp`]: [{ HostPort: hostPort.toString() }]
          },
          AutoRemove: false,
          ...options.hostConfig
        },
        Env: options.env || [],
        ...options.containerConfig
      };

      // Create and start container
      const container = await this.docker.createContainer(containerConfig);
      await container.start();

      // Get container info
      const containerInfo = await container.inspect();

      // Store container metadata
      const metadata = {
        instanceId,
        containerId: container.id,
        containerName,
        imageName,
        exposedPort,
        hostPort,
        status: 'running',
        createdAt: new Date().toISOString(),
        url: `http://localhost:${hostPort}`,
        container
      };

      this.containers.set(instanceId, metadata);

      return {
        instanceId,
        containerId: container.id,
        containerName,
        imageName,
        hostPort,
        exposedPort,
        url: `http://localhost:${hostPort}`,
        status: 'running',
        createdAt: metadata.createdAt
      };
    } catch (error) {
      throw new Error(`Failed to start container: ${error.message}`);
    }
  }

  /**
   * Stop and remove a container
   * @param {string} instanceId - Instance ID of the container
   * @returns {Promise<Object>} Result of the operation
   */
  async stopContainer(instanceId) {
    try {
      const metadata = this.containers.get(instanceId);

      if (!metadata) {
        throw new Error(`Container with instanceId ${instanceId} not found`);
      }

      const container = metadata.container;

      // Stop container
      await container.stop({ t: 10 }); // 10 seconds timeout

      // Remove container
      await container.remove({ force: true });

      // Remove from tracking
      this.containers.delete(instanceId);

      return {
        instanceId,
        status: 'stopped',
        message: 'Container stopped and removed successfully'
      };
    } catch (error) {
      // If container doesn't exist, clean up metadata
      if (error.statusCode === 404) {
        this.containers.delete(instanceId);
        return {
          instanceId,
          status: 'stopped',
          message: 'Container already removed'
        };
      }
      throw new Error(`Failed to stop container: ${error.message}`);
    }
  }

  /**
   * Get container status and info
   * @param {string} instanceId - Instance ID of the container
   * @returns {Promise<Object>} Container information
   */
  async getContainerStatus(instanceId) {
    try {
      const metadata = this.containers.get(instanceId);

      if (!metadata) {
        throw new Error(`Container with instanceId ${instanceId} not found`);
      }

      const container = metadata.container;
      const containerInfo = await container.inspect();

      return {
        instanceId,
        containerId: container.id,
        containerName: metadata.containerName,
        imageName: metadata.imageName,
        hostPort: metadata.hostPort,
        exposedPort: metadata.exposedPort,
        url: metadata.url,
        status: containerInfo.State.Status,
        running: containerInfo.State.Running,
        createdAt: metadata.createdAt,
        uptime: this.calculateUptime(metadata.createdAt)
      };
    } catch (error) {
      throw new Error(`Failed to get container status: ${error.message}`);
    }
  }

  /**
   * List all active containers
   * @returns {Array<Object>} Array of container information
   */
  async listContainers() {
    const containers = [];

    for (const [instanceId, metadata] of this.containers.entries()) {
      try {
        const status = await this.getContainerStatus(instanceId);
        containers.push(status);
      } catch (error) {
        // Container might have been removed externally
        this.containers.delete(instanceId);
      }
    }

    return containers;
  }

  /**
   * Clean up stale or stopped containers
   * @param {number} maxAgeMs - Maximum age in milliseconds (default: 1 hour)
   * @returns {Promise<Object>} Cleanup results
   */
  async cleanupContainers(maxAgeMs = 3600000) {
    const cleaned = [];
    const errors = [];

    for (const [instanceId, metadata] of this.containers.entries()) {
      try {
        const age = Date.now() - new Date(metadata.createdAt).getTime();

        if (age > maxAgeMs) {
          await this.stopContainer(instanceId);
          cleaned.push(instanceId);
        }
      } catch (error) {
        errors.push({ instanceId, error: error.message });
      }
    }

    return {
      cleaned: cleaned.length,
      cleanedInstances: cleaned,
      errors: errors.length > 0 ? errors : undefined
    };
  }

  /**
   * Pull Docker image
   * @param {string} imageName - Docker image name
   * @returns {Promise<void>}
   */
  async pullImage(imageName) {
    try {
      // Check if image exists locally
      const images = await this.docker.listImages();
      const imageExists = images.some(img =>
        img.RepoTags && img.RepoTags.includes(imageName)
      );

      if (imageExists) {
        return;
      }

      // Pull image
      console.log(`Pulling image: ${imageName}`);
      const stream = await this.docker.pull(imageName);

      // Wait for pull to complete
      await new Promise((resolve, reject) => {
        this.docker.modem.followProgress(stream, (err, res) => {
          if (err) reject(err);
          else resolve(res);
        });
      });

      console.log(`Image pulled successfully: ${imageName}`);
    } catch (error) {
      throw new Error(`Failed to pull image: ${error.message}`);
    }
  }

  /**
   * Find an available port on the host
   * @returns {Promise<number>} Available port number
   */
  async findAvailablePort() {
    const net = require('net');

    return new Promise((resolve, reject) => {
      const server = net.createServer();

      server.listen(0, () => {
        const port = server.address().port;
        server.close(() => resolve(port));
      });

      server.on('error', reject);
    });
  }

  /**
   * Calculate container uptime
   * @param {string} createdAt - ISO timestamp
   * @returns {string} Human-readable uptime
   */
  calculateUptime(createdAt) {
    const ms = Date.now() - new Date(createdAt).getTime();
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  }

  /**
   * Stop all containers
   * @returns {Promise<Object>} Results of stopping all containers
   */
  async stopAllContainers() {
    const results = [];
    const errors = [];

    for (const instanceId of this.containers.keys()) {
      try {
        const result = await this.stopContainer(instanceId);
        results.push(result);
      } catch (error) {
        errors.push({ instanceId, error: error.message });
      }
    }

    return {
      stopped: results.length,
      stoppedInstances: results,
      errors: errors.length > 0 ? errors : undefined
    };
  }
}

module.exports = DockerManager;
