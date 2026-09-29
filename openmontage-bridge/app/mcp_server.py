import os, requests
from mcp.server.fastmcp import FastMCP

API_URL = os.environ.get('BRIDGE_API_URL', 'http://127.0.0.1:8000').rstrip('/')
TOKEN = os.environ.get('BRIDGE_TOKEN', '')
HEADERS = {'Authorization': 'Bearer ' + TOKEN}

mcp = FastMCP('OpenMontage')

@mcp.tool()
def create_video(prompt: str, brand: str = '', duration_seconds: int = 45, format: str = '9:16', max_budget_usd: float = 5.0) -> dict:
    r = requests.post(API_URL + '/v1/videos', headers=HEADERS, json={'prompt': prompt, 'brand': brand or None, 'duration_seconds': duration_seconds, 'format': format, 'max_budget_usd': max_budget_usd}, timeout=30)
    r.raise_for_status()
    return r.json()

@mcp.tool()
def video_status(job_id: str) -> dict:
    r = requests.get(API_URL + '/v1/videos/' + job_id, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

@mcp.tool()
def list_videos() -> dict:
    r = requests.get(API_URL + '/v1/videos', headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

if __name__ == '__main__':
    mcp.run(transport='streamable-http')
