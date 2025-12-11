# to be run from /consumer folder

#!/bin/bash
set -e

echo "Building API image..."
docker build -f api/Dockerfile -t rusxl/consumer-api:latest .

echo "Building Job image..."
docker build -f job/Dockerfile -t rusxl/consumer-job:latest .

echo "Pushing API image..."
docker push rusxl/consumer-api:latest

echo "Pushing Job image..."
docker push rusxl/consumer-job:latest

echo "Done!"
