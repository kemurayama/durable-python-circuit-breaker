import logging
import os

import aiohttp
from uuid import uuid4
import azure.functions as func

from shared.utils import polling_durable, call_backend


async def main(timer: func.TimerRequest):
    logging.info('Python HTTP trigger function processed a request.')

    CIRCUIT_URL = os.environ.get('CIRCUIT_URL')
    circuit_breaker_request_id = str(uuid4())
    col_id = str(uuid4())
    headers = {
        'Content-Type': 'application/json',
        'X-Func-Request-Id': circuit_breaker_request_id,
        'X-Func-Correlation-Id': col_id
    }
    params = {
        'entity_key': os.environ.get('ENTITY_KEY'),
        'status': 'ok'
    }

    try:
        result = await polling_durable(CIRCUIT_URL, headers=headers, params=params, max_retry=5)
    except Exception as e:
        logging.exception(f'Failed to call circuit breaker.{e}')

    circuit_breaker_status = result['message']['status']
    if circuit_breaker_status == 'HalfOpen':
        url = os.environ.get('BACKEND_URL')
        backend_req_id = str(uuid4())
        headers = {
            'Content-Type': 'application/json',
            'X-Func-Request-Id': backend_req_id,
            'X-Func-Correlation-Id': col_id
        }
        try:
            backend_result = await call_backend(url, headers=headers, params=params, max_retry=1)
        except Exception as e:
            logging.exception(f'Failed to call backend {e}')

        if backend_result['backend_status'] == 200 and circuit_breaker_status == 'HalfOpen':
            SUCCESS_URL = os.environ.get('SUCCESS_URL')
            async with aiohttp.ClientSession() as session:
                async with session.get(SUCCESS_URL, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = response.text()
                        logging.info(
                            'Succeeded to call backend in HalfOpen. Add success count.')
                    else:
                        result = response.text()
                        logging.error('Failed to call backend in HalfOpen.')
    else:
        logging.info(
            f'Circuit Breaker is not HalfOpen. Current Status is {circuit_breaker_status}'
        )

    logging.info(f'Function processed Successfully.')
