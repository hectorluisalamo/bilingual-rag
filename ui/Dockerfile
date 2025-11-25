# ui/Dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ui/app.py ./ui/app.py
ENV API_URL="http://api:8000" DEFAULT_INDEX_NAME="c300o45"
EXPOSE 8501
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
