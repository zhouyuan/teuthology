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

    remotes = teuthology.roles_to_remotes(ctx.cluster, config)

    try:
        for rem in remotes:
            log.info(rem)
            install_package('calamari-restapi', rem)
        yield

    finally:
        for rem in remotes:
            remove_package('calamari-restapi', rem)
