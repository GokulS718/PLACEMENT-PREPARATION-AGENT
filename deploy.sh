#!/bin/bash
# Google Cloud Run Deployment Script

# 1. Project Configuration
PROJECT_ID="your-gcp-project-id"
SERVICE_NAME="placement-prep-agent"
REGION="us-central1"

echo "============================================="
echo "Deploying $SERVICE_NAME to Google Cloud Run"
echo "Project: $PROJECT_ID, Region: $REGION"
echo "============================================="

# 2. Build the Docker Image using Google Cloud Build
echo "Building container image using Cloud Build..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME --project $PROJECT_ID

# 3. Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=sqlite:///./placement_prep.db" \
  --project $PROJECT_ID

echo "============================================="
echo "Deployment initiated successfully!"
echo "============================================="
