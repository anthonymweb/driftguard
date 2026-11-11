FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask
COPY server.py demo_data.py ./
COPY templates ./templates
COPY static ./static
CMD ["python", "server.py"]
