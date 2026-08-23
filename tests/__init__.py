import tempfile
from pathlib import Path

from replio.config import Config

_GLOBAL_TEST_HOME = tempfile.mkdtemp(prefix='replio-test-global-')
Config.GLOBAL_DIR = Path(_GLOBAL_TEST_HOME)