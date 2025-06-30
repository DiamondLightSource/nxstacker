FROM python:3.13-slim

LABEL org.opencontainers.image.title=nxstacker
LABEL org.opencontainers.image.description="nxstacker is an utility to stack projections from different types of experiments to produce NeXus-compliance file(s)."
LABEL org.opencontainers.image.vendor=DiamondLightSource
LABEL org.opencontainers.image.authors="Timothy Poon <timothy.poon@diamond.ac.uk>"
LABEL org.opencontainers.image.documentation=https://github.com/DiamondLightSource/nxstacker
LABEL org.opencontainers.image.source=https://github.com/DiamondLightSource/nxstacker
LABEL org.opencontainers.image.licenses=MIT

WORKDIR /nxstacker

COPY . .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir .

# Set default command to show help
ENTRYPOINT ["tomojoin"]
CMD ["--help"]