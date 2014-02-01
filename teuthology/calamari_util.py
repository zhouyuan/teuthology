"""
Calamari package repo utilities
"""
from cStringIO import StringIO
import logging
import textwrap
from .orchestra import run
import misc

log = logging.getLogger(__name__)

RELEASE_MAP = {
    'Ubuntu precise': dict(flavor='deb', release='ubuntu', version='precise'),
    'Debian wheezy': dict(flavor='deb', release='debian', version='wheezy'),
    'CentOS 6.4': dict(flavor='rpm', release='centos', version='6.4'),
    'RedHatEnterpriseServer 6.4': dict(flavor='rpm', release='rhel', version='6.4'),
}

def get_relmap(rem):
    relmap = getattr(rem, 'relmap', None)
    if relmap is not None:
        return relmap
    lsb_release_out = StringIO()
    rem.run(args=['lsb_release', '-ics'], stdout=lsb_release_out)
    release = lsb_release_out.getvalue().replace('\n', ' ').rstrip()
    if release in RELEASE_MAP:
        rem.relmap = RELEASE_MAP[release]
        return rem.relmap
    else:
        lsb_release_out = StringIO()
        rem.run(args=['lsb_release', '-irs'], stdout=lsb_release_out)
        release = lsb_release_out.getvalue().replace('\n', ' ').rstrip()
        if release in RELEASE_MAP:
            rem.relmap = RELEASE_MAP[release]
            return rem.relmap
    raise RuntimeError('Can\'t get release info for {}'.format(rem))

def sqlite_package_name(rem):
    name = 'sqlite' if get_relmap(rem)['flavor'] == 'rpm' else 'sqlite3'
    return name

def http_service_name(rem):
    name = 'httpd' if get_relmap(rem)['flavor'] == 'rpm' else 'apache2'
    return name

def install_repo(remote, pkgdir, username, password):
    # installing repo is assumed to be idempotent

    relmap = get_relmap(remote)
    log.info('Installing repo on %s', remote)
    if relmap['flavor'] == 'deb':
        contents = 'deb https://{username}:{password}@download.inktank.com/' \
                   '{pkgdir}/deb {codename} main'
        contents = contents.format(username=username,
                                   password=password,
                                   pkgdir=pkgdir,
                                   codename=relmap['version'],
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

    elif relmap['flavor'] == 'rpm':
        baseurl='https://{username}:{password}@download.inktank.com/{pkgdir}' \
                '/rpm/{release}{version}'
        contents = textwrap.dedent('''
            [inktank]
            name=Inktank Storage, Inc.
            baseurl={baseurl}
            gpgcheck=1
            enabled=1
            '''.format(baseurl=baseurl))
        contents = contents.format(username=username,
                                   password=password,
                                   pkgdir=pkgdir,
                                   release=relmap['release'],
                                   version=relmap['version'])
        misc.sudo_write_file(remote,
                             '/etc/yum.repos.d/inktank.repo',
                             contents)
        return remote.run(args=['sudo', 'yum', 'makecache'])

    else:
        return False

def remove_repo(remote):
    log.info('Removing repo on %s', remote)
    flavor = get_relmap(remote)['flavor']
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

def install_repokey(remote):
    # installing keys is assumed to be idempotent
    log.info('Installing repo key on %s', remote)
    flavor = get_relmap(remote)['flavor']
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

def install_package(package, remote):
    """
    package: name
    remote: Remote() to install on
    release: deb only, 'precise' or 'wheezy'
    pkgdir: may or may not include a branch name, so, say, either
            packages or packages-staging/master
    """
    log.info('Installing package %s on %s', package, remote)
    flavor = get_relmap(remote)['flavor']
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

def remove_package(package, remote):
    flavor = get_relmap(remote)['flavor']
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
