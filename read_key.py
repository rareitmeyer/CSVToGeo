
# Reads a CSV "key" file, which must be in UTF-8 format.
#
# The key file has two sections: a header with values that apply to the whole
# data set, and a per-column section that describes the columns in the data.
# The two sections are separated by a blank row.
#
# The header section has a simple format: column A contains names and 
# column B containing values. Keys for the header:
# 
#
# source [required]
#  The source of the data, as a filename or a http://URL.
#  
# epsg_code [required]
#   The EPSG code for the geographic projection the data uses. Data often
#   is in WGS84 coordinates (EPSG 4326), but may not be. If it's helpful,
#   The folks at SpatialReference have nice pages on projections. EG
#      http://spatialreference.org/ref/epsg/wgs-84/
#    
# dlatcol
#   The name of the column containing degrees of latitude as a floating-point
#   number, positive for North, negative for South. If there's a column named
#   "latitude" with values like 38.313313, the value for dlatcol would be
#   latitude.
#
# dloncol
#   The name of the column containing degrees of longitude as a floating-point
#   number, positive for East, negative for South. If there's a column named
#   "longitude" with values like -122.313313, the value for dloncol would be
#   latitude.
#
# dllcol
#   The name of a column containing both degrees of latitude and longitude as
#   floating point numbers, embedded in a string. For example, some Socrata
#   data has a "Location 1" column that contains a location like this:
#     4200 Farm Hill Blvd
#     Redwood City, CA 94061
#     (37.447061, -122.260384)
#
# dllre
#   A Python regular expression with named captures for extracting the
#   degrees latiude and degrees longitude from the dllcol.  Use dlat
#   for degrees latitude and dlon for degrees longitude. For example:
#     ^(?P<address>.*)\n[(](?P<dlat>[-0-9.]+), ?(?P<dlon>[-0-9.]+)[)]$
#
# encoding
#   The encoding name of the data file, like 'latin1' or 'uft-8'.
#
# maxskippct
#   The maximum percentage of the rows allowed to have missing location 
#   information. Rows with missing latitude or longitude will be skipped,
#   and this setting controls how much of that is OK. Use values from 0..99;
#   skipping 100% of a file is never OK. Default is 0.
#   
# Either dlatcol and dloncol must be given, or dllcol and dllre must be
# given.
#
#
# The per-column settings are a series of rows, where column A contains
# a descriptive key, and columns B... contain information about the columns
# in the original CSV file. 
#
# Required rows:
#
# csv_header
#   The row (column B...) contains the column headers for the CSV
#   file, and must match those column names exactly.  This must be the
#   first row of the per-column section, which makes reading the file
#   easier.
#
# identifier
#   The row contains the identifier to use in the GeoJSON or ESRI
#   shapefile.  It must be the second row of the per-column section.
#   Identifiers must start with a letter, and contain only
#   letters, numbers or underscores --- no spaces or punctuation!
#   Additionally, identifiers must be 1-10 characters long, as ESRI
#   shapefiles cannot handle longer names. Leave the cell blank for
#   CVS columns that should not be copied into the output
#   shapefile/GeoJSON file.
#
# datatype
#   The row contains the type of the data. Must be one of string,
#   integer or real. Leave the cell blank for CVS columns that should
#   not be copied into the output shapefile/GeoJSON file.
#
# shortname:<language>
#   This row contains a short name for the column in language <language>.
#
# Columns in the data that are not listed in the file are ignored.
# 
#
#
# An example of a column section:
#
#   csv_header        SWIS Code   Unit Number   Max Tons   Place
#   identifier                    unit_num      operator   city      
#   datatype                      integer       real       string    
#   shortname:English             Unit Number   Operator   City      
#
# Here the SWIS Code column is ignored.



# ################################################################
# Key data structures:
#
# globals
#   {name: value} map of the settings that apply to the whole data
#   set.
#
# hdr_to_id
#   A map of {header: identifier} names for the columns that come
#   straight from the data
#
# ids
#   A map of {identifier: {name: value}} describing the properties
#   of the identifier.

import csv
import re
import copy

import osgeo.osr


class KeyFile(object):
    def __init__(self):
        self.filename = None
        self.globals = {}
        self.hdr_to_id = {}
        self.ids = {}


    def read(self, filename, encoding='utf-8'):
        self.filename = filename

        with open(filename, encoding=encoding, newline='') as fp:
            reader = csv.reader(fp)

            self.globals = self._read_globals(reader)
            (self.hdr_to_id, self.ids) = self._read_cols(reader)


    def _read_globals(self, reader):
        expected_keys = 'source epsg_code dlatcol dloncol dllcol dllre encoding maxskippct'.split()
        retval = {}
        for row in reader:
            # strip any spaces
            for j in range(len(row)):
                row[j] = row[j].strip()
            if len(row) < 1 or row[0] == '':
                break

            # confirm the row has an expected key...
            if row[0] not in expected_keys:
                msg = "row {r} has an invalid key, '{k}'. Please use one of {ek}".format(
                    r=reader.line_num, k=row[0], ek=repr(expected_keys))
                raise ValueError(msg)

            # If row[1] is blank, skip
            if len(row) < 2 or row[1] == '':
                continue

            # clean or sanity check values as they are read, to provide 
            # row number context.
            if row[0] == 'epsg_code':
                try:
                    retval[row[0]] = int(row[1])
                except ValueError:
                    msg = "The EPSG code in row {r}, '{val}' is not an integer.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)
                try:
                    srs = osgeo.osr.SpatialReference()
                    code = srs.ImportFromEPSG(retval[row[0]])
                    if code != 0:
                        msg = "The EPSG code in row {r}, '{val}' is not recognized.".format(
                            r=reader.line_num, val=row[1])
                        raise ValueError(msg)                    
                except:
                    msg = "The EPSG code in row {r}, '{val}' is not recognized.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)                    
            elif row[0] == 'maxskippct':
                try:
                    retval[row[0]] = float(row[1])
                except ValueError:
                    msg = "The max skip percentage row {r}, '{val}' is not a number.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)
                if retval[row[0]] < 0 or retval[row[0]] > 99:
                    msg = "The max skip percentage row {r}, '{val}' is not between 0 and 99.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)
            elif row[0] == 'dllre':
                try:
                    retval[row[0]] = re.compile(row[1], flags=re.DOTALL)
                except:
                    msg = "The dllre regular expression in row {r}, '{val}' does not compile.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)
                if 'dlat' not in retval[row[0]].groupindex:
                    msg = "The dllre regular expression in row {r}, '{val}' does not have a capture for dlat.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)
                if 'dlon' not in retval[row[0]].groupindex:
                    msg = "The dllre regular expression in row {r}, '{val}' does not have a capture for dlon.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)
            elif row[0] == 'encoding':
                try:
                    'A'.encode(row[1])
                    retval[row[0]] = row[1]
                except LookupError:
                    msg = "The encoding in row {r}, '{val}' is not valid.".format(
                        r=reader.line_num, val=row[1])
                    raise ValueError(msg)
            else:
                retval[row[0]] = row[1]

        # OK, now set defaults and sanity check the set as a whole
        if 'encoding' not in retval:
            retval['encoding'] = 'utf-8'
        if 'maxskippct' not in retval:
            retval['maxskippct'] = 0.0
        if 'epsg_code' not in retval:
            msg = "Required epsg_code is missing"
            raise ValueError(msg)
        if 'dlatcol' in retval and 'dloncol' not in retval:
            msg = "If dlatcol is present, dloncol is required"
            raise ValueError(msg)
        if 'dloncol' in retval and 'dlatcol' not in retval:
            msg = "If dloncol is present, dlatcol is required"
            raise ValueError(msg)
        if 'dllcol' in retval and 'dllre' not in retval:
            msg = "If dllcol is present, dllre is required"
            raise ValueError(msg)
        if 'dllcol' in retval and 'dlatcol' in retval:
            msg = "Only one of (dlatcol,dloncol) or (dllcol,dllre) may be specified"
            raise ValueError(msg)
            
        return retval


    def _read_cols(self, reader):
        hdr_to_id = {}
        ids = {}

        colgrid = []
        name_line = {}
        blanks = 0
        for recno, row in enumerate(reader):
            # strip any spaces and ignore any all-blank rows.
            allblank = True
            for j in range(len(row)):
                row[j] = row[j].strip()
                if row[j] != '':
                    allblank = False            
            if allblank:
                blanks += 1
                continue
                
            # save the line number for each row for error reporting
            name_line[row[0]] = reader.line_num

            # pad the columnn grid as needed
            missing_cols = len(row) - len(colgrid)
            for j in range(missing_cols):
                blank_col = (recno-blanks)*['']
                colgrid.append(blank_col)
            
            for j in range(len(row)):
                colgrid[j].append(row[j])
            for j in range(len(row),len(colgrid)):
                colgrid[j].append('')
                
        # Confirm the minimum pieces are available before assembling
        if 'csv_header' not in name_line:
            msg = 'Required field csv_header is missing'
            raise ValueError(msg)
        if 'identifier' not in name_line:
            msg = 'Required field identifier is missing'
            raise ValueError(msg)
        if 'datatype' not in name_line:
            msg = 'Required field datatype is missing'
            raise ValueError(msg)
        
        header_grididx = colgrid[0].index('csv_header')
        identifier_grididx = colgrid[0].index('identifier')
        
        idpat = re.compile('^[a-zA-Z][_a-zA-Z0-9]+$')
        for j in range(1,len(colgrid)):
            hdr = colgrid[j][header_grididx]
            id = colgrid[j][identifier_grididx]

            if hdr != '' and id != '':
                hdr_to_id[hdr] = id

            if id != '':
                if idpat.match(id) is None:
                    msg = "At row {row}, the identifier for column {hdr}, '{id}' is not valid. Identifiers must start with a letter, and contain only letters, numbers and underscores.".format(row=name_line['identifier'], hdr=hdr, id=id)
                    raise ValueError(msg)
                if len(id) > 10:
                    msg = "At row {row}, the identifier for column {hdr}, '{id}' is longer than 10 characters. This is too long for a ESRI shapefile.".format(row=name_line['identifier'], hdr=hdr, id=id)
                    logging.warn(msg)
    
                ids[id] = {}

        # OK, now fill in the ids.
        for j in range(1,len(colgrid)):
            id = colgrid[j][identifier_grididx]
            if id != '':
                for i in range(len(colgrid[j])):
                    ids[id][colgrid[0][i]] = colgrid[j][i]
                    
        # check each ID
        for id in ids:
            if id != '':
                if ids[id]['datatype'] == '':
                    msg = "Data type for identifier {id} cannot be blank".format(
                        id=id)
                    raise ValueError(msg)
                if ids[id]['datatype'] not in ['string', 'real', 'integer']:
                    msg = "Data type for identifier {id} is '{val}' but must be one of string, real or integer".format(
                        id=id, val=ids[id]['datatype'])
                    raise ValueError(msg)

        return (hdr_to_id, ids)

        
