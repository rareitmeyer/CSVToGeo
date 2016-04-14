# Overview

This is a tool to convert a CSV data file with location data into a
valid GeoJSON or ESRI Shapefile with a corresponding 'point' layer,
so it can be easily viewed by Geographic Information System tools.

Proper conversion requires a fair bit of information about the data
to convert, like the geographic projection, which column(s) have lat
and lon, etc. CSV columns might need new names, and should have clearly
defined data types.

In order to keep all of this information together, this program expects
a "key file" that describes how the CSV data file should be processed.
The key file is also in CSV format.


# Prerequisites

* A recent copy of Python3. The author has tested under Python 3.4, but
  back as far as Python 3.2 will probably work.

* The "osgeo" python package.

* The "requests" package may be a requirement in the future.


# Example

There's a sample data set and key file in the 'examples' directory.

1. Make a new directory called "test" and copy the example files to test.

2. Copy the example .csv data file and .key.csv key file to the test directory

3. Open a command prompt and change to the test directory

4. Use python 3.2 or later, which could be called python3 or just python,
   depending on your platform, to run the tool as follows:

   python3 ../CSVToGeo.py --keyfile Solid_Waste_Centers.key.csv --datafile --Solid_Waste_Centers.csv --outext .geojson

5. Look at the resulting .geojson file.


See the help (python3 CSVToGeo.py --help) for a few more invation options.


# The Key File

As above, there are a number of settings required to properly convert
a CSV file into a geographic file. The key file keeps all this
information together. As you read the following documentation, it
might be best to look at the the Solid_Waste_Centers.key.csv key file,
and the Solid_Waste_Centers.csv data file.

The key file has two sections: a header with values that apply to the whole
data set, and a per-column section that describes the columns in the data.
The two sections are separated by a blank row.


## Key File Header Section

The header section has a simple format: column A contains names and 
column B containing values. Keys for the header:

source
 The source of the data, as a http://URL. Used for documentation,
 and potentially (in a future version), data could be fetched from
 this URL.
 
epsg_code [required]
  The EPSG code for the geographic projection the data uses. Data often
  is in WGS84 coordinates (EPSG 4326), but may not be. If it's helpful,
  The folks at SpatialReference have nice pages on projections. EG
     http://spatialreference.org/ref/epsg/wgs-84/
   
dlatcol
  The name of the column containing degrees of latitude as a floating-point
  number, positive for North, negative for South. If there's a column named
  "latitude" with values like 38.313313, the value for dlatcol would be
  latitude.

dloncol
  The name of the column containing degrees of longitude as a floating-point
  number, positive for East, negative for South. If there's a column named
  "longitude" with values like -122.313313, the value for dloncol would be
  latitude.

dllcol
  The name of a column containing both degrees of latitude and longitude as
  floating point numbers, embedded in a string. For example, some Socrata
  data has a "Location 1" column that contains a location like this:
    4200 Farm Hill Blvd
    Redwood City, CA 94061
    (37.447061, -122.260384)

dllre
  A Python regular expression with named captures for extracting the
  degrees latiude and degrees longitude from the dllcol.  Use dlat
  for degrees latitude and dlon for degrees longitude. For example:
    ^(?P<address>.*)\n[(](?P<dlat>[-0-9.]+), ?(?P<dlon>[-0-9.]+)[)]$

encoding
  The encoding name of the data file, like 'latin1' or 'uft-8'.

maxskippct
  The maximum percentage of the rows allowed to have missing location 
  information. Rows with missing latitude or longitude will be skipped,
  and this setting controls how much of that is OK. Use values from 0..99;
  skipping 100% of a file is never OK. Default is 0.
  
Either dlatcol and dloncol must be given, or dllcol and dllre must be
given.


## Key File Columns Section

The per-column settings are a series of rows, where column A contains
a descriptive key, and columns B... contain information about the columns
in the original CSV file. 


Required rows:

csv_header
  The row (column B...) contains the column headers for the CSV
  file, and must match those column names exactly.  This should be
  the first row of the per-column section, which makes reading the
  file easier.

identifier
  The row contains the identifier to use in the GeoJSON or ESRI
  shapefile.  It should be the second row of the per-column section.
  Identifiers must start with a letter, and contain only
  letters, numbers or underscores --- no spaces or punctuation!
  Additionally, identifiers must be 1-10 characters long, as ESRI
  shapefiles cannot handle longer names. Leave the cell blank for
  CVS columns that should not be copied into the output
  shapefile/GeoJSON file.

datatype
  The row contains the type of the data. Must be one of string,
  integer or real. Leave the cell blank for CVS columns that should
  not be copied into the output shapefile/GeoJSON file.


Recommended rows:

shortname:<language>
  This row contains a short name for the column in language <language>.

description:<language>
  This row contains a short description name for the column in 
  language <language>.


Columns in the data that are not listed in the file are ignored.

Identifiers 'dlat' and 'dlon' are reserved for the latitude and longitude,
and should not be used for anything else. To include dlat and dlon as
properties, rather than just geometry, add them to the list of columns
(perhaps without a column heading, if they come from a regular expression
parsed from dllcol).

If a dllre regular expression has additional named captures, those
could also be included in the output. List the capture as an identifier
in the file, and provide the data type.


An example of a column section:

  csv_header        XYZ Code   Unit Number   Max Tons     Place
  identifier                   unit_num      max_weight   city      dlat   dlon
  datatype                     integer       real         string    real   real
  shortname:English            Unit Number   Max Weight   City      Lat    Long

Here the XYZ Code column is ignored, and the latitude and longitude values
will appear in the properties for each feature.


# Potential Problems

## CSV vs "CSV for Excel" on the Open San Mateo Data Portal

The Open San Mateo data portal has a lot of data files that are good
candidates for converting. But always grab those files as "CSV" and
never as "CSV for Excel."

### Why

If you ask for the data as a "CSV for Excel" file, you'll end up with
a "byte order mark" as the first 16 bits of the first column
heading. That will cause errors in processing, with messages like
this:

"Expected header column 'Name' not present in data file."

In this example, the column in the file isn't actually "Name", it's
"<bom>Name" where <bom> is the byte-order-mark. Since some spreadsheet
applications strip off the <bom>, this can be pretty confusing. If you
see a message like this, check the data file in a text editor.


# Tests

There are some unit tests and functional tests in the files marked 
test_*.py.


