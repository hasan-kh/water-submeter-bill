from django.contrib import admin

from adminsortable2.admin import SortableStackedInline, SortableAdminBase

from .models import Building, Usage, UnitUsage


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
    list_display = ('id', 'register_date_jalali_humanize', 'building_obj', 'last_update_jalali_humanize', 'created_jalali_humanize')
    list_display_links = ('id', 'register_date_jalali_humanize')
    list_filter = ('register_date',)
    ordering = ('-register_date',)
    inlines = (UnitUsageInlineAdmin,)
