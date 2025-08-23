# import random

import requests
from mcp.server.fastmcp import FastMCP
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from anyio import fail_after

# Create server (configure host/port here; FastMCP.run does not accept host/port)
mcp = FastMCP("RAGflow Server", host="0.0.0.0", port=7056)


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print(f"[debug-server] add({a}, {b})")
    return a + b


@mcp.tool()
async def ragflow_retrieval(
    dataset_ids: list[str] | None = None,
    document_ids: list[str] | None = None,
    question: str = "電聲是什麼",
    sse_url: str = "http://host.docker.internal:2124/sse",
    api_key: str | None = None,
    timeout_s: float = 15.0,
) -> dict:
    """Call remote ragflow_retrieval via SSE and return the tool result.

    Defaults mirror the provided example; pass arguments to override.
    """
    # Safe defaults based on the user's snippet
    if dataset_ids is None:
        dataset_ids = ["26c82b0c4f7a11f082840242ac180007"]
    if document_ids is None:
        document_ids = ["a12fdf204f7a11f08cfc0242ac180007"]

    headers = None
    if api_key:
        # Support either api_key header or OAuth-style Authorization
        headers = {"api_key": api_key}

    try:
        async with sse_client(sse_url, headers=headers) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                # Optional: list tools for debugging/inspection
                # tools = await session.list_tools()
                # print(f"[debug-server] remote tools: {getattr(tools, 'tools', tools)}")

                with fail_after(timeout_s):
                    resp = await session.call_tool(
                        name="ragflow_retrieval",
                        arguments={
                            "dataset_ids": dataset_ids,
                            "document_ids": document_ids,
                            "question": question,
                        },
                    )
                # Prefer model_dump when available (pydantic models)
                if hasattr(resp, "model_dump"):
                    return resp.model_dump()
                return resp  # type: ignore[return-value]
    except TimeoutError as e:
        return {"error": f"timeout after {timeout_s}s", "detail": str(e)}
    except Exception as e:
        return {"error": str(e)}


# @mcp.tool()
# def get_secret_word() -> str:
#     print("[debug-server] get_secret_word()")
#     return random.choice(["apple", "banana", "cherry"])


# @mcp.tool()
# def get_current_weather(city: str) -> str:
#     print(f"[debug-server] get_current_weather({city})")

#     endpoint = "https://wttr.in"
#     response = requests.get(f"{endpoint}/{city}")
#     return response.text


if __name__ == "__main__":
    # host and port configured in FastMCP constructor; run only needs transport
    mcp.run(transport="sse")