# The agent's container: Python, the agent's packages, its code, and the sample documents.
# Settings are not baked in. compose.yaml passes them from .env when the container starts.
FROM python:3.12-slim

WORKDIR /app
COPY agent/requirements.txt agent/requirements.txt
RUN pip install --no-cache-dir -r agent/requirements.txt

COPY agent agent
COPY docs/sample docs/sample

EXPOSE 8000
CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "8000"]
