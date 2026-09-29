import os, uuid, json, subprocess, threading, time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

APP_TOKEN = os.environ.get('BRIDGE_TOKEN', '')
OPENMONTAGE_DIR = Path(os.environ.get('OPENMONTAGE_DIR', '/opt/openmontage')).resolve()
WORK_DIR = Path(os.environ.get('WORK_DIR', '/tmp/openmontage-jobs')).resolve()
OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', str(OPENMONTAGE_DIR / 'output'))).resolve()
CODEX_BIN = os.environ.get('CODEX_BIN', 'codex')
MAX_PROMPT_CHARS = int(os.environ.get('MAX_PROMPT_CHARS', '12000'))
WORK_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='OpenMontage ChatGPT Bridge', version='0.1.0')
jobs = {}
lock = threading.Lock()

class VideoRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=MAX_PROMPT_CHARS)
    brand: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, ge=5, le=600)
    format: Optional[str] = Field(default=None, pattern='^(9:16|16:9|1:1)$')
    max_budget_usd: float = Field(default=5.0, ge=0.0, le=50.0)

def auth(authorization: Optional[str]):
    if not APP_TOKEN:
        raise HTTPException(503, 'BRIDGE_TOKEN is not configured')
    if authorization != f'Bearer {APP_TOKEN}':
        raise HTTPException(401, 'Unauthorized')

def build_prompt(req: VideoRequest, job_dir: Path) -> str:
    constraints = [
        'Run this task now, once. Do not create or edit automations.',
        'You are operating inside OpenMontage. Follow AGENT_GUIDE.md and project rules.',
        f'Keep all job-specific artifacts under: {job_dir}',
        f'Maximum production budget: ${req.max_budget_usd:.2f}. Do not exceed it.',
        'Do not modify source code, dependencies, git config, secrets, or files outside the job/output directories.',
        'Use approval/checkpoint behavior conservatively; if a creative choice is ambiguous, choose the safest professional default.',
        'At the end, write a JSON file named result.json in the job directory with keys: status, output_file, summary, cost_usd.',
        'End your final message with exactly one of: STATUS: OK, STATUS: PARTIAL, STATUS: FAILED.'
    ]
    if req.brand: constraints.append(f'Brand: {req.brand}')
    if req.duration_seconds: constraints.append(f'Target duration: {req.duration_seconds} seconds')
    if req.format: constraints.append(f'Target aspect ratio: {req.format}')
    return '\n'.join(constraints) + '\n\nUSER VIDEO BRIEF:\n' + req.prompt

def runner(job_id: str, req: VideoRequest):
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / 'agent.log'
    result_path = job_dir / 'result.json'
    with lock:
        jobs[job_id].update(status='running', started_at=time.time(), log=str(log_path))
    prompt = build_prompt(req, job_dir)
    cmd = [CODEX_BIN, 'exec', '--sandbox', 'workspace-write', '--skip-git-repo-check', '-C', str(OPENMONTAGE_DIR), '-']
    try:
        with open(log_path, 'w', encoding='utf-8') as log:
            proc = subprocess.run(cmd, input=prompt, text=True, stdout=log, stderr=subprocess.STDOUT, timeout=7200)
        payload = {}
        if result_path.exists():
            try:
                payload = json.loads(result_path.read_text(encoding='utf-8'))
            except Exception:
                payload = {}
        status = payload.get('status') or ('completed' if proc.returncode == 0 else 'failed')
        output_file = payload.get('output_file')
        if output_file:
            op = Path(output_file)
            if not op.is_absolute(): op = (OPENMONTAGE_DIR / op).resolve()
            try:
                op.relative_to(OPENMONTAGE_DIR)
            except ValueError:
                op = None
            if op and not op.exists(): op = None
        else:
            op = None
        with lock:
            jobs[job_id].update(status=status, finished_at=time.time(), returncode=proc.returncode,
                output_file=str(op) if op else None, summary=payload.get('summary'), cost_usd=payload.get('cost_usd'))
    except subprocess.TimeoutExpired:
        with lock:
            jobs[job_id].update(status='failed', finished_at=time.time(), error='timeout')
    except Exception as e:
        with lock:
            jobs[job_id].update(status='failed', finished_at=time.time(), error=str(e))

@app.get('/health')
def health():
    return {'ok': True, 'openmontage_dir': str(OPENMONTAGE_DIR), 'configured': OPENMONTAGE_DIR.exists()}

@app.post('/v1/videos')
def create_video(req: VideoRequest, authorization: Optional[str] = Header(default=None)):
    auth(authorization)
    if not OPENMONTAGE_DIR.exists():
        raise HTTPException(503, 'OpenMontage directory missing')
    job_id = uuid.uuid4().hex[:16]
    with lock:
        jobs[job_id] = {'id': job_id, 'status': 'queued', 'created_at': time.time(), 'request': req.model_dump()}
    threading.Thread(target=runner, args=(job_id, req), daemon=True).start()
    return jobs[job_id]

@app.get('/v1/videos')
def list_videos(authorization: Optional[str] = Header(default=None)):
    auth(authorization)
    with lock:
        return {'items': list(jobs.values())[-50:]}

@app.get('/v1/videos/{job_id}')
def video_status(job_id: str, authorization: Optional[str] = Header(default=None)):
    auth(authorization)
    with lock:
        if job_id not in jobs: raise HTTPException(404, 'Unknown job')
        return jobs[job_id]

@app.get('/v1/videos/{job_id}/download')
def download(job_id: str, authorization: Optional[str] = Header(default=None)):
    auth(authorization)
    with lock:
        if job_id not in jobs: raise HTTPException(404, 'Unknown job')
        output = jobs[job_id].get('output_file')
    if not output or not Path(output).exists():
        raise HTTPException(404, 'Output is not ready')
    return FileResponse(output, media_type='video/mp4', filename=Path(output).name)
