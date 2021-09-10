"""
Contains functions that handles the parsing and extraction of ATel data.

Author:
    Nathan Sutardi

License Terms and Copyright:
    Copyright (C) 2021 Nathan Sutardi

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import re

from model.constants import FIXED_KEYWORDS
from model.ds.report_types import ImportedReport

from bs4 import BeautifulSoup
from datetime import datetime
from astropy.coordinates import SkyCoord

# Regex for extracting keywords
KEYWORDS_REGEX = ["radio",
                  "millimeter",
                  "sub-millimeter",
                  "far-infra-red",
                  "infra-red",
                  "optical",
                  "ultra-violet",
                  "x-ray",
                  "gamma ray",
                  "> gev",
                  "tev",
                  "vhe",
                  "uhe",
                  "neutrinos",
                  "a comment",
                  "agn",
                  "asteroid\(binary\)",
                  "asteroid",
                  "binary",
                  "black hole",
                  "blazar",
                  "cataclysmic variable",
                  "comet",
                  "cosmic rays",
                  "direct collapse event",
                  "exoplanet",
                  "fast radio burst",
                  "gamma-ray burst",
                  "globular cluster",
                  "gravitational lensing",
                  "gravitational waves",
                  "magnetar",
                  "meteor",
                  "microlensing event",
                  "near-earth object",
                  "neutron star",
                  "nova",
                  "planet\(minor\)",
                  "planet",
                  "potentially hazardous asteroid",
                  "pre-main-sequence star",
                  "pulsar",
                  "quasar",
                  "request for observations",
                  "soft gamma-ray repeater",
                  "solar system object",
                  "star",
                  "supernova remnant",
                  "supernovae",
                  "the sun",
                  "tidal disruption event",
                  "transient",
                  "variables",
                  "young stellar object"
]

# Parser functions
def parse_report(atel_num: int, html_string: str) -> ImportedReport:
    """
    Extracts data from ATel report as stated in non-functional requirement 1 in the SRS.

    Args:
        atel_num (int): The ATel number of the report to be parsed.
        html_string (str): String representation of the downloaded HTML of ATel report from which to extract data from.

    Returns:
        ImportedReport: Object containing all extracted data from the ATel report.

    Raises:
        MissingReportElementException: Thrown when important data could not be extracted or are missing from the report.
    """

    # Parses HTML into a tree
    soup = BeautifulSoup(html_string, 'html.parser')

    # Extracts title and authors of ATel report
    title = soup.find('h1', {'class': 'title'}).get_text(strip=True)
    authors = soup.find('strong').get_text(strip=True)
    body = ''

    # Finds all possible paragraphs in the HTML
    texts = soup.find_all('p', {'class': None, 'align': None})

    # Filters out non body text elements and formats the body text
    for text in texts:
        if((text.find('iframe') == None) and (len(text.get_text(strip=True)) != 0) and ('Referred to by ATel #:' not in text.get_text(strip=True))):
            if('\n' in text.get_text()):
                body += text.get_text()
            else:
                body += text.get_text() + '\n'

    # Extracts submission date of ATel report
    elements = soup.find_all('strong')
    submission_date = elements[1].get_text(strip=True)

    # Formats submission date
    formatted_submission_date = datetime.strptime(submission_date, '%d %b %Y; %H:%M UT')

    return ImportedReport(atel_num, title, authors, body.strip(), formatted_submission_date, keywords=extract_keywords(body.strip()))

def extract_coords(body_text: str) -> list[str]:
    """
    Finds all coordinates in the body text of ATel report.

    Args:
        body_text (str): Body text of ATel report.

    Returns:
        list[str]: List of coordinates found.
    """
    return []

def parse_coords(coords: list[str]) -> list[SkyCoord]:
    """
    Parse coordinates that were found into appropriate format so that they can be used to query SIMBAD.

    Args:
        coords (list[str]): List of coordinates found in the body text of ATel report.

    Returns:
        list[SkyCoord]: List of formatted coordinates.
    """
    return []

def extract_dates(body_text: str) -> list[str]:
    """
    Finds all dates in the body text of ATel report.

    Args:
        body_text (str): Body text of ATel report.

    Returns:
        list[str]: List of dates found.
    """

    dates = []

    # Date formats could have optional time afterwards in hh:mm (23:59) or hh:mm:ss (23:59:59)
    date_regexes = ['(?:[0-3]\d|[1-9])-(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-(?:[1-2]\d\d\d|\d\d)(?:\s(?:[0-2]\d|[1-9]):[0-5]\d(?::[0-5]\d)?)?', # dd-mmm-yy (01-Feb-99) and dd-mmm-yyyy (01-Feb-1999)
                    '(?:[0-1]\d|[1-9])\/(?:[0-3]\d|[1-9])\/(?:[1-2]\d\d\d|\d\d)(?:\s(?:[0-2]\d|[1-9]):[0-5]\d(?::[0-5]\d)?)?', # mm/dd/yy (02/01/99) and mm/dd/yyyy (02/01/1999)
                    '(?:[0-3]\d|[1-9])\.(?:[0-1]\d|[1-9])\.(?:[1-2]\d\d\d|\d\d)(?:\s(?:[0-2]\d|[1-9]):[0-5]\d(?::[0-5]\d)?)?', # dd.mm.yy (01.02.99) and dd.mm.yyyy (01.02.1999)
                    '(?:[1-2]\d\d\d|\d\d)\/(?:[0-1]\d|[1-9])\/(?:[0-3]\d|[1-9])(?:\s(?:[0-2]\d|[1-9]):[0-5]\d(?::[0-5]\d)?)?', # yy/mm/dd (99/02/01) and yyyy/mm/dd (1999/02/01)
                    '(?:[1-2]\d\d\d|\d\d)-(?:[0-1]\d|[1-9])-(?:[0-3]\d|[1-9])(?:\s(?:[0-2]\d|[1-9]):[0-5]\d(?::[0-5]\d)?)?' # yy-mm-dd (99-02-01) and yyyy-mm-dd (1999-02-01)
    ]

    # Finds all dates that are in the above date formats in the body text of ATel report
    for regex in date_regexes:
        # Attempts to find all dates that are in a certain date format in the body text using regex
        date_regex = re.compile(f'[^\d]{regex}[^\d]')
        dates_found = date_regex.findall(f' {body_text.lower()} ')

        # Removes any leading and/or trailing characters that are not part of the date format
        for date in dates_found:
            date_regex = re.compile(regex)
            extracted_date = date_regex.search(date)
            dates.append(extracted_date.group())

    return list(dict.fromkeys(dates))

def parse_dates(dates: list[str]) -> list[datetime]:
    """
    Parse dates that were found into datetime objects so that they can be inserted easily to the database.

    Args:
        dates (list[str]): List of dates found in the body text of ATel report.

    Returns:
        list[datetime]: List of datetime objects representing dates.
    """
    return []

def extract_known_aliases(body_text: str) -> list[str]:
    """
    Finds all known aliases in the body text of ATel report.

    Args:
        body_text (str): Body text of ATel report.

    Returns:
        list[str]: List of known aliases found.
    """
    return []

def extract_keywords(body_text: str) -> list[str]:
    """
    Finds all keywords in the body text of ATel report.

    Args:
        body_text (str): Body text of ATel report.

    Returns:
        list[str]: List of keywords found.
    """

    i = 0
    keywords = []

    # Finds all keywords in the body text of ATel report
    for keyword in KEYWORDS_REGEX:
        # Ensures that only full words will be identified as keywords
        regex = f'[^a-z]{keyword}[^a-z]'

        # Attempts to find keyword in the body text using regex
        keyword_regex = re.compile(regex)
        keyword_found = keyword_regex.search(f' {body_text.lower()} ')

        # Adds keyword to list if it is found in the body text
        if keyword_found is not None:
            keywords.append(FIXED_KEYWORDS[i])

        i = i + 1

    return keywords