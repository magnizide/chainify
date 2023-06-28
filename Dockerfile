FROM python:3.12.0b3-alpine3.18

LABEL author="Nicolas Vargas ndvargas95@gmail.com"

COPY src /opt/src

RUN pip install -r requirements.txt

EXPOSE 8080

WORKDIR /opt/src
ENTRYPOINT [ "flask run" ]