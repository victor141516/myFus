FROM python:alpine

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt && pip install gunicorn
CMD [ "gunicorn", "-w4", "-b", ":8000", "main:app" ]
