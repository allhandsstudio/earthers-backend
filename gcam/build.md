Notes on building GCAM on Amazon Linux, for use in Lambda.

- Start new Amazon Linux instance

```bash
sudo yum update
sudo yum install git
sudo yum groupinstall "Development Tools"
git clone https://github.com/JGCRI/gcam-core.git
mkdir -p gcam-core/libs
cd gcam-core/libs
wget https://sourceforge.net/projects/boost/files/boost/1.62.0/boost_1_62_0.tar.gz/download -O boost_1_62_0.tar.gz
tar xzvf boost_1_62_0.tar.gz
cd boost_1_62_0
./bootstrap.sh --with-libraries=system,filesystem --prefix=/home/ec2-user/gcam-core/libs/boost_1_62_0/stage/lib
./b2 stage

cd ~
wget http://mirror.reverse.net/pub/apache//xerces/c/3/sources/xerces-c-3.1.4.tar.gz
tar xzvf xerces-c-3.1.4.tar.gz
cd xerces-c-3.1.4
export XERCES_INSTALL=/home/ec2-user/gcam-core/libs/xercesc
./configure --prefix=$XERCES_INSTALL --disable-netaccessor-curl
make install
```

- Edit <GCAM Workspace>/cvs/objects/util/base/include/definitions.h and set `__HAVE_JAVA__` to `0`
- Edit <GCAM Workspace>/cvs/objects/reporting/source/xml_db_outputter.cpp and set `DEBUG_XML_DB` to `1`
- Edit <GCAM Workspace>/cvs/objects/build/linux and set `JAVALINK = `

```bash
cd ~/gcam-core
make install_hector
export CXX=g++
export GCAM_HOME=/home/ec2-user/gcam-core
export BOOST_INCLUDE=${GCAM_HOME}/libs/boost_1_62_0
export BOOST_LIB=${GCAM_HOME}/libs/boost_1_62_0/stage/lib
export XERCES_INCLUDE=${GCAM_HOME}/libs/xercesc/include
export XERCES_LIB=${GCAM_HOME}/libs/xercesc/lib
export JAVA_INCLUDE=${JAVA_HOME}/include
export JAVA_LIB=${JAVA_HOME}/jre/lib/server
cd cvs/objects/build/linux/
make gcam
```

- copy `gcam.exe`, `libboost_filesystem.so.1.62.0`, `libboost_system.so.1.62.0`, `libxerces-c-3.1.so` to `lambda/lib` for inclusion in the lambda deploy zip
