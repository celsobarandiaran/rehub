# ReHub en un contenedor (Render, o cualquier alojamiento con Docker).
# Escucha en el puerto que diga la variable PORT (Render la pone); si no, en el 7860.
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
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips '*'"]
