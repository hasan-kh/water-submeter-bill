from django.test import TestCase
from freezegun import freeze_time 
from project.functions import (datetime, jdatetime, timezone,convert_to_jalali_date, convert_to_jalali_datetime, date_farsi_month_name, datetime_farsi_month_name)


class TestFunctions(TestCase):
    def test_convert_to_jalali_date_function(self) -> None:
        my_date = datetime.date(2022, 8, 28)
        self.assertEqual(convert_to_jalali_date(my_date), jdatetime.date(1401, 6, 6))
    
    @freeze_time("2022-08-28 11:05:01")
    def test_convert_to_jalali_datetime_function(self) -> None:
        self.assertEqual(convert_to_jalali_datetime(timezone.now()),
                         jdatetime.datetime(1401, 6, 6, 15, 35, 1))
    

    def test_date_farsi_month_name_pass_jalali(self):
        jalali_date = jdatetime.datetime(1401, 6, 6)
        self.assertEqual(date_farsi_month_name(jalali_date), '6 شهریور 1401')

    def test_date_farsi_month_name_pass_gregorian(self):
        gregorian_date = datetime.date(2022, 8, 28)
        self.assertEqual(date_farsi_month_name(gregorian_date), '6 شهریور 1401')
    
    def test_datetime_farsi_month_name_pass_jalali(self):
        jalali_datetime = jdatetime.datetime(1401, 6, 6, 15, 35, 1)
        self.assertEqual(datetime_farsi_month_name(jalali_datetime), '6 شهریور 1401 - 15:35')

    @freeze_time("2022-08-28 11:05:01")
    def test_datetime_farsi_month_name_pass_gregorian(self):
        gregorian_datetime = timezone.now()
        self.assertEqual(datetime_farsi_month_name(gregorian_datetime), '6 شهریور 1401 - 15:35')
    