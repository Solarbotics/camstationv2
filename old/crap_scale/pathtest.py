import configparser
import os
class ConfigManager(object):
    """docstring for ConfigManager."""
    def __init__(self):
        super(ConfigManager, self).__init__()
        self.path = os.path.join(
            os.environ['HOME'],
            'bin/config'
        )

    def get_config(self):
        parser = configparser.ConfigParser()
        print(os.path.join(self.path, '../camstation.cfg'))
        parser.read(
            os.path.join(self.path, '../camstation.cfg')
        )
        for section_name in parser.sections():
            print('Section:', section_name)
            print('  Options:', parser.options(section_name))
            for name, value in parser.items(section_name):
                print('  %s = %s' % (name, value))
            print()

        config_path = os.path.join(
            self.path,
            parser.get('Profiles', 'ActiveProfile'),
            'Configuration.ini'
        )
config_profile = ConfigManager.read(config_path)
print("Output",config_profile)