FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    requests \
    pandas \
    numpy \
    scipy \
    jupyter \
    matplotlib \
    seaborn

COPY src/ ./src/
COPY data/ ./data/

CMD ["python", "src/fda_api_client.py"]
