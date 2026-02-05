/**
 * Example QA Test Runner using Docker Manager API
 *
 * This example demonstrates how to:
 * 1. Start a fresh container before tests
 * 2. Run automated tests against the container
 * 3. Clean up the container after tests complete
 */

const axios = require('axios');

// Configuration
const CONFIG = {
  apiBase: process.env.API_BASE || 'http://localhost:3000',
  apiKey: process.env.API_KEY || 'your-secret-api-key-here',

  // Test configuration
  testImage: 'nginx:latest',
  testPort: 80,
  waitTime: 5000 // Wait time for container to be ready (ms)
};

// API Client
class DockerTestClient {
  constructor(config) {
    this.config = config;
    this.client = axios.create({
      baseURL: config.apiBase,
      headers: {
        'X-API-Key': config.apiKey,
        'Content-Type': 'application/json'
      }
    });
  }

  async startContainer(imageName, exposedPort, options = {}) {
    const response = await this.client.post('/api/containers/start', {
      imageName,
      exposedPort,
      ...options
    });
    return response.data.data;
  }

  async stopContainer(instanceId) {
    const response = await this.client.post(`/api/containers/${instanceId}/stop`);
    return response.data.data;
  }

  async getContainerStatus(instanceId) {
    const response = await this.client.get(`/api/containers/${instanceId}`);
    return response.data.data;
  }

  async listContainers() {
    const response = await this.client.get('/api/containers');
    return response.data.data;
  }

  async cleanup(maxAgeMs) {
    const response = await this.client.post('/api/containers/cleanup', { maxAgeMs });
    return response.data.data;
  }
}

// Test Suite
class TestSuite {
  constructor(name) {
    this.name = name;
    this.tests = [];
    this.results = {
      passed: 0,
      failed: 0,
      total: 0
    };
  }

  addTest(name, testFn) {
    this.tests.push({ name, testFn });
  }

  async run(url) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`Running Test Suite: ${this.name}`);
    console.log(`Target URL: ${url}`);
    console.log(`${'='.repeat(60)}\n`);

    for (const test of this.tests) {
      this.results.total++;
      try {
        console.log(`▶ Running: ${test.name}`);
        await test.testFn(url);
        this.results.passed++;
        console.log(`  ✓ PASSED\n`);
      } catch (error) {
        this.results.failed++;
        console.log(`  ✗ FAILED: ${error.message}\n`);
      }
    }

    this.printResults();
    return this.results.failed === 0;
  }

  printResults() {
    console.log(`${'='.repeat(60)}`);
    console.log('Test Results:');
    console.log(`  Total:  ${this.results.total}`);
    console.log(`  Passed: ${this.results.passed}`);
    console.log(`  Failed: ${this.results.failed}`);
    console.log(`${'='.repeat(60)}\n`);
  }
}

// Example Tests
async function exampleTests(url) {
  const suite = new TestSuite('NGINX Basic Tests');

  // Test 1: Server responds with 200
  suite.addTest('Server returns HTTP 200', async (url) => {
    const response = await axios.get(url);
    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }
  });

  // Test 2: Content type is HTML
  suite.addTest('Response content-type is HTML', async (url) => {
    const response = await axios.get(url);
    const contentType = response.headers['content-type'];
    if (!contentType.includes('text/html')) {
      throw new Error(`Expected HTML content-type, got ${contentType}`);
    }
  });

  // Test 3: Response contains expected text
  suite.addTest('Response contains "Welcome to nginx"', async (url) => {
    const response = await axios.get(url);
    if (!response.data.includes('Welcome to nginx')) {
      throw new Error('Expected text not found in response');
    }
  });

  // Test 4: Response time is acceptable
  suite.addTest('Response time < 1000ms', async (url) => {
    const start = Date.now();
    await axios.get(url);
    const duration = Date.now() - start;
    if (duration > 1000) {
      throw new Error(`Response time ${duration}ms exceeds 1000ms`);
    }
  });

  return await suite.run(url);
}

// Main Test Runner
async function main() {
  const client = new DockerTestClient(CONFIG);
  let instanceId = null;

  try {
    console.log('QA Docker Test Runner');
    console.log('=====================\n');

    // Step 1: Start container
    console.log('Step 1: Starting test container...');
    const containerInfo = await client.startContainer(
      CONFIG.testImage,
      CONFIG.testPort
    );

    instanceId = containerInfo.instanceId;
    const url = containerInfo.url;

    console.log(`✓ Container started successfully`);
    console.log(`  Instance ID: ${instanceId}`);
    console.log(`  URL: ${url}`);
    console.log(`  Container: ${containerInfo.containerName}\n`);

    // Step 2: Wait for container to be ready
    console.log(`Step 2: Waiting ${CONFIG.waitTime}ms for container to be ready...`);
    await new Promise(resolve => setTimeout(resolve, CONFIG.waitTime));

    // Verify container is running
    const status = await client.getContainerStatus(instanceId);
    console.log(`✓ Container status: ${status.status}`);
    console.log(`  Uptime: ${status.uptime}\n`);

    // Step 3: Run tests
    console.log('Step 3: Running tests...');
    const testsPassed = await exampleTests(url);

    // Step 4: Show all active containers
    console.log('Step 4: Listing all active containers...');
    const containers = await client.listContainers();
    console.log(`Active containers: ${containers.count}\n`);

    // Step 5: Cleanup
    console.log('Step 5: Cleaning up container...');
    await client.stopContainer(instanceId);
    console.log('✓ Container stopped and removed\n');

    instanceId = null; // Mark as cleaned up

    // Exit with appropriate code
    if (testsPassed) {
      console.log('✓ All tests passed!');
      process.exit(0);
    } else {
      console.log('✗ Some tests failed!');
      process.exit(1);
    }

  } catch (error) {
    console.error('\n✗ Error:', error.message);
    if (error.response) {
      console.error('API Response:', error.response.data);
    }

    // Cleanup on error
    if (instanceId) {
      try {
        console.log('\nCleaning up container after error...');
        await client.stopContainer(instanceId);
        console.log('✓ Container cleaned up');
      } catch (cleanupError) {
        console.error('Failed to cleanup container:', cleanupError.message);
      }
    }

    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}

module.exports = { DockerTestClient, TestSuite };
