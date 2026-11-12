# syntax=docker/dockerfile:1
#
# Korningsmiljo for bevisfangsten: acquire -> candidates -> pool -> select -> input.
# Parameterregistret 1.13: container med last Python-version, inte vardens systempython.
#
# Python 3.13.18, Debian trixie, slim. Samma minorversion som projektets venv (3.13).
# Digesten ar multiarkitekturindexet for python:3.13.18-slim-trixie, last 2026-11-12.
# Taggen star kvar for lasbarhet; det ar digesten som avgor vad som byggs.
FROM python:3.13.18-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git behovs for "git pull fore korning" (1.13, kodatkomst). Paketet ar inte
# versionslast; det ror inte kedjans resultat, bara hur koden hamtas.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# requirements.txt ar en lasfil och installeras som en: exakt det som star dar,
# inga beroenden lost i bygget (--no-deps), och bygget faller om filen inte ar
# sjalvbarande (pip check). Saknas ett paket i lasfilen ska bygget stanna har,
# inte natten da kedjan anropar det.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-deps -r /tmp/requirements.txt \
 && pip check \
 && rm /tmp/requirements.txt

# Icke-root. Ingen hemkatalog: HOME pekar pa /tmp via compose. uid 10001 ar en
# reserv for den som kor imagen utan compose; pa varden satter compose uid och
# gid till den egna anvandaren (KEDJA_UID, KEDJA_GID i .env).
RUN groupadd --gid 10001 kedja \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin kedja
USER 10001:10001

# Koden ligger INTE i imagen. Repot monteras och dras med git pull fore korning,
# sa att imagen beskriver miljon och klonen beskriver koden.
WORKDIR /srv/repo

# Ingen standardkorning. En image som kor nagot sjalv nar den startar ar en image
# som kan kora ett dygn av misstag. Schemalaggaren startar containern med ett
# explicit kommando; utan ett sadant stannar den med felkod 64 och gor ingenting.
ENTRYPOINT []
CMD ["sh", "-c", "echo 'Ingen standardkorning. Starta med ett explicit kommando.' >&2; exit 64"]
