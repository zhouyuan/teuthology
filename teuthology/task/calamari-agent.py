"""
Calamari agent (diamond collector package, for each cluster host)
"""
from cStringIO import StringIO
import contextlib
import logging
from teuthology.calamari_util import install_package, remove_package
import teuthology.misc as teuthology

log = logging.getLogger(__name__)

def edit_diamond_config(remote, serverhost):
    """ Edit remote's diamond config to send stats to serverhost """
    ret = remote.run(args=['sudo',
                     'sed',
                     '-i',
                     's/calamari/{host}/'.format(host=serverhost),
                     '/etc/diamond/diamond.conf'],
                     stdout=StringIO())
    if not ret:
        return False
    return remote.run(args=['sudo', 'service', 'diamond', 'restart'])

@contextlib.contextmanager
def task(ctx, config):
    """
    calamari-agent: install stats collection (for each cluster host)

    For example::

        tasks:
        - calamari-agent:
           roles:
               - mon.0
               - osd.0
               - osd.1
           server: calamari-server.0
    """

    log.info('calamari-agent starting')
    overrides = ctx.config.get('overrides', {})
    teuthology.deep_merge(config, overrides.get('calamari-agent', {}))

    remotes = teuthology.roles_to_remotes(ctx.cluster, config)
    try:
        for rem in remotes:
            log.info(rem)
            lsb_release_out = StringIO()
            rem.run(args=['lsb_release', '-cs'], stdout=lsb_release_out)
            release = lsb_release_out.getvalue().rstrip()

            log.info('Installing calamari-agent on %s', rem)
            install_package('calamari-agent', rem)
            server_role = config.get('server')
            if not server_role:
                raise RuntimeError('must supply \'server\' config key')
            server_remote = ctx.cluster.only(server_role).remotes.keys()[0]
            # why isn't shortname available by default?
            serverhost = server_remote.name.split('@')[1]
            log.info('configuring Diamond for {}'.format(serverhost))
            if not edit_diamond_config(rem, serverhost):
                raise RuntimeError(
                    'Diamond config edit failed on {0}'.format(remote)
                )
        yield
    finally:
            for rem in remotes:
                remove_package('calamari-agent', rem)
