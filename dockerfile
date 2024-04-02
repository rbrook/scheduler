FROM python:3.10-slim-bookworm

COPY . .

RUN pip install -U pip
RUN pip install poetry
RUN poetry install

CMD [ "poetry", "run", "python", "dscheduler.py" ]
