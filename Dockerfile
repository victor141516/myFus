FROM python:alpine

WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt && pip install gunicorn

COPY . /app
CMD [ "gunicorn", "-w4", "-b", ":8000", "main:app" ]
