# ReHub en Hugging Face Spaces (tipo Docker). El puerto 7860 es el que espera Hugging Face.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 REHUB_ENTORNO=nube
RUN useradd -m -u 1000 rehub
WORKDIR /home/rehub/app
COPY --chown=rehub requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=rehub app ./app
COPY --chown=rehub datos_demo ./datos_demo
USER rehub
EXPOSE 7860
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
