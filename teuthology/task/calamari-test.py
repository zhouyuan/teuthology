"""
Run the calamari smoketest
"""
import os
import subprocess
def task(ctx, config):
    """
    Tests to run are in calamari_testdir.
 
        tasks:
        - calamari-test:
            server: server.0
    """
    testhost = ctx.cluster.only(config['server']).remotes.keys()[0].name
    testhost = testhost.split('@')[1]
    mypath = os.path.dirname(__file__)
    cmd_list = [os.path.join(mypath, 'calamari_testdir',
                             'test_calamari_server.py')]
    os.environ['CALAMARI_BASE_URI'] = 'http://{0}/api/v1/'.format(testhost)
    return subprocess.call(cmd_list)
