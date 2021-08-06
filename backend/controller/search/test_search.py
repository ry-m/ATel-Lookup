""" Test suite for the search module.

These functions are used to access the SIMBAD database, providing a way to
search by name (ID) or coordinates. Data is formatted appropriately. 

Author:
    Ryan Martin

License Terms and Copyright:
    Copyright (C) 2021 Ryan Martin

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


import unittest as ut
import numpy as np
import query_simbad

from astropy.table import Table
from astropy.table.column import Column


""" Test the get_names_from_table(Table) function.
"""
class TestNameExtraction(ut.TestCase):
    def setUp(self):
        # This way of storing strings mirrors how the astroquery query 
        # function works. The string is represented as bytes. 
        col_1 = Column(name="ID", data=[b"id1", b"id2", b"id3", b"id4"])
        self.alias_table = Table()
        self.alias_table.add_column(col_1)

        # For region queries, astropy returns a column of objects for the 
        # main ID. This is different to an alias search which is an array of bytes. 
        col_2 = Column(name="MAIN_ID", data=["id1", "id2", "id3", "id4"], dtype=np.object0)
        col_3 = Column(name="RA", data=["", "", "", ""], dtype=np.str0)
        self.region_table = Table()
        self.region_table.add_column(col_2)
        self.region_table.add_column(col_3)


    # Test the alias table (dtype is bytes30)
    def test_alias_table(self):
        lst = query_simbad._get_names_from_table(self.alias_table)
        self.assertEqual(lst[0], "id1")
        self.assertEqual(lst[1], "id2")
        self.assertEqual(lst[2], "id3")
        self.assertEqual(lst[3], "id4")


    # Test the region table (dtype is object)
    def test_region_table(self):
        lst = query_simbad._get_names_from_table(self.region_table)
        self.assertEqual(lst[0], "id1")
        self.assertEqual(lst[1], "id2")
        self.assertEqual(lst[2], "id3")
        self.assertEqual(lst[3], "id4")


# Run suite. 
if __name__ == '__main__':
    ut.main()