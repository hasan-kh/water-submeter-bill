from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from django_jalali.db import models as jmodels

from project.functions import datetime_farsi_month_name, date_farsi_month_name


class Created(models.Model):
    objects = jmodels.jManager()

    created = jmodels.jDateTimeField(auto_now_add=True, verbose_name=_('creation datetime'))

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

    building_obj = models.ForeignKey(to=Building, on_delete=models.CASCADE, related_name='usages')
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
                name=_('Field amount must be greater than 0')
            )
        ]

    def __str__(self) -> str:
        return str(self.unit)