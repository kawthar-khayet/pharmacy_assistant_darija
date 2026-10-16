# API DwaTalk pour Hugging Face Spaces (Docker).
FROM python:3.11-slim

# Hugging Face lance le conteneur avec l'utilisateur 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface
WORKDIR /home/user/app

# torch en version CPU (~200 Mo) avant le reste : sinon pip prend la version CUDA (~2,5 Go)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user api/ api/
COPY --chown=user nlp/ nlp/
COPY --chown=user data/clean/ data/clean/

# data/rag/ n'est pas dans git : l'index RAG est construit ici, une fois par mise a jour.
# Le modele Whisper est telecharge maintenant pour que la 1re question vocale ne l'attende pas.
RUN python -m nlp.rag.fiches && python -m nlp.rag.index
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
