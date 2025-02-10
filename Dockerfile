# Use an official Python image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (optional)
RUN apt-get update && apt-get install -y curl

# Copy only the dependencies file first (improves caching)
COPY requirements.txt .

# Install dependencies inside the container (not using venv)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project (excluding venv via .dockerignore)
COPY . .

# Expose FastAPI's port
EXPOSE 8000

# Run FastAPI on container start
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
