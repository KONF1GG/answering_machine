FROM python:3.13-slim-bookworm

ENV TZ=Asia/Yekaterinburg
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG branch
ENV BRANCH=$branch

ADD . /app

WORKDIR /app

RUN uv venv

ENV UV_PROJECT_ENVIRONMENT=/env

RUN uv sync --frozen --no-cache

CMD ["uv", "run", "main.py"]
