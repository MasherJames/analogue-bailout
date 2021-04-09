FROM python:3.8-alpine

# Python won’t try to write .pyc files on the import of source modules
ENV PYTHONDONTWRITEBYTECODE 1
# stdout and stderr streams to be unbuffered
ENV PYTHONUNBUFFERED 1

# set working dir
WORKDIR /app

# copy everything to app
COPY . /app

# headers and libraries required to setup an environment before mysqlclient is installed
RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add --no-cache mariadb-dev


# install packages exactly as specified in Pipfile.lock and enforce that is up to date
RUN pip3 install pipenv && \
    pipenv install --dev --system --deploy --ignore-pipfile

ENTRYPOINT ["sh", "scripts/entrypoint.sh"]

