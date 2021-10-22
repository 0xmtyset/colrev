#! /usr/bin/env python
import os
import pprint

import git

from review_template import prepare
from review_template import repo_setup
from review_template import utils


entry_type_mapping = {'a': 'article', 'p': 'inproceedings',
                      'b': 'book', 'ib': 'inbook', 'pt': 'phdthesis',
                      'mt': 'masterthesis',
                      'o': 'other', 'unp': 'unpublished'}

citation_key_list = []


def print_entry(entry):
    pp = pprint.PrettyPrinter(indent=4, width=140)
    # Escape sequence to clear terminal output for each new comparison
    os.system('cls' if os.name == 'nt' else 'clear')
    pp.pprint(entry)
    if 'title' in entry:
        print('https://scholar.google.de/scholar?hl=de&as_sdt=0%2C5&q=' +
              entry['title'].replace(' ', '+'))
    return


def correct_entrytype(entry):

    if 'n' == input('ENTRYTYPE=' + entry['ENTRYTYPE'] + ' correct?'):
        choice = input('Correct type: ' +
                       'a (article), p (inproceedings), ' +
                       'b (book), ib (inbook), ' +
                       'pt (phdthesis), mt (masterthesis), '
                       'unp (unpublished), o (other), ')
        assert choice in entry_type_mapping.keys()
        correct_entry_type = [value for (key, value)
                              in entry_type_mapping.items()
                              if key == choice]
        entry['ENTRYTYPE'] = correct_entry_type[0]
    return entry


def man_completion(entry):
    if prepare.is_complete(entry):
        return entry

    reqs = prepare.entry_field_requirements[entry['ENTRYTYPE']]
    for field in reqs:
        if field not in entry:
            value = input('Please provide the ' + field + ' (or NA)')
            entry[field] = value
    return entry


def man_fix_inconsistencies(entry):
    if not prepare.has_inconsistent_fields(entry):
        return entry

    print('TODO: ask whether the inconsistent fields can be dropped?')

    return entry


def man_fix_incomplete_fields(entry):
    if not prepare.has_incomplete_fields(entry):
        return entry

    print('TODO: ask for completion of fields')
    # organize has_incomplete_fields() values in a dict?

    return entry


def man_prep_entry(entry):

    global citation_key_list

    if 'needs_manual_preparation' != entry['status']:
        return entry

    print_entry(entry)

    correct_entrytype(entry)

    man_completion(entry)

    man_fix_inconsistencies(entry)

    man_fix_incomplete_fields(entry)

    # Note: for complete_based_on_doi field:
    entry = prepare.retrieve_doi_metadata(entry)

    if (prepare.is_complete(entry) or prepare.is_doi_complete(entry)) and \
            not prepare.has_inconsistent_fields(entry) and \
            not prepare.has_incomplete_fields(entry):
        entry = prepare.drop_fields(entry)
        entry.update(ID=utils.generate_citation_key_blacklist(
            entry, citation_key_list,
            entry_in_bib_db=True,
            raise_error=False))
        citation_key_list.append(entry['ID'])
        entry.update(status='prepared')

    return entry


def man_prep_entries():
    global citation_key_list

    repo = git.Repo('')
    utils.require_clean_repo(repo)

    print('Loading records for manual preparation...')
    bib_database = utils.load_references_bib(
        modification_check=True, initialize=False,
    )

    citation_key_list = [entry['ID'] for entry in bib_database.entries]

    for entry in bib_database.entries:
        entry = man_prep_entry(entry)
        utils.save_bib_file(bib_database)

    create_commit(repo, bib_database)
    return


def create_commit(repo, bib_database):

    MAIN_REFERENCES = repo_setup.paths['MAIN_REFERENCES']
    utils.save_bib_file(bib_database, MAIN_REFERENCES)

    if MAIN_REFERENCES in [item.a_path for item in repo.index.diff(None)] or \
            MAIN_REFERENCES in repo.untracked_files:

        repo.index.add([MAIN_REFERENCES])

        hook_skipping = 'false'
        if not repo_setup.config['DEBUG_MODE']:
            hook_skipping = 'true'
        repo.index.commit(
            'Prepare records for import' +
            '\n - ' + utils.get_package_details() +
            '\n' + utils.get_status_report(),
            author=git.Actor('manual (using man_prep.py)', ''),
            committer=git.Actor(repo_setup.config['GIT_ACTOR'],
                                repo_setup.config['EMAIL']),
            skip_hooks=hook_skipping
        )

    return


def main():
    print('TODO: include processing_reports')
    man_prep_entries()
    return


if __name__ == '__main__':
    main()
