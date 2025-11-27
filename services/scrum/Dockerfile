FROM python:3.11-slim

WORKDIR /app

<<<<<<< HEAD
RUN pip install --no-cache-dir flask

COPY main.py .

EXPOSE 8000

CMD ["python", "main.py"]
=======
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
>>>>>>> 1f8cfe1 (feat: Implement new Scrum Master service with AI-powered hierarchical task decomposition, file parsing, and organization integration.)
