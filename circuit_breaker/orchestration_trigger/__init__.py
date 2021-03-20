import logging

import azure.functions as func
import azure.durable_functions as df


async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:

    func_name = req.route_params["functionName"]
    params = dict(req.params)
    client = df.DurableOrchestrationClient(starter)

    if func_name == 'read_circuit_status_orchestrator':
        instance_id = await client.start_new(func_name, None, params)
        logging.info(f"Started orchestration with ID = '{instance_id}'.")
        return client.create_check_status_response(req, instance_id)

    elif func_name == 'count_failure':
        entityId = df.EntityId("circuit_breaker_actor", params['entity_key'])
        await client.signal_entity(entityId, "count_failure")
        return func.HttpResponse(
            status_code=200,
            body="Function failed to call backend. so added 1 count"
        )
    elif func_name == 'count_success':
        entityId = df.EntityId("circuit_breaker_actor", params['entity_key'])
        await client.signal_entity(entityId, "count_success")
        return func.HttpResponse(
            status_code=200,
            body="Function succeeded to call backend. so added 1 count"
        )