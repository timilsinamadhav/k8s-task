#!/usr/bin/env python3
"""
Worker Service for Microservices Application
Processes jobs and interacts with PostgreSQL database
"""

import os
import sys
import time
import signal
import logging
import psycopg2
import structlog
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class DatabaseConnection:
    """Database connection manager with retry logic"""
    
    def __init__(self):
        self.connection: Optional[psycopg2.connection] = None
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'microservices_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
    
    def connect(self, max_retries: int = 5) -> bool:
        """Establish database connection with retry logic"""
        for attempt in range(max_retries):
            try:
                self.connection = psycopg2.connect(**self.db_config)
                self.connection.autocommit = True
                logger.info("Database connection established", 
                           host=self.db_config['host'], 
                           database=self.db_config['database'])
                return True
            except psycopg2.Error as e:
                logger.warning("Database connection failed", 
                              attempt=attempt + 1, 
                              max_retries=max_retries,
                              error=str(e))
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Failed to connect to database after all retries")
                    return False
        return False
    
    def is_connected(self) -> bool:
        """Check if database connection is active"""
        if not self.connection:
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                return True
        except psycopg2.Error:
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[list]:
        """Execute a database query with error handling"""
        if not self.is_connected():
            logger.warning("Database not connected, attempting to reconnect")
            if not self.connect():
                return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:  # Query returns data
                    return cursor.fetchall()
                return []
        except psycopg2.Error as e:
            logger.error("Database query failed", query=query, error=str(e))
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

class WorkerService:
    """Main worker service class"""
    
    def __init__(self):
        self.running = True
        self.job_counter = 0
        self.db = DatabaseConnection()
        self.process_interval = int(os.getenv('PROCESS_INTERVAL', '30'))
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("Received shutdown signal", signal=signum)
        self.running = False
    
    def initialize(self) -> bool:
        """Initialize worker service"""
        logger.info("Initializing worker service", 
                   interval=self.process_interval,
                   environment=os.getenv('ENVIRONMENT', 'development'))
        
        # Connect to database
        if not self.db.connect():
            logger.error("Failed to initialize database connection")
            return False
        
        # Initialize job tracking table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS job_logs (
            id SERIAL PRIMARY KEY,
            job_number INTEGER NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            worker_id VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'completed'
        )
        """
        
        if self.db.execute_query(create_table_query) is None:
            logger.error("Failed to create job_logs table")
            return False
        
        logger.info("Worker service initialized successfully")
        return True
    
    def process_job(self) -> bool:
        """Process a single job"""
        self.job_counter += 1
        job_id = self.job_counter
        worker_id = f"worker-{os.getpid()}"
        
        try:
            # Simulate job processing
            start_time = time.time()
            logger.info("Processing job started", 
                       job_id=job_id, 
                       worker_id=worker_id,
                       timestamp=datetime.now().isoformat())
            
            # Simulate some work (e.g., data processing, file operations, etc.)
            processing_time = 1 + (job_id % 3)  # Variable processing time
            time.sleep(processing_time)
            
            # Log job completion to database
            insert_query = """
            INSERT INTO job_logs (job_number, worker_id, status) 
            VALUES (%s, %s, %s)
            """
            
            result = self.db.execute_query(insert_query, (job_id, worker_id, 'completed'))
            
            if result is None:
                logger.error("Failed to log job completion to database", job_id=job_id)
                return False
            
            # Get user count for additional processing context
            user_count_query = "SELECT COUNT(*) FROM users"
            user_result = self.db.execute_query(user_count_query)
            user_count = user_result[0][0] if user_result else 0
            
            elapsed_time = time.time() - start_time
            logger.info("Job processing completed", 
                       job_id=job_id,
                       worker_id=worker_id,
                       processing_time_seconds=round(elapsed_time, 2),
                       user_count_in_db=user_count,
                       timestamp=datetime.now().isoformat())
            
            return True
            
        except Exception as e:
            logger.error("Job processing failed", 
                        job_id=job_id, 
                        worker_id=worker_id,
                        error=str(e))
            
            # Try to log the failure
            try:
                failure_query = """
                INSERT INTO job_logs (job_number, worker_id, status) 
                VALUES (%s, %s, %s)
                """
                self.db.execute_query(failure_query, (job_id, worker_id, 'failed'))
            except:
                pass  # Don't fail if we can't log the failure
            
            return False
    
    def run(self):
        """Main worker loop"""
        if not self.initialize():
            logger.error("Worker initialization failed")
            sys.exit(1)
        
        logger.info("Worker service started", pid=os.getpid())
        
        try:
            while self.running:
                # Process job
                success = self.process_job()
                
                if not success:
                    logger.warning("Job processing failed, continuing...")
                
                # Health check - verify database connection
                if not self.db.is_connected():
                    logger.warning("Database connection lost, attempting to reconnect")
                    if not self.db.connect():
                        logger.error("Failed to reconnect to database")
                        break
                
                # Wait before processing next job
                for _ in range(self.process_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        except Exception as e:
            logger.error("Unexpected error in worker loop", error=str(e))
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down worker service", 
                   total_jobs_processed=self.job_counter)
        self.db.close()

def main():
    """Main entry point"""
    try:
        worker = WorkerService()
        worker.run()
    except KeyboardInterrupt:
        logger.info("Worker service interrupted by user")
    except Exception as e:
        logger.error("Worker service crashed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
