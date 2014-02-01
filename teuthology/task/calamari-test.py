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
            server.0
    """
    import pdb; pdb.set_trace()
    remote = ctx.cluster.only(config['server']).remotes.keys()[0].name
    remote_site = remote[remote.find('@') + 1 :]
    mypath = __file__.split(os.sep)[:-1]
    mypath = os.sep.join(mypath)
    cmd_list = ['python',
                os.path.join(mypath, 'calamari_testdir',
                            'test_calamari_server.py'),
                '--uri',
                'http://%s' % remote_site]
    return subprocess.call(cmd_list)
    #exec ' '.join(cmd_list)
