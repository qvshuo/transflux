FROM python:alpine
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir miniflux
COPY main.py .
CMD ["python3", "main.py"]
