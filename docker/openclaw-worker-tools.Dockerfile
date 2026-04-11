# syntax=docker/dockerfile:1.6
# Chloe (worker) tools: Bun, QMD (OpenClaw memory), Himalaya, Python for m365, Bitwarden CLI (BW runs in worker).
ARG OPENCLAW_BASE_IMAGE=ghcr.io/openclaw/openclaw:main
FROM ${OPENCLAW_BASE_IMAGE}

USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG TARGETARCH
ARG HIMALAYA_VERSION=v1.1.0

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      ffmpeg \
      jq \
      python3 \
      python3-bcrypt \
      python3-pip \
      python3-venv \
      unzip \
 && rm -rf /var/lib/apt/lists/*

# Bun (install to a global path so USER node sees it on PATH)
ENV BUN_INSTALL=/usr/local/bun
ENV PATH="${BUN_INSTALL}/bin:${PATH}"
# Agent shells get a restricted PATH (includes /usr/local/bin, not BUN_INSTALL).
RUN curl -fsSL https://bun.sh/install | bash \
 && ln -sf /usr/local/bun/bin/bun /usr/local/bin/bun \
 && ln -sf /usr/local/bun/bin/bunx /usr/local/bin/bunx

# Himalaya mail CLI (official release artifact)
RUN case "${TARGETARCH}" in \
      amd64) HIMALAYA_ARCH="x86_64" ;; \
      arm64) HIMALAYA_ARCH="aarch64" ;; \
      *) echo "Unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac \
 && curl -fsSL -o /tmp/himalaya.tgz "https://github.com/pimalaya/himalaya/releases/download/${HIMALAYA_VERSION}/himalaya.${HIMALAYA_ARCH}-linux.tgz" \
 && tar -xzf /tmp/himalaya.tgz -C /usr/local/bin himalaya \
 && chmod +x /usr/local/bin/himalaya \
 && rm -f /tmp/himalaya.tgz

# Bitwarden CLI (worker holds vault access; no bridge)
RUN npm i -g @bitwarden/cli

# QMD for OpenClaw memory provider; symlink into /usr/local/bin like bun (restricted agent PATH).
RUN /usr/local/bin/bun install -g @tobilu/qmd \
 && ln -sf /usr/local/bun/bin/qmd /usr/local/bin/qmd

USER node
