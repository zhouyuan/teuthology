"""
Run the calamari smoketest
"""
import logging
import os
import subprocess
import time

log = logging.getLogger(__name__)

def task(ctx, config):
    """
    Tests to run are in calamari_testdir.
    delay: wait this long before starting
 
        tasks:
        - calamari-test:
            delay: 30
            server: server.0
    """
    delay = config.get('delay', 0)
    if delay:
        log.info("delaying %d sec", delay)
        time.sleep(delay)
    testhost = ctx.cluster.only(config['server']).remotes.keys()[0].name
    testhost = testhost.split('@')[1]
    mypath = os.path.dirname(__file__)
    cmd_list = [os.path.join(mypath, 'calamari_testdir',
                             'test_calamari_server.py')]
    os.environ['CALAMARI_BASE_URI'] = 'http://{0}/api/v1/'.format(testhost)
    log.info("testing %s", testhost)
    return subprocess.call(cmd_list)
