ARG BASE=ollama/ollama:latest
FROM ${BASE}

ARG MODEL=qwen3.5:9b-q4_K_M
ARG PYMUPDF_VERSION=1.26.7

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir "pymupdf==${PYMUPDF_VERSION}" \
 && ln -s "$(dirname "$(find /usr/share -name eng.traineddata | head -1)")" /opt/tessdata

# Model goes into the image so the running container never needs a network.
ENV OLLAMA_MODELS=/opt/models
RUN mkdir -p /opt/models \
 && (ollama serve >/tmp/pull.log 2>&1 &) \
 && for i in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done \
 && ollama pull "${MODEL}" \
 && chmod -R a+rX /opt/models && rm -f /tmp/pull.log

# Spreadsheet libraries. Kept below the model layer on purpose: anything changed above it
# makes Docker download the 6.6 GB model again.
ARG OPENPYXL_VERSION=3.1.5
ARG ET_XMLFILE_VERSION=2.0.0
ARG CALAMINE_VERSION=0.9.1
RUN /opt/venv/bin/pip install --no-cache-dir "openpyxl==${OPENPYXL_VERSION}" \
      "et-xmlfile==${ET_XMLFILE_VERSION}" "python-calamine==${CALAMINE_VERSION}"

RUN useradd --uid 10001 --no-create-home --shell /bin/bash redactor
COPY --chmod=0555 entrypoint.sh redact.py chat.py selftest.py chat docs redact bashrc /app/

ENV MODEL=${MODEL} \
    HOME=/tmp/home \
    WORK=/work \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_NOPRUNE=1 \
    OLLAMA_KEEP_ALIVE=30m \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    TESSDATA_PREFIX=/opt/tessdata \
    PATH=/app:/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001
WORKDIR /work
ENTRYPOINT ["/app/entrypoint.sh"]
