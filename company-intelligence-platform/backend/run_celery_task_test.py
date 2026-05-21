# run_celery_task_test.py
import sys
import os
import time

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_celery_task_test")

def main():
    logger.info("Initializing Celery application client...")
    from app.core.celery_app import celery_app, add_numbers
    
    logger.info("Submitting task 'add_numbers' (parameters: x=15, y=35) to the queue...")
    async_result = add_numbers.delay(15, 35)
    
    logger.info(f"Task submitted. Task ID: {async_result.id}")
    logger.info("Waiting for the Celery worker to process the task...")
    
    start_time = time.time()
    try:
        result = async_result.get(timeout=15)
        duration = time.time() - start_time
        logger.info(f"Task executed successfully in {duration:.3f} seconds!")
        logger.info(f"Task returned result: {result}")
        if result == 50:
            logger.info("SUCCESS: The Celery worker returned the correct result!")
            sys.exit(0)
        else:
            logger.error(f"FAILURE: Expected result 50, but got {result}")
            sys.exit(1)
    except TimeoutError:
        logger.error("FAILURE: Task execution timed out. The worker did not process the task within 15 seconds.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"FAILURE: An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
