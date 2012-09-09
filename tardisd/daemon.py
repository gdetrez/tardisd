from .backup import BackupChain
import ConfigParser
from IPython import embed
DEFAULT_CONFIG_FILE="tardisrc"




class TardisDaemon:

    def __init__(self, config_file=DEFAULT_CONFIG_FILE):
        self.config_file = config_file

        

    def read_config(self):
        config = ConfigParser.SafeConfigParser()
        config.read(DEFAULT_CONFIG_FILE)
        self.chains = {}
        for section in config.sections():
            source = config.get(s, "source")
            destination = config.get(s, "destination")
            if config.has_option(c, "exclude"):
                exclude = config.get(s,"eclude")
                exclude = [s.strip() for s in exclude]
            else:
                exclude = []
            self.chains[s] = BackupChain(s, source, destination, exclude)

