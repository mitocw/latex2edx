# ############
#
# This Dockerfile is created by Gregor von Laszewski
# laszewski@gmail.com
# You can create a container with
#
#
# 
# docker build -t latex2edx:1.5.3
#	docker tag latex2edx:1.5.3 latex2edx:latest
#
# to run it interactively do something like
#
# 	docker run -v `pwd`:/latex2edx -w /latex2edx --rm -it clatex2edx:latest  /bin/bash
#
# #############

FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y libxml2-dev libxml2-utils libxslt1-dev
RUN apt-get install -y texlive-full
RUN apt-get install -y texlive-latex-extra poppler-utils
RUN apt-get install -y dvipng
RUN apt-get install -y python
RUN apt-get install -y python-pip
RUN apt-get install -y libxml2-utils python-lxml

RUN pip install pip -U
RUN git clone https://github.com/mitocw/latex2edx.git

WORKDIR /latex2edx

RUN pip install -r requirements.txt
RUN pip install -r test_requirements.txt

RUN pip install .
