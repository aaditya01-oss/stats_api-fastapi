# ── Stage: base image ──────────────────────────────────────────────
# FROM tells Docker: start with this existing image as your foundation.
# We use the official Python 3.11 image on "slim" — a minimal Linux OS
# with Python pre-installed. "slim" is ~50MB vs ~900MB for the full image.
# Always pin the exact version (3.11-slim not just python) so your build
# never breaks because someone updated the base image.
FROM python:3.11-slim

# ── Working directory ───────────────────────────────────────────────
# WORKDIR creates this folder inside the container and makes it the
# default location for all following commands.
# Think of it as: cd /app, but it also creates /app if it doesn't exist.
WORKDIR /app

# ── Install dependencies FIRST ─────────────────────────────────────
# COPY the requirements file before copying your code.
# Why? Docker caches each step (called a "layer") as long as the files
# haven't changed. If you copy requirements.txt first and install, that
# layer gets cached. Next time you build after only changing your code,
# Docker skips the pip install step entirely — much faster builds.
# If you copied all files first, ANY code change would bust the cache
# and reinstall everything from scratch every time.
COPY requirements.txt .

# RUN executes a shell command during the build.
# --no-cache-dir tells pip not to store downloaded packages,
# keeping the image smaller.
RUN pip install --no-cache-dir --force-reinstall "wheel>=0.46.2" && \
    pip install --no-cache-dir -r requirements.txt
# ── Copy application code ───────────────────────────────────────────
# NOW copy the rest of the code. This layer only rebuilds when your
# code changes — not when dependencies change.
COPY . .

# ── Expose the port ─────────────────────────────────────────────────
# EXPOSE documents which port the app listens on.
# It does NOT actually open the port — that happens at docker run.
# It's documentation for humans and tools reading the Dockerfile.
EXPOSE 8000

# ── Start command ───────────────────────────────────────────────────
# CMD is the default command that runs when the container starts.
# We use JSON array format (exec form) — not a shell string.
# --host 0.0.0.0 means "listen on all network interfaces inside
# the container", not just localhost. Without this, the app listens
# only on the container's internal loopback — unreachable from outside.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]