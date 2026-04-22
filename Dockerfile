FROM python:3.11-slim

WORKDIR /app

# Copy all three directories that need to be in the container
COPY backend/ ./backend/
COPY backend_agents/ ./backend_agents/
COPY backend_earnings/ ./backend_earnings/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Set working directory to backend for uvicorn
WORKDIR /app/backend

# Start the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
