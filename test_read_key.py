import unittest
import io
import csv

import read_key


def global_helper(data):
    reader = csv.reader(io.StringIO(data))
    kf = read_key.KeyFile()
    return kf._read_globals(reader)
    

def cols_helper(data):
    reader = csv.reader(io.StringIO(data))
    kf = read_key.KeyFile()
    return kf._read_cols(reader)




class TestGlobalSuccess1(unittest.TestCase):
    def setUp(self):
        data = """epsg_code,4326
dlatcol,latitude
dloncol,longitude
,
"""
        self.globals = global_helper(data)

    def test_global_epsg(self):
        self.assertEqual(self.globals['epsg_code'], 4326)

    def test_global_dlatcol(self):
        self.assertEqual(self.globals['dlatcol'], 'latitude')
        
    def test_global_dloncol(self):
        self.assertEqual(self.globals['dloncol'], 'longitude')

    def test_default_maxskippct(self):
        self.assertEqual(self.globals['maxskippct'], 0.0)

    def test_default_encoding(self):
        self.assertEqual(self.globals['encoding'], 'utf-8')


# Now try a different order and some spaces
class TestGlobalSuccess2(unittest.TestCase):
    def setUp(self):
        data = """dlatcol,   latitude    
epsg_code,  4326
   dloncol  ,The Longitude
  , 
"""
        self.globals = global_helper(data)

    def test_global_epsg(self):
        self.assertEqual(self.globals['epsg_code'], 4326)

    def test_global_dlatcol(self):
        self.assertEqual(self.globals['dlatcol'], 'latitude')
        
    def test_global_dloncol(self):
        self.assertEqual(self.globals['dloncol'], 'The Longitude')


# Now try a with dllcol
class TestGlobalSuccess3(unittest.TestCase):
    def setUp(self):
        data = """dllcol,   position
dllre,"^.*[(](?P<dlat>[0-9]+), ?(?P<dlon>[0-9]+)[)]$"
epsg_code,4326,
maxskippct,17
source,foo.csv
encoding,latin1
  , 
"""
        self.globals = global_helper(data)

    def test_global_source(self):
        self.assertEqual(self.globals['source'], 'foo.csv')

    def test_global_maxskippct(self):
        self.assertEqual(self.globals['maxskippct'], 17.0)

    def test_global_encoding(self):
        self.assertEqual(self.globals['encoding'], 'latin1')

    def test_global_dlatcol(self):
        self.assertEqual(self.globals['dllcol'], 'position')
        
    def test_global_dloncol(self):
        self.assertEqual(self.globals['dllre'].pattern, r'^.*[(](?P<dlat>[0-9]+), ?(?P<dlon>[0-9]+)[)]$')




class TestGlobalAsserts(unittest.TestCase):
    """Confirm at least some kinds of bad data
    trigger exceptions.
    """
    def test_bad_epsg1(self):        
        """Confirm epgs_code must be a (bar) int
        """
        data = """dlatcol,latitude
dloncol,longitude
epsg_code,  epsg:4326
, 
"""
        self.assertRaises(ValueError, global_helper, data)

    def test_bad_epsg2(self):
        """Confirm epgs_code must be known
        """
        data = """dlatcol,latitude
dloncol,longitude
epsg_code,1
,
"""
        self.assertRaises(ValueError, global_helper, data)
        
    def test_missing_epsg1(self):
        """Confirm epgs_code is required
        """
        data = """dlatcol,   latitude    
dloncol,The Longitude
, 
"""
        self.assertRaises(ValueError, global_helper, data)

    def test_bad_regex1(self):
        """Confirm regular expression that is in error
        is a probelm.
        """
        data = """dllcol,   position
dllre,"^.*[(](?P<dlat>[0-9]+), ?(?P<dlon>[0-9]+)[)$"
epsg_code,4326,
maxskippct,17
source,foo.csv
  , 
"""
        self.assertRaises(ValueError, global_helper, data)

    def test_bad_regex2(self):
        """Confirm re lacking dlat is a problem
        """
        data = """dllcol,   position
dllre,"^.*[(](?P<dlatitude>[0-9]+), ?(?P<dlon>[0-9]+)[)]$"
epsg_code,4326,
maxskippct,17
source,foo.csv
  , 
"""
        self.assertRaises(ValueError, global_helper, data)


    def test_bad_regex3(self):
        """Confirm re lacking dlon is a problem
        """
        data = """dllcol,   position
dllre,"^.*[(](?P<dlat>[0-9]+)$"
epsg_code,4326,
maxskippct,17
source,foo.csv
  , 
"""
        self.assertRaises(ValueError, global_helper, data)


    def test_bad_encoding(self):
        """Confirm encoding must be recognized
        """
        data = """dllcol,   position
dllre,"^.*[(](?P<dlat>[0-9]+), ?(?P<dlon>[0-9]+)[)]$"
epsg_code,4326,
maxskippct,17
source,foo.csv
encoding,xyzzy
  , 
"""
        self.assertRaises(ValueError, global_helper, data)




class TestColumnSuccess1(unittest.TestCase):
    """Confirm basics work for reading a column section
    """
    def setUp(self):
        data = """"csv_header","SWIS Number","Unit Number","Site Name"
"identifier","swis_num","unit_num","name"
"datatype","string","integer","string"
"shortname:English","SWIS Number","Unit","Site"
"""
        self.hdr_to_id, self.identifiers = cols_helper(data)

    def test_hdr(self):
        self.assertEqual(self.hdr_to_id['SWIS Number'], 'swis_num')
        self.assertEqual(self.hdr_to_id['Unit Number'], 'unit_num')
        self.assertEqual(self.hdr_to_id['Site Name'], 'name')

    def test_datatype(self):
        self.assertEqual(self.identifiers['swis_num']['datatype'], 'string')
        self.assertEqual(self.identifiers['unit_num']['datatype'], 'integer')
        self.assertEqual(self.identifiers['name']['datatype'], 'string')

    def test_shortname_english(self):
        self.assertEqual(self.identifiers['swis_num']['shortname:English'], 'SWIS Number')
        self.assertEqual(self.identifiers['unit_num']['shortname:English'], 'Unit')
        self.assertEqual(self.identifiers['name']['shortname:English'], 'Site')


class TestColumnSuccess2(unittest.TestCase):
    """Confirm basics work if rows are re-ordered
    """
    def setUp(self):
        data = """"shortname:English","SWIS Number","Unit","Site"
"datatype","string","integer","string"
"identifier","swis_num","unit_num","name"
"csv_header","SWIS Number","Unit Number","Site Name"
"""
        self.hdr_to_id, self.identifiers = cols_helper(data)

    def test_hdr(self):
        self.assertEqual(self.hdr_to_id['SWIS Number'], 'swis_num')
        self.assertEqual(self.hdr_to_id['Unit Number'], 'unit_num')
        self.assertEqual(self.hdr_to_id['Site Name'], 'name')

    def test_datatype(self):
        self.assertEqual(self.identifiers['swis_num']['datatype'], 'string')
        self.assertEqual(self.identifiers['unit_num']['datatype'], 'integer')
        self.assertEqual(self.identifiers['name']['datatype'], 'string')

    def test_shortname_english(self):
        self.assertEqual(self.identifiers['swis_num']['shortname:English'], 'SWIS Number')
        self.assertEqual(self.identifiers['unit_num']['shortname:English'], 'Unit')
        self.assertEqual(self.identifiers['name']['shortname:English'], 'Site')


class TestColumnSuccess3(unittest.TestCase):
    """Confirm basics work if a few rows or columns are blank
    """
    def setUp(self):
        data = """"csv_header","SWIS Number","Unit Number","Site Name"
,
"datatype",,,"string","integer","real"
"identifier",,,"name","num","thingy"
,
"shortname:English","SWIS Number","Unit","Site","A Number","Some thingy"
"""
        self.hdr_to_id, self.identifiers = cols_helper(data)

    def test_hdr(self):
        self.assertTrue('SWIS Number' not in self.hdr_to_id)
        self.assertTrue('Unit Number' not in self.hdr_to_id)
        self.assertEqual(self.hdr_to_id['Site Name'], 'name')

    def test_datatype(self):
        self.assertTrue(len(self.identifiers.keys()) == 3)
        self.assertEqual(self.identifiers['name']['datatype'], 'string')
        self.assertEqual(self.identifiers['num']['datatype'], 'integer')
        self.assertEqual(self.identifiers['thingy']['datatype'], 'real')

    def test_shortname_english(self):
        self.assertEqual(self.identifiers['name']['shortname:English'], 'Site')
        self.assertEqual(self.identifiers['num']['shortname:English'], 'A Number')
        self.assertEqual(self.identifiers['thingy']['shortname:English'], 'Some thingy')




if __name__ == '__main__':
    unittest.main()
