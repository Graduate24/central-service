from django.urls import path

from analysis.views import *
from monitor.views import MonitorView

urlpatterns = [
    path('clients', MonitorView.as_view()),

    path('rule', RuleView.as_view()),
    path('rule/list', RuleListView.as_view()),
    path('rule/<str:id>', RuleView.as_view()),
    path('ruletemplate', RuleTemplateView.as_view()),
    path('ruletemplate/list', RuleTemplateListView.as_view()),
    path('ruletemplate/list/tree', RuleTemplateTreeListView.as_view()),
    path('ruletemplate/<str:id>', RuleTemplateView.as_view()),
    path('rulecategory/list', RuleCategoryListView.as_view()),
    path('rulecategory', RuleCategoryView.as_view()),
    path('rulecategory/<str:id>', RuleCategoryView.as_view()),

    path('task/list', TaskListView.as_view()),
    path('task/<str:id>', TaskView.as_view()),
    path('task/<str:id>/reanalysis', TaskReanalysisView.as_view()),
    path('task/<str:id>/merge', TaskMergeView.as_view()),

    path('file/<str:id>/code', FileCodeView.as_view()),
    path('file/<str:id>/task', LocalCodeTaskView.as_view()),

    path('code/list', CodeListView.as_view()),
    path('code/<str:id>', CodeView.as_view()),
    path('code/<str:id>/task', CodeTaskView.as_view()),
    path('code/<str:id>/listdir', CodeDirectoryView.as_view()),
    path('codesource/<str:id>/<path:path>', CodeDataView.as_view()),

    path('task/<str:tid>/detectedresult/<str:id>/audit', AuditView.as_view()),

    path('project/list', ProjectListView.as_view()),
    path('project/<str:id>', ProjectDetailView.as_view()),
    path('project/<str:id>/task', ProjectTaskView.as_view()),
]
