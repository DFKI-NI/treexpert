import os
from .base import *

# you need to set "treexpert = 'docker'" as an environment variable
# in your OS (on which your website is hosted with docker)
if os.environ.get("TREEXPERT") == "docker":
    from .docker import *
else:
    from .local import *
