"""
calamari-reposetup: set up repository for calamari tasks
"""
import contextlib
import logging
from teuthology.calamari_util import \
    install_repokey, install_repo, remove_repo
import teuthology.misc as teuthology

log = logging.getLogger(__name__)

@contextlib.contextmanager
def task(ctx, config):
    """
    calamari-reposetup:
        pkgdir: 
        username:
        password:

    pkgdir encodes package directory (possibly more than one path component)
    as in https://<username>:<password>@SERVER/<pkgdir>/{deb,rpm}{..}

    Sets up calamari repository on all remotes; cleans up when done
    """
    overrides = ctx.config.get('overrides', {})
    # XXX deep_merge returns the result, which matters if either is None
    # make sure that doesn't happen
    if config is None:
        config = {'dummy':'dummy'}
    teuthology.deep_merge(config, overrides.get('calamari-reposetup', {}))

    try:
        pkgdir = config['pkgdir']
        username = config['username']
        password = config['password']
    except KeyError:
        raise RuntimeError('requires pkgdir, username, and password')

    remotes = ctx.cluster.remotes.keys()

    try:
        for rem in remotes:
            log.info(rem)
            install_repokey(rem)
            install_repo(rem, pkgdir, username, password)
        yield

    finally:
        for rem in remotes:
            remove_repo(rem)
