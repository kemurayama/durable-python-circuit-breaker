import logging

import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    status = req.params.get('status')
    if status == 'ok':
        return func.HttpResponse(
            status_code=200,
            body= f"Hello, This HTTP triggered function executed successfully."
            )
    elif status == 'server_error':
        return func.HttpResponse(
            status_code=500,
            body= f"This HTTP triggered function had internal server error."
            )
    elif status == 'client_error':
        return func.HttpResponse(
            status_code=400,
            body= f"This HTTP triggered function had Client error."
            )




