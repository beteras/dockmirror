# dockmirror

This is in alpha

Docker wrapper to execute container program against local files.

dockmirror use rsync to make a copy of your local folder on a volume.
rsync use `docker exec` as a transport. Own container network is never used.

## install

Download this file [dockmirror.py](https://raw.githubusercontent.com/beteras/dockmirror/master/dockmirror.py)
You can copy it in `/usr/local/bin`

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
        - [rsync](https://rsync.samba.org/) synchronize it with your local folder
- Your docker command
    - Modified to include the volume
    - Executed
- Get modified files
    - rsync synchronize the volume with your local current working directory

## TODO
- Everything OK, expect the final rsync from volume to your local current working directory
- Better README.md
