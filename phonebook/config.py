from configparser import ConfigParser
import os


default_filename = os.path.abspath('database.ini')


def load_config(filename=default_filename, section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)

    if parser.has_section:
        params = parser.items(section)
        config = {}
        for key, value in params:
            config[key] = value

    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return config


if __name__ == '__main__':
    print(default_filename)
    config = load_config()
