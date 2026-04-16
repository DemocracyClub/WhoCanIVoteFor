import vcr

# Query params added for time-limited pilot features. VCR's
# filter_query_parameters strips listed flags from requests
# before matching against cassettes, so we don't need to
# re-record every cassette for the new include_2026_pilots flag.
vcr.default_vcr.filter_query_parameters = (
    *vcr.default_vcr.filter_query_parameters,
    "include_2026_pilots",
)
