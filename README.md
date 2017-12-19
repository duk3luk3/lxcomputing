# LXC Compute Cluster

Goal: Provide management and scheduling for LXC containers in a small cluster.

LXD and OpenStack both seemed very unwieldy and bloaty to me, so I decided
to make my own leveraging just the LXC python interface.

This project consists of two parts:

* A management controller and interface using Flask, SQLAlchemy, and REDIS to
  administrate the cluster configuration
* A daemon on that runs on each compute node and fetches events from REDIS to
  configure / orchestrate containers

# Prerequisites

TODO

# Setup

TODO
