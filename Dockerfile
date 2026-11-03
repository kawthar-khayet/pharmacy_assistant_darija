# API DwaTalk pour Hugging Face Spaces (Docker).
FROM python:3.11-slim

# Hugging Face lance le conteneur avec l'utilisateur 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface
WORKDIR /home/user/app

# torch et torchvision (EasyOCR) en version CPU avant le reste : sinon pip prend la version CUDA (~2,5 Go)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user api/ api/
COPY --chown=user nlp/ nlp/
COPY --chown=user data/clean/ data/clean/

# data/rag/ n'est pas dans git : l'index RAG est construit ici, une fois par mise a jour.
# Le modele Whisper est telecharge maintenant pour que la 1re question vocale ne l'attende pas.
RUN python -m nlp.rag.fiches && python -m nlp.rag.index
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
# Idem pour les modeles EasyOCR (arabe et francais) : dans l'image, charges en memoire au 1er scan seulement.
RUN python -c "import easyocr; easyocr.Reader(['ar', 'en'], gpu=False, verbose=False); easyocr.Reader(['fr'], gpu=False, verbose=False)"

EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
