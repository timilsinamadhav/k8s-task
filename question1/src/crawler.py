#!/usr/bin/env python3
"""
Kubernetes Crawler Application with Proxy Usage Telemetry
"""

import os
import sys
import time
import random
import logging
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import signal
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'crawler_requests_total',
    'Total number of requests made by crawler',
    ['pod_name', 'proxy_vendor', 'destination_domain', 'protocol', 'status_code']
)

REQUEST_DURATION = Histogram(
    'crawler_request_duration_seconds',
    'Request duration in seconds',
    ['pod_name', 'proxy_vendor', 'destination_domain', 'protocol']
)

BYTES_SENT = Counter(
    'crawler_bytes_sent_total',
    'Total bytes sent',
    ['pod_name', 'proxy_vendor', 'destination_domain']
)

BYTES_RECEIVED = Counter(
    'crawler_bytes_received_total',
    'Total bytes received',
    ['pod_name', 'proxy_vendor', 'destination_domain']
)

ACTIVE_CONNECTIONS = Gauge(
    'crawler_active_connections',
    'Number of active connections',
    ['pod_name', 'proxy_vendor']
)

@dataclass
class ProxyVendor:
    name: str
    weight: int

@dataclass
class CrawlerConfig:
    proxy_url: str
    proxy_vendors: List[ProxyVendor]
    targets: List[str]
    interval_seconds: int
    concurrency: int
    http2_enabled: bool
    pod_name: str
    pod_namespace: str

class ProxyCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.session = None
        self.running = True
        self.tasks = []
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    async def _create_session(self) -> aiohttp.ClientSession:
        """Create aiohttp session with proper configuration"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': f'KubernetesCrawler/{self.config.pod_name}',
                'Accept': 'application/json, text/html, */*'
            }
        )
    
    def _select_proxy_vendor(self) -> str:
        """Select proxy vendor based on configured weights"""
        total_weight = sum(vendor.weight for vendor in self.config.proxy_vendors)
        rand_val = random.randint(1, total_weight)
        
        current_weight = 0
        for vendor in self.config.proxy_vendors:
            current_weight += vendor.weight
            if rand_val <= current_weight:
                return vendor.name
        
        # Fallback to first vendor
        return self.config.proxy_vendors[0].name
    
    def _get_destination_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return "unknown"
    
    def _determine_protocol(self, url: str) -> str:
        """Determine protocol from URL"""
        return "https" if url.startswith("https://") else "http"
    
    async def _make_request(self, target_url: str, proxy_vendor: str) -> Dict[str, Any]:
        """Make HTTP request through proxy with telemetry"""
        destination_domain = self._get_destination_domain(target_url)
        protocol = self._determine_protocol(target_url)
        
        # Update active connections metric
        ACTIVE_CONNECTIONS.labels(
            pod_name=self.config.pod_name,
            proxy_vendor=proxy_vendor
        ).inc()
        
        start_time = time.time()
        status_code = "unknown"
        bytes_sent = 0
        bytes_received = 0
        
        try:
            # Prepare proxy configuration
            proxy_config = {
                'http': self.config.proxy_url,
                'https': self.config.proxy_url
            } if self.config.proxy_url else None
            
            # Add vendor identification to headers
            headers = {
                'X-Proxy-Vendor': proxy_vendor,
                'X-Pod-Name': self.config.pod_name,
                'X-Pod-Namespace': self.config.pod_namespace
            }
            
            # Make the request
            async with self.session.get(
                target_url,
                proxy=self.config.proxy_url if self.config.proxy_url else None,
                headers=headers
            ) as response:
                status_code = str(response.status)
                content = await response.read()
                bytes_received = len(content)
                
                # Estimate bytes sent (headers + body)
                bytes_sent = len(str(response.request_info.headers)) + len(target_url)
                
                logger.info(
                    f"Request to {destination_domain} via {proxy_vendor}: "
                    f"status={status_code}, sent={bytes_sent}B, received={bytes_received}B"
                )
                
                return {
                    'status_code': status_code,
                    'bytes_sent': bytes_sent,
                    'bytes_received': bytes_received,
                    'duration': time.time() - start_time,
                    'destination_domain': destination_domain,
                    'protocol': protocol
                }
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            status_code = "error"
            return {
                'status_code': status_code,
                'bytes_sent': bytes_sent,
                'bytes_received': bytes_received,
                'duration': time.time() - start_time,
                'destination_domain': destination_domain,
                'protocol': protocol,
                'error': str(e)
            }
        finally:
            # Update metrics
            duration = time.time() - start_time
            
            REQUEST_COUNT.labels(
                pod_name=self.config.pod_name,
                proxy_vendor=proxy_vendor,
                destination_domain=destination_domain,
                protocol=protocol,
                status_code=status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                pod_name=self.config.pod_name,
                proxy_vendor=proxy_vendor,
                destination_domain=destination_domain,
                protocol=protocol
            ).observe(duration)
            
            BYTES_SENT.labels(
                pod_name=self.config.pod_name,
                proxy_vendor=proxy_vendor,
                destination_domain=destination_domain
            ).inc(bytes_sent)
            
            BYTES_RECEIVED.labels(
                pod_name=self.config.pod_name,
                proxy_vendor=proxy_vendor,
                destination_domain=destination_domain
            ).inc(bytes_received)
            
            # Decrement active connections
            ACTIVE_CONNECTIONS.labels(
                pod_name=self.config.pod_name,
                proxy_vendor=proxy_vendor
            ).dec()
    
    async def _crawler_worker(self, worker_id: int):
        """Worker coroutine that continuously makes requests"""
        logger.info(f"Starting crawler worker {worker_id}")
        
        while self.running:
            try:
                # Select random target and proxy vendor
                target_url = random.choice(self.config.targets)
                proxy_vendor = self._select_proxy_vendor()
                
                # Add protocol if not present
                if not target_url.startswith(('http://', 'https://')):
                    protocol = 'https://' if random.choice([True, False]) else 'http://'
                    target_url = f"{protocol}{target_url}"
                
                # Make request
                await self._make_request(target_url, proxy_vendor)
                
                # Wait before next request
                await asyncio.sleep(self.config.interval_seconds + random.uniform(-1, 1))
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def start(self):
        """Start the crawler with multiple workers"""
        logger.info(f"Starting crawler with {self.config.concurrency} workers")
        
        # Create HTTP session
        self.session = await self._create_session()
        
        # Start worker tasks
        self.tasks = [
            asyncio.create_task(self._crawler_worker(i))
            for i in range(self.config.concurrency)
        ]
        
        try:
            # Wait for all tasks to complete
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")
        finally:
            # Cleanup
            if self.session:
                await self.session.close()
    
    async def stop(self):
        """Stop the crawler gracefully"""
        logger.info("Stopping crawler...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close session
        if self.session:
            await self.session.close()

def parse_proxy_vendors(vendors_str: str) -> List[ProxyVendor]:
    """Parse proxy vendors from environment variable"""
    vendors = []
    for vendor_config in vendors_str.split(','):
        parts = vendor_config.strip().split(':')
        if len(parts) == 2:
            name, weight = parts
            vendors.append(ProxyVendor(name.strip(), int(weight.strip())))
        else:
            vendors.append(ProxyVendor(parts[0].strip(), 10))  # Default weight
    return vendors

def load_config() -> CrawlerConfig:
    """Load configuration from environment variables"""
    return CrawlerConfig(
        proxy_url=os.getenv('PROXY_URL', ''),
        proxy_vendors=parse_proxy_vendors(
            os.getenv('PROXY_VENDORS', 'vendor-a:30,vendor-b:40,vendor-c:30')
        ),
        targets=os.getenv('CRAWLER_TARGETS', 'httpbin.org,jsonplaceholder.typicode.com').split(','),
        interval_seconds=int(os.getenv('CRAWLER_INTERVAL', '10')),
        concurrency=int(os.getenv('CRAWLER_CONCURRENCY', '3')),
        http2_enabled=os.getenv('HTTP2_ENABLED', 'true').lower() == 'true',
        pod_name=os.getenv('POD_NAME', socket.gethostname()),
        pod_namespace=os.getenv('POD_NAMESPACE', 'crawlers')
    )

async def health_check_server():
    """Simple health check HTTP server"""
    from aiohttp import web
    
    async def health_handler(request):
        return web.json_response({'status': 'healthy', 'timestamp': time.time()})
    
    async def ready_handler(request):
        return web.json_response({'status': 'ready', 'timestamp': time.time()})
    
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_get('/ready', ready_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logger.info("Health check server started on port 8080")
    return runner

async def main():
    """Main application entry point"""
    # Load configuration
    config = load_config()
    
    logger.info(f"Starting crawler application:")
    logger.info(f"  Pod: {config.pod_name}")
    logger.info(f"  Namespace: {config.pod_namespace}")
    logger.info(f"  Proxy URL: {config.proxy_url}")
    logger.info(f"  Proxy Vendors: {[f'{v.name}:{v.weight}' for v in config.proxy_vendors]}")
    logger.info(f"  Targets: {config.targets}")
    logger.info(f"  Interval: {config.interval_seconds}s")
    logger.info(f"  Concurrency: {config.concurrency}")
    
    # Start Prometheus metrics server
    start_http_server(8090)
    logger.info("Prometheus metrics server started on port 8090")
    
    # Start health check server
    health_runner = await health_check_server()
    
    # Create and start crawler
    crawler = ProxyCrawler(config)
    
    try:
        await crawler.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await crawler.stop()
        await health_runner.cleanup()
        logger.info("Application shutdown complete")

if __name__ == '__main__':
    asyncio.run(main())
