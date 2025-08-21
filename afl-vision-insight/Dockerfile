FROM python:3.10

WORKDIR /app

COPY . /app

RUN pip install fastapi uvicorn opencv-python python-multipart

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
