# Use amd64 so conda-forge has PsychoPy binaries
FROM --platform=linux/amd64 continuumio/miniconda3:24.11.1-0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    SDL_AUDIODRIVER=dummy

# + xauth (needed by xvfb-run) and common X11/OpenGL/audio libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth \
    libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 libsm6 libxrandr2 \
    libxi6 libxfixes3 libxcursor1 libxxf86vm1 \
    libasound2 portaudio19-dev \
    fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN conda config --add channels conda-forge \
 && conda config --set channel_priority strict

COPY environment.yml /app/
RUN conda env create -f environment.yml && conda clean -afy

COPY . /app/

# Use xvfb-run (now that xauth is present)
CMD ["bash","-lc","xvfb-run -a -s \"-screen 0 1920x1080x24\" conda run --no-capture-output -n NovelStimuli python multimodal_pairtest.py"]
