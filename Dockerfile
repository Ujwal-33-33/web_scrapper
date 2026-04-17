# Use the official Microsoft Playwright image based on Ubuntu Jammy
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . .

# Command to run the FastAPI server, using Render's assigned port
CMD uvicorn scrapper:app --host 0.0.0.0 --port ${PORT:-8000}