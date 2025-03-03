FROM python:3.8-slim
LABEL maintainer="Jonny Le <jonny.le@computacenter.com>"

WORKDIR /app

COPY ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src /app

EXPOSE 80

CMD [ "python", "main.py" ]
