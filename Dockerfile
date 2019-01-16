FROM       python:3.6.7-stretch
LABEL maintainer="Evgeniy Bondarenko <Bondarenko.Hub@gmail.com>"
MAINTAINER EvgeniyBondarenko "Bondarenko.Hub@gmail.com"

RUN apt-get update && \
    apt-get install -y  python-dev \
                        python-pip \
                        python-virtualenv \
                        libjpeg-dev \
                        default-libmysqlclient-dev \
                        git \
                        gettext \
                        dnsutils \
                        telnet \
                        curl \
                        vim \
                        libsqlite3-dev \
                        libffi-dev \
                        libssl-dev \
                        libxml2-dev \
                        libxslt1-dev \
                        libpq-dev \
                        libffi-dev \
                        libsqlite3-dev \
                        node-less \
                        cleancss \
                        libcurl4-openssl-dev \
                        python-social-auth #=0.2.11

WORKDIR /opt
EXPOSE 80
ENTRYPOINT ["./docker-entrypoint.sh" ]
CMD gunicorn -w 3 -b ${BIND_ADDR}:${BIND_PORT} wsgi:application

RUN curl -sL https://deb.nodesource.com/setup_8.x | bash && \
    apt-get install -y nodejs && \
    npm install -g bower



COPY ./requirements.txt ./
RUN pip install -r ./requirements.txt


# Copy Code
COPY . ./

RUN mkdir -p components && \
    cp ./bower.json ./components/bower.json && \
    ./manage.py bower install -- --allow-root