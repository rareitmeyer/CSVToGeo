# Basic 'parse this value' class.

class ParseDatatype(object):
    """Handles converting strings to other data types, with NA rules.
    Strings and numbers can have different NA rules: it's possible to
    decide '' or 'NA' as a number should be None, but '' or 'NA' as a
    string should remain '' or 'NA'.
    """
    def __init__(self, number_NA=None, string_NA=None):
        self.reset_number_NA(number_NA)
        self.reset_string_NA(string_NA)


    def reset_number_NA(self, number_NA=None):
        if number_NA is None:
            number_NA = []
        self.number_NA = number_NA


    def reset_string_NA(self, string_NA=None):
        if string_NA is None:
            string_NA = []
        self.string_NA = string_NA


    def integer(self, val):
        if val is None or val in self.number_NA:
            return None
        else:
            return int(val)
    int = integer


    def real(self, val):
        if val is None or val in self.number_NA:
            return None
        else:
            return float(val)
    float = real


    def string(self, val):
        if val is None or val in self.string_NA:
            return None
        else:
            return str(val)
    str = string


    def typed_val(self, typename, val):
        if typename == 'string':
            return self.string(val)
        elif typename == 'real':
            return self.real(val)
        elif typename == 'integer':
            return self.int(val)
        else:
            raise ValueError("Unknown type {typename}".format(typename=typename))

