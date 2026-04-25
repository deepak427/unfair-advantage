from google.cloud import storage
from config.settings import settings

client = storage.Client(project=settings.gcp_project_id)
bucket = client.bucket(settings.gcs_bucket_name)
blob = bucket.blob("processed/Gitapress_Gita_Roman.json")
if blob.exists():
    blob.delete()
    print("Deleted processed marker")
else:
    print("Already clean")
