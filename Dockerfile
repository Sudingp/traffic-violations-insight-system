# Airflow + Spark image for the traffic pipeline.
# Spark needs a Java runtime; PySpark itself comes from pip.
FROM apache/airflow:3.3.2

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
# Pinning apache-airflow stops pip from upgrading or downgrading Airflow itself.
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /tmp/requirements-airflow.txt
