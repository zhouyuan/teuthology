"""
Calamari Rest-API
"""
from cStringIO import StringIO
import contextlib
import logging
from teuthology.calamari_util import install_package, remove_package
import teuthology.misc as teuthology

log = logging.getLogger(__name__)

@contextlib.contextmanager
def task(ctx, config):
    """
    Calamari Rest API

    For example::

        tasks:
        - calamari-restapi:
          roles: mon.0
          pkgdir: packages-staging/master
    """
    overrides = ctx.config.get('overrides', {})
    teuthology.deep_merge(config, overrides.get('calamari-restapi', {}))

    try:
        pkgdir = config['pkgdir']
        username = config['username']
        password = config['password']
    except KeyError:
        raise RuntimeError('requires pkgdir, username, and password')

    remotes = teuthology.roles_to_remotes(ctx.cluster, config)

    try:
        for rem in remotes:
            log.info(rem)
            lsb_out = StringIO()
            release = rem.run(args=['lsb_release', '-cs'], stdout=lsb_out)
            release = lsb_out.getvalue().rstrip()
            install_package('calamari-restapi', rem, release, pkgdir,
                            username, password)
        yield

    finally:
        for rem in remotes:
            remove_package('calamari-restapi', rem, release)
