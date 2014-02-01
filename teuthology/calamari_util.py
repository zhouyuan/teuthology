"""
Calamari package repo utilities
"""
from cStringIO import StringIO
import logging
import textwrap
from .orchestra import run
import misc

log = logging.getLogger(__name__)

# TO DO: These are defaults.  We should parameterize fields in the yaml.
RELEASE_MAP = {
    'precise': dict(flavor='deb', release='ubuntu', distro='12.04'),
    'wheezy': dict(flavor='deb', release='debian', distro='7.0'),
    'centos': dict(flavor='rpm', release='centos', distro='6.4'),
    'rhel': dict(flavor='rpm', release='rhel', distro='6.4'),
}

def sqlite_package_name(release):
    flavor = RELEASE_MAP[release]['flavor']
    name = 'sqlite' if flavor == 'rpm' else 'sqlite3'
    return name

def http_service_name(release):
    flavor = RELEASE_MAP[release]['flavor']
    name = 'httpd' if flavor == 'rpm' else 'apache2'
    return name

def install_repo(remote, release, pkgdir, username, password):
    # installing repo is assumed to be idempotent

    log.info('Installing repo on %s', remote)
    flavor = RELEASE_MAP[release]['flavor']
    if flavor == 'deb':
        contents = 'deb https://{username}:{password}@download.inktank.com/' \
                   '{pkgdir}/deb {release} main'
        contents = contents.format(username=username,
                                   password=password,
                                   pkgdir=pkgdir,
                                   release=release,
                                  )
        misc.sudo_write_file(remote,
                             '/etc/apt/sources.list.d/inktank.list',
                             contents)
        remote.run(args=['sudo',
                         'apt-get',
                         'install',
                         'apt-transport-https',
                         '-y'])
        result = remote.run(args=['sudo', 'apt-get', 'update',
                '-y'], stdout=StringIO())
        return True

    elif flavor == 'rpm':
        baseurl='https://{username}:{password}@download.inktank.com/{pkgdir}' \
                '/rpm/{distro}{version}'
        contents = textwrap.dedent('''
            [inktank]
            name=Inktank Storage, Inc.
            baseurl={baseurl}
            gpgcheck=1
            enabled=1
            '''.format(baseurl=baseurl))
        contents = contents.format(username='dmick',
                                   password='dmick',
                                   pkgdir=pkgdir,
                                   distro=release,
                                   version=branch,
                                   branch=release)
        misc.sudo_write_file(remote,
                             '/etc/yum.repos.d/inktank.repo',
                             contents)
        return remote.run(args=['sudo', 'yum', 'makecache'])

    else:
        return False

def remove_repo(remote, release):
    log.info('Removing repo on %s', remote)
    flavor = RELEASE_MAP[release]['flavor']
    if flavor == 'deb':
        misc.delete_file(remote, '/etc/apt/sources.list.d/inktank.list',
                         sudo=True, force=True)
        result = remote.run(args=['sudo', 'apt-get', 'update',
                '-y'], stdout=StringIO())
        return True

    elif flavor == 'rpm':
        misc.delete_file(remote, '/etc/yum.repos.d/inktank.repo',
                         sudo=True, force=True)
        return remote.run(args=['sudo', 'yum', 'makecache'])

    else:
        return False

def install_repokey(remote, release):
    # installing keys is assumed to be idempotent
    log.info('Installing repo key on %s', remote)
    flavor = RELEASE_MAP[release]['flavor']
    if flavor == 'deb':
        return remote.run(args=['wget',
                                '-q',
                                '-O-',
                                'http://download.inktank.com/keys/release.asc',
                                run.Raw('|'),
                                'sudo',
                                'apt-key',
                                'add',
                                '-'])
    elif flavor == 'rpm':
        return remote.run(args=['sudo',
                                'rpm',
                                '--import',
                                'http://download.inktank.com/keys/release.asc'])
    else:
        return False

def install_package(package, remote, release):
    """
    package: name
    remote: Remote() to install on
    release: deb only, 'precise' or 'wheezy'
    pkgdir: may or may not include a branch name, so, say, either
            packages or packages-staging/master
    """
    log.info('Installing package %s on %s', package, remote)
    flavor = RELEASE_MAP[release]['flavor']
    if flavor == 'deb':
        pkgcmd = ['DEBIAN_FRONTEND=noninteractive',
                  'sudo',
                  '-E',
                  'apt-get',
                  '-y',
                  'install',
                  '{package}'.format(package=package)]
    elif flavor == 'rpm':
        pkgcmd = ['sudo',
                  'yum',
                  '-y',
                  'install',
                  '{package}'.format(package=package)]
    else:
        log.error('install_package: bad flavor ' + flavor + '\n')
        return False
    return remote.run(args=pkgcmd)

def remove_package(package, remote, release):
    flavor = RELEASE_MAP[release]['flavor']
    if flavor == 'deb':
        pkgcmd = ['DEBIAN_FRONTEND=noninteractive',
                  'sudo',
                  '-E',
                  'apt-get',
                  '-y',
                  'purge',
                  '{package}'.format(package=package)]
    elif flavor == 'rpm':
        pkgcmd = ['sudo',
                  'yum',
                  '-y',
                  'erase',
                  '{package}'.format(package=package)]
    else:
        log.error('remove_package: bad flavor ' + flavor + '\n')
        return False
    return remote.run(args=pkgcmd)
