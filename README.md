# dockmirror

**This is in alpha stage**

dockmirror is a docker wrapper to execute container program against local files.  

ex: `dockermirror.py docker run -it hashicorp/terraform:0.12.4 init`
![Terraform example](https://raw.githubusercontent.com/beteras/dockmirror/master/assets/terraform_sample/example.gif)

dockmirror use another container and rsync to synchronize your local current working directory on a volume.  
rsync use `docker exec` as a transport. Own container network is never used.

## why another local/container files sync

- Client side only
    - No docker host modification
    - No docker plugin
    - Own container network never used
    - No modification to your container/Dockerfile
- Easy to use
    - Few dependencies available on all Linux distro package system.
    - Just add `dockmirror.py` in front of your docker command. No fuzzy configuration/modification.
    - Multi user/machine/path by using an UID on volume.
- Fast
    - rsync is the de facto standard for efficient file sync.
    - Container used to sync files is keep running for 15min before it kill/delete itself.
    - Volume have an UID to allow reuse in case the container running sync is not running.

## install

Local dependencies
 - [Python library for the Docker Engine API](https://github.com/docker/docker-py)
 - [rsync](https://rsync.samba.org/)

Download [dockmirror.py](https://raw.githubusercontent.com/beteras/dockmirror/master/dockmirror.py).  
You can copy it in `/usr/local/bin`.

## use

if your command was:

`docker run --rm busybox ls -la`

prepend dockmirror.py:

`./dockmirror.py docker run --rm busybox ls -la`

## how it's works

- New container executed
    - Container come from [beteras/dockmirror](https://hub.docker.com/r/beteras/dockmirror)
    - This container auto kill/remove itself without activity for 15min
    - New volume created
        - rsync synchronize it with your local folder
- Your docker command
    - Modified to include the volume
    - Executed
- Get modified files back
    - rsync synchronize the volume with your local current working directory

## TODO
- Everything OK, expect the final rsync from volume to your local current working directory. Additional security is need to be avoid mass local files deleted. 
- [Github issues enhancement](https://github.com/beteras/dockmirror/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
