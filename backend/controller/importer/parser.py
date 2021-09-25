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
from model.db.db_interface import object_exists, add_object, get_all_aliases
from controller.search.query_simbad import query_simbad_by_coords, query_simbad_by_name
from controller.search.search import check_object_updates

from bs4 import BeautifulSoup
from datetime import datetime
from astropy.coordinates import SkyCoord
from astropy.time import Time

# Regexes for extracting coordinates
COORD_REGEXES = ['ra:\s(?:\+|-)?(?:0*[1-2]\d|0*\d)h(?:0*[1-6]\d|0*\d)m(?:0*[1-6]\d|0*\d)(?:\.\d+)?s(?:,?\s)dec:\s(?:\+|-)?(?:0*\d\d?)d(?:0*[1-6]\d|0*\d)m(?:0*[1-6]\d|0*\d)(?:\.\d+)?s', # hms/dms
                 'ra\s(?:\+|-)?(?:0*[1-2]\d|0*\d)h(?:0*[1-6]\d|0*\d)m(?:0*[1-6]\d|0*\d)(?:\.\d+)?s(?:,?\s)dec\s(?:\+|-)?(?:0*\d\d?)d(?:0*[1-6]\d|0*\d)m(?:0*[1-6]\d|0*\d)(?:\.\d+)?s', # hms/dms
                 'ra:\s(?:\+|-)?(?:0*[1-2]\d|0*\d):(?:0*[1-6]\d|0*\d):(?:0*[1-6]\d|0*\d)(?:\.\d+)?(?:,?\s)dec:\s(?:\+|-)?(?:0*\d\d?):(?:0*[1-6]\d|0*\d):(?:0*[1-6]\d|0*\d)(?:\.\d+)?', # hms/dms
                 'ra\s(?:\+|-)?(?:0*[1-2]\d|0*\d):(?:0*[1-6]\d|0*\d):(?:0*[1-6]\d|0*\d)(?:\.\d+)?(?:,?\s)dec\s(?:\+|-)?(?:0*\d\d?):(?:0*[1-6]\d|0*\d):(?:0*[1-6]\d|0*\d)(?:\.\d+)?', # hms/dms
                 'ra:\s(?:\+|-)?\d+(?:\.\d+)?(?:,?\s)dec:\s(?:\+|-)?(?:0*\d\d?)(?:\.\d+)?', # decimal degrees
                 'ra\s(?:\+|-)?\d+(?:\.\d+)?(?:,?\s)dec\s(?:\+|-)?(?:0*\d\d?)(?:\.\d+)?' # decimal degrees
]

# Used to convert coordinates to SkyCoord objects
COORD_FORMATS = [['(?:\+|-)?(?:0*[1-2]\d|0*\d)h(?:0*[1-6]\d|0*\d)m(?:0*[1-6]\d|0*\d)(?:\.\d+)?s', '(?:\+|-)?(?:0*\d\d?)d(?:0*[1-6]\d|0*\d)m(?:0*[1-6]\d|0*\d)(?:\.\d+)?s'], # hms/dms
                 ['(?:\+|-)?(?:0*[1-2]\d|0*\d):(?:0*[1-6]\d|0*\d):(?:0*[1-6]\d|0*\d)(?:\.\d+)?', '(?:\+|-)?(?:0*\d\d?):(?:0*[1-6]\d|0*\d):(?:0*[1-6]\d|0*\d)(?:\.\d+)?'], # hms/dms
                 ['(?:\+|-)?\d+(?:\.\d+)?', '(?:\+|-)?(?:0*\d\d?)(?:\.\d+)?'] # decimal degrees
]

# Regexes for extracting dates
DATE_REGEXES = ['(?:[0-3]\d|[1-9])\s(?:january|february|march|april|may|june|july|august|september|october|november|december)\s(?:[1-2]\d\d\d|\d\d)', # dd mmmm yy (01 February 99) and dd mmmm yyyy (01 February 1999)
                '(?:[0-3]\d|[1-9])\s(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s(?:[1-2]\d\d\d|\d\d)', # dd mmm yy (01 Feb 99) and dd mmm yyyy (01 Feb 1999)
                '(?:january|february|march|april|may|june|july|august|september|october|november|december)\s(?:[0-3]\d|[1-9]),\s(?:[1-2]\d\d\d|\d\d)', # mmmm dd, yy (February 01, 99) and mmmm dd, yyyy (February 01, 1999)
                '(?:[0-3]\d|[1-9])-(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-(?:[1-2]\d\d\d|\d\d)', # dd-mmm-yy (01-Feb-99) and dd-mmm-yyyy (01-Feb-1999)
                '(?:[0-3]\d|[1-9])-(?:[0-1]\d|[1-9])-(?:[1-2]\d\d\d|\d\d)', # dd-mm-yy (01-02-99) and dd-mm-yyyy (01-02-1999)
                '(?:[0-3]\d|[1-9])\/(?:[0-1]\d|[1-9])\/(?:[1-2]\d\d\d|\d\d)', # dd/mm/yy (01/02/99) and dd/mm/yyyy (01/02/1999)
                '(?:[1-2]\d\d\d|\d\d)\/(?:[0-1]\d|[1-9])\/(?:[0-3]\d|[1-9])', # yy/mm/dd (99/02/01) and yyyy/mm/dd (1999/02/01)
                '(?:[0-1]\d|[1-9])\/(?:[0-3]\d|[1-9])\/(?:[1-2]\d\d\d|\d\d)', # mm/dd/yy (02/01/99) and mm/dd/yyyy (02/01/1999)
                '(?:[0-3]\d|[1-9])\.(?:[0-1]\d|[1-9])\.(?:[1-2]\d\d\d|\d\d)', # dd.mm.yy (01.02.99) and dd.mm.yyyy (01.02.1999)
                '(?:[1-2]\d\d\d|\d\d)-(?:[0-1]\d|[1-9])-(?:[0-3]\d|[1-9])', # yy-mm-dd (99-02-01) and yyyy-mm-dd (1999-02-01)
                'mjd=\d+(?:\.\d+)?', # Modified Julian Date (MJD=50000.0)
                'jd=\d+(?:\.\d+)?' # Julian Date (JD=2500000.0)
]

# List of date formats to convert
DATE_FORMATS = ['%d %B %Y', # dd mmmm yyyy
                '%d %b %Y', # dd mmm yyyy
                '%B %d, %Y', # mmmm dd, yyyy
                '%d-%b-%Y', # dd-mmm-yyyy
                '%d-%m-%Y', # dd-mm-yyyy
                '%d/%m/%Y', # dd/mm/yyyy
                '%Y/%m/%d', # yyyy/mm/dd
                '%m/%d/%Y', # mm/dd/yyyy
                '%d.%m.%Y', # dd.mm.yyyy
                '%Y-%m-%d', # yyyy-mm-dd
                '%d %B %y', # dd mmmm yy
                '%d %b %y', # dd mmm yy
                '%B %d, %y', # mmmm dd, yy
                '%d-%b-%y', # dd-mmm-yy
                '%d-%m-%y', # dd-mm-yy
                '%d/%m/%y', # dd/mm/yy
                '%y/%m/%d', # yy/mm/dd
                '%m/%d/%y', # mm/dd/yy
                '%d.%m.%y', # dd.mm.yy
                '%y-%m-%d', # yy-mm-dd
                '\d+(?:\.\d+)?' # MJD and JD
]

# Regexes for extracting keywords
KEYWORD_REGEXES = ['radios?',
                  'millimeter',
                  'sub(\s|-)millimeter',
                  'far(\s|-)infra(\s|-)reds?',
                  'infra(\s|-)reds?',
                  'optical',
                  'ultra(\s|-)violets?',
                  'x(\s|-)rays?',
                  'gamma(\s|-)rays?',
                  '> gev',
                  'tev',
                  'vhe',
                  'uhe',
                  'neutrinos?',
                  'comments?',
                  'agn',
                  'asteroids?\s?\(binary\)',
                  'asteroids?',
                  'binar(y|ies)',
                  'black holes?',
                  'blazars?',
                  'cataclysmic variables?',
                  'comets?',
                  'cosmic rays?',
                  'direct collapse events?',
                  'exoplanets?',
                  'fast radio bursts?',
                  'gamma(\s|-)ray bursts?',
                  'globular clusters?',
                  'gravitational lensing',
                  'gravitational waves?',
                  'magnetars?',
                  'meteors?',
                  'microlensing events?',
                  'near(\s|-)earth objects?',
                  'neutron stars?',
                  'nova(e|s)?',
                  'planets?\s?\(minor\)',
                  'planets?',
                  'potentially hazardous asteroids?',
                  'pre(\s|-)main(\s|-)sequence stars?',
                  'pulsars?',
                  'quasars?',
                  'requests? for observations?',
                  'soft gamma(\s|-)ray repeaters?',
                  'solar system objects?',
                  'stars?',
                  'supernova remnants?',
                  'supernova(e|s)?',
                  'suns?',
                  'tidal disruption events?',
                  'transients?',
                  'variables?',
                  'young stellar objects?'
]

# Custom exception
class MissingReportElementError(Exception):
    pass

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
        MissingReportElementError: Thrown when important data could not be extracted or are missing from the report.
    """

    # Parses HTML into a tree
    soup = BeautifulSoup(html_string, 'html.parser')

    # Extracts title of ATel report
    title = ''

    if(soup.find('h1', {'class': 'title'}) is not None):
        title = str(soup.find('h1', {'class': 'title'}).get_text(strip=True))
    else:
        raise MissingReportElementError(f'Title is missing in ATel #{str(atel_num)}')
    
    # Extracts authors of ATel report
    authors = ''

    if(soup.find('strong') is not None):
        authors = str(soup.find('strong').get_text(strip=True))
    else:
        raise MissingReportElementError(f'Authors section is missing in ATel #{str(atel_num)}')

    # Finds all possible paragraphs in the HTML
    body = ''
    texts = soup.find_all('p', {'class': None, 'align': None})

    # Filters out non-body text elements and formats the body text
    for text in texts:
        if((text.find('iframe') == None) and (len(text.get_text(strip=True)) != 0) and ('Referred to by ATel #:' not in text.get_text(strip=True))):
            if('\n' in text.get_text()):
                body += str(text.get_text())
            else:
                body += f'{text.get_text()}\n'

    if(body == ''):
        raise MissingReportElementError(f'Body section is missing in ATel #{str(atel_num)}')
    
    # Extracts submission date of ATel report
    elements = soup.find_all('strong')
    submission_date = elements[1].get_text(strip=True)

    # Formats submission date
    formatted_submission_date = None

    try:
        formatted_submission_date = datetime.strptime(submission_date, '%d %b %Y; %H:%M UT')
    except ValueError:
        raise MissingReportElementError(f'Submission date is missing in ATel #{str(atel_num)}')

    # Extracts the number of any ATel reports that referenced the ATel report
    referenced_by = []

    if(soup.find('div', {'id': 'references'}) is not None):
        referenced_by = soup.find('div', {'id': 'references'}).get_text()
        referenced_by = re.findall('\d+', referenced_by)
    
    referenced_by = list(dict.fromkeys([int(referenced_by_num) for referenced_by_num in referenced_by]))

    # Extracts any links that are in the ATel report
    referenced_reports = []
    div_element = soup.find('div', {'id': 'telegram'})
    links = div_element.find_all('a', href=True)
    url_string = 'https://www.astronomerstelegram.org/?read='

    # Extracts the number of any ATel reports referenced
    for link in links:
        if((link['href'].find(url_string) != -1) and (link['href'] != url_string) and (link.get_text() != 'Previous') and (link.get_text() != 'Next')):
            num = re.search('\d+', link['href'])
            referenced_reports.append(int(num.group()))

    # Filters out referenced by ATel numbers
    for referenced_by_num in referenced_by:
        referenced_reports.remove(referenced_by_num)

    referenced_reports = list(dict.fromkeys(referenced_reports))

    # Extracts subjects for keywords extractor
    subjects = ''

    if(soup.find('p', {'class': 'subjects'}) is not None):
        subjects = soup.find('p', {'class': 'subjects'}).get_text()

    text = f'{title} {body.strip()}'

    return ImportedReport(atel_num, title, authors, body.strip(), formatted_submission_date, referenced_reports, parse_dates(extract_dates(text)), extract_keywords(f'{title} {subjects} {body.strip()}'), extract_known_aliases(text), parse_coords(extract_coords(text)), referenced_by)

def extract_coords(text: str) -> list[str]:
    """
    Finds all coordinates in the title and body of ATel report.

    Args:
        text (str): Title and body of ATel report.

    Returns:
        list[str]: List of coordinates found.
    """

    coords = []

    # Finds all coordinates that are in the above coordinate formats in the title and body of ATel report
    for regex in COORD_REGEXES:
        # Attempts to find all coordinates that are in a certain coordinate format in the title and body text using regex
        coord_regex = re.compile(f'[^a-z]{regex}[^\d]')
        coords_found = coord_regex.findall(f' {text.lower()} ')

        # Removes any leading and/or trailing characters that are not part of the coordinate format
        for coord in coords_found:
            coord_regex = re.compile(regex)
            extracted_coord = coord_regex.search(coord)
            coords.append(extracted_coord.group())

    return list(dict.fromkeys(coords))

def parse_coords(coords: list[str]) -> list[SkyCoord]:
    """
    Parses coordinates that were found into appropriate format so that they can be used to query SIMBAD.

    Args:
        coords (list[str]): List of coordinates found in the title and body of ATel report.

    Returns:
        list[SkyCoord]: List of formatted coordinates.
    """

    formatted_coords = []

    # Converts each extracted coordinate to SkyCoord object
    for coord in coords:
        for i in range(len(COORD_FORMATS)):
            coord_format = COORD_FORMATS[i]

            # Attempts to extract RA and DEC in a certain coordinate format
            ra_regex = re.compile(f'ra:?\s{coord_format[0]}')
            dec_regex = re.compile(f'dec:?\s{coord_format[1]}')

            ra_found = ra_regex.search(coord)
            dec_found = dec_regex.search(coord)

            # Extracts coordinates if they are in the coordinate format
            if((ra_found is not None) and (dec_found is not None)):
                ra_regex = re.compile(coord_format[0])
                dec_regex = re.compile(coord_format[1])

                ra = ra_regex.search(ra_found.group())
                dec = dec_regex.search(dec_found.group())

                try:
                    skycoord_obj = None
                    
                    # Converts coordinate to SkyCoord object
                    if((i == 0) or (i == 1)):
                        skycoord_obj = SkyCoord(str(ra.group()), str(dec.group()), unit=('hourangle', 'deg'))
                    elif(i == 2):
                        skycoord_obj = SkyCoord(float(ra.group()), float(dec.group()), unit=('deg', 'deg'))
                    
                    try:
                        # Queries SIMBAD by coordinate to get object IDs and its aliases
                        query_result = query_simbad_by_coords(skycoord_obj)

                        if(query_result != dict()):
                            for key, value in query_result.items():
                                try:
                                    # Checks whether object ID exist in the database
                                    exists, last_updated = object_exists(key) 

                                    # Adds new aliases associated to the object ID into the database if object ID exist and updating is needed
                                    if(exists == True):
                                        check_object_updates(key, last_updated)
                                    else:
                                        # Queries SIMBAD by name to get the object ID and its coordinates
                                        name_query_result = query_simbad_by_name(key, False)

                                        if(name_query_result is not None):
                                            # Adds object ID and its aliases into the database
                                            name, coordinates, _ = name_query_result
                                            add_object(name, coordinates, value)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    # Adds converted coordinate to list
                    formatted_coords.append(skycoord_obj)
                except ValueError:
                    pass

                break

    return formatted_coords

def extract_dates(text: str) -> list[str]:
    """
    Finds all dates in the title and body of ATel report.

    Args:
        text (str): Title and body of ATel report.

    Returns:
        list[str]: List of dates found.
    """

    dates = []

    # Finds all dates that are in the above date formats in the title and body of ATel report
    for regex in DATE_REGEXES:
        # Attempts to find all dates that are in a certain date format in the title and body text using regex
        date_regex = re.compile(f'[^\d|^a-z]{regex}[^\d]')
        dates_found = date_regex.findall(f' {text.lower()} ')

        # Removes any leading and/or trailing characters that are not part of the date format
        for date in dates_found:
            date_regex = re.compile(regex)
            extracted_date = date_regex.search(date)
            dates.append(extracted_date.group())

    return list(dict.fromkeys(dates))

def parse_dates(dates: list[str]) -> list[datetime]:
    """
    Parses dates that were found into datetime objects so that they can be inserted easily to the database.

    Args:
        dates (list[str]): List of dates found in the title and body of ATel report.

    Returns:
        list[datetime]: List of datetime objects representing dates.
    """

    formatted_dates = []

    # Converts each extracted date to datetime object
    for date in dates:
        for i in range(len(DATE_FORMATS)):
            try:
                # Standard date formats
                if(i < 20):
                    # Adds converted date to list
                    formatted_dates.append(datetime.strptime(date, DATE_FORMATS[i]))
                # MJD and JD formats
                else:
                    time_object = None
                    date_format = re.search(DATE_REGEXES[10], date)

                    if(date_format is not None):
                        # Creates Time object in MJD format
                        mjd = re.search(DATE_FORMATS[i], date_format.group())
                        time_object = Time(mjd.group(), format='mjd')
                    else:
                        # Creates Time object in JD format
                        date_format = re.search(DATE_REGEXES[11], date)

                        if(date_format is not None):
                            jd = re.search(DATE_FORMATS[i], date_format.group())
                            time_object = Time(jd.group(), format='jd')

                    if(time_object is not None):
                        # Converts MJD/JD to standard date
                        converted_date = time_object.iso
                        extracted_date = re.search(DATE_REGEXES[9], converted_date)

                        # Adds converted date to list
                        formatted_dates.append(datetime.strptime(extracted_date.group(), DATE_FORMATS[9]))
                break
            except ValueError:
                pass

    return list(dict.fromkeys(formatted_dates))

def extract_known_aliases(text: str) -> list[str]:
    """
    Finds all known aliases and object IDs in the title and body of ATel report.

    Args:
        text (str): Title and body of ATel report.

    Returns:
        list[str]: List of object IDs found.
    """

    object_IDs = []
    # Retrieves known aliases
    aliases = get_all_aliases()

    # Finds all aliases and object IDs in the title and body of ATel report
    for alias in aliases:
        # Regex for alias
        regex = f'[^\d|^a-z]{alias.alias.lower()}[^\d|^a-z]'

        # Attempts to find alias in the title and body text using regex
        alias_regex = re.compile(regex)
        alias_found = alias_regex.search(f' {text.lower()} ')

        # Adds object ID to list if its associated alias is found in the title and body text
        if(alias_found is not None):
            object_IDs.append(str(alias.object_ID.lower()))
        else:
            # Regex for object ID associated to alias
            regex = f'[^\d|^a-z]{alias.object_ID.lower()}[^\d|^a-z]'

            # Attempts to find object ID in the title and body text using regex
            object_ID_regex = re.compile(regex)
            object_ID_found = object_ID_regex.search(f' {text.lower()} ')

            # Adds object ID to list if it is found in the title and body text
            if(object_ID_found is not None):
                object_IDs.append(str(alias.object_ID.lower()))

    return list(dict.fromkeys(object_IDs))

def extract_keywords(text: str) -> list[str]:
    """
    Finds all keywords in the title, subjects section and body of ATel report.

    Args:
        text (str): Title, subjects section and body of ATel report.

    Returns:
        list[str]: List of keywords found.
    """

    i = 0
    keywords = []

    # Finds all keywords in the title, subjects section and body of ATel report
    for keyword in KEYWORD_REGEXES:
        # Ensures that only full words will be identified as keywords
        regex = f'[^a-z]{keyword}[^a-z]'

        # Attempts to find keyword in the title, subjects section and body text using regex
        keyword_regex = re.compile(regex)
        keyword_found = keyword_regex.search(f' {text.lower()} ')

        # Adds keyword to list if it is found in the title, subjects section and body text
        if(keyword_found is not None):
            keywords.append(str(FIXED_KEYWORDS[i]))

        i = i + 1

    return keywords