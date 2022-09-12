from math import ceil

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from django_jalali.db import models as jmodels
from ckeditor_uploader.fields import RichTextUploadingField

from .functions import get_price_over_14_m3, round_price
from project.functions import datetime_farsi_month_name, date_farsi_month_name


class Created(models.Model):
    objects = jmodels.jManager()

    created = jmodels.jDateTimeField(auto_now_add=True, verbose_name=_('creation datetime'))

    class Meta:
        abstract = True

    @property
    def created_jalali_humanize(self) -> str:
        return datetime_farsi_month_name(self.created)
    created_jalali_humanize.fget.short_description = _('created')


class Building(Created):
    name = models.CharField(max_length=63, verbose_name=_('building name'))
    units = models.SmallIntegerField(validators=[MinValueValidator(2)], verbose_name=_('number of units'))

    class Meta:
        verbose_name = _('building')
        verbose_name_plural = _('buildings')

    def __str__(self) -> str:
        return self.name


class Usage(Created):
    objects = jmodels.jManager()

    building = models.ForeignKey(to=Building, on_delete=models.CASCADE, related_name='usages')
    last_update = jmodels.jDateTimeField(auto_now=True, verbose_name=_('last update'))
    register_date = jmodels.jDateField(verbose_name=_('date of registration'))

    class Meta:
        verbose_name = _('usage')
        verbose_name_plural = _('usages')

    def __str__(self) -> str:
        return str(self.register_date)

    @property
    def last_update_jalali_humanize(self) -> str:
        return datetime_farsi_month_name(self.last_update)
    last_update_jalali_humanize.fget.short_description = _('last update')

    @property
    def register_date_jalali_humanize(self) -> str:
        return date_farsi_month_name(self.register_date)
    register_date_jalali_humanize.fget.short_description = _('register date')


class UnitUsage(models.Model):
    usage = models.ForeignKey(to=Usage, on_delete=models.CASCADE, related_name='unit_usages')
    unit = models.PositiveSmallIntegerField(default=0, blank=False, null=False, verbose_name=_('unit number'))
    amount = models.PositiveIntegerField(verbose_name=_('amount in liter'))
    class Meta:
        verbose_name = _('usage of unit')
        verbose_name_plural = _('usage of units')
        ordering = ('unit',)
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='unit_usage_amout_gt_0',
                violation_error_message='Field amount must be greater than 0'
            )
        ]

    def __str__(self) -> str:
        return str(self.unit)


class BillBase(Created):
    objects = jmodels.jManager()
    issuance_date = jmodels.jDateField(verbose_name=_('issuance date'))
    current_reading = jmodels.jDateField(verbose_name=_('current reading'))
    payment_deadline = jmodels.jDateField(verbose_name=_('payment dead-line'))
    
    total_payment = models.PositiveIntegerField(verbose_name=_('total payment'), help_text=_('unit is Toman'))

    class Meta:
        abstract = True

    @property
    def issuance_date_jalali_humanize(self) -> str:
        return date_farsi_month_name(self.issuance_date)
    issuance_date_jalali_humanize.fget.short_description = _('issuance date')

    @property
    def current_reading_jalali_humanize(self) -> str:
        return date_farsi_month_name(self.current_reading)
    current_reading_jalali_humanize.fget.short_description = _('current reading')
    
    @property
    def payment_deadline_jalali_humanize(self) -> str:
        return date_farsi_month_name(self.payment_deadline)
    payment_deadline_jalali_humanize.fget.short_description = _('payment deadline')


class WaterBill(BillBase):
    building = models.ForeignKey(to=Building, on_delete=models.CASCADE, related_name='water_bills', verbose_name=_('building'))
    
    water_consumption_price = models.PositiveIntegerField(verbose_name=_('water consumption price'), help_text=_('unit is Toman'))
    

    class Meta:
        verbose_name = _('water bill')
        verbose_name_plural = _('water bills')
        constraints = [
            models.CheckConstraint(
                check=models.Q(water_consumption_price__gt=0),
                name='wb_wcp_gt_0',
                violation_error_message=_('Field water_consumption_price must be greater than 0')
            ),
            models.CheckConstraint(
                check=models.Q(total_payment__gt=0),
                name='wb_total_payment_gt_0',
                violation_error_message=_('Field total_payment must be greater than 0')
            ),
            models.CheckConstraint(
                check=models.Q(total_payment__gt=models.F('water_consumption_price')),
                name='wb_total_payment_gt_wcp',
                violation_error_message=_('total_payment must be greater than water_consumption_price')
            )
        ]

    def __str__(self) -> str:
        return _('%(building)s | %(issuance_date)s | %(total_payment)sT') % {'building': self.building, 'issuance_date': self.issuance_date, 'total_payment': format(self.total_payment, ',d')}

    @property
    def tax(self) -> int:
        return self.total_payment - self.water_consumption_price

    @property
    def share_of_tax_for_each_unit(self) -> int:
        """
        Get share of each unit of tax
        """
        return round_price(ceil(self.tax/self.building.units))
    
class GasBill(BillBase):
    building = models.ForeignKey(to=Building, on_delete=models.CASCADE, related_name='gas_bills')

    class Meta:
        verbose_name = _('gas bill')
        verbose_name_plural = _('gas bills')
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_payment__gt=0),
                name='gb_total_payment_gt_0',
                violation_error_message=_('Field total payment must be greater than 0')
            )
        ]

    def __str__(self) -> str:
        return _('%(building)s | %(issuance_date)s | %(total_payment)sT') % {'building': self.building, 'issuance_date': self.issuance_date, 'total_payment': format(self.total_payment, ',d')}

    @property
    def share_of_price_for_each_unit(self) -> int:
        """
        Get share of each unit of total_payment
        """
        return round_price(ceil(self.total_payment/self.building.units))


class SubmeterCalculator(Created):

    water_bill = models.OneToOneField(to=WaterBill, on_delete=models.CASCADE)
    gas_bill = models.OneToOneField(to=GasBill, on_delete=models.SET_NULL, blank=True, null=True)

    previous_usage = models.ForeignKey(to=Usage, on_delete=models.CASCADE, related_name='+',
                                       verbose_name=_('previous usage'))
    current_usage = models.ForeignKey(to=Usage, on_delete=models.CASCADE, related_name='+',
                                      verbose_name=_('current usage'))
    
    notes = models.TextField(blank=True, null=True, verbose_name=_('notes'))

    # todo property totals
    # todo price_difference_ratio ?

    class Meta:
        verbose_name = _('submeter calculator')
        verbose_name_plural = _('submeter calculators')

    def __str__(self) -> str:
        return 'calculate %s bill' % self.water_bill.issuance_date

    @property
    def sum_of_tax_and_extra_prices(self):
        price = self.water_bill.share_of_tax_for_each_unit + self.extra_charges.aggregate(my_sum=models.Sum('amount'))['my_sum']
        if self.gas_bill:
            price += self.gas_bill.share_of_price_for_each_unit
        return price

    def calculate_submeter_prices(self) -> dict:
        # Get unit usages objects
        previous_usages = self.previous_usage.unit_usages.all()
        current_usages = self.current_usage.unit_usages.all()

        water_consumption_price = self.water_bill.water_consumption_price
    
        # duration between current and previous usage 
        usage_duration_days = (self.current_usage.register_date - self.previous_usage.register_date).days

        # extra_prices
        extra_prices = self.sum_of_tax_and_extra_prices
        
        # debts, create a {unit: amount} dictionary
        debts = dict(self.debts.values_list('unit', 'amount'))

        usage_list = []
        price_list = []
        price_with_ratio_list = []

        # Create a result object
        # result_object = self.results.create()
        result_object = Result(submeter_calculator=self)
        
        # Respectively [unit, usage, rounded price] collection
        unit_usage_price_collection = []
        # Store UnitResult objects in a list for bulk_creation
        unit_result_objects = []

        for i in range(len(current_usages)):

            usage = current_usages[i].amount - previous_usages[i].amount
            usage_list.append(usage)
            # Our price table is for 30 days duration
            usage_30_days = (usage * 30) / usage_duration_days
            
            # Price from usage-price table * affect duration on price * price coefficient of the city
            # divide by 10 to get price as toman then ceiling to an integral at last reound it
            price = round_price(ceil(
                (get_price_over_14_m3(usage_30_days) * (usage_duration_days / 30) * settings.CITY_COEFFICIENT) / 10
                ))
            price_list.append(price)
            
            # unit_results.append(UnitResult(unit=i+1, usage_amount=usage, price=price, total_payment=price+extra_prices))
            unit_usage_price_collection.append([i+1, usage, price])

            print(f'unit: {i+1} usage: {usage} price {price:,}')

        sum_price_list = sum(price_list)

        print(f'\n\nPrice list: {price_list}\n\tsum: {sum_price_list:,} toman\n\twater_consumption_price: {water_consumption_price:,}')

        # Get difference ratio between actual water_consumption_price and our calculation
        price_difference_ratio = water_consumption_price / sum_price_list
        print(f'\n\n price difference: {price_difference_ratio} so multiply each price with it')

        # Multiply each price with price_difference_ratio to reach water_consumption_price
        for i in unit_usage_price_collection:
            price_with_ratio = round_price(ceil(i[2] * price_difference_ratio))
            price_with_ratio_list.append(price_with_ratio)

            # Get unit debt or zero
            unit_debt = debts.get(i[0]) or 0

            unit_result_objects.append(
                UnitResult(result=result_object, unit=i[0], usage_amount=i[1], price=price_with_ratio,
                           debt=unit_debt, total_payment=price_with_ratio+extra_prices+unit_debt)
            )

        print(f'\n\nNew price list: {price_with_ratio_list}\n\tsum: {sum(price_with_ratio_list):,} toman\n\twater_consumption_price: {water_consumption_price:,}')

        details = {
            'usage_list': usage_list,
            'price_list': price_list,
            'price_difference_ratio': price_difference_ratio,
            'price_with_ratio_list': price_with_ratio_list,
            'extra_prices': extra_prices,
            'debts': debts ,
            # 'result_object': result_object,
        }

        result_object.submeter_calculator_details = details
        result_object.save()
        UnitResult.objects.bulk_create(unit_result_objects)

        details['result_object'] = result_object
        return details

    def clean(self) -> None:
        building_units = self.water_bill.building.units
        if self.previous_usage.unit_usages.count() != self.water_bill.building.units:
            raise ValidationError({'previous_usage':_('previous usage must have same unit count as building units (%d)' % building_units)})

        if self.current_usage.unit_usages.count() != self.water_bill.building.units:
            raise ValidationError({'current_usage': _('current usage must have same unit count as building units (%d)' % building_units)}) 

        # Previous_usage should be for same building as water_bill.building
        if self.previous_usage.building != self.water_bill.building:
            raise ValidationError({'previous_usage': _('previous_usage must be from same building as water_bill.building')})

        # Current_usage should be for same building as water_bill.building
        if self.current_usage.building != self.water_bill.building:
            raise ValidationError({'current_usage': _('current_usage must be from same building as water_bill.building')})

        # Current usage must be older than previous usage
        if self.previous_usage.register_date >= self.current_usage.register_date:
            raise ValidationError({'current_usage': _('current usage must be older than previous usage')})
        

class ExtraCharge(models.Model):
    submeter_calculator = models.ForeignKey(to=SubmeterCalculator, on_delete=models.CASCADE,
                                            related_name='extra_charges')
    title = models.CharField(max_length=127, verbose_name=_('title'))
    amount = models.PositiveIntegerField(verbose_name=_('amount'), help_text=_('unit is Toman'))
    my_order = models.PositiveSmallIntegerField(default=0, blank=False, null=False, verbose_name=_('order'))

    class Meta:
        verbose_name = _('extra charge')
        verbose_name_plural = _('extra charges')
        ordering = ('my_order',)
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='extra_charge_amount_gt_0',
                violation_error_message=_('Field amount must be greater than 0')
            )
        ]

    def __str__(self) -> str:
        return self.title


class Debt(models.Model):
    submeter_calculator = models.ForeignKey(to=SubmeterCalculator, on_delete=models.CASCADE,
                                            related_name='debts')
    unit = models.PositiveSmallIntegerField(verbose_name=_('unit'))
    amount = models.PositiveIntegerField(verbose_name=_('amount'), help_text=_('unit is Toman'))

    class Meta:
        verbose_name = _('debt')
        verbose_name_plural = _('debts')
        ordering = ('unit',)
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='debt_amount_gt_0',
                violation_error_message=_('Field amount must be greater than 0')
            )
        ]
    def __str__(self) -> str:
        return str(self.unit)


class Result(Created):

    objects = jmodels.jManager()
    submeter_calculator = models.ForeignKey(to=SubmeterCalculator, on_delete=models.CASCADE,
                                            related_name='results')
    my_notes = models.TextField(blank=True, null=True, verbose_name=_('my notes'), help_text=_('Notes just for me'))
    client_notes = RichTextUploadingField(blank=True, null=True, verbose_name=_('client notes'), help_text=_('Notes for client; appears on final result page'))
    due_date = jmodels.jDateField(blank=True, null=True, verbose_name=_('due date'))
    submeter_calculator_details = models.JSONField(blank=True, null=True, verbose_name=_('submeter calculator details'))

    class Meta:
        verbose_name = _('result')
        verbose_name_plural = _('results')

    def __str__(self) -> str:
        return 'result of bill %s' % str(self.submeter_calculator.water_bill)

    @property
    def due_date_jalali_humanize(self) -> str:
        if self.due_date:
            return date_farsi_month_name(self.due_date)
        return None
    due_date_jalali_humanize.fget.short_description = _('due date')

class UnitResult(models.Model):

    result = models.ForeignKey(to=Result, on_delete=models.CASCADE, related_name='unit_results')
    unit = models.PositiveSmallIntegerField(default=0, blank=False, null=False, verbose_name=_('unit'))
    usage_amount = models.PositiveIntegerField(verbose_name=_('usage amount'), help_text=_('unit is liter'))
    price = models.PositiveIntegerField(verbose_name=_('price'), help_text=_('unit is Toman'))
    debt = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('debt'), help_text=_('unit is Toman'))
    total_payment = models.PositiveIntegerField(verbose_name=_('total payment'), help_text=_('unit is Toman'))

    class Meta:
        verbose_name = _('unit result')
        verbose_name_plural = _('units results')
        ordering = ('unit',)

    def __str__(self) -> str:
        return str(self.unit)
