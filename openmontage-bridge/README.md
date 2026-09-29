# OpenMontage ↔ ChatGPT Bridge

Protected bridge for launching OpenMontage video jobs from ChatGPT.

Endpoints:
- GET /health
- POST /v1/videos
- GET /v1/videos
- GET /v1/videos/{job_id}
- GET /v1/videos/{job_id}/download

All /v1 endpoints require Authorization: Bearer BRIDGE_TOKEN.
