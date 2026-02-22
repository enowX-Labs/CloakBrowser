FROM python:3.12-slim

# Playwright system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdbus-1-3 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY cloakbrowser/ cloakbrowser/

RUN pip install --no-cache-dir .

# Pre-download stealth Chromium binary during build (not at runtime)
RUN python -c "from cloakbrowser import ensure_binary; ensure_binary()"

CMD ["python"]
