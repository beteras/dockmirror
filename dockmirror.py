#!/usr/bin/python3

import argparse
import getpass
import grp
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

        if self.docker_args[0].startswith('-d'):
            self.docker_args.pop(0)
            self.parent_depth = int(self.docker_args.pop(0))
        else:
            self.parent_depth = 0

        self.path = path
        self.container = None

        # TODO: No easier way ?
        self.user_name = getpass.getuser()
        self.group_name = grp.getgrgid(os.getegid()).gr_name

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

        # TODO: ugly
        self.insert_index = self.docker_args.index(unknown[1])

        if args.host:
            os.environ["DOCKER_HOST"] = args.host

    def start_container(self):
        container = self.docker.containers.run(
            image='beteras/dockmirror',

            volumes={
                self.volume_name: {
                    'bind': '/home/' + self.user_name
                },
            },

            labels={
                'mid': get_machine_id(),
                'path': get_sha256(self.path),
            },

            auto_remove=True,
            detach=True,
        )

        # TODO: Ugly fast fix
        self.container = container
        self.create_user()

        return container

    def get_container(self):
        dockmirrors = self.docker.containers.list(filters={
            'ancestor': 'beteras/dockmirror',
            'status': 'running',
            'label': [
                'mid=' + get_machine_id(),
                'path=' + get_sha256(self.path),
            ],
        })

        assert len(dockmirrors) <= 1, "can't have more than 1 container with same labels"

        return dockmirrors[0] if len(dockmirrors) == 1 else self.start_container()

    def sync(self):
        self.container = self.get_container()

        self.create_target_path()
        self.sync_local_volume()

        cmd_args = self.docker_args[0:self.insert_index + 1] + [
            '--user', '{}:{}'.format(os.geteuid(), os.getegid()),
            # '--user', '{}:{}'.format(self.user_name, self.group_name),
            '--workdir', self.path,
            '-v', self.volume_name + ':/home/' + self.user_name,
        ] + self.docker_args[self.insert_index + 1:]

        logging.debug(' '.join(cmd_args))

        subprocess.call(cmd_args)

        self.sync_volume_local()

    def docker_exec(self, args):
        subprocess.check_call([
            'docker',
            'exec',
            '--interactive',
            self.container.id,
            *map(str, args),  # Sorry, int problems
        ])

    def create_target_path(self):
        self.docker_exec([
            'mkdir',
            '-p',
            self.path,
        ])

    def create_user(self):
        logging.info('creating user/group: {}:{}'.format(
            getpass.getuser(),
            self.group_name,
        ))

        self.docker_exec([
            'addgroup',
            self.group_name,
        ])

        self.docker_exec([
            'adduser',
            '-D', self.user_name,
            '-G', self.group_name,
        ])

    def sync_local_volume(self):
        rsync_args = [
            'rsync',
            '--whole-file',

            '--archive',
            '--delete',

            '--blocking-io',  # Need to use docker as transport
            '--rsh', 'docker exec --interactive',

            self.path + '/' + ('../' * self.parent_depth),
            self.container.id + ':' + self.path + ('/..' * self.parent_depth),
        ]

        if os.path.exists(os.path.join(self.path, '.git')):
            rsync_args.extend(['--exclude', '.git*'])

        if logging.getLogger().level == logging.DEBUG:
            rsync_args.append('-vv')

        logging.debug(' '.join(rsync_args))
        subprocess.check_call(rsync_args)

        logging.info('volume synchronized')

    def sync_volume_local(self):
        rsync_args = [
            'rsync',
            '--whole-file',
            # '--dry-run',

            # '--archive',
            '--recursive',
            '--perms',
            '--times',
            "--links",

            # When shell pipe are used, new local file must be preserved
            '--update',

            # '--delete',

            '--blocking-io',  # Need to use docker as transport
            '--rsh', 'docker exec --interactive',

            self.container.id + ':' + self.path + '/',
            self.path,
        ]

        if logging.getLogger().level == logging.DEBUG:
            rsync_args.append('-vv')

        subprocess.check_call(rsync_args)

        logging.info('volume synchronized back')


def main(args):
    logging.basicConfig(
        level=logging.INFO,
        # level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    dm = DockMirror(os.getcwd(), args)
    dm.sync()


if __name__ == '__main__':
    main(sys.argv[1:])
