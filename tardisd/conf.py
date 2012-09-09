import ConfigParser
from IPython import embed
from optparse import OptionParser
import ConfigParser
import logging
import os, sys

DEFAULT_HOME = os.path.expanduser("~/.tardisd/")
DEFAULT_CONFIG_FILE= os.path.join(DEFAULT_HOME, "tardisrc")
ENVIRONMENT_VARIABLE = "TARDIS_CONFIG_FILE"


class Settings(object):

    HOME = DEFAULT_HOME
    
    
    def __init__(self):        
        """
        Load the settings file pointed to by the environment variable,
        or the default setting file.
        """
        settings_file = ""
        try:
            if not settings_file: # If it's set but is an empty string.
                raise KeyError
        except KeyError:
            settings_file = DEFAULT_CONFIG_FILE

        config = ConfigParser.SafeConfigParser()
        
        print("Reading configuration file %s" % settings_file)
        config.read(settings_file)
        self.BACKUP_CHAINS = {}
        for section in config.sections():
            source = config.get(section, "source")
            destination = config.get(section, "destination")
            if config.has_option(section, "exclude"):
                exclude = config.get(section,"exclude").split()
                exclude = [s.strip(", \n\t") for s in exclude]
            else:
                exclude = []
            self.BACKUP_CHAINS[section] = {
                'source': source,
                'destination': destination,
                'exclude': exclude
                }


settings = Settings()
