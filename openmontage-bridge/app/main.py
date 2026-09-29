import os, uuid, json, subprocess, threading, time, base64
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

APP_TOKEN = os.environ.get('BRIDGE_TOKEN', '')
OPENMONTAGE_DIR = Path(os.environ.get('OPENMONTAGE_DIR', '/opt/openmontage')).resolve()
WORK_DIR = Path(os.environ.get('WORK_DIR', str(OPENMONTAGE_DIR / '.chatgpt-jobs'))).resolve()
CODEX_BIN = os.environ.get('CODEX_BIN', 'codex')
MAX_PROMPT_CHARS = int(os.environ.get('MAX_PROMPT_CHARS', '12000'))
CONTROL_JOB_FILE = Path(os.environ.get('CONTROL_JOB_FILE', '/bridge/control/job.enc'))
CONTROL_PRIVATE_KEY_B64 = os.environ.get('CONTROL_PRIVATE_KEY_B64', '')
WORK_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='OpenMontage ChatGPT Bridge', version='0.2.0')
jobs = {}
lock = threading.Lock()

class VideoRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=MAX_PROMPT_CHARS)
    brand: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, ge=5, le=600)
    format: Optional[str] = Field(default=None, pattern='^(9:16|16:9|1:1)$')
    max_budget_usd: float = Field(default=5.0, ge=0.0, le=10.0)

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
        'Prefer local/free providers unless the brief explicitly needs a paid provider.',
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
        op = None
        if output_file:
            candidate = Path(output_file)
            if not candidate.is_absolute():
                candidate = (OPENMONTAGE_DIR / candidate).resolve()
            try:
                candidate.relative_to(OPENMONTAGE_DIR)
                if candidate.exists():
                    op = candidate
            except ValueError:
                pass
        with lock:
            jobs[job_id].update(status=status, finished_at=time.time(), returncode=proc.returncode,
                output_file=str(op) if op else None, summary=payload.get('summary'), cost_usd=payload.get('cost_usd'))
    except subprocess.TimeoutExpired:
        with lock:
            jobs[job_id].update(status='failed', finished_at=time.time(), error='timeout')
    except Exception as e:
        with lock:
            jobs[job_id].update(status='failed', finished_at=time.time(), error=str(e))

def decrypt_control_job(envelope: dict) -> dict:
    if not CONTROL_PRIVATE_KEY_B64:
        raise RuntimeError('CONTROL_PRIVATE_KEY_B64 missing')
    private_pem = base64.b64decode(CONTROL_PRIVATE_KEY_B64)
    key = serialization.load_pem_private_key(private_pem, password=None)
    ek = base64.urlsafe_b64decode(envelope['ek'] + '=' * ((4 - len(envelope['ek']) % 4) % 4))
    nonce = base64.urlsafe_b64decode(envelope['nonce'] + '=' * ((4 - len(envelope['nonce']) % 4) % 4))
    ct = base64.urlsafe_b64decode(envelope['ct'] + '=' * ((4 - len(envelope['ct']) % 4) % 4))
    aes_key = key.decrypt(ek, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    plaintext = AESGCM(aes_key).decrypt(nonce, ct, None)
    return json.loads(plaintext.decode('utf-8'))

def launch_control_job():
    if not CONTROL_JOB_FILE.exists():
        return
    try:
        raw = json.loads(CONTROL_JOB_FILE.read_text(encoding='utf-8'))
        if raw.get('disabled'):
            return
        data = decrypt_control_job(raw)
        if float(data.get('expires_at', 0)) < time.time():
            return
        job_id = str(data['id'])
        req = VideoRequest(
            prompt=data['prompt'],
            brand=data.get('brand'),
            duration_seconds=data.get('duration_seconds'),
            format=data.get('format'),
            max_budget_usd=min(float(data.get('max_budget_usd', 5.0)), 10.0),
        )
        with lock:
            jobs[job_id] = {'id': job_id, 'status': 'queued', 'created_at': time.time(), 'request': {'brand': req.brand, 'duration_seconds': req.duration_seconds, 'format': req.format, 'max_budget_usd': req.max_budget_usd}}
        try:
            CONTROL_JOB_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        threading.Thread(target=runner, args=(job_id, req), daemon=True).start()
    except Exception as e:
        print('CONTROL_JOB_ERROR', repr(e), flush=True)

@app.on_event('startup')
def startup():
    launch_control_job()

@app.get('/health')
def health():
    return {'ok': True, 'version': '0.2.0', 'openmontage_dir': str(OPENMONTAGE_DIR), 'configured': OPENMONTAGE_DIR.exists(), 'control_ready': bool(CONTROL_PRIVATE_KEY_B64)}

@app.post('/v1/videos')
def create_video(req: VideoRequest, authorization: Optional[str] = Header(default=None)):
    auth(authorization)
    if not OPENMONTAGE_DIR.exists():
        raise HTTPException(503, 'OpenMontage directory missing')
    job_id = uuid.uuid4().hex
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
        if job_id not in jobs:
            raise HTTPException(404, 'Unknown job')
        return jobs[job_id]

@app.get('/v1/videos/{job_id}/download')
def download(job_id: str, authorization: Optional[str] = Header(default=None)):
    auth(authorization)
    with lock:
        if job_id not in jobs:
            raise HTTPException(404, 'Unknown job')
        output = jobs[job_id].get('output_file')
    if not output or not Path(output).exists():
        raise HTTPException(404, 'Output is not ready')
    return FileResponse(output, media_type='video/mp4', filename=Path(output).name)

@app.get('/public/jobs/{job_id}')
def public_status(job_id: str):
    with lock:
        item = jobs.get(job_id)
        if not item:
            raise HTTPException(404, 'Unknown job')
        return {
            'id': job_id,
            'status': item.get('status'),
            'summary': item.get('summary'),
            'cost_usd': item.get('cost_usd'),
            'error': item.get('error'),
            'download_ready': bool(item.get('output_file'))
        }

@app.get('/public/jobs/{job_id}/download')
def public_download(job_id: str):
    with lock:
        item = jobs.get(job_id)
        if not item:
            raise HTTPException(404, 'Unknown job')
        output = item.get('output_file')
    if not output or not Path(output).exists():
        raise HTTPException(404, 'Output is not ready')
    return FileResponse(output, media_type='video/mp4', filename=Path(output).name)
