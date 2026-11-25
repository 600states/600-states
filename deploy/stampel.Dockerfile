# syntax=docker/dockerfile:1
#
# Korningsmiljo for STAMPLINGEN. En egen image, inte kedjans.
#
# Skalet ar inte stadning. Nio Bitcoin- och git-bibliotek hor inte hemma i det
# instrument som laser nyheter, och en stampel intygar ett fardigt manifest -
# den tillverkar det inte. Samma princip som haller urval och farg atskilda:
# den som kan rakna fram ett manifest i samma miljo som intygar det kan inte
# visa att den lat bli.
#
# DIGESTEN AR DENSAMMA SOM KEDJANS BASIMAGE, skriven en andra gang har. Det ar
# ett varde pa tva stallen - FYND 004:s form - och det ar med avsikt: kedjans
# image far inte roras i den har andringen. Flyttas den ena maste den andra
# flyttas samtidigt. En delad ARG hade krav att bada Dockerfile:erna andrades.
#
# Python 3.13.18, Debian trixie, slim. Multiarkitekturindexet, last 2026-11-12.
FROM python:3.13.18-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git behovs for "git pull fore korning" och av GitPython, som ar ett av de nio
# paketen. ca-certificates behovs for kalendrarna - stamplingen ar det enda
# steget i hela projektet som med avsikt talar med en frammande tjanst om ett
# fardigt verk.
#
# MINISIGN AR VERSIONSLAST, git och ca-certificates ar det inte. Skillnaden ar
# inte stadning: git avgor hur koden hamtas och ror inte resultatet, medan
# minisign TILLVERKAR ett bevis. Verktyget som gor beviset ar en matt parameter
# och ska bytas med avsikt, pa samma satt som de nio paketen i lasfilen.
#
# Uppmatt 2026-11-25 ur Debians PGP-signerade index for trixie:
#   minisign 0.12-1 amd64, pool/main/m/minisign/minisign_0.12-1_amd64.deb
#   17060 byte, sha256 4a3f9611a0e363e5c574129dc0195ba951c6be4b8f7ac13d64880000e3b22ebe
#   beror libc6 (>= 2.34) och libsodium23 (>= 0.7.0)
#
# libsodium23 last INTE. Det ar kryptobiblioteket under klienten, och en
# sakerhetsuppdatering dar ska na containern utan att nagon andrar en rad.
# Faller bygget for att 0.12-1 inte langre finns pa spegeln ar det ratt
# beteende: da ska versionen flyttas med avsikt, inte halka med.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates minisign=0.12-1 \
 && rm -rf /var/lib/apt/lists/*

# Egen lasfil, installerad som en: exakt det som star dar, inga beroenden lost
# i bygget, och bygget faller om filen inte ar sjalvbarande.
COPY deploy/requirements-stampel.txt /tmp/requirements-stampel.txt
RUN pip install --no-deps -r /tmp/requirements-stampel.txt \
 && pip check \
 && rm /tmp/requirements-stampel.txt

# Icke-root, ingen hemkatalog, samma reservs-uid som kedjan om imagen kors utan
# compose. Pa varden satter compose uid och gid till kedjans egen anvandare.
RUN groupadd --gid 10001 kedja \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin kedja
USER 10001:10001

# Koden ligger INTE i imagen, av samma skal som i kedjans image: imagen
# beskriver miljon, klonen beskriver koden.
WORKDIR /srv/repo

# Ingen standardkorning. En image som stamplar nar den startar kan stampla ett
# dygn av misstag, och en stampel gar inte att ta tillbaka.
ENTRYPOINT []
CMD ["sh", "-c", "echo 'Ingen standardkorning. Starta med ett explicit kommando.' >&2; exit 64"]
