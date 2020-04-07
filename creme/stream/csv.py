import csv
import datetime as dt
import os
import random

from . import utils


class DictReader(csv.DictReader):
    """Overlay on top of `csv.DictReader` which allows sampling."""

    def __init__(self, fraction, rng, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fraction = fraction
        self.rng = rng

    def __next__(self):

        if self.line_num == 0:
            self.fieldnames

        row = next(self.reader)

        if self.fraction < 1:
            while self.rng.random() > self.fraction:
                row = next(self.reader)

        return dict(zip(self.fieldnames, row))


def iter_csv(filepath_or_buffer, target_name=None, converters=None, parse_dates=None, drop=None,
             fraction=1., compression='infer', seed=None, field_size_limit=None, **kwargs):
    """Yields rows from a CSV file.

    Parameters:
        filepath_or_buffer: Either a string indicating the location of a CSV file, or a buffer
            object that has a ``read`` method.
        target_name (str): The name of the target.
        converters (dict): A `dict` mapping feature names to callables used to parse their
            associated values.
        parse_dates (dict): A `dict` mapping feature names to a format passed to the
            `datetime.datetime.strptime` method.
        drop (list): Fields to ignore.
        fraction (float): Sampling fraction.
        compression (str): For on-the-fly decompression of on-disk data. If 'infer' and
            ``filepath_or_buffer`` is path-like, then the decompression method is inferred for the
            following extensions: '.gz', '.zip'.
        seed (int): If specified, the sampling will be deterministic.
        field_size_limit (int): If not `None`, this will passed to the `csv.field_size_limit`
            function.

    All other arguments are passed to the underlying `csv.DictReader`.

    Yields:
        tuple: A pair (``x``, ``y``) where ``x`` is a dict of features and ``y`` is the target.

    Example:

        ::

            Although this function is designed to handle different kinds of inputs, the most common
            use case is to read a file on the disk. We'll first create a little CSV file to
            illustrate.

            >>> tv_shows = '''name,year,rating
            ... Planet Earth II,2016,9.5
            ... Planet Earth,2006,9.4
            ... Band of Brothers,2001,9.4
            ... Breaking Bad,2008,9.4
            ... Chernobyl,2019,9.4
            ... '''
            >>> with open('tv_shows.csv', mode='w') as f:
            ...     _ = f.write(tv_shows)

            We can now go through the rows one by one.

            >>> from creme import stream

            >>> params = {
            ...     'converters': {'rating': float},
            ...     'parse_dates': {'year': '%Y'}
            ... }
            >>> for x, y in stream.iter_csv('tv_shows.csv', **params):
            ...     print(x, y)
            {'name': 'Planet Earth II', 'year': datetime.datetime(2016, 1, 1, 0, 0), 'rating': 9.5} None
            {'name': 'Planet Earth', 'year': datetime.datetime(2006, 1, 1, 0, 0), 'rating': 9.4} None
            {'name': 'Band of Brothers', 'year': datetime.datetime(2001, 1, 1, 0, 0), 'rating': 9.4} None
            {'name': 'Breaking Bad', 'year': datetime.datetime(2008, 1, 1, 0, 0), 'rating': 9.4} None
            {'name': 'Chernobyl', 'year': datetime.datetime(2019, 1, 1, 0, 0), 'rating': 9.4} None

            The value ``y`` is always ``None`` because we haven't provided a value for the
            ``target_name`` parameter. Here is an example where a ``target_name`` is provided:

            >>> for x, y in stream.iter_csv('tv_shows.csv', target_name='rating', **params):
            ...     print(x, y)
            {'name': 'Planet Earth II', 'year': datetime.datetime(2016, 1, 1, 0, 0)} 9.5
            {'name': 'Planet Earth', 'year': datetime.datetime(2006, 1, 1, 0, 0)} 9.4
            {'name': 'Band of Brothers', 'year': datetime.datetime(2001, 1, 1, 0, 0)} 9.4
            {'name': 'Breaking Bad', 'year': datetime.datetime(2008, 1, 1, 0, 0)} 9.4
            {'name': 'Chernobyl', 'year': datetime.datetime(2019, 1, 1, 0, 0)} 9.4

            >>> import os; os.remove('tv_shows.csv')

    """

    # Set the field size limit
    limit = csv.field_size_limit()
    if field_size_limit is not None:
        csv.field_size_limit(field_size_limit)

    # If a file is not opened, then we open it
    if not hasattr(filepath_or_buffer, 'read'):
        filepath_or_buffer = utils.open_filepath(filepath_or_buffer, compression)

    for x in DictReader(
        fraction=fraction,
        rng=random.Random(seed),
        f=filepath_or_buffer,
        **kwargs
    ):

        if drop:
            for i in drop:
                del x[i]

        # Cast the values to the given types
        if converters is not None:
            for i, t in converters.items():
                x[i] = t(x[i])

        # Parse the dates
        if parse_dates is not None:
            for i, fmt in parse_dates.items():
                x[i] = dt.datetime.strptime(x[i], fmt)

        # Separate the target from the features
        y = x.pop(target_name, None)

        yield x, y

    # Close the file
    filepath_or_buffer.close()

    # Reset the file size limit to it's original value
    csv.field_size_limit(limit)
