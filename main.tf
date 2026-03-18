terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.23.0"
    }
  }
}

provider "google" {
  credentials = file("gcp-key.json")
  project     = "fin-agent-360"
  region      = "us-central1"
}

# Vertex AI API'ını aktif edelim (Agent'ımız için şart)
resource "google_project_service" "vertex_ai" {
  service = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

# Bir adet Storage Bucket oluşturalım (PDF'leri saklamak için)
resource "google_storage_bucket" "finance_docs" {
  name          = "finagent-360-docs-berk"
  location      = "US"
  force_destroy = true
}