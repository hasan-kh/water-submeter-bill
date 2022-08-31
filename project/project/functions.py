import datetime
from django.utils import timezone
import jdatetime


months_fa = ['', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']


def convert_to_jalali_date(my_date: datetime.date) -> jdatetime.date:
    return jdatetime.date.fromgregorian(date=my_date)

def convert_to_jalali_datetime(my_datetime: datetime.datetime) -> jdatetime.datetime:
    return jdatetime.datetime.fromgregorian(datetime=timezone.localtime(my_datetime))

def date_farsi_month_name(my_date: datetime.date | jdatetime.date) -> str:
    if not isinstance(my_date, jdatetime.date):
        my_date = convert_to_jalali_date(my_date)

    return '%(day)d %(month)s %(year)d' % {
        'day': my_date.day,
        'month': months_fa[my_date.month],
        'year': my_date.year,
        }

def datetime_farsi_month_name(my_datetime: datetime.datetime | jdatetime.datetime) -> str:
    if not isinstance(my_datetime, jdatetime.datetime):
        my_datetime = convert_to_jalali_datetime(my_datetime)
    return '%(day)d %(month)s %(year)d - %(hour)d:%(minute)d' % {
        'day': my_datetime.day,
        'month': months_fa[my_datetime.month],
        'year': my_datetime.year,
        'hour': my_datetime.hour,
        'minute': my_datetime.minute,
        }


