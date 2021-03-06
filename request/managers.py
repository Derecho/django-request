import datetime, time
from urlparse import urlparse

from django.db import models
from django.contrib.auth.models import User

class RequestManager(models.Manager):
    def active_users(self, **options):
        """
        Returns a list of active users.
        
        Any arguments passed to this method will be
        given to timedelta for time filtering.
        
        Example:
        >>> Request.object.active_users(minutes=15)
        [<User: kylef>, <User: krisje8>]
        """
        
        qs = self.filter(user__isnull=False)
        
        if options:
            time = datetime.datetime.now() - datetime.timedelta(**options)
            qs = qs.filter(time__gte=time)
        
        requests = qs.select_related('user').only('user')
        
        return set([request.user for request in requests])
    
    def paths(self, unique=True, count=False, qs=None, limit=None):
        if not qs:
            qs = self.all()
        
        if count: unique = False
        
        if unique:
            paths = set([request.path for request in qs.only('path')])
        else:
            paths = [request.path for request in qs.only('path')]
        
        if count:
            path_count = {}
            for path in paths:
                path_count[path] = len([None for x in paths if path == x])
            
            paths = [(v, k) for k, v in path_count.iteritems()]
            paths.sort()
            paths.reverse()
            paths = [(k, v) for v, k in paths]
        
        if limit:
            paths = paths[:limit]
        
        return paths
    
    def referrers(self, unique=True, count=False, qs=None, limit=None):
        # There is a slight misspelling here, referer should be referrer,
        # but even the http headers misspell it so I'll leave it here.
        if not qs:
            qs = self.all()
        
        if count: unique = False
        
        if unique:
            referers = set([request.referer for request in qs.only('referer')])
        else:
            referers = [request.referer for request in qs.only('referer')]
        
        if count:
            referer_count = {}
            for referer in referers:
                referer_count[referer] = len([None for x in referers if referer == x])
            
            referers = [(v, k) for k, v in referer_count.iteritems()]
            referers.sort()
            referers.reverse()
            referers = [(k, v) for v, k in referers]
        
        if limit:
            referers = referers[:limit]
        
        return referers
    
    def keywords(self, unique=True, count=False, qs=None, limit=None):
        # Currently supported search engines:
        # - Google
        
        # We will narrow down the queryset with referrers from supported search engines only
        if not qs:
            qs = self.all()
        qs = qs.filter(referer__startswith='http://google')|qs.filter(referer__startswith='http://www.google')
        
        # Now get the a list of the 'top referrers' for those
        urls = self.referrers(unique, count, qs, limit)
        
        # Parse the keywords in the urls
        searchengine = None
        keywords = []
        
        if count:
            for k, v in urls:
                # Determine search engine
                if len(k) > 18:
                    if k[:13] == "http://google" or k[:17] == "http://www.google":
                        searchengine = "Google"
                elif len(k) > 14:
                    if k[:13] == "http://google":
                        searchengine = "Google"
                
                # Get keywords
                if searchengine == "Google":
                    k = dict([part.split('=',1) for part in urlparse(k)[4].split('&')])['q'].replace('+', ' ')
                    keywords.append((v, k))
            keywords.sort()
            keywords.reverse()
            keywords = [(k, v) for v, k in keywords]
            
        else:
            for url in urls:
                # Determine search engine
                if len(url) > 18:
                    if url[:13] == "http://google" or url[:17] == "http://www.google":
                        searchengine = "Google"
                elif len(url) > 14:
                    if url[:13] == "http://google":
                        searchengine = "Google"
                
                # Get keywords
                if searchengine == "Google":
                    url = dict([part.split('=',1) for part in urlparse(url)[4].split('&')])['q'].replace('+', ' ')
                    keywords.append(url)
        
        return keywords
    
    def year(self, year):
        return self.filter(time__year=year)
    
    def month(self, year=None, month=None, month_format='%b', date=None):
        if not date:
            try:
                if year and month:
                    date = datetime.date(*time.strptime(year+month, '%Y'+month_format)[:3])
                else:
                    raise TypeError, 'Request.objects.month() takes exactly 2 arguments'
            except ValueError:
                return
        
        # Calculate first and last day of month, for use in a date-range lookup.
        first_day = date.replace(day=1)
        if first_day.month == 12:
            last_day = first_day.replace(year=first_day.year + 1, month=1)
        else:
            last_day = first_day.replace(month=first_day.month + 1)
        
        lookup_kwargs = {
            'time__gte': first_day,
            'time__lt': last_day,
        }
        
        return self.filter(**lookup_kwargs)
    
    def week(self, year, week):
        try:
            date = datetime.date(*time.strptime(year+'-0-'+week, '%Y-%w-%U')[:3])
        except ValueError:
            return
        
        # Calculate first and last day of week, for use in a date-range lookup.
        first_day = date
        last_day = date + datetime.timedelta(days=7)
        lookup_kwargs = {
            'time__gte': first_day,
            'time__lt': last_day,
        }
        
        return self.filter(**lookup_kwargs)
    
    def day(self, year=None, month=None, day=None, month_format='%b', day_format='%d', date=None):
        if not date:
            try:
                if year and month and day:
                    date = datetime.datetime.date(*time.strptime(year+month+day, '%Y'+month_format+day_format)[:3])
                else:
                    raise TypeError, 'Request.objects.day() takes exactly 3 arguments'
            except ValueError:
                return
        
        return self.filter(time__range=(datetime.datetime.combine(date, datetime.time.min), datetime.datetime.combine(date, datetime.time.max)))
    
    def today(self):
        return self.day(date=datetime.date.today())
    
    def this_year(self):
        return self.year(datetime.datetime.now().year)
    
    def this_month(self):
        return self.month(date=datetime.date.today())
    
    def this_week(self):
        today = datetime.date.today()
        return self.week(str(today.year), str(today.isocalendar()[1]-1))
