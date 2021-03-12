FROM python:3.8.1

COPY . /app

RUN pip install -r /app/requirements.txt

WORKDIR /app

ARG UNAME=app
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID -o $UNAME
RUN useradd -m -u $UID -g $GID -o -s /bin/bash $UNAME
