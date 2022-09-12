from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import redirect, reverse, render
from django.template.response import TemplateResponse
from adminsortable2.admin import SortableStackedInline, SortableTabularInline, SortableAdminBase

from .models import Building, Usage, UnitUsage, WaterBill, GasBill, SubmeterCalculator, ExtraCharge, Debt, Result, UnitResult


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'units', 'created_jalali_humanize')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    list_filter = ('created',)
    ordering = ('-created',)


class UnitUsageInlineAdmin(SortableStackedInline):
    model = UnitUsage
    fields = ('unit', 'amount')
    extra = 0


@admin.register(Usage)
class UsageAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ('id', 'register_date_jalali_humanize', 'building', 'last_update_jalali_humanize', 'created_jalali_humanize')
    list_display_links = ('id', 'register_date_jalali_humanize')
    list_filter = ('register_date',)
    ordering = ('-register_date',)
    inlines = (UnitUsageInlineAdmin,)


@admin.register(WaterBill)
class WaterBillAdmin(admin.ModelAdmin):
    list_display = ('id', 'issuance_date_jalali_humanize', 'total_payment_humanize', 'building', 'created_jalali_humanize')
    list_display_links = ('id', 'issuance_date_jalali_humanize')
    list_filter = ('created',)
    ordering = ('-issuance_date',)
    readonly_fields = ('tax_humanize', 'share_of_tax_for_each_unit_humanize')

    def total_payment_humanize(self, obj):
        return f'{obj.total_payment:,}'
    total_payment_humanize.short_description = _('total payment')

    def tax_humanize(self, obj):
        return f'{obj.tax:,}'
    tax_humanize.short_description = _('tax')

    def share_of_tax_for_each_unit_humanize(self, obj):
        return f'{obj.share_of_tax_for_each_unit:,}'
    share_of_tax_for_each_unit_humanize.short_description = _('share of tax for each unit')

    fieldsets = (
        (None, {
            'fields': ('building',)
        }),

        (_('Dates'), {
            'fields': ('issuance_date', 'current_reading', 'payment_deadline')
        }),

        (_('Prices'), {
            'fields': ('water_consumption_price', 'total_payment', 'tax_humanize', 'share_of_tax_for_each_unit_humanize')
        })
    )


@admin.register(GasBill)
class GasBillAdmin(admin.ModelAdmin):
    list_display = ('id', 'issuance_date_jalali_humanize', 'total_payment_humanize', 'building', 'created_jalali_humanize')
    list_display_links = ('id', 'issuance_date_jalali_humanize')
    list_filter = ('created',)
    ordering = ('-issuance_date',)
    readonly_fields = ('share_of_price_for_each_unit_humanize',)

    def total_payment_humanize(self, obj):
        return f'{obj.total_payment:,}'
    total_payment_humanize.short_description = _('total payment')

    def share_of_price_for_each_unit_humanize(self, obj):
        return f'{obj.share_of_price_for_each_unit:,}'
    share_of_price_for_each_unit_humanize.short_description = _('share of price for each unit')


    fieldsets = (
        (None, {
            'fields': ('building',)
        }),

        (_('Dates'), {
            'fields': ('issuance_date', 'current_reading', 'payment_deadline')
        }),

        (_('Prices'), {
            'fields': ('total_payment', 'share_of_price_for_each_unit_humanize')
        })
    )


class ExtraChargeInlineAdmin(SortableStackedInline):
    model = ExtraCharge
    fields = ('title', 'amount', 'my_order')
    extra = 0


class DebtInlineAdmin(admin.TabularInline):
    model = Debt
    fields = ('unit', 'amount')
    extra = 0


@admin.register(SubmeterCalculator)
class SubmeterCalculatorAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ('id', 'water_bill', 'current_usage', 'created_jalali_humanize')
    list_display_links = ('id', 'water_bill')
    list_filter = ('water_bill__issuance_date', 'created')
    raw_id_fields = ('water_bill', 'gas_bill', 'previous_usage', 'current_usage')
    ordering = ('-created',)
    inlines = (ExtraChargeInlineAdmin, DebtInlineAdmin)
    
    change_form_template = 'admin/submeter_change_form.html'

    def response_change(self, request, obj):
        if "_calculate_function" in request.POST:
            result_object = obj.calculate_submeter_prices()['result_object']
            self.message_user(request, _('Submeter prices calculated.'))
            return redirect('admin:building_result_change', result_object.id)

        return super().response_change(request, obj)


class UnitResultInlineAdmin(SortableTabularInline):
    model = UnitResult
    extra = 0


@admin.register(Result)
class ResultAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ('id', 'created_jalali_humanize', 'due_date_jalali_humanize')
    list_display_links = ('id',)
    list_filter = ('created',)
    ordering = ('-created',)
    raw_id_fields = ('submeter_calculator',)
    inlines = (UnitResultInlineAdmin,)
    readonly_fields = ('id', 'submeter_calculator_details_pretty_print')
    fields = ('id', 'submeter_calculator', 'due_date', 'my_notes', 'client_notes', 'submeter_calculator_details', 'submeter_calculator_details_pretty_print')

    change_form_template = 'admin/result_change_form.html'

    def submeter_calculator_details_pretty_print(self, obj):
        return '\n'.join([f'{key}: {value}' for key,value in obj.submeter_calculator_details.items()])
        # return obj.submeter_calculator_details


    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('printable_result/<int:result_id>/', self.admin_site.admin_view(self.printable_result_view), name='building_result_printable_result'),
        ]
        return my_urls + urls

    def printable_result_view(self, request, result_id):

        result = Result.objects.get(id=result_id)
        context = {
            'result': result,
            'sc': result.submeter_calculator,
            'water_bill': result.submeter_calculator.water_bill,
            'gas_bill': result.submeter_calculator.gas_bill,
        }
        return TemplateResponse(request, 'building/printable_result.html', context=context)

    def response_change(self, request, obj):
        if '_printable_result' in request.POST:
            return redirect('admin:building_result_printable_result', obj.id)
    
        return super().response_change(request, obj)
