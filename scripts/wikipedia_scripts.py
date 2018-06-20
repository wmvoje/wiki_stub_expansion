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

# Version history collection


def collect_consoidate_historical_edits(directory, wiki_title, agent_email,
                                        host='https://en.wikipedia.org'):
    """collects and consolidates all historical edits of a wikipedia page in
    the specified directory.

    Args:
        directory (str): Path to directory.
        wiki_title (st): Title of wikipedia article to search.
        agent_email (str): Email sever messages will be sent to.
        host (str, optional): Wiki to interact with.


    """

    # Create diectory
    pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

    # Create dictionary to store wikilink data
    wikilink_dict = dict()

    # populate the directory with many csv files
    write_revision_history_files(directory, wiki_title, agent_email, host,
                                 wikilink_dict)


    # Consolidate csv files into single document
    df = pd.concat([pd.read_csv(i) for i in glob.iglob(directory + '*.csv')],
                   sort=True)
    df.to_csv(os.path.join(directory, 'summary_' + wiki_title + '.csv'))

    # Dump pickle file
    with open(os.path.join(directory, 'wikilinks_to_revids.p'), 'wb') as topick:
        pickle.dump(wikilink_dict, topick)


def write_revision_history_files(directory, wiki_title, agent_email, host,
                                 wikilink_dict):
    """ Creates a wikipedia session and then itereates over an entire wiki
    history of revisions, processes those revisions, and saves every section of
    histories that wikipeida provides as individual entry.

    Args:
        directory (str): Path to directory.
        wiki_title (st): Title of wikipedia article to search.
        agent_email (str): Email sever messages will be sent to.
        host (str, optional): Wiki to interact with.
    """
    # Initialize the session
    session = mwapi.Session(host, user_agent=agent_email)

    # Define the headings of data to be stored
    headings = ['revid', 'parentid', 'user', 'userid', 'timestamp', 'comment',
                'character_count', 'external_link_count', 'heading_count',
                'wikifile_count', 'wikilink_count']

    # Query every revision of the page
    for rev_count, revision_set in enumerate(session.get(continuation=True,
                                             action='query', titles=wiki_title,
                                             prop='revisions',
                                             rvprop='ids|flags|timestamp|comment|user|userid|content',
                                             rvlimit='max')):

        # Make dataframe for storing information
        data_frame = pd.DataFrame(columns=headings)

        # Iterate over revision
        for count, revision in enumerate(next(iter(revision_set['query']['pages'].values()))['revisions']):

            # Extract edit information
            try:
                [revid, parentid, user, userid, timestamp, comment] = revision_information(revision)
            except:
                # This is a sloppy except call to deal with anamolus edits
                print(revision)
                break

            # Extract information on the website itself
            try:
                parsed = mwparserfromhell.parse(revision['*'])
            except:
                break

            [character_count, external_link_count,
             heading_count, wikilink_count,
             wikifile_count, wikilink_dict] = parsed_article_metrics(parsed,
                                                                     revid,
                                                                     wikilink_dict)

            data_frame.loc[count] = [revid, parentid, user, userid, timestamp,
                                     comment, character_count,
                                     external_link_count,
                                     heading_count,  wikifile_count,
                                     wikilink_count]

        # Dump the dataframe
        data_frame.to_csv(os.path.join(directory,
                                       wiki_title + "_" + str(rev_count) + '.csv'))


def revision_information(revision_json):
    """This returns [revid, parentid, user, userid, timestamp, comment] from a
    json which details the metadata of the revision

    Args:
        revision_json (dict): json/dict structure of the revision data

    Returns:
        TYPE: list
    """
    return [revision_json['revid'], revision_json['parentid'],
            revision_json['user'], revision_json['userid'],
            revision_json['timestamp'], revision_json['comment']]


def parsed_article_metrics(parsed_article, revid, wikilink_dict):
    """This should take a parsed article and pull out metrics of interest.
    Args:
        parsed_article (parsed): Parsed wikipedia site (mwparserfromhell)

    Returns:
        TYPE: list
    """
    character_count = len(parsed_article.strip_code())
    external_link_count = len(parsed_article.filter_external_links())
    heading_count = len(parsed_article.filter_headings())
    [wikilink_count, wikifile_count,
     wikilink_dict] = process_wikilinks(parsed_article, revid, wikilink_dict)

    return [character_count, external_link_count, heading_count,
            wikilink_count, wikifile_count, wikilink_dict]


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
