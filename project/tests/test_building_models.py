import datetime
from math import ceil

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.conf import settings

from building.models import Building, Debt, Usage, UnitUsage, WaterBill, GasBill, SubmeterCalculator, ExtraCharge, Result, UnitResult
from building.functions import round_price, get_price_over_14_m3

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

    def test_str_magic_method(self) -> None:
        self.assertEqual(str(self.building), 'H2')


class TestUsageModel(TestCase):

    @freeze_time(frozen_utc_datetime_str, tz_offset=tehran_offset)
    def setUp(self) -> None:
        self.building = Building.objects.create(name='G1', units=4)
        self.my_register_date = jdatetime.date(1401, 11, 23)
        self.month7_usage = Usage.objects.create(building=self.building,
                                                 register_date=self.my_register_date)

    def test_creation(self) -> None:

        # Test Usage.created & Usage.last_update
        self.assertEqual(self.month7_usage.created, frozen_jalali_datetime)
        self.assertEqual(self.month7_usage.last_update, frozen_jalali_datetime)

        # Test Usage.building & usage.register_date
        self.assertEqual(self.month7_usage.building.id, self.building.id)
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
        self.month7_usage = Usage.objects.create(building=building,
                                                 register_date=my_register_date)

    def test_creation(self) -> None:
        unit_usage = UnitUsage.objects.create(usage=self.month7_usage, unit=15, amount=1250)

        # self.assertEqual(unit_usage.id, 1)
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

    
    def test_creation_invalid_unit_amount(self) -> None:

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

    def test_str_magic_method(self) -> None:
        unit_usage = UnitUsage.objects.create(usage=self.month7_usage, unit=15, amount=1250)
        self.assertEqual(str(unit_usage), '15')


class TestWaterBill(TestCase):

    jalali_date = jdatetime.date(1399, 12, 1)
    jalali_date_month_name = '1 اسفند 1399'

    def setUp(self) -> None:
        self.building = Building.objects.create(name='H2', units=16)
        self.water_bill = WaterBill.objects.create(building=self.building,
                                                   issuance_date=self.jalali_date,
                                                   current_reading=self.jalali_date, 
                                                   payment_deadline=self.jalali_date,
                                                   water_consumption_price=450000,
                                                   total_payment=1250000)

    def test_creation(self) -> None:
        self.assertEqual(self.water_bill.building, self.building)
        self.assertEqual(self.water_bill.issuance_date, self.jalali_date)
        self.assertEqual(self.water_bill.current_reading, self.jalali_date)
        self.assertEqual(self.water_bill.payment_deadline, self.jalali_date)
        self.assertEqual(self.water_bill.water_consumption_price, 450000)
        self.assertEqual(self.water_bill.total_payment, 1250000)

    def test_invalid_water_consumption_price_and_total_price(self) -> None:
        to_test = [
            # [water_consumption_price, total_payment]

            # Wrong water_consumption_price
            [-5, 4578421],
            [0, 1],

            # Wrong total_payment
            [2500300, 0],
            [1, -5005],

            # Wrong water_consumption_price and total_payment
            [-2, -1],
            [-511, -8000],
            [0, 0],

            # total_payment not greater than water_consumption_price
            [650000, 620000],
            [650000, 650000],
            [2, 1],
        ]

        for i in to_test:
            with self.subTest(i=i):
                with self.assertRaises(ValidationError):
                    water_bill = WaterBill(building=self.building,
                                           issuance_date=self.jalali_date,
                                           current_reading=self.jalali_date, 
                                           payment_deadline=self.jalali_date,
                                           water_consumption_price=i[0],
                                           total_payment=i[1])
                    water_bill.full_clean()
    
    def test_str_magic_method(self) -> None:
        self.assertEqual(str(self.water_bill), '{} | {} | {:,}T'.format(self.water_bill.building, str(self.water_bill.issuance_date), self.water_bill.total_payment))

    def test_humanize_date_properties(self) -> None:
        self.assertEqual(self.water_bill.issuance_date_jalali_humanize, self.jalali_date_month_name)
        self.assertEqual(self.water_bill.current_reading_jalali_humanize, self.jalali_date_month_name)
        self.assertEqual(self.water_bill.payment_deadline_jalali_humanize, self.jalali_date_month_name)

    def test_tax_property(self) -> None:
        self.assertEqual(self.water_bill.tax, 800000)

    def test_share_of_tax_for_each_unit_property(self) -> None:
        self.assertEqual(round_price(ceil(self.water_bill.tax / self.water_bill.building.units)), 50000)


class TestGasBill(TestCase):

    jalali_date = jdatetime.date(1399, 12, 1)
    jalali_date_month_name = '1 اسفند 1399'

    def setUp(self) -> None:
        self.building = Building.objects.create(name='H2', units=16)
        self.gas_bill = GasBill.objects.create(building=self.building,
                                               issuance_date=self.jalali_date,
                                               current_reading=self.jalali_date, 
                                               payment_deadline=self.jalali_date,
                                               total_payment=339300)

    def test_creation(self) -> None:
        self.assertEqual(self.gas_bill.building, self.building)
        self.assertEqual(self.gas_bill.issuance_date, self.jalali_date)
        self.assertEqual(self.gas_bill.current_reading, self.jalali_date)
        self.assertEqual(self.gas_bill.payment_deadline, self.jalali_date)
        self.assertEqual(self.gas_bill.total_payment, 339300)

    def test_invalid_total_price(self) -> None:
        to_test = [-500, -1, 0]

        for i in to_test:
            with self.subTest(i=i):
                with self.assertRaises(ValidationError):
                    gas_bill = GasBill(building=self.building,
                                       issuance_date=self.jalali_date,
                                       current_reading=self.jalali_date, 
                                       payment_deadline=self.jalali_date,
                                       total_payment=i)
                    gas_bill.full_clean()

    def test_str_magic_method(self) -> None:
        self.assertEqual(str(self.gas_bill), '{} | {} | {:,}T'.format(self.gas_bill.building, str(self.gas_bill.issuance_date), self.gas_bill.total_payment))

    def test_humanize_date_properties(self) -> None:
        self.assertEqual(self.gas_bill.issuance_date_jalali_humanize, self.jalali_date_month_name)
        self.assertEqual(self.gas_bill.current_reading_jalali_humanize, self.jalali_date_month_name)
        self.assertEqual(self.gas_bill.payment_deadline_jalali_humanize, self.jalali_date_month_name)

    def test_share_of_price_for_each_unit_property(self):
        self.assertEqual(round_price(ceil(self.gas_bill.total_payment / self.gas_bill.building.units)), 21200)


class SubmeterCalculatorTest(TestCase):

    jalali_date = jdatetime.date(1399, 12, 1)
    jalali_date_month_name = '1 اسفند 1399'

    pre_usage_jdate = jdatetime.date(1401, 4, 10)
    cur_usage_jdate = jdatetime.date(1401, 5, 19)

    def setUp(self) -> None:

        self.building = Building.objects.create(name='H2', units=16)

        self.pre_usage = Usage.objects.create(building=self.building,
                                              register_date=self.pre_usage_jdate)
        self.cur_usage = Usage.objects.create(building=self.building,
                                              register_date=self.cur_usage_jdate)

        unit_usage_objects = [
            # for previous usage
            UnitUsage(usage=self.pre_usage, unit=1, amount=4275339),
            UnitUsage(usage=self.pre_usage, unit=2, amount=3610115),
            UnitUsage(usage=self.pre_usage, unit=3, amount=5730893),
            UnitUsage(usage=self.pre_usage, unit=4, amount=4687390),
            UnitUsage(usage=self.pre_usage, unit=5, amount=4835494),
            UnitUsage(usage=self.pre_usage, unit=6, amount=2820138),
            UnitUsage(usage=self.pre_usage, unit=7, amount=4730021),
            UnitUsage(usage=self.pre_usage, unit=8, amount=3028003),
            UnitUsage(usage=self.pre_usage, unit=9, amount=2352000),
            UnitUsage(usage=self.pre_usage, unit=10, amount=2214141),
            UnitUsage(usage=self.pre_usage, unit=11, amount=2980811),
            UnitUsage(usage=self.pre_usage, unit=12, amount=3910585),
            UnitUsage(usage=self.pre_usage, unit=13, amount=5637601),
            UnitUsage(usage=self.pre_usage, unit=14, amount=6039332),
            UnitUsage(usage=self.pre_usage, unit=15, amount=2260429),
            UnitUsage(usage=self.pre_usage, unit=16, amount=4273001),

            # for current usage
            UnitUsage(usage=self.cur_usage, unit=1, amount=4303510),
            UnitUsage(usage=self.cur_usage, unit=2, amount=3630523),
            UnitUsage(usage=self.cur_usage, unit=3, amount=5773270),
            UnitUsage(usage=self.cur_usage, unit=4, amount=4723318),
            UnitUsage(usage=self.cur_usage, unit=5, amount=4866567),
            UnitUsage(usage=self.cur_usage, unit=6, amount=2831850),
            UnitUsage(usage=self.cur_usage, unit=7, amount=4741127),
            UnitUsage(usage=self.cur_usage, unit=8, amount=3049407),
            UnitUsage(usage=self.cur_usage, unit=9, amount=2365165),
            UnitUsage(usage=self.cur_usage, unit=10, amount=2222698),
            UnitUsage(usage=self.cur_usage, unit=11, amount=2991590),
            UnitUsage(usage=self.cur_usage, unit=12, amount=3945787),
            UnitUsage(usage=self.cur_usage, unit=13, amount=5661252),
            UnitUsage(usage=self.cur_usage, unit=14, amount=6075908),
            UnitUsage(usage=self.cur_usage, unit=15, amount=2270844),
            UnitUsage(usage=self.cur_usage, unit=16, amount=4308607),
        ]
        UnitUsage.objects.bulk_create(unit_usage_objects)
        
        self.gas_bill = GasBill.objects.create(building=self.building,
                                               issuance_date=self.jalali_date,
                                               current_reading=self.jalali_date, 
                                               payment_deadline=self.jalali_date,
                                               total_payment=339300)

        self.water_bill = WaterBill.objects.create(building=self.building,
                                                   issuance_date=self.jalali_date,
                                                   current_reading=self.jalali_date, 
                                                   payment_deadline=self.jalali_date,
                                                   water_consumption_price=695800,
                                                   total_payment=1227700)                                       
        self.sc = SubmeterCalculator.objects.create(water_bill=self.water_bill,
                                                    gas_bill=self.gas_bill,
                                                    previous_usage=self.pre_usage,
                                                    current_usage=self.cur_usage,
                                                    notes='All good !')

        extra_charges = [
                ExtraCharge(submeter_calculator=self.sc, title='charge', amount=30000, my_order=1),
                ExtraCharge(submeter_calculator=self.sc, title='maintenance', amount=50000, my_order=2),
            ]
        self.extras = ExtraCharge.objects.bulk_create(extra_charges)

        debts_objects = [
            Debt(submeter_calculator=self.sc, unit=9, amount=97500),
            Debt(submeter_calculator=self.sc, unit=1, amount=5000),
            Debt(submeter_calculator=self.sc, unit=14, amount=246200),
        ]
        self.debts = Debt.objects.bulk_create(debts_objects)

        self.result = Result.objects.create(submeter_calculator=self.sc, my_notes='This is my notes', client_notes='Notes for clint',
                                            due_date=self.jalali_date)
        
        unit_result_objects = [
            UnitResult(result=self.result, unit=1, usage_amount=8432, price=15800, debt=5000, total_payment=68000),
            UnitResult(result=self.result, unit=2, usage_amount=43500, price=98700, total_payment=24600),
        ]
        self.unit_results = UnitResult.objects.bulk_create(unit_result_objects)

    def test_creation(self) -> None:
        self.assertEqual(self.sc.water_bill, self.water_bill)
        self.assertEqual(self.sc.gas_bill, self.gas_bill)
        self.assertEqual(self.sc.previous_usage, self.pre_usage)
        self.assertEqual(self.sc.current_usage, self.cur_usage)
        self.assertEqual(self.sc.notes, 'All good !')

    def test_previous_usage_with_invalid_unit_counts(self) -> None:
        local_pre_usage = Usage.objects.create(building=self.building,
                                               register_date=self.pre_usage_jdate)
                                            
        unit_usages = [
            UnitUsage(usage=local_pre_usage, unit=1, amount=4303510),
            UnitUsage(usage=local_pre_usage, unit=2, amount=3630523),
        ]
        UnitUsage.objects.bulk_create(unit_usages)

        with self.assertRaises(ValidationError) as context_manager:
            self.sc.previous_usage = local_pre_usage
            self.sc.full_clean()

        self.assertEqual(context_manager.exception.message_dict.get('previous_usage'),
                         ['previous usage must have same unit count as building units (%d)' % self.water_bill.building.units])

    def test_current_usage_with_invalid_unit_counts(self) -> None:
        local_cur_usage = Usage.objects.create(building=self.building,
                                               register_date=self.cur_usage_jdate)

        unit_usages = [
            UnitUsage(usage=local_cur_usage, unit=1, amount=4303510),
            UnitUsage(usage=local_cur_usage, unit=2, amount=3630523),
            UnitUsage(usage=local_cur_usage, unit=3, amount=4430523),
        ]
        UnitUsage.objects.bulk_create(unit_usages)

        with self.assertRaises(ValidationError) as context_manager:
            self.sc.current_usage = local_cur_usage
            self.sc.full_clean()

        self.assertEqual(context_manager.exception.message_dict.get('current_usage'),
                         ['current usage must have same unit count as building units (%d)' % self.water_bill.building.units])

    def test_previous_usage_with_invalid_building(self) -> None:

        wrong_building = Building.objects.create(name='wrong', units=16)

        local_usage = Usage.objects.create(building=wrong_building, register_date=self.pre_usage_jdate)
        
        unit_usages = [
            UnitUsage(usage=local_usage, unit=1, amount=4275339),
            UnitUsage(usage=local_usage, unit=2, amount=3610115),
            UnitUsage(usage=local_usage, unit=3, amount=5730893),
            UnitUsage(usage=local_usage, unit=4, amount=4687390,),
            UnitUsage(usage=local_usage, unit=5, amount=4835494),
            UnitUsage(usage=local_usage, unit=6, amount=2820138),
            UnitUsage(usage=local_usage, unit=7, amount=4730021),
            UnitUsage(usage=local_usage, unit=8, amount=3028003),
            UnitUsage(usage=local_usage, unit=9, amount=2352000),
            UnitUsage(usage=local_usage, unit=10, amount=2214141),
            UnitUsage(usage=local_usage, unit=11, amount=2980811),
            UnitUsage(usage=local_usage, unit=12, amount=3910585),
            UnitUsage(usage=local_usage, unit=13, amount=5637601),
            UnitUsage(usage=local_usage, unit=14, amount=6039332),
            UnitUsage(usage=local_usage, unit=15, amount=2260429),
            UnitUsage(usage=local_usage, unit=16, amount=4273001),
        ]
        UnitUsage.objects.bulk_create(unit_usages)

        with self.assertRaises(ValidationError) as context_manager:
            self.sc.previous_usage = local_usage
            self.sc.full_clean()
        self.assertEqual(context_manager.exception.message_dict.get('previous_usage'),
                         ['previous_usage must be from same building as water_bill.building'])

    def test_current_usage_with_invalid_building(self) -> None:

        wrong_building = Building.objects.create(name='wrong', units=16)

        local_usage = Usage.objects.create(building=wrong_building, register_date=self.pre_usage_jdate)
        
        unit_usages = [
            UnitUsage(usage=local_usage, unit=1, amount=4275339),
            UnitUsage(usage=local_usage, unit=2, amount=3610115),
            UnitUsage(usage=local_usage, unit=3, amount=5730893),
            UnitUsage(usage=local_usage, unit=4, amount=4687390,),
            UnitUsage(usage=local_usage, unit=5, amount=4835494),
            UnitUsage(usage=local_usage, unit=6, amount=2820138),
            UnitUsage(usage=local_usage, unit=7, amount=4730021),
            UnitUsage(usage=local_usage, unit=8, amount=3028003),
            UnitUsage(usage=local_usage, unit=9, amount=2352000),
            UnitUsage(usage=local_usage, unit=10, amount=2214141),
            UnitUsage(usage=local_usage, unit=11, amount=2980811),
            UnitUsage(usage=local_usage, unit=12, amount=3910585),
            UnitUsage(usage=local_usage, unit=13, amount=5637601),
            UnitUsage(usage=local_usage, unit=14, amount=6039332),
            UnitUsage(usage=local_usage, unit=15, amount=2260429),
            UnitUsage(usage=local_usage, unit=16, amount=4273001),
        ]
        UnitUsage.objects.bulk_create(unit_usages)

        with self.assertRaises(ValidationError) as context_manager:
            self.sc.current_usage = local_usage
            self.sc.full_clean()
        self.assertEqual(context_manager.exception.message_dict.get('current_usage'),
                         ['current_usage must be from same building as water_bill.building'])

    def test_current_usage_not_older_than_previous_usage(self) -> None:

        # Same day
        with self.assertRaises(ValidationError) as context_manager:
            self.sc.current_usage.register_date = self.pre_usage_jdate
            self.sc.full_clean()
        self.assertEqual(context_manager.exception.message_dict.get('current_usage'),
                         ['current usage must be older than previous usage'])
        # Yesterday
        with self.assertRaises(ValidationError) as context_manager:
            self.sc.current_usage.register_date = self.pre_usage_jdate - jdatetime.timedelta(days=1)
            self.sc.full_clean()
        self.assertEqual(context_manager.exception.message_dict.get('current_usage'),
                         ['current usage must be older than previous usage'])

    def test_sum_of_tax_and_extra_prices_property(self)-> None:
        # Test with gas_bill existence
        price = self.sc.water_bill.share_of_tax_for_each_unit + self.sc.extra_charges.aggregate(my_sum=Sum('amount'))['my_sum']
        price_with_gas = price + self.sc.gas_bill.share_of_price_for_each_unit

        self.assertEqual(self.sc.sum_of_tax_and_extra_prices, price_with_gas)

        # Test without gas_bill
        self.sc.gas_bill = None
        self.assertEqual(self.sc.sum_of_tax_and_extra_prices, price)

    def test_calculate_submeter_prices(self):
        building_units_count = self.sc.water_bill.building.units
        water_consumption_price = self.sc.water_bill.water_consumption_price
        usage_duration_days = (self.cur_usage.register_date - self.pre_usage.register_date).days
        extra_prices = self.sc.sum_of_tax_and_extra_prices
        debts = dict(self.sc.debts.values_list('unit', 'amount'))
        cur_unit_usages = self.cur_usage.unit_usages.all()
        pre_unit_usages = self.pre_usage.unit_usages.all()
        usage_list = []
        price_list = []
        unit_usage_price_collection = []
        price_with_ratio_list = []
        result_object = self.sc.results.create()
        unit_result_objects = []

        calculated_dict = self.sc.calculate_submeter_prices()
        
        for i in range(building_units_count):
            usage = cur_unit_usages[i].amount - pre_unit_usages[i].amount
            usage_list.append(usage)
        
            usage_30_days = usage * 30 / usage_duration_days

            price = round_price(ceil(
                (get_price_over_14_m3(usage_30_days) * (usage_duration_days / 30) * settings.CITY_COEFFICIENT) / 10
            ))
            price_list.append(price)

            unit_usage_price_collection.append([i+1, usage, price])

        price_difference_ratio = water_consumption_price / sum(price_list)

        for i in unit_usage_price_collection:
            price_with_ratio = round_price(ceil(i[2] * price_difference_ratio))
            price_with_ratio_list.append(price_with_ratio)

            unit_debt = debts.get(i[0]) or 0

            # todo create result objects
            unit_result_objects.append(
                UnitResult(result=result_object, unit=i[0], usage_amount=i[1], price=price_with_ratio,
                           debt=unit_debt, total_payment=price_with_ratio+extra_prices+unit_debt)
            )
            
        UnitResult.objects.bulk_create(unit_result_objects)

        self.assertListEqual(calculated_dict['usage_list'], usage_list)
        self.assertListEqual(calculated_dict['price_list'], price_list)
        self.assertEqual(calculated_dict['price_difference_ratio'], price_difference_ratio)
        self.assertListEqual(calculated_dict['price_with_ratio_list'], price_with_ratio_list)
        self.assertEqual(calculated_dict['extra_prices'], extra_prices)
        self.assertDictEqual(calculated_dict['debts'], debts)

        # Test result object
        self.assertEqual(result_object.submeter_calculator, self.sc)
        self.assertEqual(result_object.unit_results.count(), building_units_count)
        self.assertEqual(str(result_object), 'result of bill %s' % str((self.sc.water_bill)))
        
        # Test unti_result objects
        my_unit_results = self.sc.results.last().unit_results.all()
        for i in range(building_units_count):
            with self.subTest(i=i):
                unit_debt = debts.get(i+1) or 0
                unit_result = my_unit_results[i]
                self.assertEqual(unit_result.unit, unit_usage_price_collection[i][0])
                self.assertEqual(unit_result.usage_amount, unit_usage_price_collection[i][1])
                self.assertEqual(unit_result.price, price_with_ratio_list[i])
                self.assertEqual(unit_result.debt, unit_debt)
                self.assertEqual(unit_result.total_payment, price_with_ratio_list[i]+extra_prices+unit_debt)
    
    def test_str_magic_method(self) -> None:
        self.assertEqual(str(self.sc), 'calculate %s bill' % self.water_bill.issuance_date)

    def test_extra_charge_creation(self) -> None:
        charge, maintenance = self.sc.extra_charges.all()
        
        self.assertEqual(charge.title, 'charge')
        self.assertEqual(charge.amount, 30000)
        self.assertEqual(charge.my_order, 1)

        self.assertEqual(maintenance.title, 'maintenance')
        self.assertEqual(maintenance.amount, 50000)
        self.assertEqual(maintenance.my_order, 2)

    def test_extra_charge_invalid_amount(self) -> None:
        to_test = [-25400, -1, 0]

        for i in to_test:
            with self.subTest(i=i):
                with self.assertRaises(ValidationError) as context_manager:
                    charge = ExtraCharge(submeter_calculator=self.sc, title='repair', amount=i)
                    charge.full_clean()

    def test_extra_charge_str_magic_method(self) -> None:
        self.assertEqual(str(self.extras[1]), 'maintenance')

    def test_debt_creation(self) -> None:
        debts = self.sc.debts.all()

        self.assertEqual(debts[0].unit, 1)
        self.assertEqual(debts[0].amount, 5000)

        self.assertEqual(debts[1].unit, 9)
        self.assertEqual(debts[1].amount, 97500)

        self.assertEqual(debts[2].unit, 14)
        self.assertEqual(debts[2].amount, 246200)

    def test_debt_invalid_amount(self) -> None:
        to_test = [-25400, -1, 0]

        for i in to_test:
            with self.subTest(i=i):
                with self.assertRaises(ValidationError):
                    debt = Debt(submeter_calculator=self.sc, unit=5, amount=i)
                    debt.full_clean()

    def test_debt_str_magic_method(self) -> None:
        self.assertEqual(str(self.debts[2]), '14')

    def test_result_creation(self) -> None:
        self.assertEqual(self.result.submeter_calculator, self.sc)
        self.assertEqual(self.result.my_notes, 'This is my notes')
        self.assertEqual(self.result.client_notes, 'Notes for clint')
        self.assertEqual(self.result.due_date, self.jalali_date)
    
    def test_result_due_date_jalali_humanize_property(self) -> None:
        # With due_date
        self.assertEqual(self.result.due_date_jalali_humanize, self.jalali_date_month_name)

        # Without due_date
        local_result = Result.objects.create(submeter_calculator=self.sc, my_notes='This is my notes', client_notes='Notes for clint')
        self.assertEqual(local_result.due_date_jalali_humanize, None)

    def test_result_str_magic_method(self) -> None:
        self.assertEqual(str(self.result), 'result of bill %s' % str(self.sc.water_bill))

    def test_unit_result_str_magic_method(self) -> None:
        unit_result = self.unit_results[0]
        self.assertEqual(str(unit_result), str(unit_result.unit))
