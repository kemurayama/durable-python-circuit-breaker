
import time
import logging
import json

import azure.functions as func
import azure.durable_functions as df


def orchestrator_function(context: df.DurableOrchestrationContext):
    params = context.get_input()
    entityId = df.EntityId("circuit_breaker_actor", params['entity_key'])
    state = yield context.call_entity(entityId, "get")
    return state

main = df.Orchestrator.create(orchestrator_function)
