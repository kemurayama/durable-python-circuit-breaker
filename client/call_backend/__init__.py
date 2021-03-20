import json
import logging
import os
import azure.functions as func
from uuid import uuid4

from shared.utils import polling_durable, call_backend


async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    CIRCUIT_URL = os.environ.get('CIRCUIT_URL')
    request_id = str(uuid4())
    col_id = str(uuid4())
    headers = {
        'Content-Type': 'application/json',
        'X-Func-Request-Id': request_id,
        'X-Func-Correlation-Id': col_id
    }
    params = dict(req.params)

    # Call Durable Function to get circuit breaker state
    # Error when Durable Function returned status >= 400
    try:
        result = await polling_durable(CIRCUIT_URL, headers=headers, params=params, max_retry=5)
    except Exception as e:
        return func.HttpResponse(
            status_code=500,
            headers={'Content-Type': 'application/json'},
            body=json.dumps(
                {
                    "message": f'Failed to call backend {e}'
                },
                indent=2
            )
        )

    # Handle message from Durable Functions
    if result['error'] is True:
        return func.HttpResponse(
            status_code=500,
            headers={'Content-Type': 'application/json'},
            body=json.dumps(
                {
                    "message": f'Failed to call backend due to {result["message"]}'
                },
                indent=2
            )
        )
    else:
        if result['message']['status'] != 'Closed':
            return func.HttpResponse(
                status_code=500,
                headers={'Content-Type': 'application/json'},
                body=json.dumps(
                    {
                        'message': 'Backend is currently unavailable .'
                    },
                    indent=2
                )
            )

        else:
            url = os.environ.get('BACKEND_URL')
            req_id = str(uuid4())
            headers = {
                'Content-Type': 'application/json',
                'X-Func-Request-Id': req_id,
                'X-Func-Correlation-Id': col_id
            }
            try:
                backend_result = await call_backend(url, headers=headers, params=params, max_retry=1)
            except Exception as e:
                logging.exception(
                    f'Failed to call backend {e}'
                )
                return func.HttpResponse(
                    status_code=500,
                    body=json.dumps("Failed to call backend", indent=2)
                )

            return func.HttpResponse(
                status_code=200,
                body=json.dumps(backend_result, indent=2)
            )
