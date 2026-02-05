require('dotenv').config();
const express = require('express');
const cors = require('cors');
const DockerManager = require('./docker-manager');

const app = express();
const dockerManager = new DockerManager();

// Middleware
app.use(cors());
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// API Key authentication middleware (optional)
const authenticateApiKey = (req, res, next) => {
  const apiKey = process.env.API_KEY;

  if (!apiKey) {
    return next(); // Skip auth if no API key is set
  }

  const requestApiKey = req.headers['x-api-key'];

  if (!requestApiKey || requestApiKey !== apiKey) {
    return res.status(401).json({
      success: false,
      error: 'Unauthorized: Invalid API key'
    });
  }

  next();
};

// Apply authentication to protected routes
app.use('/api/containers', authenticateApiKey);

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

/**
 * Get API information
 */
app.get('/api/info', (req, res) => {
  res.json({
    name: 'QA Docker Test Manager',
    version: '1.0.0',
    description: 'Docker container management API for QA testing',
    endpoints: {
      'POST /api/containers/start': 'Start a new container',
      'POST /api/containers/:instanceId/stop': 'Stop a container',
      'GET /api/containers/:instanceId': 'Get container status',
      'GET /api/containers': 'List all containers',
      'POST /api/containers/cleanup': 'Cleanup stale containers',
      'POST /api/containers/stop-all': 'Stop all containers'
    }
  });
});

/**
 * Start a new container
 * POST /api/containers/start
 * Body: {
 *   imageName: string,
 *   exposedPort: number,
 *   env?: string[],
 *   options?: object
 * }
 */
app.post('/api/containers/start', async (req, res) => {
  try {
    const { imageName, exposedPort, env, options } = req.body;

    // Validation
    if (!imageName) {
      return res.status(400).json({
        success: false,
        error: 'imageName is required'
      });
    }

    if (!exposedPort || typeof exposedPort !== 'number') {
      return res.status(400).json({
        success: false,
        error: 'exposedPort is required and must be a number'
      });
    }

    // Start container
    const containerInfo = await dockerManager.startContainer(
      imageName,
      exposedPort,
      { env, ...options }
    );

    res.status(201).json({
      success: true,
      data: containerInfo
    });
  } catch (error) {
    console.error('Error starting container:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Stop a container
 * POST /api/containers/:instanceId/stop
 */
app.post('/api/containers/:instanceId/stop', async (req, res) => {
  try {
    const { instanceId } = req.params;

    const result = await dockerManager.stopContainer(instanceId);

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error stopping container:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Get container status
 * GET /api/containers/:instanceId
 */
app.get('/api/containers/:instanceId', async (req, res) => {
  try {
    const { instanceId } = req.params;

    const status = await dockerManager.getContainerStatus(instanceId);

    res.json({
      success: true,
      data: status
    });
  } catch (error) {
    console.error('Error getting container status:', error);
    res.status(404).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * List all containers
 * GET /api/containers
 */
app.get('/api/containers', async (req, res) => {
  try {
    const containers = await dockerManager.listContainers();

    res.json({
      success: true,
      data: {
        count: containers.length,
        containers
      }
    });
  } catch (error) {
    console.error('Error listing containers:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Cleanup stale containers
 * POST /api/containers/cleanup
 * Body: { maxAgeMs?: number }
 */
app.post('/api/containers/cleanup', async (req, res) => {
  try {
    const { maxAgeMs } = req.body;

    const result = await dockerManager.cleanupContainers(maxAgeMs);

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error cleaning up containers:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Stop all containers
 * POST /api/containers/stop-all
 */
app.post('/api/containers/stop-all', async (req, res) => {
  try {
    const result = await dockerManager.stopAllContainers();

    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error stopping all containers:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * 404 handler
 */
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Endpoint not found'
  });
});

/**
 * Error handler
 */
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error'
  });
});

// Start server
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';

const server = app.listen(PORT, HOST, () => {
  console.log(`QA Docker Test Manager API running on http://${HOST}:${PORT}`);
  console.log(`Health check: http://${HOST}:${PORT}/health`);
  console.log(`API info: http://${HOST}:${PORT}/api/info`);
});

// Cleanup on shutdown
const gracefulShutdown = async (signal) => {
  console.log(`\n${signal} received. Cleaning up...`);

  try {
    // Stop all containers
    await dockerManager.stopAllContainers();
    console.log('All containers stopped.');

    // Close server
    server.close(() => {
      console.log('Server closed.');
      process.exit(0);
    });
  } catch (error) {
    console.error('Error during cleanup:', error);
    process.exit(1);
  }
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Auto cleanup interval
if (process.env.AUTO_CLEANUP_INTERVAL_MS) {
  const interval = parseInt(process.env.AUTO_CLEANUP_INTERVAL_MS);
  setInterval(async () => {
    console.log('Running auto cleanup...');
    try {
      const result = await dockerManager.cleanupContainers();
      if (result.cleaned > 0) {
        console.log(`Auto cleanup: removed ${result.cleaned} containers`);
      }
    } catch (error) {
      console.error('Auto cleanup error:', error);
    }
  }, interval);
}

module.exports = app;
