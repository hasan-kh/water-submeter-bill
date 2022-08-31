import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from building.models import Building, Usage, UnitUsage

import jdatetime
from freezegun import freeze_time


frozen_utc_datetime_str = "2022-08-29 11:05:55"
frozen_jalali_datetime = jdatetime.datetime(1401, 6, 7, 15, 35, 55)
tehran_offset = datetime.timedelta(hours=4, minutes=30)


class TestBuildingModel(TestCase):

    @freeze_time(frozen_utc_datetime_str, tz_offset=tehran_offset)
    def setUp(self) -> None:
        self.building = Building.objects.create(name='H2', units=16)

    def test_building_creation(self) -> None:
        self.assertEqual(self.building.name, 'H2')
        self.assertEqual(self.building.units, 16)

        # Test created datetime
        self.assertEqual(self.building.created, frozen_jalali_datetime)

    def test_building_creation_invalid_units(self) -> None:
        name = 'sample'
        units_list = [0, 1]
        for units in units_list:
            with self.subTest(units=units):
                with self.assertRaises(ValidationError):
                    b = Building(name=name, units=units)
                    b.full_clean()

    def test_created_jalali_humanize_property(self) -> None:
        self.assertEqual(self.building.created_jalali_humanize, '7 شهریور 1401 - 15:35')

    def test_str_magic_method(self):
        self.assertEqual(str(self.building), 'H2')


class TestUsageModel(TestCase):

    @freeze_time(frozen_utc_datetime_str, tz_offset=tehran_offset)
    def setUp(self) -> None:
        self.building = Building.objects.create(name='G1', units=4)
        self.my_register_date = jdatetime.date(1401, 11, 23)
        self.month7_usage = Usage.objects.create(building_obj=self.building,
                                                 register_date=self.my_register_date)

    def test_creation(self) -> None:

        # Test Usage.created & Usage.last_update
        self.assertEqual(self.month7_usage.created, frozen_jalali_datetime)
        self.assertEqual(self.month7_usage.last_update, frozen_jalali_datetime)

        # Test Usage.building & usage.register_date
        self.assertEqual(self.month7_usage.building_obj.id, self.building.id)
        self.assertEqual(self.month7_usage.register_date, self.my_register_date)

    def test_last_update_jalali_humanize_property(self) -> None:
        self.assertEqual(self.month7_usage.last_update_jalali_humanize, '7 شهریور 1401 - 15:35')

    def test_register_date_jalali_humanize_property(self) -> None:
        self.assertEqual(self.month7_usage.register_date_jalali_humanize, '23 بهمن 1401')

    def test_str_magic_method(self):
        self.assertEqual(str(self.month7_usage), '1401-11-23')


class TestUnitUsageModel(TestCase):

    def setUp(self) -> None:
        building = Building.objects.create(name='G1', units=4)
        my_register_date = jdatetime.date(1401, 11, 23)
        self.month7_usage = Usage.objects.create(building_obj=building,
                                                 register_date=my_register_date)

    def test_creation(self):
        unit_usage = UnitUsage.objects.create(usage=self.month7_usage, unit=15, amount=1250)

        self.assertEqual(unit_usage.id, 1)
        self.assertEqual(unit_usage.usage, self.month7_usage)
        self.assertEqual(unit_usage.unit, 15)
        self.assertEqual(unit_usage.amount, 1250
        )


    def test_creation_from_usage(self) -> None:

        unit_usage_objects = [
            UnitUsage(usage=self.month7_usage, unit=1, amount=1000),
            UnitUsage(usage=self.month7_usage, unit=2, amount=2000),
            UnitUsage(usage=self.month7_usage, unit=3, amount=3000),
            UnitUsage(usage=self.month7_usage, unit=4, amount=4000),
        ]
        UnitUsage.objects.bulk_create(unit_usage_objects)

        unit_four = UnitUsage.objects.last()
        self.assertEqual(unit_four.usage, self.month7_usage)
        self.assertEqual(unit_four.unit, 4)
        self.assertEqual(unit_four.amount, 4000)

    
    def test_creation_invalid_unit_amount(self):

        to_test = [
            # [unit, amount]
            # Wrong unit
            [-5, 4578421],
            [-1, 1],
            # Wrong amount
            [1, 0],
            [14, -5005],
            # Wrong usage and amount
            [-2, 0],
            [-511, -8000],

        ]

        for i in to_test:
            with self.subTest(i=i):
                with self.assertRaises(ValidationError):
                    unit_usage = UnitUsage(usage=self.month7_usage, unit=i[0], amount=i[1])
                    unit_usage.full_clean()

    def test_str_magic_method(self):
        unit_usage = UnitUsage.objects.create(usage=self.month7_usage, unit=15, amount=1250)
        self.assertEqual(str(unit_usage), '15')


# class TestUsageAndUnitUsage(TestCase):

#     def setUp(self) -> None:
#         self.building = Building.objects.create(name='G1', units=4)
#         self.my_register_date = jdatetime.date(1401, 11, 23)

#     @freeze_time(frozen_utc_datetime_str, tz_offset=tehran_offset)
#     def test_usage_creation(self) -> None:
#         month7_usage = Usage.objects.create(building_obj=self.building, register_date=self.my_register_date)

#         # Test Usage.created & Usage.last_update
#         self.assertEqual(month7_usage.created, frozen_jalali_datetime)
#         self.assertEqual(month7_usage.last_update, frozen_jalali_datetime)

#         # Test Usage.building & usage.register_date
#         self.assertEqual(month7_usage.building_obj.id, self.building.id)
#         self.assertEqual(month7_usage.register_date, self.my_register_date)

#     @freeze_time(frozen_utc_datetime_str, tz_offset=tehran_offset)
#     def test_last_update_jalali_humanize_property(self) -> None:
#         month7_usage = Usage.objects.create(building_obj=self.building, register_date=self.my_register_date)
#         self.assertEqual(month7_usage.last_update_jalali_humanize, '7 شهریور 1401 - 15:35')

#     def test_register_date_jalali_humanize_property(self) -> None:
#         month7_usage = Usage.objects.create(building_obj=self.building, register_date=self.my_register_date)
#         self.assertEqual(month7_usage.register_date_jalali_humanize, '23 بهمن 1401')

#     def test_unit_usage_creation(self) -> None:
#         # Create Usage object
#         month7_usage = Usage.objects.create(building_obj=self.building, register_date=self.my_register_date)

#         unit_usage_objects = [
#             UnitUsage(usage=month7_usage, unit=1, amount=1000),
#             UnitUsage(usage=month7_usage, unit=2, amount=2000),
#             UnitUsage(usage=month7_usage, unit=3, amount=3000),
#             UnitUsage(usage=month7_usage, unit=4, amount=4000),
#         ]
#         units = UnitUsage.objects.bulk_create(unit_usage_objects)

#         unit_four = UnitUsage.objects.get(id=4)
#         self.assertEqual(unit_four.usage, month7_usage)
#         self.assertEqual(unit_four.unit, 4)
#         self.assertEqual(unit_four.amount, 4000)

#     def test_unit_usage_creation_invalid_unit_amount(self):
#         # Create Usage object
#         month7_usage = Usage.objects.create(building_obj=self.building, register_date=self.my_register_date)

#         to_test = [
#             # [unit, amount]
#             # Wrong unit
#             [-5, 4578421],
#             [-1, 1],
#             # Wrong amount
#             [1, 0],
#             [14, -5005],
#             # Wrong usage and amount
#             [-2, 0],
#             [-511, -8000],

#         ]

#         for i in to_test:
#             with self.subTest(i=i):
#                 with self.assertRaises(ValidationError):
#                     uu = UnitUsage(usage=month7_usage, unit=i[0], amount=i[1])
#                     uu.full_clean()

