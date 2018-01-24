#!/bin/sh

set -eu

set -x

# Probably not really needed, but we set it anyway
export http_proxy="http://proxy.in.tum.de:8080"
export https_proxy="http://proxy.in.tum.de:8080"

# We are in the rootfs
export LXC_ROOTFS=""

# make resolv.conf
echo "nameserver 131.159.254.1" >>${LXC_ROOTFS}/etc/resolvconf/resolv.conf.d/base
echo "nameserver 131.159.254.2" >>${LXC_ROOTFS}/etc/resolvconf/resolv.conf.d/base
echo "search informatik.tu-muenchen.de" >>${LXC_ROOTFS}/etc/resolvconf/resolv.conf.d/base

# fix interfaces (?)
#sed -i 's/iface eth0 inet dhcp/iface eth0 inet manual/' ${LXC_ROOTFS}/etc/network/interfaces

# fix sources.list
sed -i 's/archive.ubuntu.com/ubuntumirror.informatik.tu-muenchen.de/' ${LXC_ROOTFS}/etc/apt/sources.list

# set up proxy
if [ -n "${http_proxy:-}" ]; then
    echo "Acquire::http::Proxy::security.ubuntu.com \"${http_proxy}\";" >> ${LXC_ROOTFS}/etc/apt/apt.conf.d/apt-proxy
#    chown "${LXC_MAPPED_UID}:${LXC_MAPPED_GID}" ${LXC_ROOTFS}/etc/apt/apt.conf.d/apt-proxy

    echo "export http_proxy=${http_proxy}" >> ${LXC_ROOTFS}/etc/bash.bashrc
fi
if [ -n "${https_proxy:-}" ]; then
    echo "Acquire::https::Proxy::security.ubuntu.com \"${https_proxy}\";" >> ${LXC_ROOTFS}/etc/apt/apt.conf.d/apt-proxy
#    chown "${LXC_MAPPED_UID}:${LXC_MAPPED_GID}" ${LXC_ROOTFS}/etc/apt/apt.conf.d/apt-proxy

    echo "export https_proxy=${http_proxy}" >> ${LXC_ROOTFS}/etc/bash.bashrc
fi

echo '%root   ALL=(ALL) NOPASSWD: ALL' >> ${LXC_ROOTFS}/etc/sudoers
sed -i '/Defaults\tenv_reset/a Defaults\tenv_keep += "ftp_proxy http_proxy https_proxy no_proxy"' ${LXC_ROOTFS}/etc/sudoers

apt update
apt upgrade -y
apt install -y openssh-server


exit 0
