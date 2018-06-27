# This is where algorithms that are prototyped in exploatory notebooks
# are implemented

# imports
import pandas as pd
import os
import pathlib
import mwapi
import mwparserfromhell
import glob
import pickle
import dateutil
import re
import csv
import json


# Version history collection

def collect_consoidate_historical_edits(directory, wiki_title, agent_email,
                                        earliest_date=None):
    """collects and consolidates all historical edits of a wikipedia page in
    the specified directory.

    Args:
        directory (str): Path to directory.
        wiki_title (st): Title of wikipedia article to search.
        agent_email (str): Email sever messages will be sent to.
        host (str, optional): Wiki to interact with.
        earliest_date (str, optional): Earliest day to scrub to 'YYYYMMDD' format


    """
    # process datetime information
    if earliest_date is not None:
        earliest_date = dateutil.parser.DEFAULTPARSER.parse(earliest_date)

    # Process directory information
    directory = pathlib.Path(directory)
    wiklink_directory = directory / 'wikilinks'
    revision_directory = directory / 'revisions'

    directory.mkdir(parents=True, exist_ok=True)
    wiklink_directory.mkdir(parents=True, exist_ok=True)
    revision_directory.mkdir(parents=True, exist_ok=True)

    # Consult the database file TODO
    # This csv will have all pages with timestamps of when they were updated

    headings = ['page_title', 'revid', 'parentid', 'user', 'userid',
                'timestamp', 'comment',
                'character_count', 'word_count', 'external_link_count',
                'heading_count', 'wikifile_count', 'wikilink_count']
    # Check the revision history file
    revision_path = revision_directory / (wiki_title + '.csv')
    if not revision_path.is_file():
        with open(revision_path, encoding='UTF-16',
                  mode='w', newline='') as file:
            csvwriter = csv.writer(file)
            csvwriter.writerow(headings)

    # Check the wikilinks file
    if (wiklink_directory / (wiki_title + '.json')).is_file():
        with open(wiklink_directory / (wiki_title + '.json'), 'r') as tounpick:
            wikilink_dict = json.load(tounpick)
    else:
        wikilink_dict = dict()

    # # populate the directory with many csv files
    wikilink_dict = update_revisions_and_links(wiki_title, agent_email,
                                               revision_path,
                                               wikilink_dict, earliest_date,
                                               latest_date='NOW')

    # Dump pickle file
    with open(wiklink_directory / (wiki_title + '.json'), 'w') as topick:
        json.dump(wikilink_dict, topick)


def append_row(csv_file_path, row):
    """This function was written to deal with having files left open"""
    with open(csv_file_path, encoding='UTF-16', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(row)


def update_revisions_and_links(wiki_title, agent_email, revision_csv_path,
                               wikilink_dict, earliest_date, latest_date='NOW',
                               host='https://en.wikipedia.org'):
    """"""
    session = mwapi.Session(host, user_agent=agent_email)

    quit_this_function = False
    # Query every revision of the page
    for rev_count, revision_set in enumerate(session.get(continuation=True,
                                             action='query', titles=wiki_title,
                                             prop='revisions',
                                             rvprop='ids|flags|timestamp|comment|user|userid|content',
                                             rvlimit='max')):

        # Iterate over revision
        for count, revision in enumerate(next(iter(revision_set['query']['pages'].values()))['revisions']):

            # Extract edit information
            try:
                [revid, parent_id,
                 contrib_username, contrib_id,
                 timestamp, comment] = revision_information(revision)
            except:
                # This is a sloppy except call to deal with anamolus edits
                print('this was an anomolus edit')
                print(revision)
                break

            # Extract information on the website itself
            try:
                parsed = mwparserfromhell.parse(revision['*'])
            except:
                break

            if earliest_date is not None:
                if earliest_date > dateutil.parser.DEFAULTPARSER.parse(timestamp).replace(tzinfo=None):
                    # If the timestamp is before the earliest date stop digging
                    quit_this_function = True
                    break

            [character_count, word_count,
             external_link_count, heading_count,
             wikilink_count, wikifile_count,
             wikilink_dict] = parsed_article_metrics(parsed, revid,
                                                     wikilink_dict)


            append_row(revision_csv_path,
                       [wiki_title, revid, parent_id,
                        contrib_username, contrib_id,
                        timestamp, comment, character_count,
                        word_count,
                        external_link_count, heading_count,
                        wikilink_count, wikifile_count])
            # print([wiki_title, revid, parent_id,
            #        contrib_username, contrib_id,
            #        timestamp, comment, character_count,
            #        word_count,
            #        external_link_count, heading_count,
            #        wikilink_count, wikifile_count])

        if quit_this_function:
            return wikilink_dict

    return wikilink_dict


def revision_information(revision_json):

    try:
        parent_id = revision_json['parentid']
    except AttributeError:
        # No parent was assigned
        parent_id = None

    # Contributor
    try:
        contrib_username = revision_json['user']
    except AttributeError:
        contrib_username = None

    try:
        contrib_id = revision_json['userid']
    except AttributeError:
        contrib_id = None

    try:
        comment = revision_json['comment']
    except AttributeError:
        comment = None

    return [revision_json['revid'], parent_id,
            contrib_username, contrib_id,
            revision_json['timestamp'], comment]


def process_wikilinks(parsed, revid, wikilink_dictionary):

    wikifiles = 0
    wikilinks = 0

    for link in set([str(link.title) for link in parsed.filter_wikilinks()]):

        # Build the dictionary
        try:
            wikilink_dictionary[link].append(revid)
        except KeyError:
            wikilink_dictionary[link] = [revid]

        if link.startswith('File:'):
            wikifiles += 1
        else:
            wikilinks += 1

    return wikilinks, wikifiles, wikilink_dictionary


def parsed_article_metrics(parsed_article, revid, wikilink_dict):
    """This should take a parsed article and pull out metrics of interest.
    Args:
        parsed_article (parsed): Parsed wikipedia site (mwparserfromhell)

    Returns:
        TYPE: list
    """
    character_count = len(parsed_article.strip_code())
    # This is not an efficent word count
    word_count = len(re.findall("[a-zA-Z_]+", parsed_article.strip_code()))
    external_link_count = len(parsed_article.filter_external_links())
    heading_count = len(parsed_article.filter_headings())
    [wikilink_count, wikifile_count,
     wikilink_dict] = process_wikilinks(parsed_article, revid, wikilink_dict)

    return [character_count, word_count, external_link_count, heading_count,
            wikilink_count, wikifile_count, wikilink_dict]
