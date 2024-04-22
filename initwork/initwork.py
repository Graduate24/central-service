import json
import os

from django.utils import timezone
from mongoengine import StringField, Document, ReferenceField, IntField, ListField, DateTimeField


class RuleCategory(Document):
    meta = {'collection': 'rule_category'}
    name = StringField(max_length=200, required=True)
    is_deleted = IntField(required=True, default=0)
    description = StringField()


class Rule(Document):
    meta = {'collection': 'rule'}
    name = StringField(required=True)
    cwe = StringField()
    category = ReferenceField(RuleCategory)
    engine = StringField(default='thusa')
    # 1, 低，2,中，3,高
    level = IntField(default=1)
    source = ListField(StringField(), default=[])
    sink = ListField(StringField(), default=[])
    is_deleted = IntField(required=True, default=0)
    # 0, 停用 1，启用
    status = IntField(required=True, default=1)
    default = IntField(required=True, default=0)
    description = StringField()
    date_created = DateTimeField(required=True, default=timezone.now)


class RuleTemplate(Document):
    meta = {'collection': 'rule_template'}
    name = StringField(required=True)
    is_deleted = IntField(required=True, default=0)
    engine = StringField(default='thusa')
    # 0, 停用 1，启用
    status = IntField(required=True, default=1)
    default = IntField(required=True, default=0)
    description = StringField()
    rules = ListField(ReferenceField(Rule))
    date_created = DateTimeField(required=True, default=timezone.now)


def init_rule(category):
    rules_list = []
    current_path = os.path.abspath(__file__)
    rule_file_path = os.path.join(os.path.dirname(current_path), 'init_rule.json')
    with open(rule_file_path, encoding='utf-8') as rules:
        init_rule = json.load(rules)
        for r in init_rule:
            rule = Rule(**r)
            rule.category = category
            rule.save()
            rules_list.append(rule.id)
        return rules_list


def init_rule_category():
    current_path = os.path.abspath(__file__)
    rule_category_file_path = os.path.join(os.path.dirname(current_path), 'init_rule_category.json')
    with open(rule_category_file_path, encoding='utf-8') as rule_categories:
        r = json.load(rule_categories)
        rule_category = RuleCategory(**r)
        rule_category.save()
        return rule_category


def init_rule_template(rules):
    current_path = os.path.abspath(__file__)
    rule_template_file_path = os.path.join(os.path.dirname(current_path), 'init_rule_template.json')
    with open(rule_template_file_path, encoding='utf-8') as rule_template:
        r = json.load(rule_template)
        template = RuleTemplate(**r)
        template.rules = rules
        template.save()
        return template


def init():
    count = RuleTemplate.objects(is_deleted=0, status=1).count()
    if count == 0:
        init_rule_template(init_rule(init_rule_category()))
