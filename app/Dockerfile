# Purpose: Build the Alpine-based Campus Notice Board application.

FROM python:3.12-alpine

# Set these values when building each release.
ARG APP_VERSION=1.0.0
ARG STUDENT_ID=02230135

ENV APP_VERSION=${APP_VERSION} \
    STUDENT_ID=${STUDENT_ID} \
    FEATURE_PINNED=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Run the application as a non-root user.
RUN addgroup -S noticeboard \
    && adduser -S -G noticeboard -u 10001 noticeboard

COPY --chown=noticeboard:noticeboard app.py /app/app.py

USER noticeboard

EXPOSE 8080

CMD ["python", "/app/app.py"]