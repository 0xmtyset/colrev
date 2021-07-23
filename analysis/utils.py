#!/usr/bin/env python3
import csv
import hashlib
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from string import ascii_lowercase

import bibtexparser
import entry_hash_function
import pandas as pd
import yaml
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.customization import convert_to_unicode
from git import Repo
from nameparser import HumanName

MAIN_REFERENCES = entry_hash_function.paths['MAIN_REFERENCES']
SCREEN_FILE = entry_hash_function.paths['SCREEN']
DATA = entry_hash_function.paths['DATA']
SCREEN = entry_hash_function.paths['SCREEN']
SEARCH_DETAILS = entry_hash_function.paths['SEARCH_DETAILS']


def retrieve_local_resources():

    if os.path.exists('lexicon/JOURNAL_ABBREVIATIONS.csv'):
        JOURNAL_ABBREVIATIONS = pd.read_csv(
            'lexicon/JOURNAL_ABBREVIATIONS.csv')
    else:
        JOURNAL_ABBREVIATIONS = pd.DataFrame(
            [], columns=['journal', 'abbreviation'])

    if os.path.exists('lexicon/JOURNAL_VARIATIONS.csv'):
        JOURNAL_VARIATIONS = pd.read_csv('lexicon/JOURNAL_VARIATIONS.csv')
    else:
        JOURNAL_VARIATIONS = pd.DataFrame([], columns=['journal', 'variation'])

    if os.path.exists('lexicon/CONFERENCE_ABBREVIATIONS.csv'):
        CONFERENCE_ABBREVIATIONS = \
            pd.read_csv('lexicon/CONFERENCE_ABBREVIATIONS.csv')
    else:
        CONFERENCE_ABBREVIATIONS = pd.DataFrame(
            [], columns=['conference', 'abbreviation'])

    return JOURNAL_ABBREVIATIONS, JOURNAL_VARIATIONS, CONFERENCE_ABBREVIATIONS


def retrieve_crowd_resources():

    JOURNAL_ABBREVIATIONS = pd.DataFrame(
        [], columns=['journal', 'abbreviation'])
    JOURNAL_VARIATIONS = pd.DataFrame([], columns=['journal', 'variation'])
    CONFERENCE_ABBREVIATIONS = pd.DataFrame(
        [], columns=['conference', 'abbreviation'])

    for resource in [x for x in os.listdir() if 'crowd_resource_' == x[:15]]:

        JOURNAL_ABBREVIATIONS_ADD = pd.read_csv(
            resource + '/lexicon/JOURNAL_ABBREVIATIONS.csv')
        JOURNAL_ABBREVIATIONS = pd.concat([JOURNAL_ABBREVIATIONS,
                                           JOURNAL_ABBREVIATIONS_ADD])

        JOURNAL_VARIATIONS_ADD = pd.read_csv(
            resource + '/lexicon/JOURNAL_VARIATIONS.csv')
        JOURNAL_VARIATIONS = pd.concat([JOURNAL_VARIATIONS,
                                        JOURNAL_VARIATIONS_ADD])

        CONFERENCE_ABBREVIATIONS_ADD = pd.read_csv(
            resource + '/lexicon/CONFERENCE_ABBREVIATIONS.csv')
        CONFERENCE_ABBREVIATIONS = pd.concat([CONFERENCE_ABBREVIATIONS,
                                              CONFERENCE_ABBREVIATIONS_ADD])

    return JOURNAL_ABBREVIATIONS, JOURNAL_VARIATIONS, CONFERENCE_ABBREVIATIONS


def hash_function_up_to_date():

    with open('../analysis/entry_hash_function.py') as file:
        hash_of_hash_function = hashlib.sha256(
            file.read().encode('utf-8')).hexdigest()

    pipeline_commit_id = ''
    with open('.pre-commit-config.yaml') as f:
        data_loaded = yaml.safe_load(f)
        for repo in data_loaded['repos']:
            # note: don't check for the full url because the pre-commit
            # hooks could also be linked locally (for development)
            if 'pipeline-validation-hooks' in repo.get('repo'):
                pipeline_commit_id = repo.get('rev')

    with open('../analysis/hash_function_pipeline_commit_id.csv') as read_obj:
        csv_reader = csv.reader(read_obj)
        list_of_rows = list(csv_reader)

    up_to_date = False
    if [hash_of_hash_function, pipeline_commit_id] in list_of_rows:
        up_to_date = True

    if not up_to_date:
        print(hash_of_hash_function + ',' + pipeline_commit_id +
              ' not in analysis/hash_function_pipeline_commit_id.csv')
        raise HashFunctionError

    return up_to_date


def rmdiacritics(char):
    '''
    Return the base character of char, by "removing" any
    diacritics like accents or curls and strokes and the like.
    '''
    desc = unicodedata.name(char)
    cutoff = desc.find(' WITH ')
    if cutoff != -1:
        desc = desc[:cutoff]
        try:
            char = unicodedata.lookup(desc)
        except KeyError:
            pass  # removing "WITH ..." produced an invalid name
    return char


def remove_accents(input_str):
    try:
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        wo_ac = [
            rmdiacritics(c)
            for c in nfkd_form if not unicodedata.combining(c)
        ]
        wo_ac = ''.join(wo_ac)
    except ValueError:
        wo_ac = input_str
        pass
    return wo_ac


class CitationKeyPropagationError(Exception):
    pass


class HashFunctionError(Exception):
    pass


def get_hash_ids(bib_database):

    hash_id_list = []
    for entry in bib_database.entries:
        if 'hash_id' in entry:
            if ',' in entry['hash_id']:
                hash_id_list = hash_id_list + entry['hash_id'].split(',')
            else:
                hash_id_list = hash_id_list + [entry['hash_id']]

    return hash_id_list


def propagated_citation_key(citation_key):

    propagated = False

    if os.path.exists(SCREEN_FILE):
        screen = pd.read_csv(SCREEN_FILE, dtype=str)
        if citation_key in screen['citation_key'].tolist():
            propagated = True

    if os.path.exists(DATA):
        # Note: this may be redundant, but just to be sure:
        data = pd.read_csv(DATA, dtype=str)
        if citation_key in data['citation_key'].tolist():
            propagated = True

    # TODO: also check data_pages?

    return propagated


def generate_citation_key(entry, bib_database=None,
                          entry_in_bib_db=False,
                          raise_error=True):
    if bib_database is not None:
        citation_key_blacklist = [entry['ID']
                                  for entry in bib_database.entries]
    else:
        citation_key_blacklist = None
    return (generate_citation_key_blacklist(entry, citation_key_blacklist,
                                            entry_in_bib_db,
                                            raise_error))


def generate_citation_key_blacklist(entry, citation_key_blacklist=None,
                                    entry_in_bib_db=False,
                                    raise_error=True):

    # Make sure that citation_keys that have been propagated to the
    # screen or data will not be replaced
    # (this would break the chain of evidence)
    if propagated_citation_key(entry['ID']) and raise_error:
        raise CitationKeyPropagationError(
            'WARNING: do not change citation_keys that have been ',
            'propagated to ' + SCREEN + ' and/or ' + DATA + ' (' +
            entry['ID'] + ')',
        )

    if 'author' in entry:
        author = format_author_field(entry['author'])
    else:
        author = ''

    temp_flag = ''
    # if 'needs_manual_cleansing' in entry.get('status',''):
    #     temp_flag = '_temp_'
    if ',' in author:
        temp_citation_key = author\
            .split(',')[0].replace(' ', '') +\
            str(entry.get('year', '')) +\
            temp_flag
    else:
        temp_citation_key = author\
            .split(' ')[0] +\
            str(entry.get('year', '')) +\
            temp_flag

    if temp_citation_key.isupper():
        temp_citation_key = temp_citation_key.capitalize()
    # Replace special characters
    # (because citation_keys may be used as file names)
    temp_citation_key = remove_accents(temp_citation_key)
    temp_citation_key = re.sub(r'\(.*\)', '', temp_citation_key)
    temp_citation_key = re.sub('[^0-9a-zA-Z]+', '', temp_citation_key)

    if citation_key_blacklist is not None:
        if entry_in_bib_db:
            # allow IDs to remain the same.
            other_ids = citation_key_blacklist
            # Note: only remove it once. It needs to change when there are
            # other entries with the same ID
            if entry['ID'] in other_ids:
                other_ids.remove(entry['ID'])
        else:
            # ID can remain the same, but it has to change
            # if it is already in bib_database
            other_ids = citation_key_blacklist

        letters = iter(ascii_lowercase)
        while temp_citation_key in other_ids:
            try:

                next_letter = next(letters)
                if next_letter == 'a':
                    temp_citation_key = temp_citation_key + next_letter
                else:
                    temp_citation_key = temp_citation_key[:-1] + next_letter
            except StopIteration:
                letters = iter(ascii_lowercase)
                pass

    return temp_citation_key


def mostly_upper_case(input_string):
    # also in entry_hash_function.py - consider updating it separately
    if not re.match(r'[a-zA-Z]+', input_string):
        return input_string
    input_string = input_string.replace('.', '').replace(',', '')
    words = input_string.split()
    return sum(word.isupper() for word in words)/len(words) > 0.8


def title_if_mostly_upper_case(input_string):
    if not re.match(r'[a-zA-Z]+', input_string):
        return input_string
    words = input_string.split()
    if sum(word.isupper() for word in words)/len(words) > 0.8:
        return input_string.capitalize()
    else:
        return input_string


def format_author_field(input_string):
    # also in entry_hash_function.py - consider updating it separately

    names = input_string.split(' and ')
    author_string = ''
    for name in names:
        # Note: https://github.com/derek73/python-nameparser
        # is very effective (maybe not perfect)

        parsed_name = HumanName(name)
        if mostly_upper_case(input_string
                             .replace(' and ', '')
                             .replace('Jr', '')):
            parsed_name.capitalize(force=True)

        parsed_name.string_format = \
            '{last} {suffix}, {first} ({nickname}) {middle}'
        if author_string == '':
            author_string = str(parsed_name).replace(' , ', ', ')
        else:
            author_string = author_string + ' and ' + \
                str(parsed_name).replace(' , ', ', ')

    return author_string


def unify_pages_field(input_string):
    # also in entry_hash_function.py - consider updating it separately
    if not isinstance(input_string, str):
        return input_string
    if not re.match(r'^\d*--\d*$', input_string) and '--' not in input_string:
        input_string = input_string\
            .replace('-', '--')\
            .replace('–', '--')\
            .replace('----', '--')\
            .replace(' -- ', '--')\
            .rstrip('.')

    if not re.match(r'^\d*$', input_string) and \
       not re.match(r'^\d*--\d*$', input_string) and\
       not re.match(r'^[xivXIV]*--[xivXIV]*$', input_string):
        print('Unusual pages: ' + input_string)
    return input_string


def validate_search_details():

    search_details = pd.read_csv(SEARCH_DETAILS)

    # check columns
    predef_colnames = {
        'filename',
        'number_records',
        'iteration',
        'date_start',
        'date_completion',
        'source_url',
        'search_parameters',
        'responsible',
        'comment',
    }
    if not set(search_details.columns) == predef_colnames:
        print(
            'Problem: columns in search/search_details.csv ',
            'not matching predefined colnames',
        )
        print(set(search_details.columns))
        print('Should be')
        print(predef_colnames)
        print('')
        sys.exit()

    # TODO: filenames should exist, all files should have
    # a row, iteration, number_records should be int, start

    return


def validate_bib_file(filename):

    # Do not load/warn when bib-file contains the field "Early Access Date"
    # https://github.com/sciunto-org/python-bibtexparser/issues/230

    with open(filename) as bibfile:
        if 'Early Access Date' in bibfile.read():
            print(
                'Error while loading the file: ',
                'replace Early Access Date in bibfile before loading!',
            )
            return False

    # check number_records matching search_details.csv
    if os.path.exists(SEARCH_DETAILS):
        search_details = pd.read_csv(SEARCH_DETAILS)
        try:
            records_expected = search_details.loc[
                search_details['filename'] == Path(
                    filename,
                ).name
            ].number_records.item()
            with open(filename) as bibtex_file:
                bib_database = bibtexparser.bparser.BibTexParser(
                    customization=convert_to_unicode, common_strings=True,
                ).parse_file(bibtex_file, partial=True)

            if len(bib_database.entries) != records_expected:
                print(
                    'Error while loading the file: number of records ',
                    'imported not identical to ',
                    'search/search_details.csv$number_records',
                )
                print('Loaded: ' + str(len(bib_database.entries)))
                print('Expected: ' + str(records_expected))
                return False
        except ValueError:
            # print(
            #     'WARNING: no details on ',
            #     os.path.basename(filename),
            #     ' provided in ' + SEARCH_DETAILS,
            # )
            pass
    return True


def load_references_bib(modification_check=True, initialize=False):

    if os.path.exists(os.path.join(os.getcwd(), MAIN_REFERENCES)):
        if modification_check:
            git_modification_check(MAIN_REFERENCES)
        with open(MAIN_REFERENCES) as target_db:
            references_bib = bibtexparser.bparser.BibTexParser(
                customization=convert_to_unicode, common_strings=True,
            ).parse_file(target_db, partial=True)
    else:
        if initialize:
            references_bib = BibDatabase()
        else:
            print(MAIN_REFERENCES + ' does not exist')
            sys.exit()

    return references_bib


def git_modification_check(filename):

    repo = Repo()
    # hcommit = repo.head.commit
    # if MAIN_REFERENCES in [entry.a_path for entry in hcommit.diff(None)]:
    # print('commit changes in MAIN_REFERENCES before executing script?')
    index = repo.index
    if filename in [entry.a_path for entry in index.diff(None)]:
        print(
            'WARNING: There are changes in ',
            filename,
            ' that are not yet added to the git index. ',
            'They may be overwritten by this script. ',
            'Please consider to MANUALLY add the ' +
            filename,
            ' to the index before executing script.',
        )
        if 'y' != input('override changes (y/n)?'):
            sys.exit()

    return


def get_bib_files():
    bib_files = []

    for (dirpath, dirnames, filenames) in \
            os.walk(os.path.join(os.getcwd(), 'search/')):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)\
                .replace('/opt/workdir/', '')
            if file_path.endswith('.bib'):
                if not validate_bib_file(file_path):
                    continue
                bib_files = bib_files + [file_path]
    return bib_files


def save_bib_file(bib_database, target_file):

    writer = BibTexWriter()

    writer.contents = ['entries', 'comments']
    writer.indent = '  '
    writer.display_order = [
        'author',
        'booktitle',
        'journal',
        'title',
        'year',
        'editor',
        'number',
        'pages',
        'series',
        'volume',
        'abstract',
        'book-author',
        'book-group-author',
        'doi',
        'file',
        'hash_id',
    ]

    try:
        bib_database.comments.remove('% Encoding: UTF-8')
    except ValueError:
        pass

    writer.order_entries_by = ('ID', 'author', 'year')
    writer.add_trailing_comma = True
    writer.align_values = True
    bibtex_str = bibtexparser.dumps(bib_database, writer)

    with open('temp.bib', 'w') as out:
        out.write('% Encoding: UTF-8\n\n')
        out.write(bibtex_str + '\n')

    # to
    time_to_wait = 10
    time_counter = 0
    while not os.path.exists('temp.bib'):
        time.sleep(0.1)
        time_counter += 0.1
        if time_counter > time_to_wait:
            break

    if os.path.exists(MAIN_REFERENCES):
        os.remove(MAIN_REFERENCES)
    os.rename('temp.bib', MAIN_REFERENCES)

    return


def get_included_papers():

    assert os.path.exists(MAIN_REFERENCES)
    assert os.path.exists(SCREEN_FILE)

    pdfs = []

    screen = pd.read_csv(SCREEN_FILE, dtype=str)

    screen = screen.drop(screen[screen['inclusion_2'] != 'yes'].index)

    for record_id in screen['citation_key'].tolist():

        with open(MAIN_REFERENCES) as bib_file:
            bib_database = bibtexparser.bparser.BibTexParser(
                customization=convert_to_unicode, common_strings=True,
            ).parse_file(bib_file, partial=True)

            for entry in bib_database.entries:
                if entry.get('ID', '') == record_id:
                    if 'file' in entry:
                        filename = entry['file'].replace('.pdf:PDF', '.pdf')\
                                                .replace(':', '')
                        pdf_path = os.path.join(os.getcwd(), filename)
                        if os.path.exists(pdf_path):
                            pdfs.append(entry['ID'])
                        else:
                            print(
                                '- Error: file not available ',
                                entry['file'],
                                ' (',
                                entry['ID'],
                                ')',
                            )

    return pdfs
