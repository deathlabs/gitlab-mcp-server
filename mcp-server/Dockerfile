FROM alpine:3.24
LABEL image.authors="Victor Fernandez III"
WORKDIR /home/gitlab_mcp_server/
COPY gitlab_mcp_server/pyproject.toml pyproject.toml
COPY gitlab_mcp_server/main.py main.py
COPY gitlab_mcp_server/policy.yaml policy.yaml
COPY gitlab_mcp_server/tools/ tools/
COPY gitlab_mcp_server/uv.lock uv.lock
ENV UV_PYTHON_INSTALL_DIR=/home/gitlab_mcp_server/.uv-python
RUN apk add --no-cache python3=3.14.8-r0 uv=0.11.19-r0 && \
    apk upgrade --no-cache libcrypto3 libssl3 &&\
    uv sync --frozen --python /usr/bin/python3 && \
    addgroup -g 1000 gitlab_mcp_server &&\
    adduser -D -G gitlab_mcp_server -u 1000 gitlab_mcp_server -h /home/gitlab_mcp_server/ &&\
    chown -R gitlab_mcp_server:gitlab_mcp_server /home/gitlab_mcp_server/
ENV PATH="/home/gitlab_mcp_server/.venv/bin:$PATH"
USER 1000
EXPOSE 8003
CMD [ "python", "-m", "main" ]
