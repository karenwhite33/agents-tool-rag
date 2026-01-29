#!/bin/bash
# -----------------------
# FastAPI Backend Deployment to Cloud Run
# -----------------------

# Exit immediately if a command exits with a non-zero status
set -e

#-----------------------
# Load environment variables
#-----------------------

if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Load environment variables from .env file
set -o allexport
source .env
set +o allexport

echo "✅ Environment variables loaded."

# -----------------------
# Configuration
# -----------------------
PROJECT_ID="rss-rag-485516"
SERVICE_NAME="ai-agent-tools-fastapi"
REGION="europe-west6" #europe-west1 "europe-west6"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# -----------------------
# Set project
# -----------------------
echo "🔧 Setting GCP project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"


# -----------------------
# Enable required APIs
# -----------------------
echo "🔧 Enabling required GCP services..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com

# -----------------------
# Build and push Docker image
# -----------------------
echo "🐳 Building and pushing Docker image..."
gcloud builds submit --config cloudbuild_fastapi.yaml \
    --substitutions=_SERVICE_NAME=$SERVICE_NAME

# -----------------------
# Deploy to Cloud Run
# -----------------------
echo "🚀 Deploying $SERVICE_NAME to Cloud Run..."

# Combine all env vars using custom delimiter for values with commas
# Use ^##^ to tell gcloud to use ## as delimiter instead of comma
gcloud run deploy "$SERVICE_NAME" \
--image "$IMAGE_NAME" \
--platform managed \
--region "$REGION" \
--allow-unauthenticated \
--memory 2.5Gi \
--cpu 1 \
--timeout 180 \
--concurrency 2 \
--min-instances 0 \
--max-instances 2 \
--execution-environment gen2 \
--cpu-boost \
--set-env-vars "^##^HF_HOME=/tmp/huggingface##HUGGING_FACE__API_KEY=$HUGGING_FACE__API_KEY##QDRANT__API_KEY=$QDRANT__API_KEY##QDRANT__URL=$QDRANT__URL##QDRANT__COLLECTION_NAME=$QDRANT__COLLECTION_NAME##QDRANT__DENSE_MODEL_NAME=$QDRANT__DENSE_MODEL_NAME##QDRANT__SPARSE_MODEL_NAME=$QDRANT__SPARSE_MODEL_NAME##OPENROUTER__API_KEY=$OPENROUTER__API_KEY##OPIK__API_KEY=$OPIK__API_KEY##OPIK__PROJECT_NAME=$OPIK__PROJECT_NAME##ALLOWED_ORIGINS=$ALLOWED_ORIGINS##API_KEY=$API_KEY##AUTH_REQUIRED=$AUTH_REQUIRED##ENVIRONMENT=$ENVIRONMENT##RATE_LIMIT_PER_MINUTE=$RATE_LIMIT_PER_MINUTE##RATE_LIMIT_PER_HOUR=$RATE_LIMIT_PER_HOUR"

# Log the allowed origins
echo "✅ Allowed origins set to: $ALLOWED_ORIGINS"

# -----------------------
# Capture the deployed service URL and update BACKEND_URL
#-----------------------
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')
echo "Deployment complete!"
echo "Service URL: $SERVICE_URL"



# # -----------------------
# # Update BACKEND_URL dynamically
# # -----------------------
# echo "🔄 Updating BACKEND_URL to $SERVICE_URL..."
# gcloud run services update "$SERVICE_NAME" \
#     --region "$REGION" \
#     --update-env-vars BACKEND_URL="$SERVICE_URL"

# echo "✅ BACKEND_URL updated successfully."
