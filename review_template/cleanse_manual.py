#! /usr/bin/env python
import pprint

import git
import yaml

from review_template import entry_hash_function
from review_template import utils

with open('shared_config.yaml') as shared_config_yaml:
    shared_config = yaml.load(shared_config_yaml, Loader=yaml.FullLoader)
HASH_ID_FUNCTION = shared_config['params']['HASH_ID_FUNCTION']
with open('private_config.yaml') as private_config_yaml:
    private_config = yaml.load(private_config_yaml, Loader=yaml.FullLoader)

MAIN_REFERENCES = \
    entry_hash_function.paths[HASH_ID_FUNCTION]['MAIN_REFERENCES']

DEBUG_MODE = (1 == private_config['params']['DEBUG_MODE'])


def manual_cleanse_commit():
    r = git.Repo('')
    r.index.add([MAIN_REFERENCES])

    hook_skipping = 'false'
    if not DEBUG_MODE:
        hook_skipping = 'true'
    r.index.commit(
        'Cleanse manual ' + MAIN_REFERENCES +
        '\n - ' + utils.get_package_details(),
        author=git.Actor('manual:cleanse', ''),
        skip_hooks=hook_skipping
    )
    print('Created commit: Cleanse manual ' + MAIN_REFERENCES)

    return


def main():
    bib_database = utils.load_references_bib(
        modification_check=True, initialize=False,
    )

    print('To implement: cleanse manual')
    pp = pprint.PrettyPrinter(indent=4)
    for entry in [x for x in bib_database.entries
                  if 'needs_manual_completion' == x['status']]:
        # Escape sequence to clear terminal output for each new comparison
        print(chr(27) + '[2J')
        pp.pprint(entry)


if __name__ == '__main__':
    main()
