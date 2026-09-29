FROM node:22-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv ffmpeg git make curl espeak-ng && rm -rf /var/lib/apt/lists/*
RUN npm install -g @openai/codex
WORKDIR /opt
RUN git clone --depth=1 https://github.com/calesthio/OpenMontage.git openmontage
WORKDIR /opt/openmontage
RUN python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd remotion-composer && npm install
WORKDIR /bridge
COPY openmontage-bridge/requirements.txt .
RUN python3 -m pip install --break-system-packages -r requirements.txt
COPY openmontage-bridge/app ./app
COPY openmontage-bridge/control ./control
ENV OPENMONTAGE_DIR=/opt/openmontage
ENV WORK_DIR=/opt/openmontage/.chatgpt-jobs
ENV CONTROL_JOB_FILE=/bridge/control/job.enc
EXPOSE 10000
CMD ["sh","-c","python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
