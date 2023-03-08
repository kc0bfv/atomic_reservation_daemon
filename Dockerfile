FROM python:3-slim

RUN mkdir /etc/atomic_res/
RUN mkdir /var/lib/atomic_res

COPY empty_config.json /etc/atomic_res/config.json

RUN useradd -ms /bin/sh user
USER user
WORKDIR /home/user

COPY main.py ./atomic_res.py

EXPOSE 8080

CMD ["python", "./atomic_res.py", "/etc/atomic_res/config.json", "/var/lib/atomic_res/savefile"]