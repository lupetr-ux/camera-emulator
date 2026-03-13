FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/bluenviron/mediamtx/releases/download/v1.6.0/mediamtx_v1.6.0_linux_amd64.tar.gz && \
    tar -xzf mediamtx_v1.6.0_linux_amd64.tar.gz && \
    mv mediamtx /usr/local/bin/ && \
    rm mediamtx_v1.6.0_linux_amd64.tar.gz

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
COPY mediamtx.yml /mediamtx.yml

RUN mkdir -p /app/videos /app/config

RUN echo '#!/bin/bash\n\
/usr/local/bin/mediamtx /mediamtx.yml &\n\
sleep 3\n\
python /app/start_all_cameras.py &\n\
python main.py' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 5000 554 1935 8888 8889

CMD ["/app/start.sh"]
