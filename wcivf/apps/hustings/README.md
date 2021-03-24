A husting originally referred to a native Germanic governing assembly, the thing.

By metonymy, the term may now refer to any event, such as debates or speeches,
during an election campaign where one or more of the representative candidates are present.
The term is used synonymously with stump in the United States.

**Or so says [Wikipedia](https://en.wikipedia.org/wiki/Husting)**


To load the hustings from a Google Sheet check the URLS in `import_hustings` are correct.

Then run `python manage.py import_hustings`.

You can also import hustings from a csv file by using the `--filename` flag and passing the
path to the csv file. However this will delete all existing hustings and only create those
from within the file, so be careful when using this - it is mainly intended to help with
local development.
