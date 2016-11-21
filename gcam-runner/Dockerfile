FROM ubuntu:16.04
MAINTAINER Beau Cronin, beau.cronin@gmail.com

RUN apt-get update && apt-get install -y \
	g++ \
	gcc \
	git \
	make \
	python python-pip \
	wget

RUN git clone https://github.com/JGCRI/gcam-core.git

# Boost
RUN mkdir -p gcam-core/libs \
	&& cd gcam-core/libs \
	&& wget -nv https://sourceforge.net/projects/boost/files/boost/1.62.0/boost_1_62_0.tar.gz/download -O boost_1_62_0.tar.gz \
	&& tar xzvf boost_1_62_0.tar.gz 
RUN cd gcam-core/libs/boost_1_62_0 \
	&& ./bootstrap.sh --with-libraries=system,filesystem --prefix=/home/ec2-user/gcam-core/libs/boost_1_62_0/stage/lib; cat bootstrap.log \
	&& ./b2 stage

# Xerces
ENV XERCES_INSTALL /gcam-core/libs/xercesc
RUN wget http://mirror.reverse.net/pub/apache//xerces/c/3/sources/xerces-c-3.1.4.tar.gz \
	&& tar xzvf xerces-c-3.1.4.tar.gz \
	&& cd xerces-c-3.1.4 \
	&& ./configure --prefix=$XERCES_INSTALL --disable-netaccessor-curl \
	&& make install

# Hector
RUN cd gcam-core && make install_hector

# Patch and compile
ENV CXX g++
ENV GCAM_HOME /gcam-core
ENV BOOST_INCLUDE /gcam-core/libs/boost_1_62_0
ENV BOOST_LIB /gcam-core/libs/boost_1_62_0/stage/lib
ENV XERCES_INCLUDE /gcam-core/libs/xercesc/include
ENV XERCES_LIB /gcam-core/libs/xercesc/lib
ENV JAVA_INCLUDE ${JAVA_HOME}/include
ENV JAVA_LIB ${JAVA_HOME}/jre/lib/server

COPY nojava.patch /gcam-core/cvs/objects/util/base/include/
RUN cd gcam-core/cvs/objects/util/base/include && patch < nojava.patch
COPY xml_output.patch /gcam-core/cvs/objects/reporting/source/
RUN cd gcam-core/cvs/objects/reporting/source && patch < xml_output.patch
COPY no_javalink.patch /gcam-core/cvs/objects/build/linux/
RUN cd gcam-core/cvs/objects/build/linux && patch < no_javalink.patch

RUN cd /gcam-core/cvs/objects/build/linux/ \
	&& make gcam

RUN pip install boto3
COPY ./config /
COPY app.py /
CMD python app.py
