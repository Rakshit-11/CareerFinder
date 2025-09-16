#!/bin/bash
# Azure App Service startup script
gunicorn -k uvicorn.workers.UvicornWorker server:app --bind=0.0.0.0:8000 --timeout 600
