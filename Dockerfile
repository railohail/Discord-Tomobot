FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY ./tomobot ./tomobot

# Set the command to run
CMD ["python", "-m", "tomobot.main"]