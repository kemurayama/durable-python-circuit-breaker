import asyncio
import json
import logging
import os
from typing import Optional

import aiohttp
from aiohttp.client_exceptions import ClientConnectionError


async def polling_durable(url: str, headers: dict,  params: Optional[dict] = None, call_count: Optional[int] = 1, max_retry: Optional[int] = 5) -> dict:

    request_id = headers['X-Func-Request-Id']
    correlation_id = headers['X-Func-Correlation-Id']

    if call_count > max_retry:
        logging.error(
            f'Reached max durable call count. Request ID: {request_id}. Correlation ID: {correlation_id}')
        result = {
            'message': f'Reached max durable call count {os.environ.get("MAX_DURABLE_CALL_COUNT")}',
            'error': True
        }
        return result

    try:
        async with aiohttp.ClientSession() as poll_session:
            async with poll_session.get(url, headers=headers, params=params) as poll_response:
                polling_status = poll_response.status
                # same as runtimeStatus = 'Pending'
                if polling_status == 202:
                    logging.info(
                        f'Retry request. Status: {polling_status}. Call Count: {call_count} Request ID: {request_id}. Correlation ID: {correlation_id}'
                    )
                    retry_url = poll_response.headers['Location']
                    await asyncio.sleep(2 ** call_count)
                    call_count += 1
                    result = await polling_durable(
                        retry_url,
                        headers=headers,
                        call_count=call_count,
                        params=params
                    )
                elif polling_status >= 500:
                    logging.info(
                        f'Retry request. Status: {polling_status}. Call Count: {call_count} Request ID: {request_id}. Correlation ID: {correlation_id}'
                    )
                    await asyncio.sleep(2 ** call_count)
                    call_count += 1
                    result = await polling_durable(
                        url,
                        headers=headers,
                        call_count=call_count,
                        params=params,
                    )

                # Completed Orchestrator
                elif polling_status == 200:
                    resp_body = await poll_response.json()
                    # If Durable Function failed inside
                    if resp_body['runtimeStatus'] == 'Failed' or resp_body['runtimeStatus'] == 'Terminated':
                        message = resp_body['output']
                        logging.error(
                            f'Durable function failed due to {message}. Status: {polling_status}. Call Count: {call_count}. Request ID: {request_id}. Correlation ID: {correlation_id}'
                        )
                        result = {
                            'message': resp_body['output'],
                            'error': True
                        }
                    # If Durable Function Succeeded
                    elif resp_body['runtimeStatus'] == 'Completed':
                        message = resp_body['output']
                        logging.info(
                            f'Durable function completed.  Request ID: {request_id}')
                        result = {
                            'message': resp_body['output'],
                            'error': False
                        }
                else:
                    message = await poll_response.text()
                    logging.error(
                        f'Durable function failed due to {message}. Status: {polling_status}. Call Count: {call_count}. Request ID: {request_id}. Correlation ID: {correlation_id}')
                    result = {
                        'message': f'Client Error. status is {polling_status}, message is {message}',
                        'error': True
                    }
    except ClientConnectionError as ce:
        logging.exception(
            f'Exception request: {ce}. Request ID: {request_id}. Correlation ID: {correlation_id}'
        )
        await asyncio.sleep(2 ** call_count)
        call_count += 1
        result = await polling_durable(
            url,
            headers=headers,
            call_count=call_count,
            params=params,
        )

    except Exception as e:
        logging.exception(
            f'Exception on requesting current state: {e}. Request ID: {request_id}')
        raise

    return result


async def call_backend(url: str, headers: dict,  params: Optional[dict] = None, call_count: Optional[int] = 1, max_retry: Optional[int] = 3) -> dict:
    request_id = headers['X-Func-Request-Id']
    correlation_id = headers['X-Func-Correlation-Id']

    if call_count > max_retry:
        logging.error(
            f'Reached max durable call count. Request ID: {request_id}')
        circuit_breakder_url = os.environ.get('FAILURE_URL')
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(circuit_breakder_url, headers=headers, params=params) as response:
                    message = await response.text()
                    result = {
                        'backend_status': response.status,
                        'backend_message': message
                    }
        except Exception as e:
            logging.exception(
                f'Failed to cal durable entity'
            )
        return result

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                status = response.status
                # same as runtimeStatus = 'Pending'
                if status >= 500:
                    message = await response.text()
                    logging.error(
                        f'Retry request. Message: {message}. Status: {status}. Call Count: {call_count}. Request ID: {request_id}. Correlation ID: {correlation_id}'
                    )
                    await asyncio.sleep(2 ** call_count)
                    call_count += 1
                    result = await call_backend(
                        url,
                        headers=headers,
                        call_count=call_count,
                        params=params,
                        max_retry=max_retry
                    )

                # Completed Orchestrator
                elif status == 200:
                    message = await response.text()
                    logging.info(
                        f'Scceeded to call backend. Message: {message}. Status: {status}. Call Count: {call_count}. Request ID: {request_id}. Correlation ID: {correlation_id}')
                    result = {
                        'backend_status': response.status,
                        'backend_message': f'Succeeded to call backend. status is {status}, message is {message}',
                    }
                else:
                    message = await response.text()
                    logging.error(
                        f'Failed to call backend. Message: {message}. Status: {status}. Call Count: {call_count}. Request ID: {request_id}. Correlation ID: {correlation_id}')
                    result = {
                        'status': response.status,
                        'backend_message': f'Client Error. status is {status}, message is {message}',
                    }
    except ClientConnectionError as ce:
        logging.exception(
            f'Exception request: {ce}. Request ID: {request_id}. Correlation ID: {correlation_id}'
        )
        await asyncio.sleep(2 ** call_count)
        call_count += 1
        result = await polling_durable(
            url,
            headers=headers,
            call_count=call_count,
            params=params,
            max_retry=max_retry
        )

    except Exception as e:
        logging.exception(
            f'Exception on requesting current state: {e}. Request ID: {request_id}. Correlation ID: {correlation_id}')
        raise

    return result
