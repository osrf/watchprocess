#!/usr/bin/env python

import os
import subprocess

def test_explicit_execution():
    try:
        output =subprocess.check_output(['./symlinks/gcc', '--help'])
        assert "Watchprocess" in output, "Did not catch Watchprocess indirection."
        assert "Usage: gcc [options] file..." in output, "gcc did not generate usage"
        return True
    except:
        #failure
        return False


def test_path_extension_execution():
    new_env = os.environ.copy()
    new_env["PATH"] = ':'.join([os.path.abspath('./symlinks'), new_env['PATH']])
    try:
        output =subprocess.check_output(['gcc', '--help'], env=new_env)
        assert "Watchprocess" in output, "Did not catch Watchprocess indirection."
        assert "Usage: gcc [options] file..." in output, "gcc did not generate usage"
        return True
    except:
        #failure
        return False
