from django.db.models import Transform


class LastWord(Transform):
    """
    Split a field on space and get the last element
    """

    function = "LastWord"
    template = """
    (regexp_split_to_array(%(field)s, ' '))[
      array_upper(regexp_split_to_array(%(field)s, ' '), 1)
    ]
    """

    def __init__(self, column, output_field=None):
        super(LastWord, self).__init__(column, output_field=output_field)

    def as_postgresql(self, compiler, connection):
        return self.as_sql(compiler, connection)
