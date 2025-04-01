FROM python:3.11-slim

WORKDIR /usr/src/app
COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

COPY . .
ENV PYTHONPATH=/usr/src/app

EXPOSE 8000

CMD [ "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000" ]
