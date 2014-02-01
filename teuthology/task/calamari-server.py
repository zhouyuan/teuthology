"""
Calamari Server
"""
from cStringIO import StringIO
import logging
import contextlib
from teuthology.calamari_util import \
    install_repokey, install_repo, remove_repo, \
    install_package, remove_package, \
    http_service_name, sqlite_package_name
import textwrap
from ..orchestra import run
from teuthology import misc as teuthology

log = logging.getLogger(__name__)

def disable_default_nginx(remote):
    """
    Fix up nginx values
    """
    script = textwrap.dedent('''
        if [ -f /etc/nginx/conf.d/default.conf ]; then
            mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.disabled
        fi
        if [ -f /etc/nginx/sites-enabled/default ] ; then
            rm /etc/nginx/sites-enabled/default
        fi
        service nginx restart
        service {service} restart
    ''')
    service = http_service_name(remote)
    script = script.format(service=service)
    teuthology.sudo_write_file(remote, '/tmp/disable.nginx', script)
    return remote.run(args=['sudo', 'bash',
            '/tmp/disable.nginx'], stdout=StringIO())

def setup_calamari_cluster(remote, restapi_remote):
    """
    Add restapi db entry to the server.
    """
    restapi_hostname = str(restapi_remote).split('@')[1]
    sqlcmd = 'insert into ceph_cluster (name, api_base_url) ' \
             'values ("{host}", "http://{host}:5000/api/v0.1/");'.format(
              host=restapi_hostname)
    teuthology.write_file(remote, '/tmp/create.cluster.sql', sqlcmd)
    return remote.run(args=['cat',
                            '/tmp/create.cluster.sql',
                            run.Raw('|'),
                            'sudo',
                            'sqlite3',
                            '/opt/calamari/webapp/calamari/db.sqlite3'],
                      stdout=StringIO())

@contextlib.contextmanager
def task(ctx, config):
    """
    Calamari server setup.  "roles" is a list of roles that should run
    the webapp, and "restapi_server" is a list of roles that will
    be running the calamari-restapi package.  Both lists probably should
    have only one entry (only the first is used).

    For example::

        roles: [[server.0], [mon.0], [osd.0, osd.1]]
        tasks:
        - calamari-server:
            roles: [server.0]
            restapi_server: [mon.0]
    """
    overrides = ctx.config.get('overrides', {})
    teuthology.deep_merge(config, overrides.get('calamari-server', {}))
    pkgdir = config.get('pkgdir','packages')
    try:
        username = config['username']
        password = config['password']
    except KeyError:
        raise RuntimeError('calamari-server: must supply username/password')

    remote = teuthology.roles_to_remotes(ctx.cluster, config)[0]
    restapi_remote = teuthology.roles_to_remotes(ctx.cluster, config,
                                                 attrname='restapi_server')[0]
    if not restapi_remote:
        raise RuntimeError('Must supply restapi_server')


    try:
        sqlite_package = sqlite_package_name(remote)
        install_repokey(remote)
        install_repo(remote, pkgdir, username, password)
        if not install_package('calamari-server', remote) or \
            not install_package('calamari-clients', remote) or \
            not install_package(sqlite_package, remote) or \
            not disable_default_nginx(remote) or \
            not setup_calamari_cluster(remote, restapi_remote):
            raise RuntimeError('Server installation failure')

        log.info('client/server setup complete')
        yield
    finally:
        remove_package('calamari-server', remote)
        remove_package('calamari-clients', remote)
        remove_package(sqlite_package, remote)
        remove_repo(remote)
