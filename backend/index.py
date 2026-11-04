"""Vercel FastAPI entrypoint. Backend project root directory must be backend/.

The serverless function starts with case endpoints disabled unless Auth0 and the
database are explicitly configured.
"""
from app.main import app
