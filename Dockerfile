FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi_app.py ./
# If you plan to bake data in the image, uncomment the following lines:
# COPY transactions.csv customer_profiles.csv ./
# ENV TX_PATH=transactions.csv
# ENV PROFILES_PATH=customer_profiles.csv

EXPOSE 8000
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
