import logging
import os
from datetime import datetime, time, timedelta

import azure.durable_functions as df


def crate_circuit_breaker():
    d = {
        "status": "Closed",
        "failure_window": [],
        "open_until": None,
        "success_count": 0
    }
    return d


def entity_function(context: df.DurableEntityContext):
    """A Counter Durable Entity."""

    THREASHOLD_COUNTS = int(os.environ.get('THREASHOLD_COUNTS', 10))
    TIMESPAN_SECONDS = int(os.environ.get('TIMESPAN_SECONDS_SECONDS', 30))
    OPEN_DURATION_MINUTES = int(os.environ.get('OPEN_DURATION_MINUTES', 3))

    logging.info(
        f'Set THREASHOLD_COUNTS is {THREASHOLD_COUNTS} and TIMESPAN_SECONDS is {TIMESPAN_SECONDS}.')
    current_values = context.get_state(crate_circuit_breaker)
    operation = context.operation_name
    current_utc = datetime.utcnow()
    current_utc_str = datetime.strftime(current_utc, '%Y-%m-%dT%H:%M:%S')

    try:
        if current_values['open_until'] is not None:
            open_until = datetime.strptime(
                current_values['open_until'], '%Y-%m-%dT%H:%M:%S')
            if current_utc > open_until:
                current_values['status'] = 'HalfOpen'
                current_values['failure_window'] = list()
                current_values['open_until'] = None
                logging.info(f'Status changed to {current_values["status"]}')
                context.set_state(current_values)

        if operation == "get":
            result = {
                'status': current_values['status'],
                'open_until': current_values['open_until']
            }
            logging.debug(f'Get current status {current_values["status"]}')
            context.set_state(current_values)
            context.set_result(result)

        elif operation == 'reset':
            new_values = {
                'status': 'Closed',
                'failure_window': [],
                'open_until': None,
                'success_count': 0
            }
            logging.debug(f'Reset current status.')
            context.set_state(new_values)
            context.set_result(new_values)

        elif operation == "count_failure":
            logging.info('Evaluate if the status should be changed.')
            current_values['failure_window'].append(current_utc_str)
            # Exclude after theshold.
            sp = current_utc - timedelta(seconds=TIMESPAN_SECONDS)
            current_failures = [
                v for v in current_values['failure_window']
                if datetime.strptime(v, '%Y-%m-%dT%H:%M:%S') > sp
            ]
            current_count = len(current_failures)

            new_values = {
                'status': current_values['status'],
                'failure_window': current_failures,
                'open_until': None,
                'success_count': 0
            }

            # Update status and open_until
            if current_count >= THREASHOLD_COUNTS:

                logging.info(f'Current Failed count is greater than {THREASHOLD_COUNTS}')

                open_until = current_utc + \
                    timedelta(minutes=int(OPEN_DURATION_MINUTES))
                open_until_str = datetime.strftime(
                    open_until, '%Y-%m-%dT%H:%M:%S')

                logging.info(f'{context.entity_key} is Open until {open_until_str}')

                new_values['status'] = 'Open'
                new_values['open_until'] = open_until_str

            result = {
                'status': new_values['status'],
                'open_until': new_values['open_until']
            }
            context.set_state(new_values)
            context.set_result(result)

        elif operation == 'count_success':
            if current_values['status'] == 'HalfOpen':
                logging.info(f'Current status is {current_values["status"]}')
                current_values['success_count'] += 1
                if current_values['success_count'] >= 5:
                    new_values = {
                        "status": "Closed",
                        "failure_window": [],
                        "open_until": None,
                        "success_count": 0
                    }
                    context.set_state(new_values)
                    context.set_result(new_values)
                    return
                else:
                    context.set_state(current_values)

    except Exception as e:
        logging.exception(f'Failed Entity Function {e}')
        raise

main = df.Entity.create(entity_function)
