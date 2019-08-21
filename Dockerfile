FROM ubuntu:16.04

ENV PATH /root/.pyenv/shims:/root/.pyenv/bin:$PATH
RUN set -x \
    && pythonVersions='2.7.16 3.4.10 3.5.7 3.6.9' \
    && buildDeps='ca-certificates curl git libjpeg-dev build-essential make libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev' \
    && apt-get update \
    && apt-get install --no-install-recommends -y $buildDeps \
    && curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash \
    && echo $pythonVersions | xargs -n 1 pyenv install \
    && apt-get purge -y --auto-remove $buildDeps \
    && rm -rf /var/lib/apt/lists/*

CMD bash
