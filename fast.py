import re
from asyncio import ensure_future, gather, get_event_loop, sleep
from collections import deque
from statistics import mean
from time import time

from aiohttp import ClientSession

MIN_DURATION = 7
MAX_DURATION = 30
STABILITY_DELTA = 2
MIN_STABLE_MEASUREMENTS = 6

sessions = []


async def run():
    token = await get_token()
    urls = await get_urls(token)
    conns = await warmup(urls)
    speed = await measure(conns)
    await cleanup()
    return speed


async def get_token():
    async with ClientSession() as s:
        resp = await s.get('https://fast.com/')
        text = await resp.text()
        script = re.search(r'<script src="(.*?)">', text).group(1)

        resp = await s.get(f'https://fast.com{script}')
        text = await resp.text()
        token = re.search(r'token:"(.*?)"', text).group(1)
    return token


async def get_urls(token):
    async with ClientSession() as s:
        params = {'https': 'true', 'token': token, 'urlCount': 5}
        resp = await s.get('https://api.fast.com/netflix/speedtest', params=params)
        data = await resp.json()
    return [x['url'] for x in data]


async def warmup(urls):
    conns = [get_connection(url) for url in urls]
    return await gather(*conns)


async def get_connection(url):
    s = ClientSession()
    sessions.append(s)
    conn = await s.get(url)
    return conn


async def measure(conns):
    start = time()
    res = []
    for i in range(0,4):
        workers = [measure_speed(conn) for conn in conns]
        res.append(await gather(*workers))

    elapsed = time() - start
    total = sum(sum(res,[]))
    speed =  (total*8/elapsed)/(1024*1024)
    return speed

async def measure_speed(conn):
    chunk_size = 1024*10424
    total = 0
    async for chunk in conn.content.iter_chunked(chunk_size):
        total += len(chunk)
    return total


async def cleanup():
    await gather(*[s.close() for s in sessions])


def main():
    loop = get_event_loop()
    return loop.run_until_complete(run())


if __name__ == '__main__':
    print(f"{main()}Mbps")
