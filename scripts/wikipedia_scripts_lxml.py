# imports
import pathlib
import mwparserfromhell
import pickle
import dateutil
import csv
import datetime
import re
import requests
from bs4 import BeautifulSoup
from lxml import etree
from io import StringIO, BytesIO
import json
from lxml import html
import lxml

# Version history collection

# Assumes directory
# datafolder
# .../wikilink_dictionaries
# ......... website.p
# .../revision_history_data
# ......... website.csv
# summary_file.csv


def collect_consoidate_historical_edits(directory, wiki_title,
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
    if (revision_directory / (wiki_title + '.csv')).is_file():
        revision_csv = open(revision_directory / (wiki_title + '.csv'), 'a',
                            newline='')
        revision_writer = csv.writer(revision_csv)
    else:
        revision_csv = open(revision_directory / (wiki_title + '.csv'), 'w',
                            newline='')
        revision_writer = csv.writer(revision_csv)
        revision_writer.writerow(headings)

    # Check the wikilinks file
    if (wiklink_directory / (wiki_title + '.json')).is_file():
        with open(wiklink_directory / (wiki_title + '.json'), 'r') as tounpick:
            wikilink_dict = json.load(tounpick)
    else:
        wikilink_dict = dict()

    # # populate the directory with many csv files
    wikilink_dict = update_revisions_and_links(wiki_title, revision_writer,
                                               wikilink_dict, earliest_date,
                                               latest_date='NOW')

    # Close the revision csv
    revision_csv.close()

    # Dump pickle file
    with open(wiklink_directory / (wiki_title + '.json'), 'w') as topick:
        json.dump(wikilink_dict, topick)


def update_revisions_and_links(wiki_title, revision_csv, wikilink_dict,
                               earliest_date, latest_date='NOW'):
    """"""
    # First request a dump of all revisions from wikipedia

    if latest_date == 'NOW':
        latest_date = datetime.datetime.now(dateutil.tz.tzutc())

    earliest_date = '2015-07-01T11:03:28Z'

    number_of_revisions = 1000

    # Wikipedia will only dump 1000 versions of a page
    while number_of_revisions == 1000:
        url = 'https://en.wikipedia.org/w/index.php?title=Special:Export'
        data = {'pages': wiki_title,
                'limit': '1000',
                'offset': str(earliest_date)}

        print('request_started')
        r = requests.post(url=url,
                          data=data)
        print('request_complete')

        tree = html.parse(BytesIO(r.content))

        for count, action in enumerate(tree.iter(tag='revision')):
            # revid = parent_id = contrib_username = contrib_id = timestamp = comment = bodytext = None
            # for child in action.getchildren():
            #     text = child.text
            #     tag = child.tag

            #     # Big ugly if block to get it done
            #     if tag == 'id':
            #         revid = text
            #     elif tag == 'parentid':
            #         parent_id = text
            #     elif tag == 'timestamp':
            #         timestamp = text
            #     elif tag == 'contributor':
            #         for child1 in child.getchildren():
            #             if child1.tag == 'id':
            #                 contrib_id = child1.text
            #             elif child1.tag == 'username':
            #                 contrib_username = child1.text
            #     elif tag == 'comment':
            #         comment = text
            #     elif tag == 'text':
            #         bodytext = text
            # if bodytext not None:
            #     [character_count, word_count,
            #      external_link_count, heading_count,
            #      wikilink_count, wikifile_count,
            #      wikilink_dict] = parsed_article_metrics(parsed, revid,
            #                                          wikilink_dict)
            revision = BeautifulSoup(stringify_children(action), 'html5lib')
            try:
                parsed = mwparserfromhell.parse(revision('text')[0].contents[0])
            except IndexError:
                print('text indexing error')
                print(revision)
                continue
            [revid, parent_id,
             contrib_username, contrib_id,
             timestamp, comment] = revision_information(revision)
            [character_count, word_count,
             external_link_count, heading_count,
             wikilink_count, wikifile_count,
             wikilink_dict] = parsed_article_metrics(parsed, revid,
                                                     wikilink_dict)
            try:
                revision_csv.writerow([wiki_title, revid, parent_id,
                                       contrib_username, contrib_id,
                                       timestamp, comment, character_count,
                                       word_count,
                                       external_link_count, heading_count,
                                       wikilink_count, wikifile_count])
            except UnicodeEncodeError:
                print([wiki_title, revid, parent_id,
                       contrib_username, contrib_id,
                       timestamp, comment, character_count,
                       word_count,
                       external_link_count, heading_count,
                       wikilink_count, wikifile_count])

            earliest_date = timestamp
            number_of_revisions = count + 1

    return wikilink_dict


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


def revision_information(revision_html):

    revid = revision_html.id.contents[0]
    timestamp = revision_html.timestamp.contents[0]

    try:
        parent_id = revision_html.parentid.contents[0]
    except AttributeError:
        # No parent was assigned
        parent_id = None

    # Contributor
    try:
        contrib_username = revision_html.contributor.username.contents[0]
    except AttributeError:
        contrib_username = None

    try:
        contrib_id = revision_html.contributor.username.id.contents[0]
    except AttributeError:
        contrib_id = None

    try:
        comment = revision_html.comment.contents[0]
    except AttributeError:
        comment = None

    return [revid, parent_id,
            contrib_username, contrib_id,
            timestamp, comment]


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


def stringify_children(node):
    """Given a LXML tag, return contents as a string

       >>> html = "<p><strong>Sample sentence</strong> with tags.</p>"
       >>> node = lxml.html.fragment_fromstring(html)
       >>> extract_html_content(node)
       "<strong>Sample sentence</strong> with tags."
    """
    if node is None or (len(node) == 0 and not getattr(node, 'text', None)):
        return ""
    node.attrib.clear()
    opening_tag = len(node.tag) + 2
    closing_tag = -(len(node.tag) + 3)
    return html.tostring(node)[opening_tag:closing_tag]
