from datetime import datetime


def register_filters(app):
    @app.template_filter('format_date')
    def format_date(value):
        if not value: return ''
        for fmt in ('%Y-%m-%d', '%Y-%m'):
            try: return datetime.strptime(value, fmt).strftime('%m/%Y')
            except ValueError: pass
        return value

    @app.template_filter('format_date_full')
    def format_date_full(value):
        if not value: return ''
        try: return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError: return value

    @app.template_filter('format_year')
    def format_year(value):
        if not value: return ''
        for fmt in ('%Y-%m-%d', '%Y-%m'):
            try: return datetime.strptime(value, fmt).strftime('%Y')
            except ValueError: pass
        return value