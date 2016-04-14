# Converts CSV file with lat/lon into GeoJSON file.
# Intended to help folks coming to the Open San Mateo
# Code for America Brigade meetings as either a tool
# they can use directly, or a tool to crib from.
#
# Note that all CSV column names must be valid identifiers,
# which means they start with a letter and contain only letters
# numbers and underscores. For portability, column names
# should be <= 10 characters long.
#
# This tool requires Python 3.2+ and the "osgeo" package.

# Import python standard libs
import os
import os.path
import time
import csv
import argparse
import logging
import pprint

import osgeo.ogr, osgeo.osr

import parse_datatypes
import read_key


STARTTIME = time.time()
DATA_PARSE = parse_datatypes.ParseDatatype(number_NA=[''])

if not os.path.exists("logs"):
    os.mkdir("logs")

logging.basicConfig(
    filename=os.path.join("logs",__file__+time.strftime('.%Y%m%d_%H%M%S.log', time.localtime(STARTTIME))),
    format='%(asctime)s|%(levelno)d|%(levelname)s|%(filename)s|%(lineno)d|%(message)s',
    level=logging.DEBUG
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Convert a CSV file with lat/lon positions into a GeoJSON file with point data')
    parser.add_argument('--keyfile', metavar='keyfile', help='Name of a the key CSV file')
    parser.add_argument('--datafile', metavar='datafile', help='Name of the data CSV file')
    parser.add_argument('--outext', dest='outext', default='.geojson', help='Name of output format extension, either .shp (for ESRI shapefile) or .geojson')
    parser.add_argument('--kfencoding', dest='kfencoding', default='utf-8', help="Name of keyfile's CSV file encoding, if not utf-8")

    args = parser.parse_args(argv)
    return args




def process_data_row(args, kf, raw_record, line_num):
    """Reads a {header: cell} record, per the key file rules.

    Data will come back as a typle of a {identifier: typed_value} record
    and a None error message, if the record could be parsed cleanly
    and has a location.

    If the location could not be parsed, that *might* be OK -- the
    keyfile.globals['maxskippct'] allows the file to have some
    percentage of the data for having bad locations --- but we won't
    know what percentage has been skipped until we're done processing
    all the records.

    Any parsing errors for a field that isn't a location (EG, integer
    column that isn't an integer) will raise a ValueError.
    """
    # first, cleanup any leading/trailing whitespace
    for k in raw_record:
        raw_record[k] = raw_record[k].strip()

    retval = {'dlat': None, 'dlon': None}
    # If there's a regexp pattern, process that into additional
    # "cells" first
    if kf.globals['dllcol']:
        m = kf.globals['dllre'].match(raw_record.get(kf.globals['dllcol'], ''))
        if not m:
            msg = "CSV row {line} column {c} is '{val}', which does not matches the pattern {pat}".format(
                line=line_num, c=kf.globals['dllcol'],
                val=raw_record.get(kf.globals['dllcol']),
                pat=kf.globals['dllre'].pattern)
            return (None, msg)

        # Put dlat and dlon into the results, if they're present
        try:
            retval['dlat'] = DATA_PARSE.real(m.group('dlat'))
            retval['dlon'] = DATA_PARSE.real(m.group('dlon'))
        except ValueError:
            msg = "CSV row {line} column {c} is '{val}', which does not yeild a valid lat/lon with pattern {pat}".format(
                line=line_num, c=kf.globals['dllcol'],
                val=raw_record.get(kf.globals['dllcol']),
                pat=kf.globals['dllre'].pattern)
            return (None, msg)

        # OK, parsed... But now check for None values.
        if retval['dlat'] is None or retval['dlon'] is None:
            msg = "CSV row {line} column {c} is '{val}', which yeilds a blank lat/lon with pattern {pat}".format(
                line=line_num, c=kf.globals['dllcol'],
                val=raw_record.get(kf.globals['dllcol']),
                pat=kf.globals['dllre'].pattern)
            return (None, msg)

        # Handle any other identifiers parsed out of the column.
        for k in m.groupdict():
            if k not in ['dlat','dlon']:
                if k in kf.ids:
                    try:
                        retval[k] = DATA_PARSE.typed_val(kf.ids[k]['datatype'], m.group(k))
                    except ValueError:
                        msg = "CSV row {line} column {c} is '{val}', which does not yeild a valid {k} of {datatype} with pattern {pat}".format(
                            line=line_num, c=kf.globals['dllcol'],
                            val=raw_record.get(kf.globals['dllcol'], ''),
                            k=k, datatype=kf.ids[k]['datatype'],
                            pat=kf.globals['dllre'].pattern)
                        raise ValueError(msg)
    else:
        try:
            retval['dlat'] = DATA_PARSE.real(raw_record.get(kf.globals['dlatcol']))
            retval['dlon'] = DATA_PARSE.real(raw_record.get(kf.globals['dloncol']))
        except ValueError:
            msg = "CSV row {line} columns {dlatcol} and {dloncol} are '{dlatval}' and '{dlonval}', which does not yeild a valid lat/lon".format(
                line=line_num,
                dlatcol=kf.globals['dlatcol'],
                dloncol=kf.globals['dlatcol'],
                dlatval=raw_record.get(kf.globals['dlatcol'], ''),
                dlonval=raw_record.get(kf.globals['dloncol'], ''))
            return (None, msg)

        # Now check for None values...
        if retval['dlat'] is None or retval['dlon'] is None:
            msg = "CSV row {line} columns {dlatcol} and {dloncol} are '{dlatval}' and '{dlonval}', which does not yeild a valid lat/lon".format(
                line=line_num,
                dlatcol=kf.globals['dlatcol'],
                dloncol=kf.globals['dlatcol'],
                dlatval=raw_record.get(kf.globals['dlatcol']),
                dlonval=raw_record.get(kf.globals['dloncol']))
            return (None, msg)

    for id in kf.ids:
        if id not in ['dlat','dlon']:
            hdr = kf.ids[id]['csv_header']
            if hdr != '':
                try:
                    retval[id] = DATA_PARSE.typed_val(kf.ids[id]['datatype'], raw_record.get(hdr))
                except ValueError:
                    msg = "CSV row {line} column {c} is '{val}', which does not yeild a valid {datatype}.".format(
                        line=line_num, c=hdr,
                        val=raw_record.get(hdr, ''),
                        datatype=kf.ids[id]['datatype'])
                    raise ValueError(msg)

    return (retval, None)


def check_cols(args, kf):
    """Check that the file can be processed by the rules
    in the key file.

    Return the string columns and their widths.
    """
    str_col_widths = {k:0 for k in kf.ids if kf.ids[k]['datatype'] == 'string'}
    skipped_count = 0
    row_count = 0
    skipped_msgs = []
    with open(args.datafile, encoding=kf.globals['encoding'], newline='') as fp:
        reader = csv.reader(fp)
        header = next(reader)

        # Confirm header has the expected columns
        for h in kf.hdr_to_id:
            if h not in header:
                msg = "Expected header column '{h}' not present in data file.".format(h=h)
                raise ValueError(msg)

        # OK, now look at every row to confirm int & real values are ints or reals.
        # And that every row has a lat and a lon.
        # And build up the string widths while we're here.
        for row in reader:
            raw_record = dict(zip(header, row))
            row_count += 1

            # Process the row.
            # This will raise a value error for most 'unparseable' data types
            # or return a skipped_msg if the row has no lat/lon
            (record, skipped_msg) = process_data_row(args, kf, raw_record, reader.line_num)
            if skipped_msg is not None:
                skipped_msgs.append(skipped_msg)
                skipped_count += 1
                continue

            for sc in str_col_widths:
                 str_col_widths[sc] = max(str_col_widths[sc], len(record.get(sc, '')))

    logging.info("Have {rows} rows, {skipped} of which are skipped".format(rows=row_count, skipped=skipped_count))
    for m in skipped_msgs:
        logging.info("  "+m)

    if (100.0*skipped_count/row_count) > kf.globals['maxskippct']:
        raise RuntimeError("Skipped {skipped} of {rows} rows for missing position, which is more than the {pct} percent threshold".format(
            skipped=skipped_count, rows=row_count, pct=kf.globals['maxskippct']))

    return str_col_widths


def make_output(datafile, outext, epsg_code):
    """Make the output shapefile or geojson data source.
    Will need to add columns to this, but it will create
    the basics.

    datafile is the base name --- any extension will be stripped off and replaced with outext
    outext is the output format extension, one of .shp or .GeoJSON
    epsg_code is the integer EPSG projection code
    """
    # Pick an output driver. Popular choices would be "GeoJSON" or "ESRI Shapefile"
    driver_name = {'.geojson': 'GeoJSON',
                   '.GeoJSON': 'GeoJSON',
                   '.shp': 'ESRI Shapefile'}[outext]
    (fileroot, fileext) = os.path.splitext(datafile)

    output_driver = osgeo.ogr.GetDriverByName(driver_name)
    if os.path.exists(fileroot+outext):
        output_driver.DeleteDataSource(fileroot+outext)
    data_src = output_driver.CreateDataSource(fileroot+outext)

    srs = osgeo.osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)

    # Make a point layer
    layer = data_src.CreateLayer(os.path.basename(fileroot), srs, osgeo.ogr.wkbPoint)

    return (data_src, layer)


def add_schema(layer, ids, str_col_widths):
    """OK, add the schema to the layer.

    layer is the layer to update
    identifiers is a dictionary of {identifier:{'datatype': val}}
    str_col_widths is a dictionary of {identifiers: width}
    """
    for c in ids:
        if ids[c]['datatype'] == 'integer':
            layer.CreateField(osgeo.ogr.FieldDefn(c, osgeo.ogr.OFTInteger))
        elif ids[c]['datatype'] == 'real':
            layer.CreateField(osgeo.ogr.FieldDefn(c, osgeo.ogr.OFTReal))
        elif ids[c]['datatype'] == 'string':
            field = osgeo.ogr.FieldDefn(c, osgeo.ogr.OFTString)
            field.SetWidth(str_col_widths[c]+5) # pad a little.
            layer.CreateField(field)
        else:
            msg = "Unrecognized data type {dt} for field {c}".format(
                dt=ids[c]['datatype'], c=c)
            raise ValueError(msg)


def add_data(layer, args, kf):
    layer_def = layer.GetLayerDefn()
    with open(args.datafile, encoding=kf.globals['encoding'], newline='') as fp:
        reader = csv.reader(fp)
        header = next(reader)

        for row in reader:
            raw_record = dict(zip(header, row))
            (record, skipped_msg) = process_data_row(args, kf, raw_record, reader.line_num)

            pprint.pprint(record)

            if record is not None:
                feature = osgeo.ogr.Feature(layer_def)

                for c in kf.ids:
                    feature.SetField(c, record[c])

                point = osgeo.ogr.Geometry(osgeo.ogr.wkbPoint)
                point.AddPoint(record['dlon'], record['dlat']) # Note it's lon,lat not lat,lon
                feature.SetGeometry(point)

                layer.CreateFeature(feature)

                feature.Destroy() # free resources


def main(argv=None):
    args = parse_args(argv)
    if args.keyfile is None:
        raise ValueError("Must supply a --keyfile")
    if not os.path.exists(args.keyfile):
        raise ValueError("The --keyfile '{filename}' does not exist".format(filename=args.keyfile))
    if args.datafile is None:
        raise ValueError("Must supply a --datafile")
    if not os.path.exists(args.datafile):
        raise ValueError("The --datafile '{filename}' does not exist".format(filename=args.datafile))


    # Do as much sanity checking as possible before making, and
    # perhaps breaking, the output. And get the string column
    # widths.
    kf = read_key.KeyFile()
    kf.read(args.keyfile, args.kfencoding)
    str_col_widths = check_cols(args, kf)

    # OK, that's all the checking we can do. Make the layer.
    (ds, layer) = make_output(args.datafile, args.outext, kf.globals['epsg_code'])
    add_schema(layer, kf.ids, str_col_widths)
    add_data(layer, args, kf)


if __name__ == '__main__':
    main()

