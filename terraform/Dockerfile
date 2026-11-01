FROM debian:bookworm-slim

# Set non-interactive frontend for aptENV DEBIAN_FRONTEND=noninteractive

# Install prerequisites and Terraform
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        unzip \
        wget

RUN install -m 0755 -d /etc/apt/keyrings && \
    wget -qO- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    gpg --no-default-keyring --keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg --fingerprint && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main" > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends terraform=1.16.0-1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /usr/share/keyrings/hashicorp-archive-keyring.gpg

# Verify Terraform installation
RUN terraform --version

# AWS credentials and session token (passed at build/run time)
ENV AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"
ENV AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY"
ENV AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN"

# Set working directory
WORKDIR /workspace