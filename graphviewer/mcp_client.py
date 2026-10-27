"""Long-lived MCP sessions owned by one background task per connection."""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def transport(source):
    if source["transport"] == "http":
        async with streamable_http_client(source["url"]) as (read, write, _):
            yield read, write
    else:
        params = StdioServerParameters(command=source["command"], args=source.get("args", []),
                                       cwd=source.get("repo_root") or None)
        async with stdio_client(params) as streams:
            yield streams


def decode(result):
    if result.isError:
        raise ValueError("MCP tool returned an error")
    if result.structuredContent:
        return result.structuredContent
    for block in result.content:
        if hasattr(block, "text"):
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                continue
    raise ValueError("The MCP server did not return structured graph data")


class Worker:
    def __init__(self, source):
        self.source, self.queue = source, asyncio.Queue()
        self.ready = asyncio.get_running_loop().create_future()
        self.task = asyncio.create_task(self.run())

    async def run(self):
        try:
            async with transport(self.source) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=90)) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.ready.set_result([tool.name for tool in tools.tools])
                    await self.process(session)
        except BaseException as exc:
            if not self.ready.done():
                self.ready.set_exception(RuntimeError(str(exc)))
            while not self.queue.empty():
                _, _, future = self.queue.get_nowait()
                if not future.done():
                    future.set_exception(RuntimeError("MCP connection closed"))

    async def process(self, session):
        while True:
            name, arguments, future = await self.queue.get()
            try:
                result = decode(await session.call_tool(name, arguments))
                if result.get("status") in ("error", "not_found"):
                    raise ValueError(result.get("error", result.get("summary", "Graph query failed")))
                if not future.done():
                    future.set_result(result)
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)

    async def call(self, name, arguments):
        await asyncio.wait_for(asyncio.shield(self.ready), 100)
        if self.task.done():
            raise ValueError("MCP connection closed; reconnect the source")
        future = asyncio.get_running_loop().create_future()
        await self.queue.put((name, arguments, future))
        return await asyncio.wait_for(future, 100)


class MCPPool:
    def __init__(self):
        self.workers = {}

    def worker(self, source):
        identity = source["id"]
        if identity not in self.workers:
            self.workers[identity] = Worker(source)
        return self.workers[identity]

    async def call(self, source, name, arguments):
        if source.get("repo_root"):
            arguments = {**arguments, "repo_root": source["repo_root"]}
        return await self.worker(source).call(name, arguments)

    async def close(self, identity=None):
        keys = [identity] if identity else list(self.workers)
        for key in keys:
            worker = self.workers.pop(key, None)
            if worker:
                worker.task.cancel()
                await asyncio.gather(worker.task, return_exceptions=True)
