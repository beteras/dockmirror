#!/usr/bin/python3

import argparse
import hashlib
import logging
import os
import subprocess
import sys

import docker


def get_size(start_path = '.'):
    total_size = 0
    total_file = 0

    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            total_file += 1

            # skip if it is symbolic link
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size, total_file


def get_sha256(text):
    return hashlib.sha256(bytearray(text, 'utf8')).hexdigest()


def auto_unit(size):
    power = 2 ** 10
    n = 0
    power_labels = {0: '', 1: 'k', 2: 'm', 3: 'g', 4: 't'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n] + 'b'


# FIXME: Linux with dbus only
def get_machine_id():
    return open('/var/lib/dbus/machine-id').read().strip()


class DockMirror:
    def __init__(self, path, docker_args):
        self.docker_args = docker_args
        self.path = path

        self.volume_name = 'dockmirror_{}_{}'.format(
            get_machine_id(),
            get_sha256(self.path)
        )

        self.convert_docker_args_to_env()
        self.docker = docker.from_env()

        path_size, path_files = get_size()
        logging.info('current dir: files: {}: size: {:.2f} {}'.format(
            path_files,
            *auto_unit(path_size)
        ))

    # https://docs.docker.com/engine/reference/commandline/cli/#environment-variables
    # TODO: Implements all useful others vars
    def convert_docker_args_to_env(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-H', '--host')
        args, unknown = parser.parse_known_args(self.docker_args)

        if args.host:
            os.environ["DOCKER_HOST"] = args.host

    def sync(self):
        dockmirrors = self.docker.containers.list(filters={
            'ancestor': 'dockmirror',
            'status': 'running',
            'label': [
                'mid=' + get_machine_id(),
                'path=' + get_sha256(self.path),
            ],
        })

        assert len(dockmirrors) <= 1, "can't have more than 1 container with same labels"

        dockmirror = dockmirrors[0] if len(dockmirrors) == 1 else None

        if not dockmirror:
            dockmirror = self.docker.containers.run(
                image='dockmirror',

                volumes={
                    self.volume_name: {
                        'bind': '/home/dockmirror'
                    },
                },

                labels={
                    'mid': get_machine_id(),
                    'path': get_sha256(self.path),
                },

                auto_remove=True,
                detach=True,
            )

        rsync = [
            'rsync',
            '--blocking-io',
            '--archive',
            '-e',
            'docker exec -i',
            '.',
            dockmirror.id + ':'
        ]

        if logging.getLogger().level == logging.DEBUG:
            rsync.append('-vv')

        subprocess.check_call(rsync)

        logging.info('volume synchronized')


def main(args):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    dm = DockMirror(os.getcwd(), args)
    dm.sync()


if __name__ == '__main__':
    main(sys.argv[1:])