import asyncio
import asyncio
import logging
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main() -> None:
    URL = 'http://localhost:7071/api/call_backend'
    params = {
        'entity_key': 'debugentity',
        'status': 'server_error'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(URL, params=params) as response:
            status = response.status
            response_message = await response.text()

    logger.info(f'response status: {status}. response message {response_message}')
    await asyncio.sleep(1)


if __name__ == '__main__':
    while True:
        asyncio.run(main())
