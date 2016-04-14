class UTMTrackerMiddleware(object):
    def process_request(self, request):
        def _get_value_from_req(key):
            return (key, request.GET.get(key, None))
        keys = ('utm_source', 'utm_medium', 'utm_campaign')
        utm_data = {k: v for k, v in map(_get_value_from_req, keys) if v}
        request.session['utm_data'] = utm_data
